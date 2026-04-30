from __future__ import annotations

from backend.models import DailyQuote, MarketStateDaily


def _ratio(part: int, total: int) -> float:
    return part / total if total else 0.0


def _amount_shrinking(amount_history: list[tuple[str, float]]) -> bool:
    if len(amount_history) < 3:
        return False
    current = amount_history[0][1]
    previous = amount_history[1][1]
    before_previous = amount_history[2][1]
    return 0 < current < previous < before_previous


def calculate_market_state(
    trade_date: str,
    quotes: dict[str, DailyQuote],
    amount_history: list[tuple[str, float]],
) -> MarketStateDaily:
    quote_items = list(quotes.values())
    total_count = len(quote_items)
    up_count = sum(1 for item in quote_items if item.pct_chg > 0)
    down_count = sum(1 for item in quote_items if item.pct_chg < 0)
    limit_up_count = sum(1 for item in quote_items if item.pct_chg >= 9.8)
    limit_down_count = sum(1 for item in quote_items if item.pct_chg <= -9.8)
    total_amount = sum(item.amount for item in quote_items)
    up_ratio = _ratio(up_count, total_count)
    down_ratio = _ratio(down_count, total_count)
    above_ma20_ratio = _ratio(
        sum(1 for item in quote_items if item.ma20 > 0 and item.close >= item.ma20),
        total_count,
    )
    above_ma60_ratio = _ratio(
        sum(1 for item in quote_items if item.ma60 > 0 and item.close >= item.ma60),
        total_count,
    )
    previous_amount = amount_history[1][1] if len(amount_history) > 1 else 0.0
    amount_expanding = previous_amount > 0 and total_amount >= previous_amount * 1.05
    amount_shrinking = _amount_shrinking(amount_history)
    index_trend = (
        f"MA20上方占比{above_ma20_ratio:.1%}，MA60上方占比{above_ma60_ratio:.1%}"
    )

    defensive_reasons: list[str] = []
    if down_ratio > 0.70:
        defensive_reasons.append("全市场下跌家数 > 70%")
    if amount_shrinking:
        defensive_reasons.append("全市场成交额连续萎缩")
    if above_ma20_ratio < 0.45 or above_ma60_ratio < 0.40:
        defensive_reasons.append("主要指数趋势代理跌破关键均线")
    if limit_down_count >= max(10, int(total_count * 0.01)):
        defensive_reasons.append("跌停家数明显增加")

    attack_reasons: list[str] = []
    if up_ratio >= 0.60:
        attack_reasons.append("上涨家数明显多于下跌家数")
    if amount_expanding:
        attack_reasons.append("全市场成交额放大")
    if above_ma20_ratio >= 0.55:
        attack_reasons.append("主要指数趋势代理站上 MA20")
    if limit_up_count >= max(10, int(total_count * 0.01)):
        attack_reasons.append("涨停家数较多")

    if defensive_reasons:
        market_state = "防守"
        reason = "；".join(defensive_reasons)
    elif len(attack_reasons) >= 3:
        market_state = "进攻"
        reason = "；".join(attack_reasons)
    else:
        market_state = "震荡"
        reason = "上涨和下跌家数或成交额未形成明确进攻/防守信号"

    strong_stock_status = (
        f"涨停{limit_up_count}只，跌停{limit_down_count}只，"
        f"上涨占比{up_ratio:.1%}，下跌占比{down_ratio:.1%}"
    )
    return MarketStateDaily(
        trade_date=trade_date,
        market_state=market_state,
        up_count=up_count,
        down_count=down_count,
        limit_up_count=limit_up_count,
        limit_down_count=limit_down_count,
        total_amount=total_amount,
        index_trend=index_trend,
        strong_stock_status=strong_stock_status,
        reason=reason,
    )
