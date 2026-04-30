from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime

from backend.config import settings
from backend.models import StockBasic


@dataclass
class PoolFilterResult:
    tradable: list[StockBasic]
    excluded: list[tuple[StockBasic, str]]


def _listing_days(list_date: str, as_of: date) -> int:
    listed_on = datetime.strptime(list_date, "%Y-%m-%d").date()
    return (as_of - listed_on).days


def filter_tradable_stocks(items: list[StockBasic], as_of: date) -> PoolFilterResult:
    tradable: list[StockBasic] = []
    excluded: list[tuple[StockBasic, str]] = []

    for item in items:
        if item.is_st:
            excluded.append((item, "ST / *ST"))
            continue
        if item.status == "risk":
            excluded.append((item, "退市风险股票"))
            continue
        if item.is_suspended:
            excluded.append((item, "长期停牌"))
            continue
        if item.status != "active":
            excluded.append((item, "非正常交易状态"))
            continue
        if _listing_days(item.list_date, as_of) < settings.min_listing_days:
            excluded.append((item, "上市不足 120 个交易日"))
            continue
        if item.avg_amount_20d <= 0:
            excluded.append((item, "流动性明显不足"))
            continue
        if item.avg_amount_20d < settings.min_avg_amount_20d:
            excluded.append((item, "近 20 日平均成交额低于 5000 万"))
            continue
        tradable.append(item)

    return PoolFilterResult(tradable=tradable, excluded=excluded)
