from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_collectors.quote_collector import QuoteCollector
from backend.db.repository import Database
from backend.models import DailyQuote, FundamentalSnapshot, StockBasic


class ShouldNotCallTushareProvider:
    provider_name = "tushare"

    def fetch_stock_basics(self) -> list[StockBasic]:
        raise AssertionError("same-day stock basic snapshot should be reused before calling tushare stock_basic")

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        return [
            DailyQuote(
                stock_code=stock_codes[0],
                trade_date=trade_date,
                open=10.0,
                high=10.5,
                low=9.8,
                close=10.1,
                volume=1000.0,
                amount=1000000.0,
                turnover_rate=1.0,
                pct_chg=1.0,
                ma5=10.1,
                ma10=10.1,
                ma20=10.1,
                ma60=10.1,
            )
        ]

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        return []


def make_stock_basic(code: str = "000001.SZ", is_st: bool = False) -> StockBasic:
    return StockBasic(
        stock_code=code,
        stock_name="平安银行" if code == "000001.SZ" else "*ST示例",
        exchange=code.split(".")[-1],
        industry="银行",
        concepts="金融",
        market_cap=1.0,
        is_st=is_st,
        list_date="1991-04-03" if not is_st else "2010-05-10",
        status="active" if not is_st else "risk",
        avg_amount_20d=100000000.0 if not is_st else 1000000.0,
        is_suspended=False,
    )


def main() -> None:
    db_path = PROJECT_ROOT / "data" / "tushare_stock_basic_reuse_test.db"
    if db_path.exists():
        db_path.unlink()

    database = Database(db_path=db_path)
    database.initialize()
    database.upsert_stock_basics([make_stock_basic(), make_stock_basic("603000.SH", is_st=True)])

    collector = QuoteCollector(provider=ShouldNotCallTushareProvider(), database=database)
    result = collector.collect(date.today())

    assert result.stock_basic_source_status == "fresh"
    assert result.warnings[0].startswith("stock_basic_reuse:"), "same-day reuse should be recorded in warnings"
    assert len(result.filter_result.tradable) == 1, "stock pool filtering should still run after snapshot reuse"
    assert len(result.filter_result.excluded) == 1, "excluded stocks should remain visible after snapshot reuse"

    with database.connect() as connection:
        count = connection.execute("SELECT COUNT(*) FROM stock_basic").fetchone()[0]
        assert count == 2, "full stock basic snapshot should remain in storage"

    if db_path.exists():
        db_path.unlink()
    print("Tushare stock_basic reuse checks passed.")


if __name__ == "__main__":
    main()
