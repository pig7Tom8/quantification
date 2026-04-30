from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from backend.config import settings
from backend.data_collectors.data_quality_checker import DataQualityChecker
from backend.data_collectors.fundamental_collector import FundamentalCollector
from backend.data_collectors.history_collector import HistoricalQuoteCollector
from backend.data_collectors.providers.base_provider import BaseMarketDataProvider
from backend.data_collectors.providers.akshare_provider import AkshareProvider
from backend.data_collectors.providers.base_provider import DisabledMarketDataProvider, ProviderError
from backend.data_collectors.providers.eastmoney_provider import EastmoneyProvider
from backend.data_collectors.providers.fallback_provider import FallbackMarketDataProvider
from backend.data_collectors.providers.mock_provider import MockMarketDataProvider
from backend.data_collectors.providers.tushare_provider import TushareProvider
from backend.data_collectors.quote_collector import QuoteCollector
from backend.db.repository import Database
from backend.errors import PipelineExecutionError
from backend.reports.daily_report import DailyReportContext, DailyReportService
from backend.reports.factor_report import FactorReportContext, FactorReportService
from backend.scoring.score_engine import ScoreEngine


@dataclass
class PipelineResult:
    trade_date: date
    stock_count: int
    excluded_count: int
    quote_count: int
    data_confidence: str
    quality_summary: str
    provider_name: str
    provider_warnings: tuple[str, ...]
    market_data_status: str
    report_path: str
    factor_report_path: str | None = None
    scored_count: int = 0
    top50_count: int = 0
    s_count: int = 0
    a_count: int = 0
    risk_count: int = 0
    market_state: str | None = None
    medium_crowding_count: int = 0
    high_crowding_count: int = 0
    extreme_crowding_count: int = 0


def build_provider() -> BaseMarketDataProvider:
    if settings.use_mock_provider:
        return MockMarketDataProvider()
    provider_map = {
        "akshare": AkshareProvider,
        "tushare": TushareProvider,
        "eastmoney": EastmoneyProvider,
    }
    providers: list[BaseMarketDataProvider] = []
    for name in settings.provider_order:
        provider_class = provider_map.get(name.lower())
        if provider_class is not None:
            try:
                providers.append(provider_class())
            except ProviderError as exc:
                providers.append(DisabledMarketDataProvider(name.lower(), str(exc)))
    if not providers:
        raise NotImplementedError("No real providers configured.")
    return FallbackMarketDataProvider(providers)


def run_phase0_pipeline(
    trade_date: date | None = None,
    provider: BaseMarketDataProvider | None = None,
    database: Database | None = None,
) -> PipelineResult:
    settings.ensure_directories()
    effective_date = trade_date or date.today()
    database = database or Database()
    database.initialize()

    provider = provider or build_provider()
    quote_collector = QuoteCollector(provider=provider, database=database)
    try:
        quote_result = quote_collector.collect(effective_date)
    except ProviderError as exc:
        warnings = tuple(getattr(provider, "last_warnings", ()) or ())
        raise PipelineExecutionError(
            "核心行情数据获取失败，已停止正式运行。",
            warnings if warnings else (str(exc),),
        ) from exc
    filter_result = quote_result.filter_result

    quality_checker = DataQualityChecker()
    quality_report = quality_checker.evaluate(
        filter_result.tradable,
        quote_result.quotes,
        stock_basic_source_status=quote_result.stock_basic_source_status,
        quote_source_status=quote_result.quote_source_status,
    )

    provider_name = getattr(provider, "last_provider_name", None) or getattr(provider, "provider_name", "unknown")
    notes = [
        f"数据质量摘要: {quality_report.summary}",
        f"数据来源: {provider_name}",
        *quote_result.warnings,
    ]
    if quote_result.stock_basic_source_status == "stale":
        notes.append("股票基础信息沿用昨日股票池。")
    if quote_result.historical_quotes:
        notes.append("历史行情可作为均线兜底，但今日关键行情缺失。")
    if provider_name == "mock":
        notes.append("当前运行使用 mock provider。")

    if not quality_report.formal_output_allowed:
        raise PipelineExecutionError(
            "行情数据不完整，不生成正式评分和正式日报。",
            (quality_report.summary, *quote_result.warnings),
        )

    fundamental_count = 0
    try:
        fundamental_count = FundamentalCollector(provider=provider, database=database).collect(
            effective_date,
            filter_result.tradable,
        )
    except ProviderError as exc:
        notes.append(f"基本面数据采集失败，基本面分将按缺失处理: {exc}")
    if fundamental_count:
        notes.append(f"基本面数据入库数量: {fundamental_count}")

    history_count = 0
    if provider_name != "mock":
        history_count = HistoricalQuoteCollector(database=database).collect_tushare_daily_history(
            effective_date,
            [item.stock_code for item in filter_result.tradable],
        )
    if history_count:
        notes.append(f"历史日线补充数量: {history_count}")

    report_service = DailyReportService(database=database)
    report_path = report_service.generate(
        DailyReportContext(
            trade_date=effective_date,
            filter_result=filter_result,
            quote_count=quality_report.quote_count,
            data_confidence=quality_report.data_confidence,
            notes=tuple(notes),
        )
    )
    score_result = ScoreEngine(database=database).calculate(
        effective_date.isoformat(),
        filter_result.tradable,
    )
    factor_report_path = FactorReportService(database=database).generate(
        FactorReportContext(
            trade_date=effective_date.isoformat(),
            top50=score_result.top50,
            s_list=score_result.s_list,
            a_list=score_result.a_list,
            risk_list=score_result.risk_list,
            market_state=score_result.market_state,
            crowding=score_result.crowding,
        )
    )
    medium_crowding_count = sum(1 for item in score_result.crowding if item.crowding_level == "中拥挤")
    high_crowding_count = sum(1 for item in score_result.crowding if item.crowding_level == "高拥挤")
    extreme_crowding_count = sum(1 for item in score_result.crowding if item.crowding_level == "极高拥挤")

    return PipelineResult(
        trade_date=effective_date,
        stock_count=len(filter_result.tradable),
        excluded_count=len(filter_result.excluded),
        quote_count=quality_report.quote_count,
        data_confidence=quality_report.data_confidence,
        quality_summary=quality_report.summary,
        provider_name=provider_name,
        provider_warnings=tuple(getattr(provider, "last_warnings", ()) or ()),
        market_data_status=quality_report.market_data_status,
        report_path=str(report_path),
        factor_report_path=str(factor_report_path),
        scored_count=len(score_result.scores),
        top50_count=len(score_result.top50),
        s_count=len(score_result.s_list),
        a_count=len(score_result.a_list),
        risk_count=len(score_result.risk_list),
        market_state=score_result.market_state.market_state,
        medium_crowding_count=medium_crowding_count,
        high_crowding_count=high_crowding_count,
        extreme_crowding_count=extreme_crowding_count,
    )
