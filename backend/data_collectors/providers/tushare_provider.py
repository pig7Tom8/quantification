from __future__ import annotations

from backend.config import settings
from backend.data_collectors.providers.base_provider import BaseMarketDataProvider, ProviderError
from backend.models import DailyQuote, FundamentalSnapshot, StockBasic


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("-", "", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class TushareProvider(BaseMarketDataProvider):
    provider_name = "tushare"

    def __init__(self) -> None:
        if not settings.tushare_token:
            raise ProviderError("tushare token missing")
        try:
            import tushare as ts
        except ImportError as exc:
            raise ProviderError("tushare package not installed") from exc
        self.pro = ts.pro_api(settings.tushare_token)

    def fetch_stock_basics(self) -> list[StockBasic]:
        try:
            frame = self.pro.stock_basic(
                exchange="",
                list_status="L",
                fields="ts_code,symbol,name,area,industry,list_date",
            )
        except Exception as exc:
            raise ProviderError(f"tushare stock_basic fetch failed: {exc}") from exc

        if frame.empty:
            raise ProviderError("tushare returned empty stock basics")

        items: list[StockBasic] = []
        for _, row in frame.iterrows():
            ts_code = str(row.get("ts_code", "")).strip()
            if not ts_code:
                continue
            list_date = str(row.get("list_date", "")).strip()
            if len(list_date) == 8:
                list_date = f"{list_date[:4]}-{list_date[4:6]}-{list_date[6:]}"
            items.append(
                StockBasic(
                    stock_code=ts_code,
                    stock_name=str(row.get("name", "")).strip(),
                    exchange=ts_code.split(".")[-1],
                    industry=str(row.get("industry", "")).strip(),
                    concepts="",
                    market_cap=0.0,
                    float_market_cap=0.0,
                    is_st="ST" in str(row.get("name", "")).upper(),
                    list_date=list_date or "2000-01-01",
                    status="active",
                    avg_amount_20d=0.0,
                    is_suspended=False,
                )
            )
        if not items:
            raise ProviderError("tushare returned no usable stock basics")
        return items

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        trade_date_compact = trade_date.replace("-", "")
        symbols = {code.split(".")[0]: code for code in stock_codes}
        quotes: list[DailyQuote] = []
        try:
            frame = self.pro.daily(trade_date=trade_date_compact)
        except Exception as exc:
            raise ProviderError(f"tushare daily fetch failed: {exc}") from exc
        if frame.empty:
            raise ProviderError("tushare returned empty daily quotes")

        for _, row in frame.iterrows():
            ts_code = str(row.get("ts_code", "")).strip()
            if ts_code not in stock_codes:
                continue
            close = _safe_float(row.get("close"))
            quotes.append(
                DailyQuote(
                    stock_code=ts_code,
                    trade_date=trade_date,
                    open=_safe_float(row.get("open"), close),
                    high=_safe_float(row.get("high"), close),
                    low=_safe_float(row.get("low"), close),
                    close=close,
                    volume=_safe_float(row.get("vol")),
                    amount=_safe_float(row.get("amount")) * 1000,
                    turnover_rate=0.0,
                    pct_chg=_safe_float(row.get("pct_chg")),
                    ma5=close,
                    ma10=close,
                    ma20=close,
                    ma60=close,
                )
            )
        if not quotes:
            raise ProviderError("tushare returned no usable daily quotes")
        return quotes

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        return []
