from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
import time

import requests

from backend.data_collectors.providers.base_provider import BaseMarketDataProvider, ProviderError
from backend.models import DailyQuote, FundamentalSnapshot, StockBasic


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("-", "", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_code(code: str) -> str:
    if "." in code:
        return code
    if code.startswith(("600", "601", "603", "605", "688", "689")):
        return f"{code}.SH"
    return f"{code}.SZ"


class EastmoneyProvider(BaseMarketDataProvider):
    provider_name = "eastmoney"
    spot_url = "https://82.push2.eastmoney.com/api/qt/clist/get"
    stock_url = "https://push2.eastmoney.com/api/qt/stock/get"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://quote.eastmoney.com/",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Cache-Control": "no-cache",
        "Pragma": "no-cache",
        "Connection": "close",
    }
    stock_fields = "f43,f44,f45,f46,f47,f48,f57,f58,f168,f169,f170"
    quote_request_retries = 3

    def _request_spot(self) -> list[dict]:
        params = {
            "pn": "1",
            "pz": "6000",
            "po": "1",
            "np": "1",
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": "2",
            "invt": "2",
            "fid": "f3",
            "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
            "fields": "f12,f14,f2,f3,f5,f6,f8,f15,f16,f17,f20,f21",
        }
        try:
            with requests.Session() as session:
                response = session.get(self.spot_url, params=params, headers=self.headers, timeout=20)
                response.raise_for_status()
                payload = response.json()
        except Exception as exc:  # pragma: no cover - external IO
            raise ProviderError(f"eastmoney spot fetch failed: {exc}") from exc

        diff = payload.get("data", {}).get("diff")
        if not diff:
            raise ProviderError("eastmoney returned empty spot payload")
        return diff

    @staticmethod
    def _secid_for_code(stock_code: str) -> str:
        code = stock_code.split(".")[0]
        market = "1" if stock_code.endswith(".SH") else "0"
        return f"{market}.{code}"

    def _request_single_quote(self, stock_code: str) -> DailyQuote | None:
        params = {
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "invt": "2",
            "fltt": "2",
            "secid": self._secid_for_code(stock_code),
            "fields": self.stock_fields,
        }
        headers = self.headers | {
            "Referer": f"https://quote.eastmoney.com/{stock_code.lower().replace('.', '')}.html",
        }
        payload = None
        for attempt in range(self.quote_request_retries):
            try:
                response = requests.get(self.stock_url, params=params, headers=headers, timeout=20)
                response.raise_for_status()
                payload = response.json()
                break
            except Exception:
                if attempt == self.quote_request_retries - 1:
                    return None
                time.sleep(0.4 * (attempt + 1))

        data = payload.get("data")
        if not data:
            return None
        close = _safe_float(data.get("f43"))
        if close <= 0:
            return None
        return DailyQuote(
            stock_code=stock_code,
            trade_date="",
            open=_safe_float(data.get("f46"), close) or close,
            high=_safe_float(data.get("f44"), close) or close,
            low=_safe_float(data.get("f45"), close) or close,
            close=close,
            volume=_safe_float(data.get("f47")),
            amount=_safe_float(data.get("f48")),
            turnover_rate=0.0,
            pct_chg=_safe_float(data.get("f170"), _safe_float(data.get("f168"))),
            ma5=close,
            ma10=close,
            ma20=close,
            ma60=close,
        )

    def fetch_stock_basics(self) -> list[StockBasic]:
        diff = self._request_spot()
        items: list[StockBasic] = []
        for row in diff:
            code = _normalize_code(str(row.get("f12", "")).zfill(6))
            name = str(row.get("f14", ""))
            close = _safe_float(row.get("f2"))
            items.append(
                StockBasic(
                    stock_code=code,
                    stock_name=name,
                    exchange="SH" if code.endswith(".SH") else "SZ",
                    industry="",
                    concepts="",
                    market_cap=_safe_float(row.get("f20")),
                    float_market_cap=_safe_float(row.get("f21")),
                    is_st="ST" in name.upper(),
                    list_date="2000-01-01",
                    status="active" if close > 0 else "halted",
                    avg_amount_20d=_safe_float(row.get("f6")),
                    is_suspended=close <= 0,
                )
            )
        return items

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        quotes: list[DailyQuote] = []
        max_workers = min(4, max(1, len(stock_codes)))
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_map = {executor.submit(self._request_single_quote, stock_code): stock_code for stock_code in stock_codes}
            for future in as_completed(future_map):
                quote = future.result()
                if quote is None:
                    continue
                quote.trade_date = trade_date
                quotes.append(quote)
        if not quotes:
            raise ProviderError("eastmoney returned empty daily quotes")
        return quotes

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        return []
