from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_collectors.data_quality_checker import DataQualityChecker
from backend.data_collectors.providers.base_provider import BaseMarketDataProvider, ProviderError
from backend.db.repository import Database
from backend.errors import PipelineExecutionError
from backend.models import DailyQuote, FundamentalSnapshot, StockBasic
from backend.pipeline import run_phase0_pipeline


def stock(code: str, avg_amount: float = 100000000.0, is_st: bool = False, list_date: str = "2000-01-01") -> StockBasic:
    return StockBasic(
        stock_code=code,
        stock_name=code,
        exchange=code.split(".")[-1],
        industry="行业",
        concepts="概念",
        market_cap=1000000000.0,
        is_st=is_st,
        list_date=list_date,
        status="active",
        avg_amount_20d=avg_amount,
        is_suspended=False,
    )


def quote(code: str, trade_date: str, close: float = 10.0, amount: float = 1000000.0) -> DailyQuote:
    return DailyQuote(
        stock_code=code,
        trade_date=trade_date,
        open=close,
        high=close + 0.5,
        low=close - 0.5,
        close=close,
        volume=1000.0,
        amount=amount,
        turnover_rate=1.0,
        pct_chg=1.0,
        ma5=close,
        ma10=close,
        ma20=close,
        ma60=close,
    )


class PartialQuoteProvider(BaseMarketDataProvider):
    provider_name = "partial"

    def fetch_stock_basics(self) -> list[StockBasic]:
        return [stock(f"{i:06d}.SZ") for i in range(1, 101)]

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        return [quote(code, trade_date) for code in stock_codes[:80]]

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        return []


class StockBasicFallbackProvider(BaseMarketDataProvider):
    provider_name = "stock-basic-fallback"

    def fetch_stock_basics(self) -> list[StockBasic]:
        raise ProviderError("stock basic source unavailable")

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        return [quote(code, trade_date) for code in stock_codes]

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        return []


class QuoteFallbackProvider(BaseMarketDataProvider):
    provider_name = "quote-fallback"

    def fetch_stock_basics(self) -> list[StockBasic]:
        return [stock("000001.SZ"), stock("000002.SZ")]

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        raise ProviderError("quote source unavailable")

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        return []


def make_temp_db(name: str) -> Database:
    db_path = PROJECT_ROOT / "data" / f"{name}.db"
    if db_path.exists():
        db_path.unlink()
    database = Database(db_path=db_path)
    database.initialize()
    return database


def run_incomplete_quote_case() -> None:
    database = make_temp_db("phase0_incomplete")
    try:
        run_phase0_pipeline(
            trade_date=date(2026, 4, 29),
            provider=PartialQuoteProvider(),
            database=database,
        )
        raise AssertionError("partial quote case should not allow formal output")
    except PipelineExecutionError as exc:
        assert "行情数据不完整" in str(exc)


def run_stock_basic_fallback_case() -> None:
    database = make_temp_db("phase0_stock_basic_fallback")
    database.upsert_stock_basics([stock("000001.SZ"), stock("000002.SZ")])
    result = run_phase0_pipeline(
        trade_date=date(2026, 4, 29),
        provider=StockBasicFallbackProvider(),
        database=database,
    )
    assert result.data_confidence == "medium", "stock basic fallback should downgrade confidence to medium"
    assert result.market_data_status == "complete", "stock basic fallback should still allow formal output"


def run_history_fallback_case() -> None:
    database = make_temp_db("phase0_history_fallback")
    database.upsert_stock_basics([stock("000001.SZ"), stock("000002.SZ")])
    database.upsert_daily_quotes(
        [
            quote("000001.SZ", "2026-04-28"),
            quote("000002.SZ", "2026-04-28"),
        ]
    )
    try:
        run_phase0_pipeline(
            trade_date=date(2026, 4, 29),
            provider=QuoteFallbackProvider(),
            database=database,
        )
        raise AssertionError("history fallback case should block formal output when today's key fields are missing")
    except PipelineExecutionError as exc:
        assert "行情数据不完整" in str(exc)
        assert "daily_quote_fallback" in str(exc)


def run_confidence_level_case() -> None:
    checker = DataQualityChecker()
    high = checker.evaluate([stock("000001.SZ")], [quote("000001.SZ", "2026-04-29")])
    medium = checker.evaluate(
        [stock("000001.SZ")],
        [quote("000001.SZ", "2026-04-29")],
        stock_basic_source_status="stale",
    )
    low = checker.evaluate([stock("000001.SZ"), stock("000002.SZ")], [quote("000001.SZ", "2026-04-29")])
    assert high.data_confidence == "high"
    assert medium.data_confidence == "medium"
    assert low.data_confidence == "low"


def main() -> None:
    run_incomplete_quote_case()
    run_stock_basic_fallback_case()
    run_history_fallback_case()
    run_confidence_level_case()
    print("Phase 0 stability checks passed.")


if __name__ == "__main__":
    main()
