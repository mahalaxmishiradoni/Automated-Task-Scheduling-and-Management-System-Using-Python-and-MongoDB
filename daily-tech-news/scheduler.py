import hashlib
import logging
import os
import tempfile
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import portalocker
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from news_collector import collect_news


TIMEZONE = ZoneInfo("Asia/Kolkata")
SCHEDULE_TIME_ENV = "NEWS_SCHEDULE_TIME"
DEFAULT_SCHEDULE_TIME = "08:00"
JOB_ID = "daily-tech-news-collector"

logger = logging.getLogger(__name__)


def get_schedule_time() -> tuple[int, int]:
    """Read and validate the daily collection time in HH:MM format."""
    schedule_time = os.getenv(SCHEDULE_TIME_ENV, DEFAULT_SCHEDULE_TIME)
    try:
        parsed_time = datetime.strptime(schedule_time, "%H:%M")
    except ValueError as error:
        raise ValueError(
            f"{SCHEDULE_TIME_ENV} must be a valid 24-hour time in HH:MM format."
        ) from error
    return parsed_time.hour, parsed_time.minute


def run_scheduled_collection() -> None:
    """Run the collector and log its result or failure."""
    try:
        counts = collect_news()
    except Exception:
        logger.exception("Scheduled news collection failed.")
        raise
    logger.info("Scheduled news collection completed: %s", counts)


def get_lock_file_path() -> Path:
    """Return a temporary lock-file path unique to this project directory."""
    project_path = str(Path(__file__).resolve().parent).casefold()
    project_id = hashlib.sha256(project_path.encode("utf-8")).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / f"daily-tech-news-{project_id}.lock"


def main() -> None:
    """Start one daily collector job in the Asia/Kolkata timezone."""
    hour, minute = get_schedule_time()
    scheduler = BlockingScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        run_scheduled_collection,
        trigger=CronTrigger(hour=hour, minute=minute, timezone=TIMEZONE),
        id=JOB_ID,
        replace_existing=True,
        max_instances=1,
        coalesce=True,
    )

    lock_file = get_lock_file_path()
    try:
        with portalocker.Lock(str(lock_file), mode="a", timeout=0):
            logger.info(
                "Starting daily news collection at %02d:%02d Asia/Kolkata.",
                hour,
                minute,
            )
            scheduler.start()
    except portalocker.exceptions.LockException as error:
        raise SystemExit(
            "Another Daily Global Tech News scheduler instance is already running."
        ) from error


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
