from __future__ import annotations

import sqlite3
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.pipeline import run_phase0_pipeline
from backend.scheduler import DailySchedulerService

DB_PATH = PROJECT_ROOT / "data" / "quant_mvp.db"
REPORT_PATH = PROJECT_ROOT / "output" / "reports" / f"daily_report_{date.today().isoformat()}.md"


def query_count(connection: sqlite3.Connection, table: str) -> int:
    return connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]


def main() -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    if REPORT_PATH.exists():
        REPORT_PATH.unlink()

    first_result = run_phase0_pipeline()
    second_result = run_phase0_pipeline()

    assert first_result.stock_count == 5, f"unexpected tradable stock count: {first_result.stock_count}"
    assert first_result.excluded_count == 1, f"unexpected excluded count: {first_result.excluded_count}"
    assert first_result.quote_count == 5, f"unexpected quote count: {first_result.quote_count}"
    assert first_result.data_confidence == "high", f"unexpected data confidence: {first_result.data_confidence}"
    assert first_result.market_data_status == "complete", f"unexpected market data status: {first_result.market_data_status}"
    assert "missing=0" in first_result.quality_summary, f"unexpected quality summary: {first_result.quality_summary}"
    assert first_result.report_path == str(REPORT_PATH), "unexpected report path"
    assert second_result.stock_count == first_result.stock_count, "rerun changed tradable stock count"
    assert second_result.quote_count == first_result.quote_count, "rerun changed quote count"

    assert DB_PATH.exists(), "database file was not created"
    assert REPORT_PATH.exists(), "report file was not created"

    with sqlite3.connect(DB_PATH) as connection:
        assert query_count(connection, "stock_basic") == 6, "stock_basic count mismatch"
        assert query_count(connection, "daily_quote") == 5, "daily_quote count mismatch"
        st_rows = connection.execute(
            "SELECT COUNT(*) FROM stock_basic WHERE stock_code = '603000.SH'"
        ).fetchone()[0]
        assert st_rows == 1, "full stock basic snapshot should include excluded stocks"

    report_text = REPORT_PATH.read_text(encoding="utf-8")
    assert "603000.SH" in report_text, "excluded ST stock should appear in report"
    assert "当前运行使用 mock provider。" in report_text, "mock provider note missing from report"
    assert "数据可信度评级" in report_text, "data confidence section missing from report"
    assert "数据质量摘要" in report_text, "data quality summary missing from report"

    scheduler = DailySchedulerService()
    scheduled_for_today = datetime.combine(date.today(), scheduler.daily_time)
    before_window = scheduled_for_today - timedelta(minutes=1)
    next_run_before = scheduler.compute_next_run(before_window)
    assert next_run_before.date() == date.today(), "next run should stay on the same day before schedule"
    scheduled_result = scheduler.run_pending(scheduled_for_today)
    assert scheduled_result is not None, "daily scheduler should run when scheduled time is reached"
    duplicate_result = scheduler.run_pending(scheduled_for_today + timedelta(minutes=1))
    assert duplicate_result is None, "daily scheduler should not rerun on the same day"

    print("Phase 0 acceptance checks passed.")


if __name__ == "__main__":
    main()
