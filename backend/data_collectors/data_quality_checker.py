from __future__ import annotations

from dataclasses import dataclass

from backend.models import DailyQuote, StockBasic


@dataclass
class DataQualityReport:
    quote_count: int
    stock_count: int
    missing_quotes: list[str]
    invalid_quotes: list[str]
    missing_critical_fields: list[str]
    data_confidence: str
    market_data_status: str
    formal_output_allowed: bool
    summary: str


class DataQualityChecker:
    def evaluate(
        self,
        stocks: list[StockBasic],
        quotes: list[DailyQuote],
        stock_basic_source_status: str = "fresh",
        quote_source_status: str = "fresh",
    ) -> DataQualityReport:
        stock_codes = {item.stock_code for item in stocks}
        quote_map = {item.stock_code: item for item in quotes}

        missing_quotes = sorted(stock_codes - set(quote_map))
        invalid_quotes: list[str] = []
        missing_critical_fields: list[str] = []

        for stock_code, quote in quote_map.items():
            if quote.open <= 0 or quote.high <= 0 or quote.low <= 0 or quote.close <= 0:
                invalid_quotes.append(stock_code)
                continue
            if quote.high < max(quote.open, quote.close, quote.low):
                invalid_quotes.append(stock_code)
                continue
            if quote.low > min(quote.open, quote.close, quote.high):
                invalid_quotes.append(stock_code)
                continue
            if quote.amount < 0 or quote.volume < 0:
                invalid_quotes.append(stock_code)
                continue
            if quote.close == 0 or quote.amount == 0:
                missing_critical_fields.append(stock_code)

        completeness = 1.0 if not stock_codes else (len(quote_map) - len(invalid_quotes)) / len(stock_codes)
        if completeness >= 0.98 and not missing_quotes and not invalid_quotes and stock_basic_source_status == "fresh":
            confidence = "high"
        elif completeness >= 0.95 or stock_basic_source_status == "stale" or quote_source_status == "stale":
            confidence = "medium"
        else:
            confidence = "low"

        market_data_status = "complete"
        formal_output_allowed = True
        if completeness < 0.90 or missing_quotes or invalid_quotes or missing_critical_fields or quote_source_status != "fresh":
            market_data_status = "incomplete"
            formal_output_allowed = False

        summary = (
            f"quotes={len(quote_map)}/{len(stock_codes)} "
            f"missing={len(missing_quotes)} invalid={len(invalid_quotes)} "
            f"critical_missing={len(missing_critical_fields)} "
            f"stock_basic_source={stock_basic_source_status} quote_source={quote_source_status}"
        )
        return DataQualityReport(
            quote_count=len(quote_map),
            stock_count=len(stock_codes),
            missing_quotes=missing_quotes,
            invalid_quotes=invalid_quotes,
            missing_critical_fields=missing_critical_fields,
            data_confidence=confidence,
            market_data_status=market_data_status,
            formal_output_allowed=formal_output_allowed,
            summary=summary,
        )
