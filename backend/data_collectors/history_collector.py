from __future__ import annotations

from datetime import date, timedelta

from backend.config import settings
from backend.db.repository import Database
from backend.models import DailyQuote


def _safe_float(value: object, default: float = 0.0) -> float:
    try:
        if value in ("-", "", None):
            return default
        return float(value)
    except (TypeError, ValueError):
        return default


class HistoricalQuoteCollector:
    def __init__(self, database: Database) -> None:
        self.database = database

    def collect_tushare_daily_history(
        self,
        trade_date: date,
        stock_codes: list[str],
        target_trade_days: int = 60,
        lookback_calendar_days: int = 120,
    ) -> int:
        if not settings.tushare_token or not stock_codes:
            return 0
        try:
            import tushare as ts
        except ImportError:
            return 0

        pro = ts.pro_api(settings.tushare_token)
        requested = set(stock_codes)
        collected_days = 0
        inserted_quotes = 0
        for offset in range(1, lookback_calendar_days + 1):
            day = trade_date - timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            day_text = day.isoformat()
            existing = self.database.fetch_daily_quotes_for_date(day_text)
            if existing:
                collected_days += 1
                if collected_days >= target_trade_days:
                    break
                continue

            try:
                frame = pro.daily(trade_date=day.strftime("%Y%m%d"))
            except Exception:
                continue
            if frame.empty:
                continue

            quotes: list[DailyQuote] = []
            for _, row in frame.iterrows():
                stock_code = str(row.get("ts_code", "")).strip()
                if stock_code not in requested:
                    continue
                close = _safe_float(row.get("close"))
                quotes.append(
                    DailyQuote(
                        stock_code=stock_code,
                        trade_date=day_text,
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
            if quotes:
                self.database.upsert_daily_quotes(quotes)
                inserted_quotes += len(quotes)
                collected_days += 1
            if collected_days >= target_trade_days:
                break
        return inserted_quotes
