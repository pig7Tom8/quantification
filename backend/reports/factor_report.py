from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from backend.config import settings
from backend.db.repository import Database
from backend.models import ConceptCrowdingDaily, FactorScore, MarketStateDaily


@dataclass
class FactorReportContext:
    trade_date: str
    top50: list[FactorScore]
    s_list: list[FactorScore]
    a_list: list[FactorScore]
    risk_list: list[FactorScore]
    market_state: MarketStateDaily | None = None
    crowding: list[ConceptCrowdingDaily] | None = None


class FactorReportService:
    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _table(
        scores: list[FactorScore],
        stock_names: dict[str, str],
        limit: int | None = None,
    ) -> list[str]:
        selected = scores[:limit] if limit is not None else scores
        lines = [
            "| 股票代码 | 股票名称 | 总分 | 评级 | 趋势分 | 资金分 | 基本面分 | 资讯分 | 风险分 | 拥挤度调整 |",
            "| --- | --- | ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: |",
        ]
        if not selected:
            lines.append("| - | - | - | - | - | - | - | - | - | - |")
            return lines
        for item in selected:
            stock_name = stock_names.get(item.stock_code, "-")
            lines.append(
                f"| {item.stock_code} | {stock_name} | {item.total_score:.1f} | {item.rating} | "
                f"{item.trend_score:.1f} | {item.money_score:.1f} | "
                f"{item.fundamental_score:.1f} | {item.news_score:.1f} | "
                f"{item.risk_score:.1f} | {item.crowding_adjustment:.1f} |"
            )
        return lines

    @staticmethod
    def _crowding_table(items: list[ConceptCrowdingDaily], limit: int = 20) -> list[str]:
        lines = [
            "| 题材 | 拥挤度 | 成交额占比 | 涨停家数 | RSI>70占比 | 近5日平均涨幅 |",
            "| --- | --- | ---: | ---: | ---: | ---: |",
        ]
        selected = [item for item in items if item.crowding_level in {"中拥挤", "高拥挤", "极高拥挤"}]
        selected = selected[:limit]
        if not selected:
            lines.append("| - | - | - | - | - | - |")
            return lines
        for item in selected:
            lines.append(
                f"| {item.concept_name} | {item.crowding_level} | "
                f"{item.amount_ratio:.2%} | {item.limit_up_count} | "
                f"{item.rsi_over_70_ratio:.2%} | {item.avg_5d_return:.2f}% |"
            )
        return lines

    def generate(self, context: FactorReportContext) -> Path:
        path = settings.report_dir / f"factor_report_{context.trade_date}.md"
        stock_names = {
            item.stock_code: item.stock_name
            for item in self.database.fetch_latest_stock_basics()
        }
        market_lines: list[str] = []
        if context.market_state is not None:
            market_lines = [
                "## 市场状态",
                f"- 今日市场状态: `{context.market_state.market_state}`",
                f"- 市场状态原因: {context.market_state.reason}",
                f"- 强势股/涨跌停状态: {context.market_state.strong_stock_status}",
                f"- 指数趋势代理: {context.market_state.index_trend}",
                "",
            ]
        content = "\n".join(
            [
                "# Phase 2 市场状态与拥挤度日报",
                "",
                f"- 交易日: `{context.trade_date}`",
                f"- Top 50 数量: `{len(context.top50)}`",
                f"- S 级股票数: `{len(context.s_list)}`",
                f"- A 级股票数: `{len(context.a_list)}`",
                f"- 风险剔除股票数: `{len(context.risk_list)}`",
                "",
                *market_lines,
                "## 题材拥挤度提醒",
                *self._crowding_table(context.crowding or []),
                "",
                "## Top 50 股票",
                *self._table(context.top50, stock_names, limit=50),
                "",
                "## S 级股票",
                *self._table(context.s_list, stock_names),
                "",
                "## A 级股票",
                *self._table(context.a_list, stock_names),
                "",
                "## 风险剔除股票",
                *self._table(context.risk_list, stock_names),
                "",
                "## 说明",
                "- 当前为 Phase 2 市场状态与拥挤度日报。",
                "- 资讯分在 Phase 3 实现，本阶段按主 PRD 记为 0。",
                "- 市场状态用于约束是否开新仓；题材高拥挤会影响评级或开仓动作。",
                "",
            ]
        )
        path.write_text(content, encoding="utf-8")
        return path
