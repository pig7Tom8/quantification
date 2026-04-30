from __future__ import annotations

from collections import defaultdict

from backend.models import ConceptCrowdingDaily, DailyQuote, StockBasic

CROWDING_ORDER = {
    "低拥挤": 0,
    "中拥挤": 1,
    "高拥挤": 2,
    "极高拥挤": 3,
}

CROWDING_ADJUSTMENT = {
    "低拥挤": 0.0,
    "中拥挤": -3.0,
    "高拥挤": -8.0,
    "极高拥挤": -15.0,
}


def split_concepts(concepts: str) -> list[str]:
    return [item.strip() for item in concepts.replace(",", ";").split(";") if item.strip()]


def _rsi_over_70(history: list[DailyQuote], period: int = 14) -> bool:
    if len(history) <= period:
        return False
    closes = [item.close for item in history[-(period + 1) :]]
    gains = 0.0
    losses = 0.0
    for previous, current in zip(closes, closes[1:]):
        change = current - previous
        if change > 0:
            gains += change
        else:
            losses += abs(change)
    if losses == 0:
        return gains > 0
    rsi = 100 - (100 / (1 + gains / losses))
    return rsi > 70


def _avg_5d_return(history: list[DailyQuote]) -> float:
    if len(history) < 6:
        return 0.0
    base = history[-6].close
    if base <= 0:
        return 0.0
    return (history[-1].close - base) / base * 100


def _crowding_level(
    amount_ratio: float,
    limit_up_ratio: float,
    rsi_over_70_ratio: float,
    avg_5d_return: float,
) -> str:
    high_signal_count = sum(
        (
            amount_ratio >= 0.08,
            limit_up_ratio >= 0.20,
            rsi_over_70_ratio >= 0.50,
            avg_5d_return >= 15,
        )
    )
    if amount_ratio >= 0.12 and high_signal_count >= 3:
        return "极高拥挤"
    if high_signal_count >= 2 or amount_ratio >= 0.10:
        return "高拥挤"
    if amount_ratio >= 0.05 or limit_up_ratio >= 0.10 or rsi_over_70_ratio >= 0.30 or avg_5d_return >= 8:
        return "中拥挤"
    return "低拥挤"


def calculate_concept_crowding(
    trade_date: str,
    stocks: list[StockBasic],
    quotes: dict[str, DailyQuote],
    quote_history: dict[str, list[DailyQuote]],
) -> list[ConceptCrowdingDaily]:
    market_amount = sum(item.amount for item in quotes.values())
    stocks_by_code = {item.stock_code: item for item in stocks}
    concept_codes: dict[str, list[str]] = defaultdict(list)
    for stock in stocks:
        for concept in split_concepts(stock.concepts):
            if stock.stock_code in quotes:
                concept_codes[concept].append(stock.stock_code)

    results: list[ConceptCrowdingDaily] = []
    for concept, stock_codes in concept_codes.items():
        concept_quotes = [quotes[code] for code in stock_codes if code in quotes]
        if not concept_quotes:
            continue
        concept_amount = sum(item.amount for item in concept_quotes)
        amount_ratio = concept_amount / market_amount if market_amount else 0.0
        limit_up_count = sum(1 for item in concept_quotes if item.pct_chg >= 9.8)
        rsi_over_70_count = sum(
            1 for code in stock_codes if _rsi_over_70(quote_history.get(code, []))
        )
        avg_5d_return = sum(
            _avg_5d_return(quote_history.get(code, [])) for code in stock_codes
        ) / len(stock_codes)
        level = _crowding_level(
            amount_ratio,
            limit_up_count / len(stock_codes),
            rsi_over_70_count / len(stock_codes),
            avg_5d_return,
        )
        if stocks_by_code:
            results.append(
                ConceptCrowdingDaily(
                    trade_date=trade_date,
                    concept_name=concept,
                    concept_amount=concept_amount,
                    market_amount=market_amount,
                    amount_ratio=amount_ratio,
                    limit_up_count=limit_up_count,
                    rsi_over_70_ratio=rsi_over_70_count / len(stock_codes),
                    avg_5d_return=avg_5d_return,
                    crowding_level=level,
                )
            )
    results.sort(
        key=lambda item: (
            CROWDING_ORDER[item.crowding_level],
            item.amount_ratio,
            item.avg_5d_return,
        ),
        reverse=True,
    )
    return results


def highest_crowding_for_stock(
    stock: StockBasic,
    crowding_by_concept: dict[str, ConceptCrowdingDaily],
) -> ConceptCrowdingDaily | None:
    matched = [
        crowding_by_concept[concept]
        for concept in split_concepts(stock.concepts)
        if concept in crowding_by_concept
    ]
    if not matched:
        return None
    return max(matched, key=lambda item: CROWDING_ORDER[item.crowding_level])


def downgrade_rating_for_crowding(rating: str, crowding_level: str) -> str:
    if crowding_level == "高拥挤":
        if rating == "S":
            return "A"
        if rating == "A":
            return "B"
    return rating
