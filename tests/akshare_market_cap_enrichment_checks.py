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
            {"代码": "000001", "名称": "平安银行", "成交额": 1000000000, "最新价": 11.5},
            {"代码": "300750", "名称": "宁德时代", "成交额": 2000000000, "最新价": 445.0},
        ]
    )
    provider._load_industry_map.cache_clear()
    provider._load_concept_map.cache_clear()
    provider._load_industry_map = lambda: {  # type: ignore[method-assign]
        "000001.SZ": "J 金融业",
        "300750.SZ": "C 制造业",
    }
    provider._load_concept_map = lambda: {}  # type: ignore[method-assign]
    provider._load_market_cap_map = lambda stock_codes: {  # type: ignore[method-assign]
        "000001.SZ": (223556177641.0, 223552519523.0),
        "300750.SZ": (2031015656960.0, 1894298249110.0),
    }

    items = provider.fetch_stock_basics()
    market_caps = {item.stock_code: (item.market_cap, item.float_market_cap) for item in items}
    assert market_caps["000001.SZ"] == (223556177641.0, 223552519523.0)
    assert market_caps["300750.SZ"] == (2031015656960.0, 1894298249110.0)
    print("AkShare market cap enrichment checks passed.")


if __name__ == "__main__":
    main()
