from __future__ import annotations

from datetime import datetime
from functools import lru_cache

import requests

import akshare as ak

from backend.data_collectors.providers.base_provider import BaseMarketDataProvider, ProviderError
from backend.models import DailyQuote, FundamentalSnapshot, StockBasic


def _full_stock_code(code: str) -> str:
    if code.startswith(("600", "601", "603", "605", "688", "689")):
        return f"{code}.SH"
    return f"{code}.SZ"


def _exchange_from_code(code: str) -> str:
    return "SH" if code.endswith(".SH") else "SZ"


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("-", "", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class AkshareProvider(BaseMarketDataProvider):
    provider_name = "akshare"

    def _load_spot(self):
        try:
            return ak.stock_zh_a_spot()
        except Exception as exc:  # pragma: no cover - depends on external service
            raise ProviderError(f"akshare spot fetch failed: {exc}") from exc

    @staticmethod
    @lru_cache(maxsize=1)
    def _load_industry_map() -> dict[str, str]:
        industry_map: dict[str, str] = {}
        try:
            sz_frame = ak.stock_info_sz_name_code(symbol="A股列表")
            for _, row in sz_frame.iterrows():
                code = str(row.get("A股代码", "")).strip().zfill(6)
                industry = str(row.get("所属行业", "")).strip()
                if code and industry:
                    industry_map[f"{code}.SZ"] = industry
        except Exception:
            pass

        sh_headers = {
            "Host": "query.sse.com.cn",
            "Pragma": "no-cache",
            "Referer": "https://www.sse.com.cn/assortment/stock/list/share/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/81.0.4044.138 Safari/537.36"
            ),
        }
        sh_base_params = {
            "REG_PROVINCE": "",
            "CSRC_CODE": "",
            "STOCK_CODE": "",
            "sqlId": "COMMON_SSE_CP_GPJCTPZ_GPLB_GP_L",
            "COMPANY_STATUS": "2,4,5,7,8",
            "type": "inParams",
            "isPagination": "true",
            "pageHelp.cacheSize": "1",
            "pageHelp.beginPage": "1",
            "pageHelp.pageSize": "10000",
            "pageHelp.pageNo": "1",
            "pageHelp.endPage": "1",
        }
        for stock_type in ("1", "8"):
            try:
                response = requests.get(
                    "https://query.sse.com.cn/sseQuery/commonQuery.do",
                    params=sh_base_params | {"STOCK_TYPE": stock_type},
                    headers=sh_headers,
                    timeout=20,
                )
                response.raise_for_status()
                payload = response.json()
                for row in payload.get("result", []):
                    code = str(row.get("A_STOCK_CODE", "")).strip().zfill(6)
                    industry = str(row.get("CSRC_CODE_DESC", "")).strip()
                    if code and industry:
                        industry_map[f"{code}.SH"] = industry
            except Exception:
                continue
        return industry_map

    def fetch_stock_basics(self) -> list[StockBasic]:
        frame = self._load_spot()
        industry_map = self._load_industry_map()
        items: list[StockBasic] = []
        for _, row in frame.iterrows():
            raw_code = str(row["代码"]).strip()
            if raw_code.startswith(("sh", "sz", "bj")):
                code = raw_code[2:].zfill(6)
            else:
                code = raw_code.zfill(6)
            code = _full_stock_code(code)
            name = str(row["名称"])
            amount = _safe_float(row.get("成交额"))
            items.append(
                StockBasic(
                    stock_code=code,
                    stock_name=name,
                    exchange=_exchange_from_code(code),
                    industry=industry_map.get(code, ""),
                    concepts="",
                    market_cap=0.0,
                    is_st="ST" in name.upper(),
                    list_date="2000-01-01",
                    status="active" if _safe_float(row.get("最新价")) > 0 else "halted",
                    avg_amount_20d=amount,
                    is_suspended=_safe_float(row.get("最新价")) <= 0,
                )
            )
        if not items:
            raise ProviderError("akshare returned empty stock basics")
        return items

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        frame = self._load_spot()
        lookup = {}
        for _, row in frame.iterrows():
            raw_code = str(row["代码"]).strip()
            if raw_code.startswith(("sh", "sz", "bj")):
                normalized = _full_stock_code(raw_code[2:].zfill(6))
            else:
                normalized = _full_stock_code(raw_code.zfill(6))
            lookup[normalized] = row
        quotes: list[DailyQuote] = []
        for stock_code in stock_codes:
            row = lookup.get(stock_code)
            if row is None:
                continue
            close = _safe_float(row.get("最新价"))
            open_price = _safe_float(row.get("今开"), close)
            high = _safe_float(row.get("最高"), close)
            low = _safe_float(row.get("最低"), close)
            quotes.append(
                DailyQuote(
                    stock_code=stock_code,
                    trade_date=trade_date,
                    open=open_price or close,
                    high=high or close,
                    low=low or close,
                    close=close,
                    volume=_safe_float(row.get("成交量")),
                    amount=_safe_float(row.get("成交额")),
                    turnover_rate=_safe_float(row.get("换手率")),
                    pct_chg=_safe_float(row.get("涨跌幅")),
                    ma5=close,
                    ma10=close,
                    ma20=close,
                    ma60=close,
                )
            )
        if not quotes:
            raise ProviderError("akshare returned empty daily quotes")
        return quotes

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        snapshots: list[FundamentalSnapshot] = []
        today = datetime.strptime(trade_date, "%Y-%m-%d").strftime("%Y%m%d")
        for stock_code in stock_codes[:50]:
            symbol = stock_code.split(".")[0]
            try:
                frame = ak.stock_financial_analysis_indicator(symbol=symbol)
            except Exception:
                continue
            if frame.empty:
                continue
            row = frame.iloc[0]
            snapshots.append(
                FundamentalSnapshot(
                    stock_code=stock_code,
                    trade_date=trade_date,
                    revenue_yoy=_safe_float(row.get("主营业务收入增长率(%)"), None),
                    net_profit_yoy=_safe_float(row.get("净利润增长率(%)"), None),
                    roe=_safe_float(row.get("净资产收益率(%)"), None),
                    gross_margin=_safe_float(row.get("销售毛利率(%)"), None),
                    debt_ratio=_safe_float(row.get("资产负债率(%)"), None),
                    operating_cashflow=_safe_float(row.get("每股经营性现金流(元)"), None),
                    goodwill=None,
                    source_status="fresh" if today else "fresh",
                )
            )
        return snapshots
