from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass

from backend.db.repository import Database
from backend.factors.crowding_factor import (
    CROWDING_ADJUSTMENT,
    calculate_concept_crowding,
    downgrade_rating_for_crowding,
    highest_crowding_for_stock,
)
from backend.factors.fundamental_factor import calculate_fundamental_score
from backend.factors.market_state_factor import calculate_market_state
from backend.factors.money_factor import calculate_money_score
from backend.factors.risk_factor import calculate_risk_score
from backend.factors.trend_factor import calculate_trend_score
from backend.models import ConceptCrowdingDaily, DailyQuote, FactorScore, FundamentalSnapshot, MarketStateDaily, StockBasic


@dataclass
class ScoreEngineResult:
    trade_date: str
    scores: list[FactorScore]
    top50: list[FactorScore]
    s_list: list[FactorScore]
    a_list: list[FactorScore]
    risk_list: list[FactorScore]
    market_state: MarketStateDaily
    crowding: list[ConceptCrowdingDaily]


def rating_for_score(total_score: float, risk_triggered: bool) -> str:
    if risk_triggered:
        return "R"
    if total_score >= 85:
        return "S"
    if total_score >= 75:
        return "A"
    if total_score >= 65:
        return "B"
    if total_score >= 50:
        return "C"
    return "D"


def _strong_industries(stocks: list[StockBasic], quotes: dict[str, DailyQuote]) -> set[str]:
    amount_by_industry: dict[str, float] = defaultdict(float)
    for stock in stocks:
        quote = quotes.get(stock.stock_code)
        if quote is None or not stock.industry:
            continue
        amount_by_industry[stock.industry] += quote.amount
    if not amount_by_industry:
        return set()
    ranked = sorted(amount_by_industry.items(), key=lambda item: item[1], reverse=True)
    keep_count = max(1, int(len(ranked) * 0.2))
    return {industry for industry, _ in ranked[:keep_count]}


def _industry_debt_averages(
    stocks: list[StockBasic],
    fundamentals: dict[str, FundamentalSnapshot],
) -> dict[str, float]:
    values: dict[str, list[float]] = defaultdict(list)
    for stock in stocks:
        fundamental = fundamentals.get(stock.stock_code)
        if not stock.industry or fundamental is None or fundamental.debt_ratio is None:
            continue
        values[stock.industry].append(fundamental.debt_ratio)
    return {
        industry: sum(items) / len(items)
        for industry, items in values.items()
        if items
    }


class ScoreEngine:
    def __init__(self, database: Database) -> None:
        self.database = database

    def calculate(self, trade_date: str, stocks: list[StockBasic] | None = None) -> ScoreEngineResult:
        stock_items = stocks or self.database.fetch_latest_stock_basics()
        quotes = self.database.fetch_daily_quotes_for_date(trade_date)
        stock_items = [item for item in stock_items if item.stock_code in quotes]
        stock_codes = [item.stock_code for item in stock_items]
        quote_history = self.database.fetch_quote_history(trade_date, stock_codes, limit=60)
        fundamentals = self.database.fetch_latest_fundamentals(stock_codes)
        strong_industries = _strong_industries(stock_items, quotes)
        debt_averages = _industry_debt_averages(stock_items, fundamentals)
        market_state = calculate_market_state(
            trade_date,
            quotes,
            self.database.fetch_market_amount_history(trade_date),
        )
        crowding_items = calculate_concept_crowding(trade_date, stock_items, quotes, quote_history)
        crowding_by_concept = {item.concept_name: item for item in crowding_items}

        scores: list[FactorScore] = []
        for stock in stock_items:
            current = quotes[stock.stock_code]
            history = quote_history.get(stock.stock_code, [current])
            fundamental = fundamentals.get(stock.stock_code)

            trend = calculate_trend_score(current, history)
            money = calculate_money_score(current, history, stock, strong_industries)
            fundamental_result = calculate_fundamental_score(
                fundamental,
                debt_averages.get(stock.industry),
            )
            risk = calculate_risk_score(
                stock,
                current,
                history,
                fundamental,
                fundamental_result.score,
            )
            news_score = 0.0
            crowding = highest_crowding_for_stock(stock, crowding_by_concept)
            crowding_adjustment = (
                CROWDING_ADJUSTMENT[crowding.crowding_level] if crowding is not None else 0.0
            )
            total_score = (
                trend.score
                + money.score
                + fundamental_result.score
                + news_score
                + risk.score
                + crowding_adjustment
            )
            rating = rating_for_score(total_score, risk.triggered)
            if not risk.triggered and crowding is not None:
                rating = downgrade_rating_for_crowding(rating, crowding.crowding_level)
            reason_parts = [
                *trend.reasons,
                *money.reasons,
                *fundamental_result.reasons,
                *risk.reasons,
            ]
            if crowding is not None and crowding.crowding_level != "低拥挤":
                reason_parts.append(
                    f"{crowding.concept_name}为{crowding.crowding_level}，拥挤度调整{crowding_adjustment:g}分"
                )
                if crowding.crowding_level == "极高拥挤":
                    reason_parts.append("极高拥挤：S/A 均不触发买入，只进入观察池")
            scores.append(
                FactorScore(
                    stock_code=stock.stock_code,
                    trade_date=trade_date,
                    trend_score=trend.score,
                    money_score=money.score,
                    fundamental_score=fundamental_result.score,
                    news_score=news_score,
                    risk_score=risk.score,
                    crowding_adjustment=crowding_adjustment,
                    total_score=total_score,
                    rating=rating,
                    reason="；".join(reason_parts),
                )
            )

        scores.sort(key=lambda item: (item.total_score, item.stock_code), reverse=True)
        self.database.replace_market_state(market_state)
        self.database.replace_concept_crowding(trade_date, crowding_items)
        self.database.replace_factor_scores(trade_date, scores)
        self.database.replace_strategy_signals(trade_date, scores, market_state.market_state)
        return ScoreEngineResult(
            trade_date=trade_date,
            scores=scores,
            top50=scores[:50],
            s_list=[item for item in scores if item.rating == "S"],
            a_list=[item for item in scores if item.rating == "A"],
            risk_list=[item for item in scores if item.rating == "R"],
            market_state=market_state,
            crowding=crowding_items,
        )
