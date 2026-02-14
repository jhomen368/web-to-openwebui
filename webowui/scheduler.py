"""Scheduling daemon for automated scraping."""

import asyncio
import logging
import signal
import sys
from pathlib import Path

from apscheduler.jobstores.sqlalchemy import SQLAlchemyJobStore
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from .config import SiteConfig, app_config

logger = logging.getLogger(__name__)


# Module-level async functions for APScheduler serialization
async def _execute_scrape_with_retry(site_name: str):
    """Execute scrape with retry logic (module-level for APScheduler serialization)."""
    # Reload config from site name (APScheduler can only serialize simple types)
    site_config = app_config.load_site_config(site_name)

    max_attempts = (
        site_config.schedule_retry_max_attempts if site_config.schedule_retry_enabled else 1
    )
    delay = site_config.schedule_retry_delay_minutes

    for attempt in range(1, max_attempts + 1):
        try:
            logger.info(
                f"Starting scheduled scrape: {site_config.name} (attempt {attempt}/{max_attempts})"
            )
            await _execute_scrape(site_config)
            logger.info(f"Completed scheduled scrape: {site_config.name}")
            return  # Success
        except Exception as e:
            logger.error(
                f"Scrape attempt {attempt} failed for {site_config.name}: {e}", exc_info=True
            )
            if attempt < max_attempts:
                logger.warning(f"Retrying in {delay} minutes...")
                await asyncio.sleep(delay * 60)
            else:
                logger.error(f"All {max_attempts} attempts failed for {site_config.name}")
                # TODO: Send alert (email, webhook, etc.)


async def _execute_scrape(site_config: SiteConfig):
    """Execute a single scrape (same logic as CLI scrape command)."""
    from .cli import _scrape_site

    await _scrape_site(site_config, do_upload=site_config.auto_upload)


class ScraperScheduler:
    """Manages scheduled scraping jobs."""

    def __init__(self, config_dir: Path, outputs_dir: Path):
        """Initialize scheduler with job persistence."""
        jobstore = SQLAlchemyJobStore(url=f"sqlite:///{outputs_dir}/scheduler.db")
        self.scheduler = AsyncIOScheduler(jobstores={"default": jobstore}, timezone="UTC")
        self.config_dir = config_dir
        self.outputs_dir = outputs_dir
        self.jobs: dict[str, SiteConfig] = {}
        self._shutdown_requested = False

        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)

    def load_schedules(self):
        """Load all site configs and register scheduled jobs."""
        site_names = app_config.list_sites()
        logger.info(f"Loading schedules for {len(site_names)} sites")

        active_job_ids = set()

        for site_name in site_names:
            try:
                site_config = app_config.load_site_config(site_name)
                if site_config.schedule_enabled:
                    job_id = self.register_job(site_config)
                    active_job_ids.add(job_id)
                else:
                    logger.debug(f"Skipping {site_name} (scheduling disabled)")
            except Exception as e:
                logger.error(f"Failed to load config for {site_name}: {e}")

        # Prune stale jobs (jobs in DB but not in current config)
        self._prune_stale_jobs(active_job_ids)

    def _prune_stale_jobs(self, active_job_ids: set[str]):
        """Remove jobs that are no longer in the active configuration."""
        # Get all jobs from the scheduler
        # Note: We need to be careful only to touch 'scrape-' jobs managed by us
        all_jobs = self.scheduler.get_jobs()

        for job in all_jobs:
            if job.id.startswith("scrape-") and job.id not in active_job_ids:
                logger.info(f"Removing stale job: {job.id} (config removed or disabled)")
                try:
                    self.scheduler.remove_job(job.id)
                    if job.id in self.jobs:
                        del self.jobs[job.id]
                except Exception as e:
                    logger.error(f"Failed to remove stale job {job.id}: {e}")

    def register_job(self, site_config: SiteConfig) -> str:
        """Register a scheduled scrape job."""
        job_id = f"scrape-{site_config.name}"

        # Create trigger based on schedule type
        if site_config.schedule_type == "cron":
            trigger = CronTrigger.from_crontab(
                site_config.schedule_cron, timezone=site_config.schedule_timezone
            )
        else:  # interval
            trigger = IntervalTrigger(
                **site_config.schedule_interval, timezone=site_config.schedule_timezone
            )

        # Register job with scheduler - use module-level function for serialization
        self.scheduler.add_job(
            _execute_scrape_with_retry,  # Module-level function, not instance method
            trigger=trigger,
            id=job_id,
            args=[site_config.name],  # Pass only string, not entire object
            replace_existing=True,
            max_instances=1,  # Prevent concurrent runs of same job
        )

        self.jobs[job_id] = site_config
        logger.info(f"Registered job: {job_id} ({site_config.schedule_type})")
        return job_id

    def start(self):
        """Start the scheduler daemon."""
        logger.info("Starting scheduler daemon...")

        # Clean up old database records on startup (before loading schedules)
        self._cleanup_database()

        # Run the scheduler initialization and main loop
        asyncio.run(self._run_scheduler())

    async def _run_scheduler(self):
        """Run scheduler within an async context."""
        # Now we're inside a running event loop, so AsyncIOScheduler can be started
        # This loads jobs from the database into memory
        self.scheduler.start()

        # Load site configs and register new/updated jobs
        # This must happen AFTER scheduler.start() so we can see what jobs exist in DB
        self.load_schedules()

        if not self.jobs:
            logger.warning("No scheduled jobs configured!")
            logger.warning("At least one site must have schedule.enabled: true")

        logger.info(f"Scheduler started with {len(self.jobs)} job(s)")

        # Print schedule summary
        for job_id, site_config in self.jobs.items():
            job = self.scheduler.get_job(job_id)
            if job:
                next_run = job.next_run_time
                logger.info(f"  {site_config.name}: Next run at {next_run}")

        # Keep the scheduler running indefinitely
        try:
            while True:
                await asyncio.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            self.shutdown()

    def shutdown(self):
        """Graceful shutdown."""
        if self._shutdown_requested:
            return

        self._shutdown_requested = True
        logger.info("Shutting down scheduler...")
        self.scheduler.shutdown(wait=True)
        logger.info("Scheduler stopped cleanly")

    def _handle_signal(self, signum, frame):
        """Handle shutdown signals."""
        logger.info(f"Received signal {signum}, initiating graceful shutdown...")
        self.shutdown()
        sys.exit(0)

    def _cleanup_database(self):
        """Remove job history older than 30 days."""
        import sqlite3
        from datetime import datetime, timedelta

        db_path = self.outputs_dir / "scheduler.db"

        if not db_path.exists():
            return

        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()

            # Delete records older than 30 days
            cutoff = (datetime.now() - timedelta(days=30)).timestamp()
            cursor.execute(
                "DELETE FROM apscheduler_jobs WHERE next_run_time < ?",
                (cutoff,),
            )

            deleted = cursor.rowcount
            conn.commit()

            # Reclaim unused disk space
            conn.execute("VACUUM")
            conn.close()

            if deleted > 0:
                logger.info(f"DB cleanup: removed {deleted} old job records")
        except Exception as e:
            logger.warning(f"DB cleanup failed (non-critical): {e}")
