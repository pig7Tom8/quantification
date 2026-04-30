from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_collectors.providers.base_provider import BaseMarketDataProvider, ProviderError
from backend.data_collectors.providers.fallback_provider import FallbackMarketDataProvider
from backend.models import DailyQuote, FundamentalSnapshot, StockBasic


class AkshareFailingProvider(BaseMarketDataProvider):
    provider_name = "akshare"

    def fetch_stock_basics(self) -> list[StockBasic]:
        raise ProviderError("akshare unavailable")

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        raise ProviderError("akshare quote unavailable")

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        raise ProviderError("akshare fundamentals unavailable")


class TushareFailingProvider(BaseMarketDataProvider):
    provider_name = "tushare"

    def fetch_stock_basics(self) -> list[StockBasic]:
        raise ProviderError("tushare unavailable")

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        raise ProviderError("tushare quote unavailable")

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        raise ProviderError("tushare fundamentals unavailable")


class EastmoneyBackupProvider(BaseMarketDataProvider):
    provider_name = "eastmoney"

    def fetch_stock_basics(self) -> list[StockBasic]:
        return [
            StockBasic(
                stock_code="000001.SZ",
                stock_name="平安银行",
                exchange="SZ",
                industry="银行",
                concepts="金融",
                market_cap=1.0,
                float_market_cap=1.0,
                is_st=False,
                list_date="2000-01-01",
                status="active",
                avg_amount_20d=100000000.0,
            )
        ]

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        return [
            DailyQuote(
                stock_code="000001.SZ",
                trade_date=trade_date,
                open=10.0,
                high=10.5,
                low=9.9,
                close=10.2,
                volume=1000.0,
                amount=1000000.0,
                turnover_rate=1.2,
                pct_chg=1.0,
                ma5=10.2,
                ma10=10.2,
                ma20=10.2,
                ma60=10.2,
            )
        ]

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        return []


def main() -> None:
    sleep_calls: list[int] = []
    provider = FallbackMarketDataProvider(
        providers=[AkshareFailingProvider(), TushareFailingProvider(), EastmoneyBackupProvider()],
        retry_delays=(10, 60, 0),
        sleeper=sleep_calls.append,
    )
    stocks = provider.fetch_stock_basics()
    assert provider.last_provider_name == "eastmoney", "eastmoney should take over after akshare and tushare fail"
    assert len(provider.last_warnings) == 6, "warnings should record three akshare and three tushare failures"
    assert provider.last_warnings[0].startswith("akshare:"), "first fallback warning should come from akshare"
    assert provider.last_warnings[3].startswith("tushare:"), "tushare warnings should appear after akshare retries"
    assert sleep_calls == [10, 60, 10, 60], "retry cadence should follow 10s then 60s before switching source"
    assert provider.attempt_log[:3] == [
        "akshare:fetch_stock_basics:attempt1",
        "akshare:fetch_stock_basics:attempt2",
        "akshare:fetch_stock_basics:attempt3",
    ], "akshare should be retried three times before switching"
    quotes = provider.fetch_daily_quotes(["000001.SZ"], "2026-04-29")
    assert quotes and provider.last_provider_name == "eastmoney", "eastmoney should serve daily quotes after fallback"
    fundamentals = provider.fetch_fundamentals(["000001.SZ"], "2026-04-29")
    assert fundamentals == [], "fundamentals should degrade to empty list when unavailable"
    print("Provider fallback checks passed.")


if __name__ == "__main__":
    main()
