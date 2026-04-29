from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from backend.models import DailyQuote, FundamentalSnapshot, StockBasic


class ProviderError(RuntimeError):
    """Raised when a provider cannot return valid data."""


class DisabledProviderError(ProviderError):
    """Raised when a configured provider cannot be initialized."""


@dataclass
class ProviderFetchResult:
    provider_name: str
    stock_basics: list[StockBasic] | None = None
    daily_quotes: list[DailyQuote] | None = None
    fundamentals: list[FundamentalSnapshot] | None = None
    warnings: tuple[str, ...] = ()


class BaseMarketDataProvider(ABC):
    provider_name = "base"

    @abstractmethod
    def fetch_stock_basics(self) -> list[StockBasic]:
        raise NotImplementedError

    @abstractmethod
    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        raise NotImplementedError

    @abstractmethod
    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        raise NotImplementedError

    def healthcheck(self) -> bool:
        return True


class DisabledMarketDataProvider(BaseMarketDataProvider):
    def __init__(self, provider_name: str, reason: str) -> None:
        self.provider_name = provider_name
        self.reason = reason

    def fetch_stock_basics(self) -> list[StockBasic]:
        raise DisabledProviderError(self.reason)

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        raise DisabledProviderError(self.reason)

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        raise DisabledProviderError(self.reason)
