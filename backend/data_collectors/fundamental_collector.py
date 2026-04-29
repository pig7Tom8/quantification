from __future__ import annotations

from datetime import date

from backend.data_collectors.providers.base_provider import BaseMarketDataProvider
from backend.db.repository import Database
from backend.models import StockBasic


class FundamentalCollector:
    def __init__(self, provider: BaseMarketDataProvider, database: Database) -> None:
        self.provider = provider
        self.database = database

    def collect(self, trade_date: date, tradable_stocks: list[StockBasic]) -> None:
        fundamentals = self.provider.fetch_fundamentals(
            stock_codes=[item.stock_code for item in tradable_stocks],
            trade_date=trade_date.isoformat(),
        )
        if fundamentals:
            self.database.upsert_fundamentals(fundamentals)
