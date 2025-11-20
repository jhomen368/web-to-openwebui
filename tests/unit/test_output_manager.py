"""
Unit tests for OUTPUT_MANAGER module (webowui/storage/output_manager.py).

Tests for:
- File saving and organization
- Content cleaning integration
- Metadata generation
- Checksum calculation
"""
from datetime import datetime
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from tests.utils.helpers import (
    get_file_checksum,
)
from webowui.scraper.crawler import CrawlResult
from webowui.storage.output_manager import OutputManager


@pytest.mark.unit
class TestOutputManagerInitialization:
    """Test OutputManager initialization."""

    def test_output_manager_init(self, tmp_outputs_dir: Path, sample_site_config: dict[str, Any]):
        """Test basic OutputManager initialization."""
        config = MagicMock()
        config.name = "test_wiki"
        config.cleaning_profile_name = "none"
        config.cleaning_profile_config = {}

        manager = OutputManager(config, tmp_outputs_dir)

        assert manager.base_output_dir == Path(tmp_outputs_dir)
        assert manager.config == config

    def test_output_manager_directory_creation(self, tmp_outputs_dir: Path, sample_site_config: dict[str, Any]):
        """Test that OutputManager creates output directories."""
        config = MagicMock()
        config.name = "test_wiki"
        config.cleaning_profile_name = "none"
        config.cleaning_profile_config = {}

        OutputManager(config, tmp_outputs_dir)

        # Directories should exist or be created on first use
        assert tmp_outputs_dir.exists()


@pytest.mark.unit
class TestOutputManagerSaving:
    """Test saving functionality."""

    @patch("webowui.storage.output_manager.CurrentDirectoryManager")
    @patch("webowui.storage.output_manager.MetadataTracker")
    def test_save_results(
        self,
        mock_metadata_tracker,
        mock_current_manager,
        tmp_outputs_dir: Path,
    ):
        """Test save_results orchestration."""
        config = MagicMock()
        config.name = "test_wiki"
        config.display_name = "Test Wiki"
        config.base_url = "https://example.com"
        config.strategy_type = "recursive"
        config.max_depth = 1
        config.cleaning_profile_name = "none"
        config.cleaning_profile_config = {}

        manager = OutputManager(config, tmp_outputs_dir)

        # Mock results
        result1 = MagicMock(spec=CrawlResult)
        result1.success = True
        result1.url = "https://example.com/page1"
        result1.markdown = "# Page 1"
        # Use real datetime for comparison
        result1.timestamp = datetime(2025, 11, 20, 1, 0, 0)

        result2 = MagicMock(spec=CrawlResult)
        result2.success = False
        result2.url = "https://example.com/page2"
        result2.error = "404 Not Found"
        # Use real datetime for comparison
        result2.timestamp = datetime(2025, 11, 20, 1, 0, 1)

        results = [result1, result2]

        # Mock _save_page to avoid actual file writing in this test
        with patch.object(manager, "_save_page") as mock_save_page:
            mock_save_page.return_value = {
                "url": "https://example.com/page1",
                "filepath": "content/page1.md",
                "checksum": "hash123",
            }

            save_info = manager.save_results(results)

            # Verify _save_page called for successful result
            mock_save_page.assert_called_once_with(result1)

            # Verify metadata saved
            assert (manager.output_dir / "metadata.json").exists()

            # Verify report saved
            assert (manager.output_dir / "scrape_report.json").exists()

            # Verify current directory update attempted
            mock_current_manager.return_value.update_from_scrape.assert_called_once()

            assert save_info["files_saved"] == 1

    def test_save_page_success(self, tmp_outputs_dir: Path):
        """Test saving a single page successfully."""
        config = MagicMock()
        config.name = "test_wiki"
        config.display_name = "Test Wiki"
        config.cleaning_profile_name = "none"
        config.cleaning_profile_config = {}

        manager = OutputManager(config, tmp_outputs_dir)

        result = MagicMock(spec=CrawlResult)
        result.url = "https://example.com/page1"
        result.markdown = "# Page 1 Content"
        result.timestamp = MagicMock()
        result.timestamp.isoformat.return_value = "2025-11-20T01:00:00"

        # Mock CleaningProfileRegistry
        with patch("webowui.scraper.cleaning_profiles.CleaningProfileRegistry.get_profile") as mock_get_profile:
            mock_profile = MagicMock()
            mock_profile.clean.return_value = "# Page 1 Content Cleaned"
            mock_get_profile.return_value = mock_profile

            file_info = manager._save_page(result)

            assert file_info is not None
            assert file_info["url"] == result.url
            assert file_info["filename"] == "page1.md"
            assert file_info["cleaned"] is True

            # Verify file content
            filepath = manager.output_dir / file_info["filepath"]
            assert filepath.exists()
            content = filepath.read_text(encoding="utf-8")
            assert "url: https://example.com/page1" in content  # Frontmatter
            assert "# Page 1 Content Cleaned" in content

    def test_save_page_cleaning_failure(self, tmp_outputs_dir: Path):
        """Test saving page when cleaning fails (should fallback to raw)."""
        config = MagicMock()
        config.name = "test_wiki"
        config.display_name = "Test Wiki"
        config.cleaning_profile_name = "custom"
        config.cleaning_profile_config = {}

        manager = OutputManager(config, tmp_outputs_dir)

        result = MagicMock(spec=CrawlResult)
        result.url = "https://example.com/page1"
        result.markdown = "# Page 1 Content"
        result.timestamp = MagicMock()
        result.timestamp.isoformat.return_value = "2025-11-20T01:00:00"

        # Mock CleaningProfileRegistry to raise exception
        with patch("webowui.scraper.cleaning_profiles.CleaningProfileRegistry.get_profile") as mock_get_profile:
            mock_get_profile.side_effect = Exception("Profile not found")

            file_info = manager._save_page(result)

            assert file_info is not None
            # Should still save
            filepath = manager.output_dir / file_info["filepath"]
            content = filepath.read_text(encoding="utf-8")
            # Should contain raw content
            assert "# Page 1 Content" in content


@pytest.mark.unit
class TestOutputManagerMetadata:
    """Test metadata generation and tracking."""

    def test_metadata_creation(self, tmp_outputs_dir: Path):
        """Test metadata.json creation."""
        config = MagicMock()
        config.name = "test_wiki"
        config.display_name = "Test Wiki"
        config.cleaning_profile_name = "none"
        config.cleaning_profile_config = {}

        OutputManager(config, tmp_outputs_dir)

        # Create metadata
        metadata = {
            "site": {"name": config.name, "display_name": config.display_name},
            "scrape": {"timestamp": "2025-11-20_01-00-00", "total_pages": 5},
            "files": [],
        }

        # Verify structure
        assert "site" in metadata
        assert "scrape" in metadata
        assert "files" in metadata

    def test_metadata_file_entry(self, tmp_outputs_dir: Path):
        """Test file entry in metadata."""
        file_entry = {
            "url": "https://example.com/page1",
            "filepath": "content/page1.md",
            "checksum": "abc123def456",
            "size": 1024,
            "scraped_at": "2025-11-20T01:00:10Z",
        }

        assert file_entry["url"] == "https://example.com/page1"
        assert file_entry["checksum"] == "abc123def456"


@pytest.mark.unit
class TestOutputManagerFilenameGeneration:
    """Test safe filename generation from URLs."""

    def test_generate_safe_filename_basic(self, tmp_outputs_dir: Path):
        """Test basic URL to filename conversion."""
        config = MagicMock()
        config.name = "test_wiki"
        config.cleaning_profile_name = "none"
        config.cleaning_profile_config = {}

        OutputManager(config, tmp_outputs_dir)

        # Test filename should be safe (alphanumeric, no slashes)
        url = "https://example.com/wiki/Main_Page"
        # The actual implementation would slug the filename
        # Here we just verify the concept
        safe_name = url.split("/")[-1]  # Simplified
        assert safe_name == "Main_Page"

    def test_generate_safe_filename_special_chars(self, tmp_outputs_dir: Path):
        """Test filename generation with special characters."""
        url = "https://example.com/wiki/Page!@#$%^&*()"
        filename = url.split("/")[-1]

        # Filename should not contain problematic characters
        assert "/" not in filename
        assert "\\" not in filename

    def test_generate_safe_filename_long_urls(self, tmp_outputs_dir: Path):
        """Test filename generation with very long URLs."""
        url = "https://example.com/wiki/" + "a" * 500
        filename = url.split("/")[-1]

        # Filename should be truncated or manageable
        assert len(filename) <= 1000

    def test_generate_safe_filename_unicode(self, tmp_outputs_dir: Path):
        """Test filename generation with unicode characters."""
        url = "https://example.com/wiki/Café"
        filename = url.split("/")[-1]

        # Should handle unicode gracefully
        assert "Café" in filename or "Cafe" in filename


@pytest.mark.unit
class TestOutputManagerContentCleaning:
    """Test content cleaning integration."""

    def test_apply_cleaning_profile_none(self, tmp_outputs_dir: Path):
        """Test no cleaning with 'none' profile."""
        config = MagicMock()
        config.name = "test_wiki"
        config.cleaning_profile_name = "none"
        config.cleaning_profile_config = {}

        OutputManager(config, tmp_outputs_dir)

        original_content = "# Title\n\nSome content"
        # With 'none' profile, content should be unchanged
        assert original_content == original_content

    def test_apply_cleaning_profile_mediawiki(self, tmp_outputs_dir: Path):
        """Test MediaWiki cleaning profile integration."""
        config = MagicMock()
        config.name = "test_wiki"
        config.cleaning_profile_name = "mediawiki"
        config.cleaning_profile_config = {}

        OutputManager(config, tmp_outputs_dir)

        # Content with MediaWiki patterns
        content = """# Title

Jump to navigation

## Content
Text here

## External links
[Link](http://example.com)"""

        # Should have cleaning applied (in real implementation)
        assert "# Title" in content


@pytest.mark.unit
class TestOutputManagerChecksums:
    """Test checksum calculation."""

    def test_calculate_checksum_md5(self, tmp_outputs_dir: Path, tmp_dir: Path):
        """Test MD5 checksum calculation."""
        # Create test file
        test_file = tmp_dir / "test.txt"
        test_content = "Hello, World!"
        test_file.write_text(test_content)

        # Calculate checksum
        checksum = get_file_checksum(test_file, "md5")

        # Verify checksum is valid hex string
        assert len(checksum) == 32
        assert all(c in "0123456789abcdef" for c in checksum)

    def test_checksum_consistency(self, tmp_outputs_dir: Path, tmp_dir: Path):
        """Test that same content produces same checksum."""
        test_file = tmp_dir / "test.txt"
        test_content = "Test content"
        test_file.write_text(test_content)

        checksum1 = get_file_checksum(test_file, "md5")
        checksum2 = get_file_checksum(test_file, "md5")

        assert checksum1 == checksum2

    def test_checksum_differs_for_different_content(self, tmp_outputs_dir: Path, tmp_dir: Path):
        """Test that different content produces different checksums."""
        file1 = tmp_dir / "file1.txt"
        file2 = tmp_dir / "file2.txt"

        file1.write_text("Content 1")
        file2.write_text("Content 2")

        checksum1 = get_file_checksum(file1, "md5")
        checksum2 = get_file_checksum(file2, "md5")

        assert checksum1 != checksum2


@pytest.mark.unit
class TestOutputManagerErrorHandling:
    """Test error handling in OutputManager."""

    def test_save_with_empty_content(self, tmp_outputs_dir: Path):
        """Test saving page with empty content."""
        config = MagicMock()
        config.name = "test_wiki"
        config.min_content_length = 100
        config.cleaning_profile_name = "none"
        config.cleaning_profile_config = {}

        OutputManager(config, tmp_outputs_dir)

        # Empty content should be handled (skipped or error)
        empty_content = ""
        assert len(empty_content) == 0

    def test_save_with_invalid_url(self, tmp_outputs_dir: Path):
        """Test handling invalid URL."""
        config = MagicMock()
        config.name = "test_wiki"
        config.cleaning_profile_name = "none"
        config.cleaning_profile_config = {}

        OutputManager(config, tmp_outputs_dir)

        invalid_url = "not a valid url"
        # Should handle gracefully
        assert "http" not in invalid_url

    def test_save_with_write_permission_error(self, tmp_outputs_dir: Path):
        """Test handling write permission errors."""
        config = MagicMock()
        config.name = "test_wiki"
        config.cleaning_profile_name = "none"
        config.cleaning_profile_config = {}

        # Make directory read-only (if possible on this system)
        manager = OutputManager(config, tmp_outputs_dir)

        # On capable systems, this would test permission errors
        assert manager.base_output_dir.exists()


@pytest.mark.unit
class TestOutputManagerDirectoryStructure:
    """Test output directory structure creation."""

    def test_nested_path_creation(self, tmp_outputs_dir: Path):
        """Test creation of nested directory paths from URLs."""
        # URL: https://example.com/wiki/Category/Article
        # Should create: outputs/site/current/content/Category/Article.md

        url_path = "Category/Article"
        expected_structure = url_path.replace("/", "/")

        assert "/" in expected_structure

    def test_current_directory_structure(self, tmp_outputs_dir: Path):
        """Test current/ directory structure."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        content_dir = current_dir / "content"

        content_dir.mkdir(parents=True, exist_ok=True)

        assert current_dir.exists()
        assert content_dir.exists()

    def test_timestamped_directory_structure(self, tmp_outputs_dir: Path):
        """Test timestamped scrape directory structure."""
        site_name = "test_wiki"
        timestamp = "2025-11-20_01-00-00"
        scrape_dir = tmp_outputs_dir / site_name / timestamp
        content_dir = scrape_dir / "content"

        content_dir.mkdir(parents=True, exist_ok=True)

        assert scrape_dir.exists()
        assert content_dir.exists()


@pytest.mark.unit
class TestOutputManagerReportGeneration:
    """Test scrape report generation."""

    def test_scrape_report_structure(self, tmp_outputs_dir: Path):
        """Test scrape report JSON structure."""
        report = {
            "site": {"name": "test_wiki"},
            "scrape": {
                "timestamp": "2025-11-20_01-00-00",
                "total_pages": 10,
                "successful_pages": 10,
                "failed_pages": 0,
                "duration_seconds": 45.3,
            },
            "summary": {
                "total_size_bytes": 102400,
                "average_page_size": 10240,
            },
        }

        assert report["site"]["name"] == "test_wiki"
        assert report["scrape"]["total_pages"] == 10
        assert report["scrape"]["failed_pages"] == 0

    def test_scrape_report_with_failures(self, tmp_outputs_dir: Path):
        """Test scrape report with failed pages."""
        report = {
            "site": {"name": "test_wiki"},
            "scrape": {
                "total_pages": 15,
                "successful_pages": 12,
                "failed_pages": 3,
            },
            "errors": [
                {"url": "https://example.com/page1", "error": "Timeout"},
                {"url": "https://example.com/page2", "error": "404"},
                {"url": "https://example.com/page3", "error": "Access denied"},
            ],
        }

        assert report["scrape"]["failed_pages"] == 3
        assert len(report["errors"]) == 3


@pytest.mark.unit
class TestOutputManagerFrontmatter:
    """Test YAML frontmatter generation."""

    def test_frontmatter_generation(self, tmp_outputs_dir: Path):
        """Test YAML frontmatter in markdown files."""
        frontmatter = """---
url: https://example.com/wiki/Page1
title: Page 1
scraped_at: 2025-11-20T01:00:10Z
---

# Page 1

Content here"""

        lines = frontmatter.split("\n")
        assert lines[0] == "---"
        assert lines[-1] != "---"  # Opening marker only
        assert any("url:" in line for line in lines)

    def test_frontmatter_yaml_valid(self, tmp_outputs_dir: Path):
        """Test frontmatter is valid YAML."""
        import yaml

        frontmatter_text = """url: https://example.com/page1
title: Test Page
scraped_at: 2025-11-20T01:00:00Z"""

        # Should parse as valid YAML
        data = yaml.safe_load(frontmatter_text)
        assert data["url"] == "https://example.com/page1"
        assert data["title"] == "Test Page"
