from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from backend.data_collectors.providers.base_provider import BaseMarketDataProvider, ProviderError
from backend.db.repository import Database
from backend.models import DailyQuote
from backend.stock_pool import PoolFilterResult, filter_tradable_stocks


@dataclass
class QuoteCollectionResult:
    filter_result: PoolFilterResult
    quotes: list[DailyQuote]
    stock_basic_source_status: str
    quote_source_status: str
    warnings: tuple[str, ...] = ()
    historical_quotes: tuple[DailyQuote, ...] = ()


class QuoteCollector:
    def __init__(self, provider: BaseMarketDataProvider, database: Database) -> None:
        self.provider = provider
        self.database = database

    def collect(self, trade_date: date) -> QuoteCollectionResult:
        warnings: list[str] = []
        stock_basic_source_status = "fresh"
        if self.provider.provider_name == "tushare" and self.database.has_stock_basics_for_date(trade_date):
            stock_basics = self.database.fetch_latest_stock_basics()
            warnings.append("stock_basic_reuse:reuse database snapshot updated today")
        else:
            try:
                stock_basics = self.provider.fetch_stock_basics()
            except ProviderError as exc:
                stock_basics = self.database.fetch_latest_stock_basics()
                if not stock_basics:
                    raise
                stock_basic_source_status = "stale"
                warnings.append(f"stock_basic_fallback:{exc}")
        filter_result = filter_tradable_stocks(stock_basics, trade_date)

        self.database.upsert_stock_basics(stock_basics)
        stock_codes = [item.stock_code for item in filter_result.tradable]
        quote_source_status = "fresh"
        historical_quotes: tuple[DailyQuote, ...] = ()
        try:
            quotes = self.provider.fetch_daily_quotes(
                stock_codes=stock_codes,
                trade_date=trade_date.isoformat(),
            )
            self.database.upsert_daily_quotes(quotes)
        except ProviderError as exc:
            quotes = []
            quote_source_status = "stale"
            historical_quotes = tuple(
                self.database.fetch_latest_quotes_before(trade_date.isoformat(), stock_codes)
            )
            warnings.append(f"daily_quote_fallback:{exc}")
        return QuoteCollectionResult(
            filter_result=filter_result,
            quotes=quotes,
            stock_basic_source_status=stock_basic_source_status,
            quote_source_status=quote_source_status,
            warnings=tuple(warnings),
            historical_quotes=historical_quotes,
        )
