from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from click.testing import CliRunner

from webowui.cli import cli
from webowui.config import SiteConfig


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def mock_app_config():
    with patch("webowui.cli.app_config") as mock:
        yield mock


def test_sites_command_no_sites(runner, mock_app_config):
    """Test 'sites' command when no sites are configured."""
    mock_app_config.list_sites.return_value = []

    result = runner.invoke(cli, ["sites"])

    assert result.exit_code == 0
    assert "No sites configured" in result.output


def test_sites_command_with_sites(runner, mock_app_config):
    """Test 'sites' command with configured sites."""
    mock_app_config.list_sites.return_value = ["site1", "site2"]

    # Mock load_site_config to return a mock config object
    mock_config1 = MagicMock(spec=SiteConfig)
    mock_config1.display_name = "Site 1"
    mock_config1.base_url = "http://site1.com"
    mock_config1.strategy_type = "recursive"

    mock_config2 = MagicMock(spec=SiteConfig)
    mock_config2.display_name = "Site 2"
    mock_config2.base_url = "http://site2.com"
    mock_config2.strategy_type = "selective"

    def side_effect(name):
        if name == "site1":
            return mock_config1
        elif name == "site2":
            return mock_config2
        raise FileNotFoundError(f"Config not found for {name}")

    mock_app_config.load_site_config.side_effect = side_effect

    result = runner.invoke(cli, ["sites"])

    assert result.exit_code == 0
    assert "Configured Sites:" in result.output
    assert "site1" in result.output
    assert "Site 1" in result.output
    assert "http://site1.com" in result.output
    assert "site2" in result.output
    assert "Site 2" in result.output
    assert "http://site2.com" in result.output


def test_sites_command_error_loading(runner, mock_app_config):
    """Test 'sites' command when a site config fails to load."""
    mock_app_config.list_sites.return_value = ["site1"]
    mock_app_config.load_site_config.side_effect = Exception("Load error")

    result = runner.invoke(cli, ["sites"])

    assert result.exit_code == 0
    assert "site1" in result.output
    assert "(error loading)" in result.output


@patch("webowui.cli._scrape_site")
def test_scrape_command_single_site(mock_scrape_site, runner, mock_app_config):
    """Test 'scrape' command for a single site."""
    mock_app_config.load_site_config.return_value.validate.return_value = []

    result = runner.invoke(cli, ["scrape", "--site", "site1"])

    assert result.exit_code == 0
    assert "Scraping site: site1" in result.output
    mock_app_config.load_site_config.assert_called_with("site1")
    mock_scrape_site.assert_called_once()


@patch("webowui.cli._scrape_site")
def test_scrape_command_all_sites(mock_scrape_site, runner, mock_app_config):
    """Test 'scrape' command for all sites."""
    mock_app_config.list_sites.return_value = ["site1", "site2"]
    mock_app_config.load_site_config.return_value.validate.return_value = []

    result = runner.invoke(cli, ["scrape", "--all"])

    assert result.exit_code == 0
    assert "Scraping site: site1" in result.output
    assert "Scraping site: site2" in result.output
    assert mock_scrape_site.call_count == 2


@patch("webowui.cli._scrape_site")
def test_scrape_command_error_handling(mock_scrape_site, runner, mock_app_config):
    """Test 'scrape' command error handling."""
    # Test invalid site
    mock_app_config.load_site_config.side_effect = FileNotFoundError("Config not found")
    result = runner.invoke(cli, ["scrape", "--site", "invalid"])
    assert result.exit_code == 0  # Should handle gracefully
    assert "Error: Config not found" in result.output

    # Test config validation error
    mock_app_config.load_site_config.side_effect = None
    mock_config = MagicMock(spec=SiteConfig)
    mock_config.validate.return_value = ["Invalid URL"]
    mock_app_config.load_site_config.return_value = mock_config

    result = runner.invoke(cli, ["scrape", "--site", "site1"])
    assert result.exit_code == 0
    assert "Configuration errors:" in result.output
    assert "Invalid URL" in result.output
    mock_scrape_site.assert_not_called()


def test_scrape_command_no_args(runner):
    """Test 'scrape' command with no arguments."""
    result = runner.invoke(cli, ["scrape"])

    assert result.exit_code == 1
    assert "Error: Specify --site <name> or --all" in result.output


def test_scrape_command_invalid_config(runner, mock_app_config):
    """Test 'scrape' command with invalid site configuration."""
    mock_app_config.load_site_config.return_value.validate.return_value = ["Invalid URL"]

    result = runner.invoke(cli, ["scrape", "--site", "site1"])

    assert result.exit_code == 0  # Should continue but print errors
    assert "Configuration errors:" in result.output
    assert "Invalid URL" in result.output


@patch("webowui.cli._scrape_site")
def test_scrape_command_exception(mock_scrape_site, runner, mock_app_config):
    """Test 'scrape' command handling exceptions during scrape."""
    mock_app_config.load_site_config.return_value.validate.return_value = []
    mock_scrape_site.side_effect = Exception("Scrape failed")

    result = runner.invoke(cli, ["scrape", "--site", "site1"])

    assert result.exit_code == 0
    assert "Error: Scrape failed" in result.output


@patch("webowui.cli.RetentionManager")
@patch("webowui.cli.OutputManager")
@patch("webowui.cli.WikiCrawler")
@patch("webowui.cli._upload_scrape")
def test_scrape_command_with_retention_and_upload(
    mock_upload,
    mock_crawler_cls,
    mock_output_mgr_cls,
    mock_retention_mgr_cls,
    runner,
    mock_app_config,
):
    """Test 'scrape' command with retention cleanup and auto-upload."""
    # Setup config
    mock_config = MagicMock(spec=SiteConfig)
    mock_config.name = "site1"
    mock_config.validate.return_value = []
    mock_config.retention_enabled = True
    mock_config.retention_auto_cleanup = True
    mock_config.retention_keep_backups = 3
    mock_config.auto_upload = True
    mock_config.knowledge_name = "KB"
    mock_config.knowledge_description = "Desc"
    mock_config.knowledge_id = "kb1"
    mock_app_config.load_site_config.return_value = mock_config

    # Setup crawler
    mock_crawler = mock_crawler_cls.return_value
    mock_crawler.crawl = AsyncMock(return_value=[])
    mock_crawler.get_stats.return_value = {"total_crawled": 10, "total_failed": 0}

    # Setup output manager
    mock_output_mgr = mock_output_mgr_cls.return_value
    mock_output_mgr.save_results.return_value = {"output_dir": "out", "timestamp": "t1"}

    # Setup retention manager
    mock_retention_mgr = mock_retention_mgr_cls.return_value
    mock_retention_mgr.apply_retention.return_value = {"deleted": 1, "kept_timestamps": ["t1"]}

    result = runner.invoke(cli, ["scrape", "--site", "site1", "--upload"])

    assert result.exit_code == 0
    assert "Scrape complete" in result.output
    assert "Retention: Deleted 1 old backups" in result.output
    assert "Uploading to OpenWebUI" in result.output
    mock_upload.assert_called_once()


@patch("webowui.cli._upload_scrape")
def test_upload_command(mock_upload_scrape, runner, mock_app_config):
    """Test 'upload' command."""
    mock_config = MagicMock(spec=SiteConfig)
    mock_config.knowledge_id = "kb1"
    mock_config.knowledge_name = "KB 1"
    mock_config.knowledge_description = "Description"
    mock_config.preserve_deleted_files = False
    mock_config.cleanup_untracked = False
    mock_app_config.load_site_config.return_value = mock_config

    result = runner.invoke(cli, ["upload", "--site", "site1"])

    assert result.exit_code == 0
    mock_upload_scrape.assert_called_once()

    # Verify arguments passed to _upload_scrape
    args = mock_upload_scrape.call_args[0]
    assert args[0] == "site1"
    assert args[1] is None  # from_timestamp
    assert args[2] is True  # incremental (default)
    assert args[3] == "KB 1"
    assert args[4] == "Description"
    assert args[5] == "kb1"
    assert args[6] is False  # keep_files
    assert args[7] is False  # cleanup_untracked


@patch("webowui.cli.MetadataTracker")
@patch("webowui.cli._upload_scrape")
def test_upload_command_from_timestamp(
    mock_upload_scrape, mock_tracker_cls, runner, mock_app_config
):
    """Test 'upload' command with --from-timestamp."""
    mock_config = MagicMock(spec=SiteConfig)
    mock_config.knowledge_id = "kb1"
    mock_config.knowledge_name = "KB 1"
    mock_config.knowledge_description = "Desc"
    mock_config.preserve_deleted_files = False
    mock_config.cleanup_untracked = False
    mock_app_config.load_site_config.return_value = mock_config

    # We need to mock _upload_scrape to verify it's called correctly
    # But wait, _upload_scrape is the function being called by the command.
    # The command calls asyncio.run(_upload_scrape(...))
    # So we are mocking the internal function call.

    result = runner.invoke(cli, ["upload", "--site", "site1", "--from-timestamp", "t1"])

    assert result.exit_code == 0
    mock_upload_scrape.assert_called_once()
    args = mock_upload_scrape.call_args[0]
    assert args[1] == "t1"  # from_timestamp


@patch("webowui.cli.CurrentDirectoryManager")
def test_upload_command_current_missing(mock_cdm_cls, runner, mock_app_config):
    """Test 'upload' command when current directory is missing."""
    # This test needs to run the actual _upload_scrape logic up to the point of checking current dir
    # But _upload_scrape is an async function called via asyncio.run inside the command.
    # If we don't mock _upload_scrape, the command will try to run it.
    # However, the command implementation calls _upload_scrape.
    # The logic for checking current directory is INSIDE _upload_scrape.
    # So we should test _upload_scrape directly or let the command run it.
    # If we let the command run it, we need to mock dependencies used inside _upload_scrape.

    # Let's test the command's invocation of _upload_scrape, and then test _upload_scrape separately?
    # Or we can use the fact that we are testing the CLI command wrapper here.
    # The CLI command wrapper just calls _upload_scrape.
    # The logic "Current directory does not exist" is inside _upload_scrape.
    # So to test that output, we need to NOT mock _upload_scrape, but mock what it uses.

    mock_config = MagicMock(spec=SiteConfig)
    mock_config.knowledge_id = "kb1"
    mock_config.knowledge_name = "KB 1"
    mock_config.knowledge_description = "Desc"
    mock_config.preserve_deleted_files = False
    mock_config.cleanup_untracked = False
    mock_app_config.load_site_config.return_value = mock_config
    mock_app_config.validate_openwebui_config.return_value = []

    mock_cdm = mock_cdm_cls.return_value
    mock_cdm.get_current_state.return_value = None  # Missing current

    # We need to patch asyncio.run to run the coroutine synchronously or just let it run if dependencies are mocked.
    # Since _upload_scrape is async, we can use `runner.invoke` which runs the command.
    # The command calls `asyncio.run(_upload_scrape(...))`.
    # We need to make sure `_upload_scrape` doesn't hit real network/disk.

    with patch("webowui.cli.OpenWebUIClient"):
        result = runner.invoke(cli, ["upload", "--site", "site1"])

    assert result.exit_code == 1
    assert "Current directory does not exist" in result.output


@patch("webowui.cli._upload_scrape")
def test_upload_command_with_options(mock_upload_scrape, runner, mock_app_config):
    """Test 'upload' command with CLI options overriding config."""
    mock_config = MagicMock(spec=SiteConfig)
    mock_config.knowledge_id = "kb1"
    mock_config.knowledge_name = "KB 1"
    mock_config.knowledge_description = "Description"
    mock_config.preserve_deleted_files = False
    mock_config.cleanup_untracked = False
    mock_app_config.load_site_config.return_value = mock_config

    result = runner.invoke(
        cli,
        [
            "upload",
            "--site",
            "site1",
            "--full",
            "--knowledge-id",
            "kb2",
            "--knowledge-name",
            "KB 2",
            "--keep-files",
            "--cleanup-untracked",
        ],
    )

    assert result.exit_code == 0
    mock_upload_scrape.assert_called_once()

    args = mock_upload_scrape.call_args[0]
    assert args[0] == "site1"
    assert args[2] is False  # incremental=False (full)
    assert args[3] == "KB 2"
    assert args[5] == "kb2"
    assert args[6] is True  # keep_files
    assert args[7] is True  # cleanup_untracked


@patch("webowui.cli._upload_scrape")
def test_upload_command_incremental(mock_upload_scrape, runner, mock_app_config):
    """Test 'upload' command with --incremental flag."""
    mock_config = MagicMock(spec=SiteConfig)
    mock_config.knowledge_id = "kb1"
    mock_config.knowledge_name = "KB 1"
    mock_config.knowledge_description = "Description"
    mock_config.preserve_deleted_files = False
    mock_config.cleanup_untracked = False
    mock_app_config.load_site_config.return_value = mock_config
    mock_app_config.validate_openwebui_config.return_value = []

    result = runner.invoke(cli, ["upload", "--site", "site1", "--incremental"])

    assert result.exit_code == 0
    mock_upload_scrape.assert_called_once()
    args = mock_upload_scrape.call_args[0]
    assert args[2] is True  # incremental


@patch("webowui.cli._upload_scrape")
def test_upload_command_full(mock_upload_scrape, runner, mock_app_config):
    """Test 'upload' command with --full flag."""
    mock_config = MagicMock(spec=SiteConfig)
    mock_config.knowledge_id = "kb1"
    mock_config.knowledge_name = "KB 1"
    mock_config.knowledge_description = "Description"
    mock_config.preserve_deleted_files = False
    mock_config.cleanup_untracked = False
    mock_app_config.load_site_config.return_value = mock_config

    result = runner.invoke(cli, ["upload", "--site", "site1", "--full"])

    assert result.exit_code == 0
    mock_upload_scrape.assert_called_once()
    args = mock_upload_scrape.call_args[0]
    assert args[2] is False  # incremental


@patch("webowui.cli._upload_scrape")
def test_upload_command_keep_files(mock_upload_scrape, runner, mock_app_config):
    """Test 'upload' command with --keep-files flag."""
    mock_config = MagicMock(spec=SiteConfig)
    mock_config.knowledge_id = "kb1"
    mock_config.knowledge_name = "KB 1"
    mock_config.knowledge_description = "Description"
    mock_config.preserve_deleted_files = False
    mock_config.cleanup_untracked = False
    mock_app_config.load_site_config.return_value = mock_config

    result = runner.invoke(cli, ["upload", "--site", "site1", "--keep-files"])

    assert result.exit_code == 0
    mock_upload_scrape.assert_called_once()
    args = mock_upload_scrape.call_args[0]
    assert args[6] is True  # keep_files


def test_upload_command_config_error(runner, mock_app_config):
    """Test 'upload' command when config fails to load."""
    mock_app_config.load_site_config.side_effect = FileNotFoundError("Config missing")

    result = runner.invoke(cli, ["upload", "--site", "site1"])

    assert result.exit_code == 1
    assert "Error: Config missing" in result.output


def test_validate_command_valid(runner, mock_app_config):
    """Test 'validate' command with valid configuration."""
    mock_app_config.list_sites.return_value = ["site1"]
    mock_config = MagicMock(spec=SiteConfig)
    mock_config.validate.return_value = []
    mock_app_config.load_site_config.return_value = mock_config

    result = runner.invoke(cli, ["validate"])

    assert result.exit_code == 0
    assert "site1" in result.output
    assert "✓ Valid" in result.output
    assert "All configurations valid" in result.output


def test_validate_command_invalid(runner, mock_app_config):
    """Test 'validate' command with invalid configuration."""
    mock_app_config.list_sites.return_value = ["site1"]
    mock_config = MagicMock(spec=SiteConfig)
    mock_config.validate.return_value = ["Invalid URL"]
    mock_app_config.load_site_config.return_value = mock_config

    result = runner.invoke(cli, ["validate"])

    assert result.exit_code == 1
    assert "site1" in result.output
    assert "✗ Errors" in result.output
    assert "Invalid URL" in result.output
    assert "Some configurations have errors" in result.output


def test_validate_command_specific_site(runner, mock_app_config):
    """Test 'validate' command for a specific site."""
    mock_config = MagicMock(spec=SiteConfig)
    mock_config.validate.return_value = []
    mock_app_config.load_site_config.return_value = mock_config

    result = runner.invoke(cli, ["validate", "--site", "site1"])

    assert result.exit_code == 0
    assert "site1" in result.output
    mock_app_config.load_site_config.assert_called_with("site1")


def test_validate_command_missing_config(runner, mock_app_config):
    """Test 'validate' command when config file is missing."""
    mock_app_config.list_sites.return_value = ["site1"]
    mock_app_config.load_site_config.side_effect = FileNotFoundError("Config missing")

    result = runner.invoke(cli, ["validate"])

    assert result.exit_code == 1
    assert "site1" in result.output
    assert "Config file not found" in result.output


@patch("webowui.cli.OpenWebUIClient")
@patch("os.access")
@patch("webowui.cli.asyncio.run")
def test_health_command_healthy(
    mock_asyncio_run, mock_access, mock_client_cls, runner, mock_app_config
):
    """Test 'health' command when system is healthy."""
    # Mock file system checks
    mock_app_config.config_dir.exists.return_value = True
    mock_app_config.outputs_dir.exists.return_value = True
    mock_access.return_value = True
    mock_app_config.list_sites.return_value = ["site1"]

    # Mock API check
    mock_app_config.openwebui_api_key = "key"
    mock_asyncio_run.return_value = True

    result = runner.invoke(cli, ["health"])

    assert result.exit_code == 0
    assert '"status": "healthy"' in result.output
    assert '"api_reachable": true' in result.output
    mock_asyncio_run.assert_called_once()


@patch("os.access")
def test_health_command_unhealthy(mock_access, runner, mock_app_config):
    """Test 'health' command when system is unhealthy."""
    # Mock file system checks failure
    mock_app_config.config_dir.exists.return_value = False
    mock_app_config.outputs_dir.exists.return_value = False
    mock_access.return_value = False
    mock_app_config.list_sites.return_value = []
    mock_app_config.openwebui_api_key = None

    result = runner.invoke(cli, ["health"])

    assert result.exit_code == 1
    assert '"status": "unhealthy"' in result.output
    assert '"config_dir": false' in result.output
    assert '"outputs_dir": false' in result.output
    assert '"sites_configured": false' in result.output


@patch("webowui.cli.OpenWebUIClient")
@patch("os.access")
@patch("webowui.cli.asyncio.run")
def test_health_command_api_failure(
    mock_asyncio_run, mock_access, mock_client_cls, runner, mock_app_config
):
    """Test 'health' command when API check fails."""
    # Mock file system checks success
    mock_app_config.config_dir.exists.return_value = True
    mock_app_config.outputs_dir.exists.return_value = True
    mock_access.return_value = True
    mock_app_config.list_sites.return_value = ["site1"]

    # Mock API check failure
    mock_app_config.openwebui_api_key = "key"
    mock_asyncio_run.return_value = False

    result = runner.invoke(cli, ["health"])

    assert result.exit_code == 1
    assert '"status": "unhealthy"' in result.output
    assert '"api_reachable": false' in result.output
    mock_asyncio_run.assert_called_once()


@patch("webowui.cli.MetadataTracker")
def test_list_sites_command(mock_tracker_cls, runner, mock_app_config):
    """Test 'list' command."""
    mock_app_config.list_sites.return_value = ["site1"]
    mock_tracker = mock_tracker_cls.return_value
    mock_tracker.get_all_scrapes.return_value = [
        {
            "scrape": {"timestamp": "2023-01-01_12-00-00"},
            "statistics": {"total_pages": 10, "successful": 9, "failed": 1},
        }
    ]
    mock_tracker.get_upload_status.return_value = {"uploaded": True}

    result = runner.invoke(cli, ["list"])

    assert result.exit_code == 0
    assert "site1" in result.output
    assert "2023-01-01_12-00-00" in result.output
    assert "10" in result.output
    assert "✓" in result.output


@patch("webowui.cli.MetadataTracker")
def test_list_sites_command_filter(mock_tracker_cls, runner, mock_app_config):
    """Test 'list' command with --site filter."""
    mock_tracker = mock_tracker_cls.return_value
    mock_tracker.get_all_scrapes.return_value = []

    result = runner.invoke(cli, ["list", "--site", "site1"])

    assert result.exit_code == 0
    mock_tracker_cls.assert_called_with(mock_app_config.outputs_dir, "site1")


@patch("webowui.cli.MetadataTracker")
def test_diff_command(mock_tracker_cls, runner, mock_app_config):
    """Test 'diff' command."""
    mock_app_config.load_site_config.return_value = MagicMock()
    mock_tracker = mock_tracker_cls.return_value
    mock_tracker.compare_scrapes.return_value = {
        "statistics": {
            "added_count": 1,
            "modified_count": 1,
            "removed_count": 1,
            "unchanged_count": 5,
        },
        "changes": {
            "added": ["http://site.com/new"],
            "modified": ["http://site.com/mod"],
            "removed": ["http://site.com/del"],
        },
    }

    result = runner.invoke(cli, ["diff", "--site", "site1", "--old", "t1", "--new", "t2"])

    assert result.exit_code == 0
    assert "Comparison: t1 → t2" in result.output
    assert "Added: 1" in result.output
    assert "Modified: 1" in result.output
    assert "Removed: 1" in result.output
    assert "+ http://site.com/new" in result.output
    assert "~ http://site.com/mod" in result.output
    assert "- http://site.com/del" in result.output


@patch("webowui.cli.MetadataTracker")
def test_diff_command_error(mock_tracker_cls, runner, mock_app_config):
    """Test 'diff' command with error."""
    mock_app_config.load_site_config.return_value = MagicMock()
    mock_tracker = mock_tracker_cls.return_value
    mock_tracker.compare_scrapes.return_value = {"error": "Scrape not found"}

    result = runner.invoke(cli, ["diff", "--site", "site1", "--old", "t1", "--new", "t2"])

    assert result.exit_code == 1
    assert "Scrape not found" in result.output


@patch("webowui.cli.MetadataTracker")
def test_clean_command(mock_tracker_cls, runner, mock_app_config):
    """Test 'clean' command."""
    mock_app_config.list_sites.return_value = ["site1"]
    mock_tracker = mock_tracker_cls.return_value
    # Mock 6 scrapes to trigger cleanup (keep default is 5)
    mock_tracker.get_all_scrapes.return_value = [{} for _ in range(6)]

    result = runner.invoke(cli, ["clean", "--all"])

    assert result.exit_code == 0
    assert "Removing 1 old scrapes" in result.output
    mock_tracker.cleanup_old_scrapes.assert_called_with(5)


@patch("webowui.cli.MetadataTracker")
def test_clean_command_dry_run(mock_tracker_cls, runner, mock_app_config):
    """Test 'clean' command with dry-run (simulated by checking output)."""
    # Note: The clean command doesn't have a --dry-run flag in the current implementation
    # It just prints what it's doing.
    # But we can test that it correctly identifies scrapes to remove.
    mock_app_config.list_sites.return_value = ["site1"]
    mock_tracker = mock_tracker_cls.return_value
    mock_tracker.get_all_scrapes.return_value = [{} for _ in range(6)]

    result = runner.invoke(cli, ["clean", "--site", "site1", "--keep", "5"])

    assert result.exit_code == 0
    assert "Removing 1 old scrapes" in result.output
    mock_tracker.cleanup_old_scrapes.assert_called_with(5)


@patch("webowui.utils.reclean.reclean_directory")
@patch("webowui.cli.CurrentDirectoryManager")
def test_reclean_command(mock_cdm_cls, mock_reclean_dir, runner, mock_app_config):
    """Test 'reclean' command."""
    mock_config = MagicMock(spec=SiteConfig)
    mock_config.cleaning_profile_name = "profile1"
    mock_app_config.load_site_config.return_value = mock_config

    mock_cdm = mock_cdm_cls.return_value
    mock_cdm.get_current_state.return_value = {"source_timestamp": "t1"}
    mock_cdm.content_dir = Path("/path/to/content")

    # We need to patch where it is imported in cli.py, but it is imported inside the function.
    # So we patch the module where it is defined.
    # Wait, if it is imported inside the function, we should patch 'webowui.utils.reclean.reclean_directory'
    # and since we are running the cli command which imports it, that should work.

    result = runner.invoke(cli, ["reclean", "--site", "site1"])

    assert result.exit_code == 0
    assert "Re-cleaning content for site1" in result.output
    assert "Profile: profile1" in result.output
    mock_reclean_dir.assert_called_with(Path("/path/to/content"), "profile1")


@patch("webowui.cli.CurrentDirectoryManager")
def test_show_current_command(mock_cdm_cls, runner, mock_app_config):
    """Test 'show-current' command."""
    mock_app_config.load_site_config.return_value = MagicMock()
    mock_cdm = mock_cdm_cls.return_value
    mock_cdm.get_current_state.return_value = {
        "source_timestamp": "2023-01-01",
        "total_files": 100,
        "total_size": 10240,
        "last_updated": "now",
        "files": [{"filepath": "f1"}],
    }
    mock_cdm.get_upload_status.return_value = {
        "knowledge_id": "kb1",
        "last_upload": "yesterday",
        "files": [],
    }

    result = runner.invoke(cli, ["show-current", "--site", "site1", "--verbose"])

    assert result.exit_code == 0
    assert "Current Directory Status" in result.output
    assert "Source: 2023-01-01" in result.output
    assert "Files: 100" in result.output
    assert "Knowledge ID: kb1" in result.output
    assert "f1" in result.output


@patch("webowui.cli.CurrentDirectoryManager")
def test_show_current_command_missing(mock_cdm_cls, runner, mock_app_config):
    """Test 'show-current' command when directory is missing."""
    mock_app_config.load_site_config.return_value = MagicMock()
    mock_cdm = mock_cdm_cls.return_value
    mock_cdm.get_current_state.return_value = None

    result = runner.invoke(cli, ["show-current", "--site", "site1"])

    assert result.exit_code == 0
    assert "Current directory does not exist" in result.output


@patch("webowui.cli.CurrentDirectoryManager")
@patch("webowui.cli.MetadataTracker")
def test_rebuild_current_command(mock_tracker_cls, mock_cdm_cls, runner, mock_app_config):
    """Test 'rebuild-current' command."""
    mock_app_config.load_site_config.return_value = MagicMock()

    mock_cdm = mock_cdm_cls.return_value
    mock_cdm.get_current_state.return_value = None  # Current doesn't exist
    mock_cdm.rebuild_from_timestamp.return_value = {"summary": "Rebuilt successfully"}

    mock_tracker = mock_tracker_cls.return_value
    mock_tracker.get_latest_scrape.return_value = {"scrape": {"timestamp": "t1"}}

    result = runner.invoke(cli, ["rebuild-current", "--site", "site1"])

    assert result.exit_code == 0
    assert "Rebuilding current/ from t1" in result.output
    assert "Rebuilt successfully" in result.output
    mock_cdm.rebuild_from_timestamp.assert_called_with("t1")


@patch("webowui.cli.CurrentDirectoryManager")
def test_rebuild_current_command_exists(mock_cdm_cls, runner, mock_app_config):
    """Test 'rebuild-current' command when current directory already exists."""
    mock_app_config.load_site_config.return_value = MagicMock()
    mock_cdm = mock_cdm_cls.return_value
    mock_cdm.get_current_state.return_value = {
        "source_timestamp": "t1",
        "total_files": 10,
        "last_updated": "now",
    }

    # Test with abort
    result = runner.invoke(cli, ["rebuild-current", "--site", "site1"], input="n\n")
    assert result.exit_code == 0
    assert "Current directory already exists" in result.output
    assert "Cancelled" in result.output

    # Test with force
    mock_cdm.rebuild_from_timestamp.return_value = {"summary": "Rebuilt"}
    # We need to mock get_latest_scrape because if we force, it proceeds to get timestamp
    with patch("webowui.cli.MetadataTracker") as mock_tracker_cls:
        mock_tracker = mock_tracker_cls.return_value
        mock_tracker.get_latest_scrape.return_value = {"scrape": {"timestamp": "t2"}}

        result = runner.invoke(cli, ["rebuild-current", "--site", "site1", "--force"])
        assert result.exit_code == 0
        assert "Rebuilding current/ from t2" in result.output


@patch("webowui.cli.CurrentDirectoryManager")
@patch("webowui.cli.OpenWebUIClient")
@patch("webowui.cli.StateManager")
def test_rebuild_state_command(
    mock_state_mgr_cls, mock_client_cls, mock_cdm_cls, runner, mock_app_config
):
    """Test 'rebuild-state' command."""
    mock_app_config.load_site_config.return_value = MagicMock(
        display_name="Site 1", knowledge_id="kb1"
    )
    mock_app_config.validate_openwebui_config.return_value = []
    mock_app_config.openwebui_api_key = "key"

    mock_cdm = mock_cdm_cls.return_value
    mock_cdm.metadata_file.exists.return_value = True
    mock_cdm.get_upload_status.return_value = None

    mock_client = mock_client_cls.return_value
    mock_client.test_connection = AsyncMock(return_value=True)

    mock_state_mgr = mock_state_mgr_cls.return_value
    mock_state_mgr.rebuild_from_remote = AsyncMock(
        return_value=(
            True,
            {
                "knowledge_id": "kb1",
                "files_uploaded": 10,
                "rebuild_confidence": "high",
                "rebuild_match_rate": 1.0,
            },
            None,
        )
    )

    result = runner.invoke(cli, ["rebuild-state", "--site", "site1"])

    assert result.exit_code == 0
    assert "State rebuilt successfully" in result.output
    assert "Confidence: high" in result.output


@patch("webowui.cli.CurrentDirectoryManager")
@patch("webowui.cli.OpenWebUIClient")
@patch("webowui.cli.StateManager")
def test_rebuild_state_command_real_async(
    mock_state_mgr_cls, mock_client_cls, mock_cdm_cls, runner, mock_app_config
):
    """Test 'rebuild-state' command with real asyncio.run."""
    mock_app_config.load_site_config.return_value = MagicMock(
        display_name="Site 1", knowledge_id="kb1"
    )
    mock_app_config.validate_openwebui_config.return_value = []
    mock_app_config.openwebui_api_key = "key"

    mock_cdm = mock_cdm_cls.return_value
    mock_cdm.metadata_file.exists.return_value = True
    mock_cdm.get_upload_status.return_value = None

    mock_client = mock_client_cls.return_value
    mock_client.test_connection = AsyncMock(return_value=True)

    mock_state_mgr = mock_state_mgr_cls.return_value
    mock_state_mgr.rebuild_from_remote = AsyncMock(
        return_value=(
            True,
            {
                "knowledge_id": "kb1",
                "files_uploaded": 10,
                "rebuild_confidence": "high",
                "rebuild_match_rate": 1.0,
            },
            None,
        )
    )

    result = runner.invoke(cli, ["rebuild-state", "--site", "site1"])

    assert result.exit_code == 0
    assert "State rebuilt successfully" in result.output
    assert "Confidence: high" in result.output


@patch("webowui.cli.CurrentDirectoryManager")
@patch("webowui.cli.OpenWebUIClient")
@patch("webowui.cli.StateManager")
def test_check_state_command(
    mock_state_mgr_cls, mock_client_cls, mock_cdm_cls, runner, mock_app_config
):
    """Test 'check-state' command."""
    mock_app_config.load_site_config.return_value = MagicMock(
        display_name="Site 1", knowledge_id="kb1"
    )
    mock_app_config.validate_openwebui_config.return_value = []
    mock_app_config.openwebui_api_key = "key"

    mock_cdm = mock_cdm_cls.return_value
    mock_cdm.get_upload_status.return_value = {"knowledge_id": "kb1"}

    mock_client = mock_client_cls.return_value
    mock_client.test_connection = AsyncMock(return_value=True)

    mock_state_mgr = mock_state_mgr_cls.return_value
    mock_state_mgr.check_health = AsyncMock(
        return_value={
            "status": "healthy",
            "local_file_count": 10,
            "remote_file_count": 10,
            "issues": [],
            "recommendation": None,
        }
    )

    result = runner.invoke(cli, ["check-state", "--site", "site1"])

    assert result.exit_code == 0
    assert "Checking state health for site1" in result.output
    assert "Status: HEALTHY" in result.output
    assert "Local files: 10" in result.output
    assert "Remote files: 10" in result.output


@patch("webowui.cli.CurrentDirectoryManager")
@patch("webowui.cli.OpenWebUIClient")
@patch("webowui.cli.StateManager")
def test_sync_command_with_fix(
    mock_state_mgr_cls, mock_client_cls, mock_cdm_cls, runner, mock_app_config
):
    """Test 'sync' command with --fix flag."""
    mock_app_config.load_site_config.return_value = MagicMock()
    mock_app_config.openwebui_api_key = "key"

    mock_client = mock_client_cls.return_value
    mock_client.test_connection = AsyncMock(return_value=True)

    mock_state_mgr = mock_state_mgr_cls.return_value
    mock_state_mgr.sync_state = AsyncMock(
        return_value={
            "success": True,
            "local_count": 10,
            "remote_count": 10,
            "in_sync_count": 9,
            "missing_remote": {"file1"},
            "extra_remote": set(),
            "local_file_map": {"file1": {"filename": "f1"}},
            "remote_files": [],
            "fixed_count": 1,
        }
    )

    result = runner.invoke(cli, ["sync", "--site", "site1", "--fix"])

    assert result.exit_code == 0
    assert "Files in local state but missing from OpenWebUI: 1" in result.output
    assert "Fixed: Removed 1 files" in result.output


@patch("webowui.cli.CurrentDirectoryManager")
@patch("webowui.cli.OpenWebUIClient")
@patch("webowui.cli.StateManager")
def test_sync_command(mock_state_mgr_cls, mock_client_cls, mock_cdm_cls, runner, mock_app_config):
    """Test 'sync' command."""
    mock_app_config.load_site_config.return_value = MagicMock()
    mock_app_config.openwebui_api_key = "key"

    mock_client = mock_client_cls.return_value
    mock_client.test_connection = AsyncMock(return_value=True)

    mock_state_mgr = mock_state_mgr_cls.return_value
    mock_state_mgr.sync_state = AsyncMock(
        return_value={
            "success": True,
            "local_count": 10,
            "remote_count": 10,
            "in_sync_count": 8,
            "missing_remote": {"file1"},
            "extra_remote": {"file2"},
            "local_file_map": {"file1": {"filename": "f1"}},
            "remote_files": [{"id": "file2", "filename": "f2"}],
            "fixed_count": 1,
        }
    )

    result = runner.invoke(cli, ["sync", "--site", "site1", "--fix"])

    assert result.exit_code == 0
    assert "Files in local state but missing from OpenWebUI: 1" in result.output
    assert "Files in OpenWebUI but not in local state: 1" in result.output
    assert "Fixed: Removed 1 files" in result.output


@patch("webowui.cli.RetentionManager")
def test_rollback_command_list(mock_retention_mgr_cls, runner, mock_app_config):
    """Test 'rollback' command with --list."""
    mock_app_config.load_site_config.return_value = MagicMock()
    mock_app_config.outputs_dir = MagicMock()
    mock_app_config.outputs_dir.__truediv__.return_value.exists.return_value = True

    mock_retention_mgr = mock_retention_mgr_cls.return_value
    mock_retention_mgr.get_scrape_directories.return_value = [
        MagicMock(name="2023-01-01"),
        MagicMock(name="2023-01-02"),
    ]
    # Fix: name attribute on MagicMock needs to be set differently or accessed differently if it's a path object
    # Let's assume get_scrape_directories returns Path objects or similar that have a .name attribute
    mock_retention_mgr.get_scrape_directories.return_value[0].name = "2023-01-01"
    mock_retention_mgr.get_scrape_directories.return_value[1].name = "2023-01-02"

    mock_retention_mgr.get_current_source.return_value = "2023-01-02"

    result = runner.invoke(cli, ["rollback", "--site", "site1", "--list"])

    assert result.exit_code == 0
    assert "Available Backups for site1" in result.output
    assert "2023-01-01" in result.output
    assert "2023-01-02" in result.output
    assert "Active Source" in result.output


@patch("webowui.cli.RetentionManager")
def test_rollback_command_no_backups(mock_retention_mgr_cls, runner, mock_app_config):
    """Test 'rollback' command with no backups."""
    mock_app_config.load_site_config.return_value = MagicMock()
    mock_app_config.outputs_dir = MagicMock()
    mock_app_config.outputs_dir.__truediv__.return_value.exists.return_value = True

    mock_retention_mgr = mock_retention_mgr_cls.return_value
    mock_retention_mgr.get_scrape_directories.return_value = []

    result = runner.invoke(cli, ["rollback", "--site", "site1"])

    assert result.exit_code == 0
    assert "No backups found" in result.output


@patch("webowui.cli.RetentionManager")
@patch("webowui.cli.CurrentDirectoryManager")
def test_rollback_command_perform(mock_cdm_cls, mock_retention_mgr_cls, runner, mock_app_config):
    """Test 'rollback' command performing rollback."""
    mock_app_config.load_site_config.return_value = MagicMock()
    mock_app_config.outputs_dir = MagicMock()
    site_dir = mock_app_config.outputs_dir.__truediv__.return_value
    site_dir.exists.return_value = True
    # Mock backup dir exists
    site_dir.__truediv__.return_value.exists.return_value = True

    mock_retention_mgr = mock_retention_mgr_cls.return_value
    mock_retention_mgr.get_scrape_directories.return_value = [MagicMock(name="2023-01-01")]
    mock_retention_mgr.get_scrape_directories.return_value[0].name = "2023-01-01"

    mock_cdm = mock_cdm_cls.return_value
    mock_cdm.rebuild_from_timestamp.return_value = {"summary": "Rollback successful"}

    # Use --force to skip confirmation
    result = runner.invoke(cli, ["rollback", "--site", "site1", "--force"])

    assert result.exit_code == 0
    assert "Rolling back to 2023-01-01" in result.output
    assert "Rollback successful" in result.output
    mock_cdm.rebuild_from_timestamp.assert_called_with("2023-01-01")


@patch("webowui.cli.RetentionManager")
@patch("webowui.cli.CurrentDirectoryManager")
def test_rollback_command_interactive(
    mock_cdm_cls, mock_retention_mgr_cls, runner, mock_app_config
):
    """Test 'rollback' command with interactive confirmation."""
    mock_app_config.load_site_config.return_value = MagicMock()
    mock_app_config.outputs_dir = MagicMock()
    site_dir = mock_app_config.outputs_dir.__truediv__.return_value
    site_dir.exists.return_value = True
    site_dir.__truediv__.return_value.exists.return_value = True

    mock_retention_mgr = mock_retention_mgr_cls.return_value
    mock_retention_mgr.get_scrape_directories.return_value = [MagicMock(name="2023-01-01")]
    mock_retention_mgr.get_scrape_directories.return_value[0].name = "2023-01-01"

    mock_cdm = mock_cdm_cls.return_value
    mock_cdm.rebuild_from_timestamp.return_value = {"summary": "Rollback successful"}

    # Test with 'y' input
    result = runner.invoke(cli, ["rollback", "--site", "site1"], input="y\n")

    assert result.exit_code == 0
    assert "Rolling back to 2023-01-01" in result.output
    assert "Rollback successful" in result.output
    mock_cdm.rebuild_from_timestamp.assert_called_once_with("2023-01-01")

    # Reset mock for the next independent test case
    mock_cdm.reset_mock()

    # Test with 'n' input
    result = runner.invoke(cli, ["rollback", "--site", "site1"], input="n\n")

    assert result.exit_code == 0
    assert "Cancelled" in result.output
    # Should not call rebuild at all in this case
    mock_cdm.rebuild_from_timestamp.assert_not_called()


@patch("webowui.cli.RetentionManager")
@patch("webowui.cli.CurrentDirectoryManager")
def test_rollback_command_specific_timestamp(
    mock_cdm_cls, mock_retention_mgr_cls, runner, mock_app_config
):
    """Test 'rollback' command with specific timestamp."""
    mock_app_config.load_site_config.return_value = MagicMock()
    mock_app_config.outputs_dir = MagicMock()
    site_dir = mock_app_config.outputs_dir.__truediv__.return_value
    site_dir.exists.return_value = True
    site_dir.__truediv__.return_value.exists.return_value = True

    mock_retention_mgr = mock_retention_mgr_cls.return_value
    mock_retention_mgr.get_scrape_directories.return_value = [
        MagicMock(name="2023-01-01"),
        MagicMock(name="2023-01-02"),
    ]
    mock_retention_mgr.get_scrape_directories.return_value[0].name = "2023-01-01"
    mock_retention_mgr.get_scrape_directories.return_value[1].name = "2023-01-02"

    mock_cdm = mock_cdm_cls.return_value
    mock_cdm.rebuild_from_timestamp.return_value = {"summary": "Rollback successful"}

    result = runner.invoke(
        cli, ["rollback", "--site", "site1", "--timestamp", "2023-01-01", "--force"]
    )

    assert result.exit_code == 0
    assert "Rolling back to 2023-01-01" in result.output
    mock_cdm.rebuild_from_timestamp.assert_called_with("2023-01-01")


@patch("webowui.cli.app_config")
def test_schedules_command(mock_app_config_patch, runner):
    """Test 'schedules' command."""
    # Note: We are patching app_config in the fixture, but here we need to set specific return values
    # The fixture mock_app_config is already passed as argument, use it.
    mock_app_config = mock_app_config_patch  # Use the argument

    mock_app_config.list_sites.return_value = ["site1", "site2"]

    mock_config1 = MagicMock()
    mock_config1.schedule_enabled = True
    mock_config1.schedule_type = "cron"
    mock_config1.schedule_cron = "0 0 * * *"
    mock_config1.schedule_timezone = "UTC"
    mock_config1.auto_upload = True

    mock_config2 = MagicMock()
    mock_config2.schedule_enabled = False

    def load_config_side_effect(name):
        if name == "site1":
            return mock_config1
        return mock_config2

    mock_app_config.load_site_config.side_effect = load_config_side_effect

    result = runner.invoke(cli, ["schedules"])

    assert result.exit_code == 0
    assert "Scheduled Jobs" in result.output
    assert "site1" in result.output
    assert "cron" in result.output
    assert "0 0 * * *" in result.output
    assert "site2" in result.output
    assert "✗" in result.output
