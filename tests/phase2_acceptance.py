from __future__ import annotations

import sqlite3
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_collectors.providers.mock_provider import MockMarketDataProvider
from backend.db.repository import Database
from backend.factors.crowding_factor import downgrade_rating_for_crowding
from backend.pipeline import run_phase0_pipeline


def _fetch_count(db_path: Path, table: str, trade_date: str) -> int:
    with sqlite3.connect(db_path) as connection:
        return connection.execute(
            f"SELECT COUNT(*) FROM {table} WHERE trade_date = ?",
            (trade_date,),
        ).fetchone()[0]


def _fetch_one(db_path: Path, sql: str, params: tuple[object, ...]) -> sqlite3.Row:
    with sqlite3.connect(db_path) as connection:
        connection.row_factory = sqlite3.Row
        row = connection.execute(sql, params).fetchone()
    assert row is not None
    return row


def main() -> None:
    assert downgrade_rating_for_crowding("S", "高拥挤") == "A"
    assert downgrade_rating_for_crowding("A", "高拥挤") == "B"
    assert downgrade_rating_for_crowding("S", "极高拥挤") == "S"
    assert downgrade_rating_for_crowding("B", "中拥挤") == "B"

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "phase2.db"
        database = Database(db_path=db_path)
        result = run_phase0_pipeline(
            provider=MockMarketDataProvider(),
            database=database,
        )
        trade_date = result.trade_date.isoformat()

        assert result.market_state in {"进攻", "震荡", "防守"}
        assert _fetch_count(db_path, "market_state_daily", trade_date) == 1
        assert _fetch_count(db_path, "concept_crowding_daily", trade_date) > 0

        market_state = _fetch_one(
            db_path,
            """
            SELECT market_state, up_count, down_count, total_amount, reason
            FROM market_state_daily
            WHERE trade_date = ?
            """,
            (trade_date,),
        )
        assert market_state["market_state"] in {"进攻", "震荡", "防守"}
        assert market_state["up_count"] > market_state["down_count"]
        assert market_state["total_amount"] > 0
        assert market_state["reason"]

        crowded_concept = _fetch_one(
            db_path,
            """
            SELECT concept_name, crowding_level, amount_ratio
            FROM concept_crowding_daily
            WHERE trade_date = ?
            ORDER BY amount_ratio DESC
            LIMIT 1
            """,
            (trade_date,),
        )
        assert crowded_concept["crowding_level"] in {"中拥挤", "高拥挤", "极高拥挤"}
        assert crowded_concept["amount_ratio"] > 0

        adjusted_score = _fetch_one(
            db_path,
            """
            SELECT stock_code, crowding_adjustment, reason
            FROM factor_score
            WHERE trade_date = ? AND crowding_adjustment < 0
            ORDER BY crowding_adjustment ASC
            LIMIT 1
            """,
            (trade_date,),
        )
        assert adjusted_score["crowding_adjustment"] < 0
        assert "拥挤" in adjusted_score["reason"]

        signal = _fetch_one(
            db_path,
            """
            SELECT reason
            FROM strategy_signals
            WHERE trade_date = ? AND signal_type = 'top50'
            LIMIT 1
            """,
            (trade_date,),
        )
        assert "市场" in signal["reason"]

        assert result.factor_report_path is not None
        report_text = Path(result.factor_report_path).read_text(encoding="utf-8")
        assert "市场状态" in report_text
        assert "题材拥挤度提醒" in report_text
        assert "| 股票代码 | 股票名称 | 总分 |" in report_text
        assert "| 002594.SZ | 比亚迪 |" in report_text

    print("Phase 2 acceptance checks passed.")


if __name__ == "__main__":
    main()
