from __future__ import annotations

from dataclasses import dataclass

from backend.factors.common import clamp
from backend.models import DailyQuote, FundamentalSnapshot, StockBasic


@dataclass
class RiskResult:
    score: float
    triggered: bool
    reasons: list[str]


def calculate_risk_score(
    stock: StockBasic,
    current: DailyQuote,
    history: list[DailyQuote],
    fundamental: FundamentalSnapshot | None,
    fundamental_score: float,
) -> RiskResult:
    score = 0.0
    reasons: list[str] = []
    triggered = False

    if stock.is_st or stock.status == "risk":
        score -= 5
        triggered = True
        reasons.append("-5 ST / 退市风险")

    if len(history) >= 20 and history[-20].close > 0:
        pct_20 = (current.close - history[-20].close) / history[-20].close * 100
        if pct_20 > 60 and fundamental_score < 10:
            score -= 5
            reasons.append("-5 近 20 日涨幅过高且无业绩支撑")

    closes = [item.close for item in (history or [current])]
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current.ma20
    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else current.ma60
    if current.close < ma20 and current.close < ma60:
        score -= 5
        reasons.append("-5 连续跌破关键均线")

    if fundamental is not None and fundamental.net_profit_yoy is not None and fundamental.net_profit_yoy < -20:
        score -= 5
        reasons.append("-5 业绩亏损扩大")

    if current.turnover_rate > 30:
        score -= 5
        reasons.append("-5 换手率异常过高")

    return RiskResult(score=clamp(score, -20, 0), triggered=triggered or score <= -10, reasons=reasons)
