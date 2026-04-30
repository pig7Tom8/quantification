from __future__ import annotations

from backend.factors.common import FactorResult, clamp
from backend.models import FundamentalSnapshot


def calculate_fundamental_score(
    fundamental: FundamentalSnapshot | None,
    industry_debt_average: float | None = None,
) -> FactorResult:
    if fundamental is None:
        return FactorResult(score=0.0, reasons=["基本面数据缺失"])

    score = 0.0
    reasons: list[str] = []

    if fundamental.revenue_yoy is not None and fundamental.revenue_yoy > 10:
        score += 5
        reasons.append("+5 营收同比增长 > 10%")
    if fundamental.net_profit_yoy is not None and fundamental.net_profit_yoy > 10:
        score += 5
        reasons.append("+5 净利润同比增长 > 10%")
    if fundamental.roe is not None and fundamental.roe > 8:
        score += 5
        reasons.append("+5 ROE > 8%")
    if fundamental.gross_margin is not None and fundamental.gross_margin > 0:
        score += 3
        reasons.append("+3 毛利率稳定或提升")
    if fundamental.debt_ratio is not None and fundamental.debt_ratio <= 70:
        score += 2
        reasons.append("+2 资产负债率不过高")

    if fundamental.net_profit_yoy is not None and fundamental.net_profit_yoy < -10:
        score -= 5
        reasons.append("-5 净利润连续下滑")
    if fundamental.goodwill is not None and fundamental.goodwill > 0 and fundamental.goodwill > 10_000_000_000:
        score -= 5
        reasons.append("-5 商誉占比过高")
    if (
        fundamental.debt_ratio is not None
        and industry_debt_average is not None
        and fundamental.debt_ratio > industry_debt_average + 20
    ):
        score -= 5
        reasons.append("-5 资产负债率明显高于行业平均")

    return FactorResult(score=clamp(score, 0, 20), reasons=reasons)

