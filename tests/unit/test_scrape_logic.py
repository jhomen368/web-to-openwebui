from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from webowui.cli import _scrape_site
from webowui.config import SiteConfig


@pytest.mark.asyncio
async def test_scrape_site_auto_upload_arguments():
    """
    Verify that _scrape_site calls _upload_scrape with correct arguments
    for incremental upload when auto_upload is enabled.
    """
    # Mock site config
    site_config = MagicMock(spec=SiteConfig)
    site_config.name = "test_site"
    site_config.auto_upload = True
    site_config.knowledge_name = "Test Knowledge"
    site_config.knowledge_description = "Test Description"
    site_config.knowledge_id = "kb-123"
    site_config.retention_enabled = False

    # Mock dependencies
    with (
        patch("webowui.cli.WikiCrawler") as mock_crawler_cls,
        patch("webowui.cli.OutputManager") as mock_output_manager_cls,
        patch("webowui.cli._upload_scrape", new_callable=AsyncMock) as mock_upload_scrape,
    ):

        # Setup crawler mock
        mock_crawler_instance = mock_crawler_cls.return_value
        mock_crawler_instance.crawl = AsyncMock(return_value=[])
        mock_crawler_instance.get_stats.return_value = {"total_crawled": 10, "total_failed": 0}

        # Setup output manager mock
        mock_output_manager_instance = mock_output_manager_cls.return_value
        mock_output_manager_instance.save_results.return_value = {
            "output_dir": "/tmp/output",
            "timestamp": "2025-01-01_12-00-00",
        }

        # Run the function
        await _scrape_site(site_config, do_upload=True)

        # Verify _upload_scrape was called correctly
        mock_upload_scrape.assert_called_once_with(
            site_name="test_site",
            from_timestamp=None,  # Should be None for incremental upload from current/
            incremental=True,  # Should be True
            knowledge_name="Test Knowledge",
            knowledge_description="Test Description",
            knowledge_id="kb-123",
        )


@pytest.mark.asyncio
async def test_scrape_site_no_upload():
    """Verify that _upload_scrape is not called when do_upload is False."""
    site_config = MagicMock(spec=SiteConfig)
    site_config.name = "test_site"
    site_config.auto_upload = True  # Config says yes, but override says no
    site_config.retention_enabled = False

    with (
        patch("webowui.cli.WikiCrawler") as mock_crawler_cls,
        patch("webowui.cli.OutputManager") as mock_output_manager_cls,
        patch("webowui.cli._upload_scrape", new_callable=AsyncMock) as mock_upload_scrape,
    ):

        mock_crawler_instance = mock_crawler_cls.return_value
        mock_crawler_instance.crawl = AsyncMock(return_value=[])
        mock_crawler_instance.get_stats.return_value = {"total_crawled": 0, "total_failed": 0}

        mock_output_manager_instance = mock_output_manager_cls.return_value
        mock_output_manager_instance.save_results.return_value = {"output_dir": "", "timestamp": ""}

        await _scrape_site(site_config, do_upload=False)

        mock_upload_scrape.assert_not_called()


@pytest.mark.asyncio
async def test_scrape_site_config_no_upload():
    """Verify that _upload_scrape is not called when config.auto_upload is False."""
    site_config = MagicMock(spec=SiteConfig)
    site_config.name = "test_site"
    site_config.auto_upload = False  # Config says no
    site_config.retention_enabled = False

    with (
        patch("webowui.cli.WikiCrawler") as mock_crawler_cls,
        patch("webowui.cli.OutputManager") as mock_output_manager_cls,
        patch("webowui.cli._upload_scrape", new_callable=AsyncMock) as mock_upload_scrape,
    ):

        mock_crawler_instance = mock_crawler_cls.return_value
        mock_crawler_instance.crawl = AsyncMock(return_value=[])
        mock_crawler_instance.get_stats.return_value = {"total_crawled": 0, "total_failed": 0}

        mock_output_manager_instance = mock_output_manager_cls.return_value
        mock_output_manager_instance.save_results.return_value = {"output_dir": "", "timestamp": ""}

        await _scrape_site(site_config, do_upload=True)  # Override says yes, but config says no

        mock_upload_scrape.assert_not_called()
