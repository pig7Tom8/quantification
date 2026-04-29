from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from backend.config import settings
from backend.data_collectors.data_quality_checker import DataQualityChecker
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
    if settings.use_mock_provider:
        notes.append("当前运行使用 mock provider。")

    if not quality_report.formal_output_allowed:
        raise PipelineExecutionError(
            "行情数据不完整，不生成正式评分和正式日报。",
            (quality_report.summary, *quote_result.warnings),
        )

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
    )
