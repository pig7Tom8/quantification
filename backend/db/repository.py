from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from backend.config import settings
from backend.db.schema import SCHEMA_SQL
from backend.models import (
    ConceptCrowdingDaily,
    DailyQuote,
    FactorScore,
    FundamentalSnapshot,
    MarketStateDaily,
    StockBasic,
)


def utc_now_text() -> str:
    return datetime.utcnow().isoformat(timespec="seconds")


class Database:
    def __init__(self, db_path: Path | None = None) -> None:
        self.db_path = db_path or settings.sqlite_path

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.db_path)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(self) -> None:
        with self.connect() as connection:
            connection.executescript(SCHEMA_SQL)
            columns = {
                row["name"]
                for row in connection.execute("PRAGMA table_info(stock_basic)").fetchall()
            }
            if "float_market_cap" not in columns:
                connection.execute("ALTER TABLE stock_basic ADD COLUMN float_market_cap REAL DEFAULT 0")

    def upsert_stock_basics(self, items: list[StockBasic]) -> None:
        payload = [
            (
                item.stock_code,
                item.stock_name,
                item.exchange,
                item.industry,
                item.concepts,
                item.market_cap,
                item.float_market_cap,
                int(item.is_st),
                item.list_date,
                item.status,
                item.avg_amount_20d,
                int(item.is_suspended),
                utc_now_text(),
            )
            for item in items
        ]
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO stock_basic (
                    stock_code, stock_name, exchange, industry, concepts, market_cap,
                    float_market_cap, is_st, list_date, status, avg_amount_20d, is_suspended, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stock_code) DO UPDATE SET
                    stock_name = excluded.stock_name,
                    exchange = excluded.exchange,
                    industry = excluded.industry,
                    concepts = excluded.concepts,
                    market_cap = excluded.market_cap,
                    float_market_cap = excluded.float_market_cap,
                    is_st = excluded.is_st,
                    list_date = excluded.list_date,
                    status = excluded.status,
                    avg_amount_20d = excluded.avg_amount_20d,
                    is_suspended = excluded.is_suspended,
                    updated_at = excluded.updated_at
                """,
                payload,
            )

    def upsert_daily_quotes(self, items: list[DailyQuote]) -> None:
        payload = [
            (
                item.stock_code,
                item.trade_date,
                item.open,
                item.high,
                item.low,
                item.close,
                item.volume,
                item.amount,
                item.turnover_rate,
                item.pct_chg,
                item.ma5,
                item.ma10,
                item.ma20,
                item.ma60,
                utc_now_text(),
            )
            for item in items
        ]
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO daily_quote (
                    stock_code, trade_date, open, high, low, close, volume, amount,
                    turnover_rate, pct_chg, ma5, ma10, ma20, ma60, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stock_code, trade_date) DO UPDATE SET
                    open = excluded.open,
                    high = excluded.high,
                    low = excluded.low,
                    close = excluded.close,
                    volume = excluded.volume,
                    amount = excluded.amount,
                    turnover_rate = excluded.turnover_rate,
                    pct_chg = excluded.pct_chg,
                    ma5 = excluded.ma5,
                    ma10 = excluded.ma10,
                    ma20 = excluded.ma20,
                    ma60 = excluded.ma60,
                    created_at = excluded.created_at
                """,
                payload,
            )

    def upsert_fundamentals(self, items: list[FundamentalSnapshot]) -> None:
        payload = [
            (
                item.stock_code,
                item.trade_date,
                item.revenue_yoy,
                item.net_profit_yoy,
                item.roe,
                item.gross_margin,
                item.debt_ratio,
                item.operating_cashflow,
                item.goodwill,
                item.source_status,
                utc_now_text(),
            )
            for item in items
        ]
        with self.connect() as connection:
            connection.executemany(
                """
                INSERT INTO fundamental_snapshot (
                    stock_code, trade_date, revenue_yoy, net_profit_yoy, roe,
                    gross_margin, debt_ratio, operating_cashflow, goodwill,
                    source_status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stock_code, trade_date) DO UPDATE SET
                    revenue_yoy = excluded.revenue_yoy,
                    net_profit_yoy = excluded.net_profit_yoy,
                    roe = excluded.roe,
                    gross_margin = excluded.gross_margin,
                    debt_ratio = excluded.debt_ratio,
                    operating_cashflow = excluded.operating_cashflow,
                    goodwill = excluded.goodwill,
                    source_status = excluded.source_status,
                    created_at = excluded.created_at
                """,
                payload,
            )

    def replace_factor_scores(self, trade_date: str, items: list[FactorScore]) -> None:
        payload = [
            (
                item.stock_code,
                item.trade_date,
                item.trend_score,
                item.money_score,
                item.fundamental_score,
                item.news_score,
                item.risk_score,
                item.crowding_adjustment,
                item.total_score,
                item.rating,
                item.reason,
                utc_now_text(),
            )
            for item in items
        ]
        with self.connect() as connection:
            connection.execute("DELETE FROM factor_score WHERE trade_date = ?", (trade_date,))
            connection.executemany(
                """
                INSERT INTO factor_score (
                    stock_code, trade_date, trend_score, money_score, fundamental_score,
                    news_score, risk_score, crowding_adjustment, total_score, rating, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )

    def replace_strategy_signals(
        self,
        trade_date: str,
        items: list[FactorScore],
        market_state: str | None = None,
    ) -> None:
        def market_action(rating: str) -> str:
            if market_state == "进攻" and rating in {"S", "A"}:
                return "市场进攻：S/A 可参与虚拟买入，总仓位上限 100%"
            if market_state == "震荡" and rating == "S":
                return "市场震荡：S 可虚拟买入，A 只观察，总仓位上限 60%"
            if market_state == "震荡" and rating == "A":
                return "市场震荡：A 只进入观察池，总仓位上限 60%"
            if market_state == "防守":
                return "市场防守：所有评级只观察，不开新仓，总仓位上限 0%~30%"
            return "市场状态未约束开仓"

        payload: list[tuple[object, ...]] = []
        for index, item in enumerate(items[:50], start=1):
            payload.append(
                (
                    trade_date,
                    item.stock_code,
                    "phase2_market_crowding_rating",
                    "top50",
                    item.total_score,
                    item.rating,
                    f"Top50 rank {index}; {market_action(item.rating)}；{item.reason}",
                    utc_now_text(),
                )
            )
        for item in items:
            if item.rating == "S":
                signal_type = "s_rating"
            elif item.rating == "A":
                signal_type = "a_rating"
            elif item.rating == "R":
                signal_type = "risk_exclude"
            else:
                continue
            payload.append(
                (
                    trade_date,
                    item.stock_code,
                    "phase2_market_crowding_rating",
                    signal_type,
                    item.total_score,
                    item.rating,
                    f"{market_action(item.rating)}；{item.reason}",
                    utc_now_text(),
                )
            )
        with self.connect() as connection:
            connection.execute("DELETE FROM strategy_signals WHERE trade_date = ?", (trade_date,))
            connection.executemany(
                """
                INSERT INTO strategy_signals (
                    trade_date, stock_code, strategy_name, signal_type, score, rating, reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )

    def replace_market_state(self, item: MarketStateDaily) -> None:
        with self.connect() as connection:
            connection.execute("DELETE FROM market_state_daily WHERE trade_date = ?", (item.trade_date,))
            connection.execute(
                """
                INSERT INTO market_state_daily (
                    trade_date, market_state, up_count, down_count, limit_up_count,
                    limit_down_count, total_amount, index_trend, strong_stock_status,
                    reason, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    item.trade_date,
                    item.market_state,
                    item.up_count,
                    item.down_count,
                    item.limit_up_count,
                    item.limit_down_count,
                    item.total_amount,
                    item.index_trend,
                    item.strong_stock_status,
                    item.reason,
                    utc_now_text(),
                ),
            )

    def replace_concept_crowding(self, trade_date: str, items: list[ConceptCrowdingDaily]) -> None:
        payload = [
            (
                item.trade_date,
                item.concept_name,
                item.concept_amount,
                item.market_amount,
                item.amount_ratio,
                item.limit_up_count,
                item.rsi_over_70_ratio,
                item.avg_5d_return,
                item.crowding_level,
                utc_now_text(),
            )
            for item in items
        ]
        with self.connect() as connection:
            connection.execute("DELETE FROM concept_crowding_daily WHERE trade_date = ?", (trade_date,))
            connection.executemany(
                """
                INSERT INTO concept_crowding_daily (
                    trade_date, concept_name, concept_amount, market_amount, amount_ratio,
                    limit_up_count, rsi_over_70_ratio, avg_5d_return, crowding_level, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                payload,
            )

    def fetch_market_amount_history(self, trade_date: str, limit: int = 3) -> list[tuple[str, float]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT trade_date, SUM(amount) AS total_amount
                FROM daily_quote
                WHERE trade_date <= ?
                GROUP BY trade_date
                ORDER BY trade_date DESC
                LIMIT ?
                """,
                (trade_date, limit),
            ).fetchall()
        return [(row["trade_date"], row["total_amount"] or 0.0) for row in rows]

    def fetch_market_state(self, trade_date: str) -> sqlite3.Row | None:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT *
                FROM market_state_daily
                WHERE trade_date = ?
                """,
                (trade_date,),
            ).fetchone()

    def fetch_concept_crowding(self, trade_date: str) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT *
                FROM concept_crowding_daily
                WHERE trade_date = ?
                ORDER BY
                    CASE crowding_level
                        WHEN '极高拥挤' THEN 1
                        WHEN '高拥挤' THEN 2
                        WHEN '中拥挤' THEN 3
                        ELSE 4
                    END,
                    amount_ratio DESC,
                    concept_name ASC
                """,
                (trade_date,),
            ).fetchall()

    def fetch_stock_pool_report_rows(self, trade_date: str) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT sb.stock_code, sb.stock_name, sb.industry, sb.status, dq.close, dq.pct_chg, dq.amount
                FROM stock_basic sb
                LEFT JOIN daily_quote dq
                    ON sb.stock_code = dq.stock_code AND dq.trade_date = ?
                ORDER BY dq.amount DESC, sb.stock_code ASC
                """,
                (trade_date,),
            ).fetchall()

    def fetch_latest_stock_basics(self) -> list[StockBasic]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT stock_code, stock_name, exchange, industry, concepts, market_cap,
                       float_market_cap, is_st, list_date, status, avg_amount_20d, is_suspended
                FROM stock_basic
                ORDER BY stock_code ASC
                """
            ).fetchall()
        return [
            StockBasic(
                stock_code=row["stock_code"],
                stock_name=row["stock_name"],
                exchange=row["exchange"],
                industry=row["industry"],
                concepts=row["concepts"],
                market_cap=row["market_cap"] or 0.0,
                float_market_cap=row["float_market_cap"] or 0.0,
                is_st=bool(row["is_st"]),
                list_date=row["list_date"],
                status=row["status"],
                avg_amount_20d=row["avg_amount_20d"] or 0.0,
                is_suspended=bool(row["is_suspended"]),
            )
            for row in rows
        ]

    def fetch_daily_quotes_for_date(self, trade_date: str) -> dict[str, DailyQuote]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT stock_code, trade_date, open, high, low, close, volume, amount,
                       turnover_rate, pct_chg, ma5, ma10, ma20, ma60
                FROM daily_quote
                WHERE trade_date = ?
                """,
                (trade_date,),
            ).fetchall()
        return {
            row["stock_code"]: DailyQuote(
                stock_code=row["stock_code"],
                trade_date=row["trade_date"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                amount=row["amount"],
                turnover_rate=row["turnover_rate"],
                pct_chg=row["pct_chg"],
                ma5=row["ma5"],
                ma10=row["ma10"],
                ma20=row["ma20"],
                ma60=row["ma60"],
            )
            for row in rows
        }

    def fetch_quote_history(
        self,
        trade_date: str,
        stock_codes: list[str],
        limit: int = 60,
    ) -> dict[str, list[DailyQuote]]:
        if not stock_codes:
            return {}
        placeholders = ",".join("?" for _ in stock_codes)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT stock_code, trade_date, open, high, low, close, volume, amount,
                       turnover_rate, pct_chg, ma5, ma10, ma20, ma60
                FROM daily_quote
                WHERE trade_date <= ? AND stock_code IN ({placeholders})
                ORDER BY stock_code ASC, trade_date DESC
                """,
                [trade_date, *stock_codes],
            ).fetchall()
        history: dict[str, list[DailyQuote]] = {}
        for row in rows:
            items = history.setdefault(row["stock_code"], [])
            if len(items) >= limit:
                continue
            items.append(
                DailyQuote(
                    stock_code=row["stock_code"],
                    trade_date=row["trade_date"],
                    open=row["open"],
                    high=row["high"],
                    low=row["low"],
                    close=row["close"],
                    volume=row["volume"],
                    amount=row["amount"],
                    turnover_rate=row["turnover_rate"],
                    pct_chg=row["pct_chg"],
                    ma5=row["ma5"],
                    ma10=row["ma10"],
                    ma20=row["ma20"],
                    ma60=row["ma60"],
                )
            )
        return {stock_code: list(reversed(items)) for stock_code, items in history.items()}

    def fetch_latest_fundamentals(self, stock_codes: list[str]) -> dict[str, FundamentalSnapshot]:
        if not stock_codes:
            return {}
        placeholders = ",".join("?" for _ in stock_codes)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT f1.stock_code, f1.trade_date, f1.revenue_yoy, f1.net_profit_yoy,
                       f1.roe, f1.gross_margin, f1.debt_ratio, f1.operating_cashflow,
                       f1.goodwill, f1.source_status
                FROM fundamental_snapshot f1
                INNER JOIN (
                    SELECT stock_code, MAX(trade_date) AS max_trade_date
                    FROM fundamental_snapshot
                    WHERE stock_code IN ({placeholders})
                    GROUP BY stock_code
                ) f2
                ON f1.stock_code = f2.stock_code AND f1.trade_date = f2.max_trade_date
                """,
                stock_codes,
            ).fetchall()
        return {
            row["stock_code"]: FundamentalSnapshot(
                stock_code=row["stock_code"],
                trade_date=row["trade_date"],
                revenue_yoy=row["revenue_yoy"],
                net_profit_yoy=row["net_profit_yoy"],
                roe=row["roe"],
                gross_margin=row["gross_margin"],
                debt_ratio=row["debt_ratio"],
                operating_cashflow=row["operating_cashflow"],
                goodwill=row["goodwill"],
                source_status=row["source_status"],
            )
            for row in rows
        }

    def fetch_factor_scores(self, trade_date: str) -> list[sqlite3.Row]:
        with self.connect() as connection:
            return connection.execute(
                """
                SELECT fs.*, sb.stock_name, sb.industry
                FROM factor_score fs
                LEFT JOIN stock_basic sb ON fs.stock_code = sb.stock_code
                WHERE fs.trade_date = ?
                ORDER BY fs.total_score DESC, fs.stock_code ASC
                """,
                (trade_date,),
            ).fetchall()

    def has_stock_basics_for_date(self, target_date: date) -> bool:
        with self.connect() as connection:
            row = connection.execute("SELECT MAX(updated_at) AS updated_at FROM stock_basic").fetchone()
        updated_at = row["updated_at"] if row else None
        if not updated_at:
            return False
        try:
            return datetime.fromisoformat(updated_at).date() == target_date
        except ValueError:
            return False

    def fetch_latest_quotes_before(self, trade_date: str, stock_codes: list[str]) -> list[DailyQuote]:
        if not stock_codes:
            return []
        placeholders = ",".join("?" for _ in stock_codes)
        with self.connect() as connection:
            rows = connection.execute(
                f"""
                SELECT q1.stock_code, q1.trade_date, q1.open, q1.high, q1.low, q1.close,
                       q1.volume, q1.amount, q1.turnover_rate, q1.pct_chg, q1.ma5, q1.ma10, q1.ma20, q1.ma60
                FROM daily_quote q1
                INNER JOIN (
                    SELECT stock_code, MAX(trade_date) AS max_trade_date
                    FROM daily_quote
                    WHERE trade_date < ? AND stock_code IN ({placeholders})
                    GROUP BY stock_code
                ) q2
                ON q1.stock_code = q2.stock_code AND q1.trade_date = q2.max_trade_date
                """,
                [trade_date, *stock_codes],
            ).fetchall()
        return [
            DailyQuote(
                stock_code=row["stock_code"],
                trade_date=row["trade_date"],
                open=row["open"],
                high=row["high"],
                low=row["low"],
                close=row["close"],
                volume=row["volume"],
                amount=row["amount"],
                turnover_rate=row["turnover_rate"],
                pct_chg=row["pct_chg"],
                ma5=row["ma5"],
                ma10=row["ma10"],
                ma20=row["ma20"],
                ma60=row["ma60"],
            )
            for row in rows
        ]
