from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Iterator

from backend.config import settings
from backend.db.schema import SCHEMA_SQL
from backend.models import DailyQuote, FundamentalSnapshot, StockBasic


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

    def upsert_stock_basics(self, items: list[StockBasic]) -> None:
        payload = [
            (
                item.stock_code,
                item.stock_name,
                item.exchange,
                item.industry,
                item.concepts,
                item.market_cap,
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
                    is_st, list_date, status, avg_amount_20d, is_suspended, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(stock_code) DO UPDATE SET
                    stock_name = excluded.stock_name,
                    exchange = excluded.exchange,
                    industry = excluded.industry,
                    concepts = excluded.concepts,
                    market_cap = excluded.market_cap,
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
                       is_st, list_date, status, avg_amount_20d, is_suspended
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
                is_st=bool(row["is_st"]),
                list_date=row["list_date"],
                status=row["status"],
                avg_amount_20d=row["avg_amount_20d"] or 0.0,
                is_suspended=bool(row["is_suspended"]),
            )
            for row in rows
        ]

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
