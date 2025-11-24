import signal
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger

from webowui.config import SiteConfig
from webowui.scheduler import ScraperScheduler, _execute_scrape, _execute_scrape_with_retry


@pytest.fixture
def mock_scheduler_cls():
    with patch("webowui.scheduler.AsyncIOScheduler") as mock:
        yield mock


@pytest.fixture
def mock_jobstore_cls():
    with patch("webowui.scheduler.SQLAlchemyJobStore") as mock:
        yield mock


@pytest.fixture
def mock_app_config():
    with patch("webowui.scheduler.app_config") as mock:
        yield mock


@pytest.fixture
def scheduler(mock_scheduler_cls, mock_jobstore_cls):
    config_dir = Path("/tmp/config")
    outputs_dir = Path("/tmp/outputs")
    return ScraperScheduler(config_dir, outputs_dir)


class TestScraperScheduler:
    def test_init(self, mock_scheduler_cls, mock_jobstore_cls):
        """Test scheduler initialization."""
        config_dir = Path("/tmp/config")
        outputs_dir = Path("/tmp/outputs")

        scheduler = ScraperScheduler(config_dir, outputs_dir)

        mock_jobstore_cls.assert_called_once_with(url=f"sqlite:///{outputs_dir}/scheduler.db")
        mock_scheduler_cls.assert_called_once()
        assert scheduler.config_dir == config_dir
        assert scheduler.outputs_dir == outputs_dir
        assert scheduler.jobs == {}
        assert scheduler._shutdown_requested is False

    def test_load_schedules(self, scheduler, mock_app_config):
        """Test loading schedules from config."""
        # Setup mock sites
        mock_app_config.list_sites.return_value = ["site1", "site2", "site3"]

        site1_config = MagicMock(spec=SiteConfig)
        site1_config.name = "site1"
        site1_config.schedule_enabled = True
        site1_config.schedule_type = "cron"
        site1_config.schedule_cron = "0 2 * * *"
        site1_config.schedule_timezone = "UTC"

        site2_config = MagicMock(spec=SiteConfig)
        site2_config.name = "site2"
        site2_config.schedule_enabled = False

        def load_config_side_effect(name):
            if name == "site1":
                return site1_config
            elif name == "site2":
                return site2_config
            elif name == "site3":
                raise Exception("Config load error")
            return None

        mock_app_config.load_site_config.side_effect = load_config_side_effect

        # Mock register_job to verify it's called
        with patch.object(scheduler, "register_job") as mock_register:
            scheduler.load_schedules()

            mock_register.assert_called_once_with(site1_config)
            assert (
                len(scheduler.jobs) == 0
            )  # register_job was mocked, so jobs dict not updated here

    def test_register_job_cron(self, scheduler):
        """Test registering a cron job."""
        site_config = MagicMock(spec=SiteConfig)
        site_config.name = "test_site"
        site_config.schedule_type = "cron"
        site_config.schedule_cron = "0 2 * * *"
        site_config.schedule_timezone = "UTC"

        scheduler.register_job(site_config)

        scheduler.scheduler.add_job.assert_called_once()
        call_args = scheduler.scheduler.add_job.call_args
        assert call_args[0][0] == _execute_scrape_with_retry
        assert isinstance(call_args[1]["trigger"], CronTrigger)
        assert call_args[1]["id"] == "scrape-test_site"
        assert call_args[1]["args"] == ["test_site"]
        assert "scrape-test_site" in scheduler.jobs

    def test_register_job_interval(self, scheduler):
        """Test registering an interval job."""
        site_config = MagicMock(spec=SiteConfig)
        site_config.name = "test_site"
        site_config.schedule_type = "interval"
        site_config.schedule_interval = {"hours": 6}
        site_config.schedule_timezone = "UTC"

        scheduler.register_job(site_config)

        scheduler.scheduler.add_job.assert_called_once()
        call_args = scheduler.scheduler.add_job.call_args
        assert isinstance(call_args[1]["trigger"], IntervalTrigger)

    def test_start(self, scheduler):
        """Test starting the scheduler."""
        with (
            patch.object(scheduler, "load_schedules") as mock_load,
            patch("asyncio.run") as mock_asyncio_run,
            patch.object(scheduler, "_run_scheduler", new_callable=MagicMock),
        ):

            # Test with jobs
            scheduler.jobs = {"job1": MagicMock()}
            scheduler.start()

            mock_load.assert_called_once()
            mock_asyncio_run.assert_called_once()

            # Test without jobs (logs warning)
            mock_load.reset_mock()
            mock_asyncio_run.reset_mock()
            scheduler.jobs = {}

            with patch("webowui.scheduler.logger") as mock_logger:
                scheduler.start()
                mock_logger.warning.assert_called()

    @pytest.mark.asyncio
    async def test_run_scheduler(self, scheduler):
        """Test the internal run loop."""
        # Setup a job to test the logging loop
        site_config = MagicMock(spec=SiteConfig)
        site_config.name = "test_site"
        scheduler.jobs = {"job1": site_config}

        mock_job = MagicMock()
        mock_job.next_run_time = "tomorrow"
        scheduler.scheduler.get_job.return_value = mock_job

        # Mock asyncio.sleep to raise SystemExit to break the infinite loop
        with patch("asyncio.sleep", side_effect=[None, SystemExit]):
            import contextlib

            with contextlib.suppress(SystemExit):
                await scheduler._run_scheduler()

            scheduler.scheduler.start.assert_called_once()
            scheduler.scheduler.get_job.assert_called_with("job1")
            scheduler.scheduler.shutdown.assert_called_once()

    def test_shutdown(self, scheduler):
        """Test graceful shutdown."""
        scheduler.shutdown()

        assert scheduler._shutdown_requested is True
        scheduler.scheduler.shutdown.assert_called_once_with(wait=True)

        # Test idempotent
        scheduler.scheduler.shutdown.reset_mock()
        scheduler.shutdown()
        scheduler.scheduler.shutdown.assert_not_called()

    def test_handle_signal(self, scheduler):
        """Test signal handling."""
        with patch("sys.exit") as mock_exit:
            scheduler._handle_signal(signal.SIGTERM, None)

            assert scheduler._shutdown_requested is True
            scheduler.scheduler.shutdown.assert_called_once()
            mock_exit.assert_called_once_with(0)


@pytest.mark.asyncio
async def test_execute_scrape(mock_app_config):
    """Test the execute scrape function."""
    site_config = MagicMock(spec=SiteConfig)
    site_config.auto_upload = True

    with patch("webowui.cli._scrape_site", new_callable=AsyncMock) as mock_scrape_site:
        await _execute_scrape(site_config)
        mock_scrape_site.assert_called_once_with(site_config, do_upload=True)


@pytest.mark.asyncio
async def test_execute_scrape_with_retry(mock_app_config):
    """Test the retry logic wrapper."""
    site_config = MagicMock(spec=SiteConfig)
    site_config.name = "test_site"
    site_config.schedule_retry_enabled = True
    site_config.schedule_retry_max_attempts = 2
    site_config.schedule_retry_delay_minutes = 0.001  # Fast for test
    site_config.auto_upload = False

    mock_app_config.load_site_config.return_value = site_config

    # Mock the actual scrape function
    with patch("webowui.scheduler._execute_scrape", new_callable=AsyncMock) as mock_scrape:
        # Case 1: Success on first try
        await _execute_scrape_with_retry("test_site")
        assert mock_scrape.call_count == 1

        # Case 2: Fail then succeed
        mock_scrape.reset_mock()
        mock_scrape.side_effect = [Exception("Fail"), None]

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await _execute_scrape_with_retry("test_site")
            assert mock_scrape.call_count == 2
            mock_sleep.assert_called_once()

        # Case 3: All fail
        mock_scrape.reset_mock()
        mock_scrape.side_effect = Exception("Fail")

        with patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep:
            await _execute_scrape_with_retry("test_site")
            assert mock_scrape.call_count == 2  # Max attempts


def test_cleanup_database(scheduler, tmp_path):
    """Test that old database records are cleaned up."""
    import sqlite3
    from datetime import datetime, timedelta

    # Create a dummy database
    db_path = tmp_path / "outputs" / "scheduler.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Create table
    cursor.execute("CREATE TABLE apscheduler_jobs (id TEXT, next_run_time REAL, job_state BLOB)")

    # Insert old record (31 days ago)
    old_time = (datetime.now() - timedelta(days=31)).timestamp()
    cursor.execute("INSERT INTO apscheduler_jobs VALUES (?, ?, ?)", ("old_job", old_time, b""))

    # Insert new record (1 day ago)
    new_time = (datetime.now() - timedelta(days=1)).timestamp()
    cursor.execute("INSERT INTO apscheduler_jobs VALUES (?, ?, ?)", ("new_job", new_time, b""))

    conn.commit()
    conn.close()

    # Run cleanup
    scheduler._cleanup_database()

    # Verify old record removed
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM apscheduler_jobs")
    rows = cursor.fetchall()
    conn.close()

    # Debug output
    print(f"Rows found: {rows}")

    # The scheduler fixture uses a different tmp_path than the one passed to this test function
    # We need to make sure the scheduler uses the same outputs_dir as our test database
    scheduler.outputs_dir = tmp_path / "outputs"

    # Run cleanup again with correct path
    scheduler._cleanup_database()

    # Verify old record removed
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM apscheduler_jobs")
    rows = cursor.fetchall()
    conn.close()

    assert len(rows) == 1
    assert rows[0][0] == "new_job"
