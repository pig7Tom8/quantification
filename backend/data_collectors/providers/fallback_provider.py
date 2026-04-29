from __future__ import annotations

import time

from backend.data_collectors.providers.base_provider import BaseMarketDataProvider, ProviderError
from backend.models import DailyQuote, FundamentalSnapshot, StockBasic


class FallbackMarketDataProvider(BaseMarketDataProvider):
    provider_name = "fallback"

    def __init__(
        self,
        providers: list[BaseMarketDataProvider],
        retry_delays: tuple[int, ...] = (10, 60, 0),
        sleeper=time.sleep,
    ) -> None:
        self.providers = providers
        self.retry_delays = retry_delays
        self.sleeper = sleeper
        self.last_provider_name: str | None = None
        self.last_warnings: list[str] = []
        self.attempt_log: list[str] = []
        self.sleep_log: list[int] = []

    def _attempt(self, callback_name: str, *args):
        errors: list[str] = []
        self.attempt_log = []
        self.sleep_log = []
        for provider in self.providers:
            for attempt, delay in enumerate(self.retry_delays, start=1):
                self.attempt_log.append(f"{provider.provider_name}:{callback_name}:attempt{attempt}")
                try:
                    result = getattr(provider, callback_name)(*args)
                    self.last_provider_name = provider.provider_name
                    self.last_warnings = errors
                    return result
                except ProviderError as exc:
                    errors.append(f"{provider.provider_name}:{callback_name}:attempt{attempt}:{exc}")
                    if delay > 0:
                        self.sleep_log.append(delay)
                        self.sleeper(delay)
                    continue
        self.last_provider_name = None
        self.last_warnings = errors
        raise ProviderError("; ".join(errors) if errors else f"all providers failed for {callback_name}")

    def fetch_stock_basics(self) -> list[StockBasic]:
        return self._attempt("fetch_stock_basics")

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        return self._attempt("fetch_daily_quotes", stock_codes, trade_date)

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        try:
            return self._attempt("fetch_fundamentals", stock_codes, trade_date)
        except ProviderError:
            return []
