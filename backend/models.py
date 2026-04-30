from __future__ import annotations

from dataclasses import dataclass


@dataclass
class StockBasic:
    stock_code: str
    stock_name: str
    exchange: str
    industry: str
    concepts: str
    market_cap: float
    float_market_cap: float
    is_st: bool
    list_date: str
    status: str
    avg_amount_20d: float
    is_suspended: bool = False


@dataclass
class DailyQuote:
    stock_code: str
    trade_date: str
    open: float
    high: float
    low: float
    close: float
    volume: float
    amount: float
    turnover_rate: float
    pct_chg: float
    ma5: float
    ma10: float
    ma20: float
    ma60: float


@dataclass
class FundamentalSnapshot:
    stock_code: str
    trade_date: str
    revenue_yoy: float | None
    net_profit_yoy: float | None
    roe: float | None
    gross_margin: float | None
    debt_ratio: float | None
    operating_cashflow: float | None
    goodwill: float | None
    source_status: str = "fresh"


@dataclass
class FactorScore:
    stock_code: str
    trade_date: str
    trend_score: float
    money_score: float
    fundamental_score: float
    news_score: float
    risk_score: float
    crowding_adjustment: float
    total_score: float
    rating: str
    reason: str
