from __future__ import annotations

from backend.factors.common import FactorResult, clamp
from backend.models import DailyQuote, StockBasic


def calculate_money_score(
    current: DailyQuote,
    history: list[DailyQuote],
    stock: StockBasic,
    strong_industries: set[str],
) -> FactorResult:
    score = 0.0
    reasons: list[str] = []
    ordered = history or [current]

    if len(ordered) >= 5:
        amounts = [item.amount for item in ordered[-5:]]
        if all(later > earlier for earlier, later in zip(amounts, amounts[1:])):
            score += 5
            reasons.append("+5 近 5 日成交额持续放大")

    if len(ordered) >= 20:
        recent_20 = ordered[-20:]
        avg_amount_20 = sum(item.amount for item in recent_20) / len(recent_20)
        if avg_amount_20 > 0 and current.amount > avg_amount_20 * 1.5:
            score += 5
            reasons.append("+5 今日成交额大于近 20 日均值 1.5 倍")

    if 3 <= current.turnover_rate <= 15:
        score += 5
        reasons.append("+5 换手率在 3% ~ 15%")
    if current.turnover_rate > 30:
        score -= 5
        reasons.append("-5 换手率过高，比如 > 30%")

    if stock.industry and stock.industry in strong_industries:
        score += 5
        reasons.append("+5 所属板块成交额排名靠前")

    upper_shadow_ratio = 0.0
    if current.close > 0:
        upper_shadow_ratio = (current.high - max(current.open, current.close)) / current.close
    if upper_shadow_ratio > 0.05 and current.amount > stock.avg_amount_20d * 1.5:
        score -= 5
        reasons.append("-5 高位爆量长上影")

    return FactorResult(score=clamp(score, 0, 25), reasons=reasons)

