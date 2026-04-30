from __future__ import annotations

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.data_collectors.providers.akshare_provider import AkshareProvider


class FakeFrame:
    def __init__(self, rows: list[dict[str, object]]) -> None:
        self._rows = rows

    def iterrows(self):
        for index, row in enumerate(self._rows):
            yield index, row


def main() -> None:
    provider = AkshareProvider()
    provider._load_spot = lambda: FakeFrame(
        [
            {"代码": "000001", "名称": "平安银行", "成交额": 1000000000, "最新价": 11.5, "总市值": 2100e8, "流通市值": 1800e8},
            {"代码": "300750", "名称": "宁德时代", "成交额": 2000000000, "最新价": 445.0, "总市值": 8900e8, "流通市值": 7600e8},
        ]
    )
    provider._load_industry_map.cache_clear()
    provider._load_concept_map.cache_clear()
    provider._load_industry_map = lambda: {  # type: ignore[method-assign]
        "000001.SZ": "J 金融业",
        "300750.SZ": "C 制造业",
    }
    provider._load_concept_map = lambda: {  # type: ignore[method-assign]
        "000001.SZ": "银行;沪深300",
        "300750.SZ": "新能源车;锂电池",
    }
    provider._load_market_cap_map = lambda stock_codes: {  # type: ignore[method-assign]
        "000001.SZ": (2100e8, 1800e8),
        "300750.SZ": (8900e8, 7600e8),
    }

    items = provider.fetch_stock_basics()
    concept_map = {item.stock_code: item.concepts for item in items}
    assert concept_map["000001.SZ"] == "银行;沪深300"
    assert concept_map["300750.SZ"] == "新能源车;锂电池"
    print("AkShare concept enrichment checks passed.")


if __name__ == "__main__":
    main()
