from __future__ import annotations

from backend.config import settings
from backend.errors import PipelineExecutionError
from backend.scheduler import DailySchedulerService
from backend.scheduler import run_daily_job


if __name__ == "__main__":
    if settings.scheduler_mode.lower() == "daily":
        service = DailySchedulerService()
        status = service.status()
        print("Phase 0 daily scheduler started.")
        print(f"Next run at: {status.next_run_at.isoformat()}")
        print(f"Poll seconds: {service.poll_seconds}")
        service.run_forever()
    else:
        try:
            result = run_daily_job()
        except PipelineExecutionError as exc:
            print("Phase 0 pipeline failed.")
            print(str(exc))
            raise SystemExit(2) from exc

        print("Phase 0 pipeline completed.")
        print(f"Trade date: {result.trade_date.isoformat()}")
        print(f"Tradable stocks: {result.stock_count}")
        print(f"Excluded stocks: {result.excluded_count}")
        print(f"Daily quotes stored: {result.quote_count}")
        print(f"Data confidence: {result.data_confidence}")
        print(f"Market data status: {result.market_data_status}")
        print(f"Quality summary: {result.quality_summary}")
        print(f"Provider: {result.provider_name}")
        print(f"Report: {result.report_path}")
