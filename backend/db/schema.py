from __future__ import annotations

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stock_basic (
    stock_code TEXT PRIMARY KEY,
    stock_name TEXT,
    exchange TEXT,
    industry TEXT,
    concepts TEXT,
    market_cap REAL,
    float_market_cap REAL,
    is_st INTEGER,
    list_date TEXT,
    status TEXT,
    avg_amount_20d REAL,
    is_suspended INTEGER DEFAULT 0,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS daily_quote (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT,
    trade_date TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    volume REAL,
    amount REAL,
    turnover_rate REAL,
    pct_chg REAL,
    ma5 REAL,
    ma10 REAL,
    ma20 REAL,
    ma60 REAL,
    created_at TEXT,
    UNIQUE(stock_code, trade_date)
);

CREATE TABLE IF NOT EXISTS fundamental_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT,
    trade_date TEXT,
    revenue_yoy REAL,
    net_profit_yoy REAL,
    roe REAL,
    gross_margin REAL,
    debt_ratio REAL,
    operating_cashflow REAL,
    goodwill REAL,
    source_status TEXT,
    created_at TEXT,
    UNIQUE(stock_code, trade_date)
);

CREATE TABLE IF NOT EXISTS factor_score (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT,
    trade_date TEXT,
    trend_score REAL,
    money_score REAL,
    fundamental_score REAL,
    news_score REAL,
    risk_score REAL,
    crowding_adjustment REAL,
    total_score REAL,
    rating TEXT,
    reason TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS news_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stock_code TEXT,
    publish_time TEXT,
    source TEXT,
    title TEXT,
    summary TEXT,
    event_type TEXT,
    sentiment TEXT,
    confidence REAL,
    impact_score REAL,
    url TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS virtual_positions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    account_name TEXT,
    stock_code TEXT,
    buy_date TEXT,
    buy_price REAL,
    position_pct REAL,
    shares REAL,
    current_price REAL,
    pnl REAL,
    pnl_pct REAL,
    status TEXT,
    sell_date TEXT,
    sell_price REAL,
    sell_reason TEXT,
    created_at TEXT,
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS strategy_signals (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT,
    stock_code TEXT,
    strategy_name TEXT,
    signal_type TEXT,
    score REAL,
    rating TEXT,
    reason TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS market_state_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT,
    market_state TEXT,
    up_count INTEGER,
    down_count INTEGER,
    limit_up_count INTEGER,
    limit_down_count INTEGER,
    total_amount REAL,
    index_trend TEXT,
    strong_stock_status TEXT,
    reason TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS concept_crowding_daily (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT,
    concept_name TEXT,
    concept_amount REAL,
    market_amount REAL,
    amount_ratio REAL,
    limit_up_count INTEGER,
    rsi_over_70_ratio REAL,
    avg_5d_return REAL,
    crowding_level TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS strategy_daily_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT,
    strategy_name TEXT,
    market_state TEXT,
    selected_count INTEGER,
    s_count INTEGER,
    a_count INTEGER,
    hold_count INTEGER,
    top5_stocks TEXT,
    top5_scores TEXT,
    paper_pnl REAL,
    paper_total_return REAL,
    paper_max_drawdown REAL,
    benchmark_name TEXT,
    benchmark_return REAL,
    excess_return REAL,
    win_rate REAL,
    avg_holding_days REAL,
    reason TEXT,
    created_at TEXT
);
"""
