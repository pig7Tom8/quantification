from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import time
from pathlib import Path


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


PROJECT_ROOT = Path(__file__).resolve().parent.parent
_load_env_file(PROJECT_ROOT / ".env")


@dataclass
class Settings:
    project_root: Path = PROJECT_ROOT
    data_dir: Path = PROJECT_ROOT / "data"
    output_dir: Path = PROJECT_ROOT / "output"
    report_dir: Path = PROJECT_ROOT / "output" / "reports"
    sqlite_path: Path = PROJECT_ROOT / "data" / "quant_mvp.db"
    use_mock_provider: bool = os.getenv("USE_MOCK_PROVIDER", "true").lower() == "true"
    provider_order: tuple[str, ...] = tuple(
        item.strip() for item in os.getenv("PROVIDER_ORDER", "akshare,tushare,eastmoney").split(",") if item.strip()
    )
    tushare_token: str = os.getenv("TUSHARE_TOKEN", "")
    market_scope: tuple[str, ...] = ("sh_main", "sz_main", "chi_next", "star")
    min_listing_days: int = int(os.getenv("MIN_LISTING_DAYS", "120"))
    min_avg_amount_20d: float = float(os.getenv("MIN_AVG_AMOUNT_20D", "50000000"))
    scheduler_mode: str = os.getenv("SCHEDULER_MODE", "manual")
    scheduler_daily_time: str = os.getenv("SCHEDULER_DAILY_TIME", "17:00")
    scheduler_poll_seconds: int = int(os.getenv("SCHEDULER_POLL_SECONDS", "30"))
    llm_base_url: str = os.getenv("LLM_BASE_URL", "")
    llm_api_key: str = os.getenv("LLM_API_KEY", "")
    llm_model: str = os.getenv("LLM_MODEL", "")
    feishu_app_id: str = os.getenv("FEISHU_APP_ID", "")
    feishu_app_secret: str = os.getenv("FEISHU_APP_SECRET", "")
    feishu_push_chat_id: str = os.getenv("FEISHU_PUSH_CHAT_ID", "")

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.report_dir.mkdir(parents=True, exist_ok=True)

    def scheduler_time(self) -> time:
        hour_text, minute_text = self.scheduler_daily_time.split(":", 1)
        return time(hour=int(hour_text), minute=int(minute_text))


settings = Settings()
