from __future__ import annotations

import time as time_module
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from backend.config import settings
from backend.pipeline import PipelineResult, run_phase0_pipeline


def run_daily_job(trade_date: date | None = None) -> PipelineResult:
    return run_phase0_pipeline(trade_date=trade_date)


@dataclass
class SchedulerStatus:
    mode: str
    next_run_at: datetime | None
    last_run_date: date | None = None


class DailySchedulerService:
    def __init__(self) -> None:
        self.daily_time = settings.scheduler_time()
        self.poll_seconds = settings.scheduler_poll_seconds
        self.last_run_date: date | None = None

    def compute_next_run(self, now: datetime) -> datetime:
        candidate = datetime.combine(now.date(), self.daily_time)
        if now >= candidate:
            candidate += timedelta(days=1)
        return candidate

    def should_run(self, now: datetime) -> bool:
        scheduled_for_today = datetime.combine(now.date(), self.daily_time)
        return now >= scheduled_for_today and self.last_run_date != now.date()

    def run_pending(self, now: datetime | None = None) -> PipelineResult | None:
        effective_now = now or datetime.now()
        if not self.should_run(effective_now):
            return None
        result = run_daily_job(trade_date=effective_now.date())
        self.last_run_date = effective_now.date()
        return result

    def status(self, now: datetime | None = None) -> SchedulerStatus:
        effective_now = now or datetime.now()
        return SchedulerStatus(
            mode=settings.scheduler_mode,
            next_run_at=self.compute_next_run(effective_now),
            last_run_date=self.last_run_date,
        )

    def run_forever(self) -> None:
        while True:
            result = self.run_pending()
            if result is not None:
                print(
                    f"daily job completed trade_date={result.trade_date.isoformat()} "
                    f"data_confidence={result.data_confidence} report={result.report_path} "
                    f"market_state={result.market_state} "
                    f"crowding={result.medium_crowding_count}/"
                    f"{result.high_crowding_count}/{result.extreme_crowding_count} "
                    f"factor_report={result.factor_report_path}"
                )
            time_module.sleep(self.poll_seconds)


if __name__ == "__main__":
    mode = settings.scheduler_mode.lower()
    service = DailySchedulerService()

    if mode in {"manual", "once"}:
        result = run_daily_job()
        print(
            f"trade_date={result.trade_date.isoformat()} "
            f"stock_count={result.stock_count} excluded_count={result.excluded_count} "
            f"quote_count={result.quote_count} data_confidence={result.data_confidence} "
            f"report={result.report_path}"
        )
    elif mode == "daily":
        scheduler_status = service.status()
        print(
            f"starting daily scheduler next_run_at={scheduler_status.next_run_at.isoformat()} "
            f"poll_seconds={service.poll_seconds}"
        )
        service.run_forever()
    else:
        raise ValueError(f"Unsupported scheduler mode: {settings.scheduler_mode}")
