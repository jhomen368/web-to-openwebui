"""
Test helper functions and utilities.

Provides helper functions for:
- Creating temporary site configurations
- Generating test scrape directories
- Comparing file contents
- Mocking async functions
- Working with paths and directories
"""

import asyncio
import hashlib
import json
from collections.abc import Coroutine
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import yaml

# ============================================================================
# File and Directory Helpers
# ============================================================================


def create_test_file(
    directory: Path,
    filename: str,
    content: str,
    encoding: str = "utf-8",
) -> Path:
    """
    Create a test file with content.

    Args:
        directory: Directory to create file in
        filename: Filename to create
        content: File content
        encoding: Text encoding

    Returns:
        Path: Path to created file
    """
    directory.mkdir(parents=True, exist_ok=True)
    filepath = directory / filename
    filepath.write_text(content, encoding=encoding)
    return filepath


def create_test_directory_structure(
    base_dir: Path,
    structure: dict[str, str],
) -> dict[str, Path]:
    """
    Create a directory structure with files.

    Args:
        base_dir: Base directory
        structure: Dict mapping relative paths to content
                   (e.g., {"dir/file.txt": "content"})

    Returns:
        Dict: Mapping of paths to created file paths
    """
    created_paths = {}

    for path_str, content in structure.items():
        filepath = base_dir / path_str
        filepath.parent.mkdir(parents=True, exist_ok=True)
        filepath.write_text(content)
        created_paths[path_str] = filepath

    return created_paths


def compare_file_contents(file1: Path, file2: Path) -> bool:
    """
    Compare contents of two files.

    Args:
        file1: First file path
        file2: Second file path

    Returns:
        bool: True if contents are identical
    """
    if not file1.exists() or not file2.exists():
        return False

    return file1.read_text() == file2.read_text()


def get_file_checksum(filepath: Path, algorithm: str = "md5") -> str:
    """
    Calculate file checksum.

    Args:
        filepath: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)

    Returns:
        str: Hex digest of file content

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    if not filepath.exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    hasher = hashlib.new(algorithm)
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)

    return hasher.hexdigest()


def directory_size(directory: Path) -> int:
    """
    Calculate total size of directory in bytes.

    Args:
        directory: Directory path

    Returns:
        int: Total size in bytes
    """
    total = 0
    for filepath in directory.rglob("*"):
        if filepath.is_file():
            total += filepath.stat().st_size
    return total


def count_files(directory: Path, pattern: str = "*") -> int:
    """
    Count files in directory matching pattern.

    Args:
        directory: Directory path
        pattern: Glob pattern (e.g., "*.md", "*.json")

    Returns:
        int: Number of matching files
    """
    if not directory.exists():
        return 0

    return len(list(directory.rglob(pattern)))


# ============================================================================
# Configuration Helpers
# ============================================================================


def create_temp_site_config(
    config_dir: Path,
    site_name: str,
    config: dict[str, Any] | None = None,
) -> Path:
    """
    Create a temporary site configuration file.

    Args:
        config_dir: Config directory (typically config/sites/)
        site_name: Site name
        config: Configuration dict (uses minimal default if None)

    Returns:
        Path: Path to created config file
    """
    if config is None:
        config = {
            "name": site_name,
            "display_name": f"{site_name} Test",
            "base_url": f"https://{site_name}.example.com",
            "start_urls": [f"https://{site_name}.example.com"],
            "crawling": {
                "strategy": "recursive",
                "max_depth": 1,
            },
        }

    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / f"{site_name}.yaml"

    with open(config_file, "w") as f:
        yaml.dump(config, f)

    return config_file


def load_yaml_config(filepath: Path) -> dict[str, Any]:
    """
    Load YAML configuration file.

    Args:
        filepath: Path to YAML file

    Returns:
        Dict: Parsed configuration

    Raises:
        FileNotFoundError: If file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    if not filepath.exists():
        raise FileNotFoundError(f"Config file not found: {filepath}")

    with open(filepath) as f:
        return yaml.safe_load(f)


def save_yaml_config(
    filepath: Path,
    config: dict[str, Any],
) -> Path:
    """
    Save configuration to YAML file.

    Args:
        filepath: Path to save to
        config: Configuration dictionary

    Returns:
        Path: Path to saved file
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)

    with open(filepath, "w") as f:
        yaml.dump(config, f, default_flow_style=False)

    return filepath


# ============================================================================
# Metadata and JSON Helpers
# ============================================================================


def create_test_metadata(
    filepath: Path,
    site_name: str,
    num_files: int = 3,
    timestamp: str = "2025-11-20_01-15-00",
) -> dict[str, Any]:
    """
    Create test metadata.json file.

    Args:
        filepath: Path to metadata.json
        site_name: Site name
        num_files: Number of files to include
        timestamp: Scrape timestamp

    Returns:
        Dict: Metadata dictionary
    """
    files = []
    for i in range(num_files):
        files.append(
            {
                "url": f"https://example.com/page{i}",
                "filepath": f"content/page{i}.md",
                "filename": f"page_{i}.md",
                "checksum": f"hash{i:04d}",
                "size": 1024 * (i + 1),
            }
        )

    metadata = {
        "site": {
            "name": site_name,
            "display_name": f"{site_name} Test",
        },
        "scrape": {
            "timestamp": timestamp,
            "duration_seconds": 45.3,
            "total_pages": num_files,
            "successful_pages": num_files,
            "failed_pages": 0,
        },
        "files": files,
    }

    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(json.dumps(metadata, indent=2))

    return metadata


def load_json_file(filepath: Path) -> dict[str, Any]:
    """
    Load JSON file.

    Args:
        filepath: Path to JSON file

    Returns:
        Dict: Parsed JSON

    Raises:
        FileNotFoundError: If file doesn't exist
        json.JSONDecodeError: If JSON parsing fails
    """
    if not filepath.exists():
        raise FileNotFoundError(f"JSON file not found: {filepath}")

    return json.loads(filepath.read_text())


def save_json_file(
    filepath: Path,
    data: dict[str, Any],
    indent: int = 2,
) -> Path:
    """
    Save data to JSON file.

    Args:
        filepath: Path to save to
        data: Data to serialize
        indent: JSON indentation level

    Returns:
        Path: Path to saved file
    """
    filepath.parent.mkdir(parents=True, exist_ok=True)
    filepath.write_text(json.dumps(data, indent=indent))
    return filepath


# ============================================================================
# Scrape Directory Helpers
# ============================================================================


def create_test_scrape_directory(
    outputs_dir: Path,
    site_name: str,
    timestamp: str = "2025-11-20_01-15-00",
    num_files: int = 3,
) -> Path:
    """
    Create a test scrape directory structure.

    Creates:
    - outputs/{site_name}/{timestamp}/content/
    - outputs/{site_name}/{timestamp}/metadata.json

    Args:
        outputs_dir: Root outputs directory
        site_name: Site name
        timestamp: Scrape timestamp
        num_files: Number of test files to create

    Returns:
        Path: Path to created scrape directory
    """
    scrape_dir = outputs_dir / site_name / timestamp
    content_dir = scrape_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    # Create metadata
    create_test_metadata(
        scrape_dir / "metadata.json",
        site_name,
        num_files=num_files,
        timestamp=timestamp,
    )

    # Create content files
    for i in range(num_files):
        content_file = content_dir / f"page_{i}.md"
        content_file.write_text(f"# Page {i}\n\nContent for page {i}")

    return scrape_dir


def create_current_directory(
    outputs_dir: Path,
    site_name: str,
    num_files: int = 3,
) -> Path:
    """
    Create a current/ directory structure.

    Creates:
    - outputs/{site_name}/current/content/
    - outputs/{site_name}/current/metadata.json
    - outputs/{site_name}/current/upload_status.json

    Args:
        outputs_dir: Root outputs directory
        site_name: Site name
        num_files: Number of test files to create

    Returns:
        Path: Path to created current directory
    """
    current_dir = outputs_dir / site_name / "current"
    content_dir = current_dir / "content"
    content_dir.mkdir(parents=True, exist_ok=True)

    # Create metadata
    create_test_metadata(
        current_dir / "metadata.json",
        site_name,
        num_files=num_files,
    )

    # Create upload status
    upload_status = {
        "site_name": site_name,
        "knowledge_id": f"kb-{site_name}",
        "knowledge_name": f"{site_name} KB",
        "files": [
            {
                "url": f"https://example.com/page{i}",
                "filename": f"page_{i}.md",
                "file_id": f"file-{i:04d}",
                "checksum": f"hash{i:04d}",
            }
            for i in range(num_files)
        ],
    }
    save_json_file(current_dir / "upload_status.json", upload_status)

    # Create content files
    for i in range(num_files):
        content_file = content_dir / f"page_{i}.md"
        content_file.write_text(f"# Page {i}\n\nCurrent version of page {i}")

    return current_dir


# ============================================================================
# Async Mocking Helpers
# ============================================================================


def create_mock_async_function(return_value: Any = None) -> AsyncMock:
    """
    Create a mock async function.

    Args:
        return_value: Value for function to return

    Returns:
        AsyncMock: Configured async mock function
    """
    mock = AsyncMock()
    mock.return_value = return_value
    return mock


def create_mock_async_context_manager(return_value: Any = None) -> MagicMock:
    """
    Create a mock async context manager.

    Usage:
        async with mock_context_manager() as cm:
            ...

    Args:
        return_value: Value for context manager to yield

    Returns:
        MagicMock: Configured async context manager mock
    """
    mock = MagicMock()
    mock.__aenter__ = AsyncMock(return_value=return_value)
    mock.__aexit__ = AsyncMock(return_value=None)
    return mock


def async_test_helper(coro: Coroutine) -> Any:
    """
    Run async function in sync context (for debugging/simple tests).

    Args:
        coro: Coroutine to run

    Returns:
        Any: Result of coroutine
    """
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


# ============================================================================
# Comparison Helpers
# ============================================================================


def compare_dictionaries(
    dict1: dict[str, Any],
    dict2: dict[str, Any],
    ignore_keys: list[str] | None = None,
) -> bool:
    """
    Compare two dictionaries, optionally ignoring specific keys.

    Args:
        dict1: First dictionary
        dict2: Second dictionary
        ignore_keys: Keys to ignore in comparison

    Returns:
        bool: True if dictionaries are equal (ignoring specified keys)
    """
    ignore_keys = ignore_keys or []

    def filter_dict(d: dict) -> dict:
        return {k: v for k, v in d.items() if k not in ignore_keys}

    return filter_dict(dict1) == filter_dict(dict2)


def compare_json_files(
    file1: Path,
    file2: Path,
    ignore_keys: list[str] | None = None,
) -> bool:
    """
    Compare two JSON files.

    Args:
        file1: First JSON file
        file2: Second JSON file
        ignore_keys: Keys to ignore in comparison

    Returns:
        bool: True if JSON content is equal
    """
    data1 = load_json_file(file1)
    data2 = load_json_file(file2)
    return compare_dictionaries(data1, data2, ignore_keys)


# ============================================================================
# List/Array Helpers
# ============================================================================


def generate_urls(
    base_url: str,
    num_urls: int = 10,
    path_prefix: str = "page",
) -> list[str]:
    """
    Generate a list of test URLs.

    Args:
        base_url: Base URL (e.g., "https://example.com")
        num_urls: Number of URLs to generate
        path_prefix: Path prefix (e.g., "page" -> "/page-1", "/page-2")

    Returns:
        List[str]: Generated URLs
    """
    return [f"{base_url}/{path_prefix}-{i}" for i in range(1, num_urls + 1)]


def generate_checksums(num_checksums: int = 10) -> list[str]:
    """
    Generate fake checksums for testing.

    Args:
        num_checksums: Number of checksums to generate

    Returns:
        List[str]: Hex strings suitable as checksums
    """
    return [f"{i:032x}" for i in range(num_checksums)]


# ============================================================================
# Validation Helpers
# ============================================================================


def validate_scrape_directory(scrape_dir: Path) -> bool:
    """
    Validate that a scrape directory has the correct structure.

    Expected structure:
    - {scrape_dir}/content/ (directory with markdown files)
    - {scrape_dir}/metadata.json (file)

    Args:
        scrape_dir: Scrape directory to validate

    Returns:
        bool: True if structure is valid
    """
    # Check required directories
    if not (scrape_dir / "content").is_dir():
        return False

    # Check required files
    if not (scrape_dir / "metadata.json").is_file():
        return False

    # Check metadata is valid JSON
    try:
        load_json_file(scrape_dir / "metadata.json")
    except (json.JSONDecodeError, FileNotFoundError):
        return False

    return True


def validate_current_directory(current_dir: Path) -> bool:
    """
    Validate that a current/ directory has the correct structure.

    Expected structure:
    - {current_dir}/content/ (directory with markdown files)
    - {current_dir}/metadata.json (file)
    - {current_dir}/upload_status.json (file)

    Args:
        current_dir: Current directory to validate

    Returns:
        bool: True if structure is valid
    """
    # Check required directories
    if not (current_dir / "content").is_dir():
        return False

    # Check required files
    required_files = ["metadata.json", "upload_status.json"]
    for filename in required_files:
        filepath = current_dir / filename
        if not filepath.is_file():
            return False

        try:
            load_json_file(filepath)
        except (json.JSONDecodeError, FileNotFoundError):
            return False

    return True
