"""
Root pytest configuration and fixtures for web-to-openwebui tests.

Provides:
- Temporary directory fixtures for test isolation
- Sample configuration fixtures
- Mock OpenWebUI server setup
- Test data generators
"""

import json
import os
import tempfile
from collections.abc import Generator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest
import yaml

# ============================================================================
# Temporary Directory Fixtures
# ============================================================================


@pytest.fixture
def tmp_dir() -> Generator[Path, None, None]:
    """
    Temporary directory for test files.

    Automatically cleaned up after test completes.

    Yields:
        Path: Temporary directory path
    """
    with tempfile.TemporaryDirectory(prefix="web_to_openwebui_test_") as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def tmp_config_dir(tmp_dir: Path) -> Path:
    """
    Temporary config directory structure.

    Creates standard data/config/{sites,profiles} structure.

    Args:
        tmp_dir: Base temporary directory

    Returns:
        Path: Root of config directory
    """
    config_dir = tmp_dir / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "sites").mkdir()
    (config_dir / "profiles").mkdir()
    return config_dir


@pytest.fixture
def tmp_data_dir(tmp_dir: Path) -> Path:
    """
    Temporary data directory structure.

    Creates standard data/{config,outputs,logs} structure.

    Args:
        tmp_dir: Base temporary directory

    Returns:
        Path: Root of data directory
    """
    data_dir = tmp_dir / "data"
    data_dir.mkdir()
    (data_dir / "config").mkdir()
    (data_dir / "config" / "sites").mkdir()
    (data_dir / "config" / "profiles").mkdir()
    (data_dir / "outputs").mkdir()
    (data_dir / "logs").mkdir()
    return data_dir


@pytest.fixture
def tmp_outputs_dir(tmp_dir: Path) -> Path:
    """
    Temporary outputs directory.

    Creates standard outputs/{site_name}/{current,timestamps} structure.

    Args:
        tmp_dir: Base temporary directory

    Returns:
        Path: Root of outputs directory
    """
    outputs_dir = tmp_dir / "outputs"
    outputs_dir.mkdir()
    return outputs_dir


# ============================================================================
# Sample Configuration Fixtures
# ============================================================================


@pytest.fixture
def sample_site_config() -> dict[str, Any]:
    """
    Sample site configuration dictionary.

    Returns:
        Dict: Configuration matching SiteConfig schema
    """
    return {
        "name": "test_wiki",
        "display_name": "Test Wiki",
        "site": {
            "name": "test_wiki",
            "display_name": "Test Wiki",
            "base_url": "https://test.example.com",
            "start_urls": ["https://test.example.com/wiki/Main_Page"],
        },
        "strategy": {
            "type": "recursive",
            "max_depth": 2,
            "follow_patterns": ["^https://test\\.example\\.com/wiki/.*"],
            "exclude_patterns": [".*Special:.*", ".*User:.*"],
            "rate_limit": {
                "requests_per_second": 2,
                "delay_between_requests": 0.5,
            },
        },
        "cleaning": {
            "profile": "none",
            "config": {},
        },
        "retention": {
            "enabled": False,
            "keep_backups": 2,
            "auto_cleanup": False,
        },
        "openwebui": {
            "knowledge_id": "test-kb-123",
            "knowledge_name": "Test Knowledge",
        },
        "schedule": {
            "enabled": False,
        },
    }


@pytest.fixture
def sample_site_config_mediawiki() -> dict[str, Any]:
    """
    Sample MediaWiki site configuration.

    Returns:
        Dict: Configuration for a MediaWiki-based site
    """
    return {
        "name": "mw_test",
        "display_name": "MediaWiki Test",
        "base_url": "https://wiki.example.com",
        "start_urls": ["https://wiki.example.com/wiki/Main_Page"],
        "crawling": {
            "strategy": "recursive",
            "max_depth": 3,
            "requests_per_second": 1,
            "delay_between_requests": 1.0,
            "follow_patterns": ["^https://wiki\\.example\\.com/wiki/[^:]+$"],
            "exclude_patterns": [
                ".*Special:.*",
                ".*User:.*",
                ".*Talk:.*",
                ".*File:.*",
                ".*Category:.*",
            ],
        },
        "cleaning": {
            "profile": "mediawiki",
            "config": {
                "filter_dead_links": False,
                "remove_citations": True,
                "remove_categories": True,
            },
        },
        "retention": {
            "enabled": True,
            "keep_backups": 2,
            "auto_cleanup": True,
        },
        "openwebui": {
            "knowledge_id": "mw-kb-456",
            "knowledge_name": "MediaWiki Docs",
        },
    }


@pytest.fixture
def mock_site_config_obj(sample_site_config):
    """
    Mock SiteConfig object with attribute access.

    Args:
        sample_site_config: Sample configuration dictionary

    Returns:
        Mock: Mock object mimicking SiteConfig
    """
    from unittest.mock import Mock

    config = Mock()
    config.name = sample_site_config["name"]
    config.display_name = sample_site_config["display_name"]
    config.base_url = sample_site_config["site"]["base_url"]
    config.start_urls = sample_site_config["site"]["start_urls"]

    # Strategy config
    strategy = sample_site_config["strategy"]
    config.strategy_type = strategy["type"]
    config.max_depth = strategy["max_depth"]
    config.follow_patterns = strategy["follow_patterns"]
    config.exclude_patterns = strategy["exclude_patterns"]
    config.requests_per_second = strategy["rate_limit"]["requests_per_second"]
    config.delay_between_requests = strategy["rate_limit"]["delay_between_requests"]

    # Cleaning config
    config.min_content_length = 100
    config.max_content_length = 1000000
    config.markdown_options = {}

    return config


@pytest.fixture
def sample_app_config(tmp_data_dir: Path) -> dict[str, Any]:
    """
    Sample app configuration dictionary.

    Args:
        tmp_data_dir: Temporary data directory

    Returns:
        Dict: Configuration matching AppConfig schema
    """
    return {
        "base_dir": str(tmp_data_dir.parent),
        "data_dir": str(tmp_data_dir),
        "config_dir": str(tmp_data_dir / "config"),
        "sites_dir": str(tmp_data_dir / "config" / "sites"),
        "outputs_dir": str(tmp_data_dir / "outputs"),
        "logs_dir": str(tmp_data_dir / "logs"),
        "openwebui_base_url": "http://localhost:8000",
        "openwebui_api_key": "test-key-123",
    }


@pytest.fixture
def sample_metadata() -> dict[str, Any]:
    """
    Sample scrape metadata.

    Returns:
        Dict: Metadata matching schema from metadata_tracker.py
    """
    return {
        "site": {
            "name": "test_wiki",
            "display_name": "Test Wiki",
            "base_url": "https://test.example.com",
        },
        "scrape": {
            "timestamp": "2025-11-20_01-15-00",
            "duration_seconds": 45.3,
            "total_pages": 10,
            "successful_pages": 10,
            "failed_pages": 0,
        },
        "files": [
            {
                "url": "https://test.example.com/wiki/Page1",
                "filepath": "content/Page1.md",
                "checksum": "abc123def456",
                "size": 1024,
                "scraped_at": "2025-11-20T01:15:10Z",
            },
        ],
    }


@pytest.fixture
def sample_upload_status() -> dict[str, Any]:
    """
    Sample upload status.

    Returns:
        Dict: Upload status structure
    """
    return {
        "site_name": "test_wiki",
        "knowledge_id": "test-kb-123",
        "knowledge_name": "Test Knowledge",
        "last_upload": "2025-11-20T01:15:00Z",
        "last_timestamp": "2025-11-20_01-15-00",
        "files": [
            {
                "url": "https://test.example.com/wiki/Page1",
                "filename": "Page1.md",
                "file_id": "file-123",
                "checksum": "abc123def456",
                "uploaded_at": "2025-11-20T01:15:10Z",
            },
        ],
    }


# ============================================================================
# Sample Content Fixtures
# ============================================================================


@pytest.fixture
def sample_markdown() -> str:
    """
    Sample markdown content.

    Returns:
        str: Realistic markdown content
    """
    return """---
url: https://test.example.com/wiki/Page1
title: Test Page
---

# Test Page

This is a test page with some content.

## Section 1

This is the first section with some body text.

### Subsection 1.1

Detailed information goes here.

## Section 2

More content in section 2.

- List item 1
- List item 2
- List item 3

| Column 1 | Column 2 |
|----------|----------|
| Value 1  | Value 2  |

[Link to other page](https://test.example.com/wiki/OtherPage)
"""


@pytest.fixture
def sample_markdown_content_variations() -> dict[str, str]:
    """
    Sample markdown content variations for testing.

    Returns:
        Dict: Various markdown samples
    """
    return {
        "minimal": "# Title\n\nContent",
        "with_code": "# Title\n\n```python\ndef hello():\n    print('world')\n```",
        "with_tables": "# Title\n\n| A | B |\n|---|---|\n| 1 | 2 |",
        "with_references": "# Title\n\nSee also: [Link](http://example.com)",
        "empty": "",
        "whitespace_only": "   \n\n   ",
    }


@pytest.fixture
def sample_html() -> str:
    """
    Sample HTML content for content cleaner tests.

    Returns:
        str: Realistic HTML structure
    """
    return """<!DOCTYPE html>
<html>
<head>
    <title>Test Page</title>
</head>
<body>
    <h1>Test Page</h1>
    <div class="mw-parser-output">
        <p>This is a test page with some content.</p>
        <h2>Section 1</h2>
        <p>This is the first section with some body text.</p>
        <h3>Subsection 1.1</h3>
        <p>Detailed information goes here.</p>
        <div class="navbox">Navigation Box</div>
        <h2>External links</h2>
        <ul>
            <li><a href="https://example.com">Example</a></li>
        </ul>
        <div class="footer">Footer content</div>
    </div>
</body>
</html>
"""


# ============================================================================
# Mock OpenWebUI Client Fixture
# ============================================================================


@pytest.fixture
def mock_openwebui_client() -> AsyncMock:
    """
    Mock OpenWebUI client.

    Returns:
        AsyncMock: Mock client with realistic return values
    """
    mock = AsyncMock()

    # Setup mock methods with realistic returns
    mock.test_connection.return_value = True
    mock.create_knowledge.return_value = {
        "id": "kb-test-123",
        "name": "Test Knowledge",
        "description": "Test description",
    }
    mock.upload_files.return_value = {
        "file_ids": ["file-1", "file-2"],
        "succeeded": 2,
        "failed": 0,
    }
    mock.add_files_to_knowledge_batch.return_value = {
        "succeeded": 2,
        "failed": 0,
    }
    mock.get_knowledge_files.return_value = [
        {"id": "file-1", "name": "page1.md"},
        {"id": "file-2", "name": "page2.md"},
    ]
    mock.verify_file_exists.return_value = True

    return mock


# ============================================================================
# Test Data Generators
# ============================================================================


@pytest.fixture
def create_test_scrape_dir(tmp_outputs_dir: Path):
    """
    Factory fixture for creating test scrape directories.

    Usage:
        scrape_dir = create_test_scrape_dir("test_site", "2025-11-20_01-15-00")

    Args:
        tmp_outputs_dir: Temporary outputs directory

    Yields:
        Callable: Function to create test scrape directory
    """

    def _create(site_name: str, timestamp: str, num_files: int = 3) -> Path:
        """
        Create test scrape directory with content.

        Args:
            site_name: Site name
            timestamp: Timestamp string
            num_files: Number of test files to create

        Returns:
            Path: Path to created scrape directory
        """
        scrape_dir = tmp_outputs_dir / site_name / timestamp
        content_dir = scrape_dir / "content"
        content_dir.mkdir(parents=True)

        # Create metadata
        metadata = {
            "site": {"name": site_name},
            "scrape": {"timestamp": timestamp, "total_pages": num_files},
            "files": [],
        }

        # Create sample content files
        for i in range(num_files):
            filename = f"page_{i}.md"
            filepath = content_dir / filename
            filepath.write_text(f"# Page {i}\n\nContent for page {i}")
            metadata["files"].append(
                {
                    "url": f"https://example.com/page{i}",
                    "filepath": f"content/{filename}",
                    "checksum": f"hash{i}",
                }
            )

        # Write metadata
        metadata_file = scrape_dir / "metadata.json"
        metadata_file.write_text(json.dumps(metadata, indent=2))

        return scrape_dir

    return _create


@pytest.fixture
def create_test_site_config(tmp_config_dir: Path):
    """
    Factory fixture for creating test site configs.

    Usage:
        config_file = create_test_site_config("mysite", {"name": "mysite", ...})

    Args:
        tmp_config_dir: Temporary config directory

    Yields:
        Callable: Function to create test site config
    """

    def _create(site_name: str, config: dict[str, Any] | None = None) -> Path:
        """
        Create test site config YAML file.

        Args:
            site_name: Site name
            config: Config dictionary (uses defaults if None)

        Returns:
            Path: Path to created config file
        """
        if config is None:
            config = {
                "name": site_name,
                "display_name": f"{site_name} Test",
                "base_url": f"https://{site_name}.example.com",
                "start_urls": [f"https://{site_name}.example.com/wiki/Main_Page"],
                "crawling": {
                    "strategy": "recursive",
                    "max_depth": 1,
                },
            }

        config_file = tmp_config_dir / "sites" / f"{site_name}.yaml"
        config_file.write_text(yaml.dump(config))
        return config_file

    return _create


# ============================================================================
# Environment Fixtures
# ============================================================================


@pytest.fixture
def mock_env() -> Generator[dict[str, str], None, None]:
    """
    Mock environment variables for testing.

    Yields:
        Dict: Environment variable overrides
    """
    with patch.dict(
        os.environ,
        {
            "OPENWEBUI_BASE_URL": "http://localhost:8000",
            "OPENWEBUI_API_KEY": "test-key-123",
            "LOG_LEVEL": "DEBUG",
        },
    ):
        yield os.environ


@pytest.fixture
def mock_home_dir(tmp_dir: Path) -> Generator[Path, None, None]:
    """
    Mock home directory for testing.

    Args:
        tmp_dir: Temporary directory to use as home

    Yields:
        Path: Mocked home directory
    """
    with patch.dict(os.environ, {"HOME": str(tmp_dir)}):
        yield tmp_dir


# ============================================================================
# Markers for Test Organization
# ============================================================================


def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as a unit test")
    config.addinivalue_line("markers", "integration: mark test as an integration test")
    config.addinivalue_line("markers", "e2e: mark test as an end-to-end test")
    config.addinivalue_line("markers", "requires_openwebui: mark test as requiring OpenWebUI")
    config.addinivalue_line("markers", "slow: mark test as slow (>5 seconds)")
