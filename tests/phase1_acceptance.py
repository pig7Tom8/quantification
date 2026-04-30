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
from backend.pipeline import run_phase0_pipeline
from backend.scoring.score_engine import rating_for_score


def _count_rows(db_path: Path, table: str, trade_date: str) -> int:
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
    assert rating_for_score(90, False) == "S"
    assert rating_for_score(75, False) == "A"
    assert rating_for_score(65, False) == "B"
    assert rating_for_score(50, False) == "C"
    assert rating_for_score(49, False) == "D"
    assert rating_for_score(90, True) == "R"

    with tempfile.TemporaryDirectory() as temp_dir:
        db_path = Path(temp_dir) / "phase1.db"
        database = Database(db_path=db_path)
        result = run_phase0_pipeline(
            provider=MockMarketDataProvider(),
            database=database,
        )
        trade_date = result.trade_date.isoformat()

        assert result.scored_count == 5
        assert result.top50_count == 5
        assert result.factor_report_path is not None
        assert Path(result.factor_report_path).exists()
        assert _count_rows(db_path, "factor_score", trade_date) == 5
        assert _count_rows(db_path, "strategy_signals", trade_date) == 5

        top = _fetch_one(
            db_path,
            """
            SELECT stock_code, trend_score, money_score, fundamental_score,
                   news_score, risk_score, crowding_adjustment, total_score, rating
            FROM factor_score
            WHERE trade_date = ?
            ORDER BY total_score DESC, stock_code ASC
            LIMIT 1
            """,
            (trade_date,),
        )
        assert top["stock_code"] == "002594.SZ"
        assert top["trend_score"] >= 0
        assert top["money_score"] >= 0
        assert top["fundamental_score"] >= 0
        assert top["news_score"] == 0
        assert top["crowding_adjustment"] <= 0
        assert top["rating"] in {"S", "A", "B", "C", "D", "R"}

    print("Phase 1 acceptance checks passed.")


if __name__ == "__main__":
    main()
