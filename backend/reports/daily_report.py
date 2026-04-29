from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path

from backend.config import settings
from backend.db.repository import Database
from backend.stock_pool import PoolFilterResult


@dataclass
class DailyReportContext:
    trade_date: date
    filter_result: PoolFilterResult
    quote_count: int
    data_confidence: str = "high"
    notes: tuple[str, ...] = ()


class DailyReportService:
    def __init__(self, database: Database) -> None:
        self.database = database

    def generate(self, context: DailyReportContext) -> Path:
        rows = self.database.fetch_stock_pool_report_rows(context.trade_date.isoformat())
        path = settings.report_dir / f"daily_report_{context.trade_date.isoformat()}.md"

        top_rows = rows[:10]
        excluded_lines = [
            f"- `{item.stock_code}` {item.stock_name}: {reason}"
            for item, reason in context.filter_result.excluded[:10]
        ]
        top_lines = [
            f"| {row['stock_code']} | {row['stock_name']} | {row['industry']} | {row['close'] or '-'} | {row['pct_chg'] or '-'} | {row['amount'] or '-'} |"
            for row in top_rows
        ]

        content = "\n".join(
            [
                "# Phase 0 每日数据日报",
                "",
                f"- 交易日: `{context.trade_date.isoformat()}`",
                f"- 数据可信度: `{context.data_confidence}`",
                f"- 可交易股票数: `{len(context.filter_result.tradable)}`",
                f"- 被过滤股票数: `{len(context.filter_result.excluded)}`",
                f"- 已入库行情数: `{context.quote_count}`",
                "",
                "## 数据状态",
                f"- 数据可信度评级: `{context.data_confidence}`",
                "",
                "## 股票池过滤摘要",
                *(excluded_lines or ["- 无"]),
                "",
                "## 成交额前十样本",
                "| 股票代码 | 股票名称 | 行业 | 收盘价 | 涨跌幅 | 成交额 |",
                "| --- | --- | --- | ---: | ---: | ---: |",
                *(top_lines or ["| - | - | - | - | - | - |"]),
                "",
                "## 说明",
                "- 当前为 Phase 0 骨架日报，后续会补评分、市场状态、资讯和虚拟跑盘结果。",
                *[f"- {note}" for note in context.notes],
                "",
            ]
        )
        path.write_text(content, encoding="utf-8")
        return path
