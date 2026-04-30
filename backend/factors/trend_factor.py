from __future__ import annotations

from backend.factors.common import FactorResult, clamp
from backend.models import DailyQuote


def _return_pct(start: float, end: float) -> float | None:
    if start <= 0:
        return None
    return (end - start) / start * 100


def calculate_trend_score(current: DailyQuote, history: list[DailyQuote]) -> FactorResult:
    score = 0.0
    reasons: list[str] = []
    ordered = history or [current]
    closes = [item.close for item in ordered]
    ma5 = sum(closes[-5:]) / 5 if len(closes) >= 5 else current.ma5
    ma10 = sum(closes[-10:]) / 10 if len(closes) >= 10 else current.ma10
    ma20 = sum(closes[-20:]) / 20 if len(closes) >= 20 else current.ma20
    ma60 = sum(closes[-60:]) / 60 if len(closes) >= 60 else current.ma60

    if current.close > ma20:
        score += 5
        reasons.append("+5 股价 > MA20")
    else:
        score -= 5
        reasons.append("-5 跌破 MA20")

    if ma5 > ma10 > ma20:
        score += 5
        reasons.append("+5 MA5 > MA10 > MA20")

    if current.close < ma60:
        score -= 10
        reasons.append("-10 股价跌破 MA60")

    if len(ordered) >= 20:
        recent_20 = ordered[-20:]
        pct_20 = _return_pct(recent_20[0].close, current.close)
        if pct_20 is not None:
            if 5 <= pct_20 <= 35:
                score += 5
                reasons.append("+5 最近 20 日涨幅在 5% ~ 35%")
            if pct_20 > 60:
                score -= 5
                reasons.append("-5 最近 20 日涨幅 > 60%，短线过热")

    if len(ordered) >= 10:
        recent_10 = ordered[-10:]
        avg_amount_10 = sum(item.amount for item in recent_10) / len(recent_10)
        if any(item.close > item.open and item.amount > avg_amount_10 * 1.2 for item in recent_10):
            score += 5
            reasons.append("+5 最近 10 日有放量阳线")

    if len(ordered) >= 5:
        recent_5 = ordered[-5:]
        avg_amount_5 = sum(item.amount for item in recent_5) / len(recent_5)
        if any(item.close < item.open and item.amount > avg_amount_5 * 1.2 for item in recent_5):
            score -= 5
            reasons.append("-5 最近 5 日放量下跌")

    high_window = ordered[-60:] if len(ordered) >= 60 else ordered
    high_60 = max(item.high for item in high_window)
    if high_60 > 0:
        distance_from_high = (high_60 - current.close) / high_60 * 100
        if distance_from_high < 5:
            score += 5
            reasons.append("+5 距离 60 日新高小于 5%")
        if distance_from_high < 15:
            score += 5
            reasons.append("+5 最近回撤小于 15%")

    return FactorResult(score=clamp(score, 0, 30), reasons=reasons)
