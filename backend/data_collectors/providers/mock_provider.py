from __future__ import annotations

from backend.data_collectors.providers.base_provider import BaseMarketDataProvider
from backend.models import DailyQuote, FundamentalSnapshot, StockBasic


class MockMarketDataProvider(BaseMarketDataProvider):
    provider_name = "mock"

    def fetch_stock_basics(self) -> list[StockBasic]:
        return [
            StockBasic("000001.SZ", "平安银行", "SZ", "银行", "金融;高股息", 2100e8, 1800e8, False, "1991-04-03", "active", 12e8),
            StockBasic("300750.SZ", "宁德时代", "SZ", "电池", "新能源;锂电池", 8900e8, 7600e8, False, "2018-06-11", "active", 68e8),
            StockBasic("688981.SH", "中芯国际", "SH", "半导体", "芯片;国产替代", 4200e8, 3100e8, False, "2020-07-16", "active", 54e8),
            StockBasic("600519.SH", "贵州茅台", "SH", "白酒", "消费;高端白酒", 22000e8, 21000e8, False, "2001-08-27", "active", 35e8),
            StockBasic("002594.SZ", "比亚迪", "SZ", "汽车", "新能源车;电池", 7600e8, 6200e8, False, "2011-06-30", "active", 72e8),
            StockBasic("603000.SH", "*ST示例", "SH", "制造业", "示例概念", 32e8, 28e8, True, "2010-05-10", "risk", 0.4e8),
        ]

    def fetch_daily_quotes(self, stock_codes: list[str], trade_date: str) -> list[DailyQuote]:
        demo_quotes = {
            "000001.SZ": DailyQuote("000001.SZ", trade_date, 10.2, 10.4, 10.1, 10.35, 1.2e8, 12.4e8, 1.21, 1.47, 10.11, 10.02, 9.95, 9.80),
            "300750.SZ": DailyQuote("300750.SZ", trade_date, 201.0, 208.4, 199.8, 206.2, 2.5e7, 52.0e8, 2.48, 2.18, 198.0, 194.0, 189.2, 182.6),
            "688981.SH": DailyQuote("688981.SH", trade_date, 48.6, 50.5, 48.1, 50.2, 8.6e7, 43.8e8, 3.12, 3.93, 47.3, 46.8, 45.4, 43.0),
            "600519.SH": DailyQuote("600519.SH", trade_date, 1698.0, 1710.8, 1685.0, 1705.5, 2.3e6, 39.2e8, 0.21, 0.62, 1680.0, 1665.0, 1640.5, 1608.0),
            "002594.SZ": DailyQuote("002594.SZ", trade_date, 236.1, 242.6, 234.8, 241.8, 3.4e7, 81.0e8, 3.88, 2.54, 232.4, 228.2, 220.6, 210.5),
        }
        return [demo_quotes[code] for code in stock_codes if code in demo_quotes]

    def fetch_fundamentals(self, stock_codes: list[str], trade_date: str) -> list[FundamentalSnapshot]:
        demo_fundamentals = {
            "000001.SZ": FundamentalSnapshot("000001.SZ", trade_date, 4.2, 2.9, 10.6, 0.0, 91.2, 0.0, 0.0),
            "300750.SZ": FundamentalSnapshot("300750.SZ", trade_date, 18.1, 14.6, 18.2, 22.4, 62.5, 286e8, 14e8),
            "688981.SH": FundamentalSnapshot("688981.SH", trade_date, 12.0, 7.5, 7.9, 19.8, 41.0, 96e8, 0.0),
            "600519.SH": FundamentalSnapshot("600519.SH", trade_date, 15.8, 16.3, 31.4, 91.5, 12.4, 410e8, 0.0),
            "002594.SZ": FundamentalSnapshot("002594.SZ", trade_date, 21.3, 19.1, 23.5, 20.1, 68.4, 355e8, 8e8),
        }
        return [demo_fundamentals[code] for code in stock_codes if code in demo_fundamentals]
