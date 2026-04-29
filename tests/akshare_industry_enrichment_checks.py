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
            {"代码": "600519", "名称": "贵州茅台", "成交额": 2000000000, "最新价": 1400.0},
        ]
    )
    provider._load_industry_map.cache_clear()
    provider._load_industry_map = lambda: {  # type: ignore[method-assign]
        "000001.SZ": "J 金融业",
        "600519.SH": "C 制造业",
    }

    items = provider.fetch_stock_basics()
    industry_map = {item.stock_code: item.industry for item in items}
    assert industry_map["000001.SZ"] == "J 金融业"
    assert industry_map["600519.SH"] == "C 制造业"
    print("AkShare industry enrichment checks passed.")


if __name__ == "__main__":
    main()
