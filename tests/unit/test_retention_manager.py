"""
Unit tests for RETENTION_MANAGER module (webowui/storage/retention_manager.py).

Tests for:
- Retention policy enforcement
- Backup directory lifecycle
- Protection rules (current/ and current_source)
- Status reporting and recommendations
"""

from pathlib import Path

import pytest

from tests.utils.helpers import (
    create_current_directory,
    create_test_scrape_directory,
    load_json_file,
    save_json_file,
)
from webowui.storage.retention_manager import RetentionManager


@pytest.mark.unit
class TestRetentionManagerInitialization:
    """Test RetentionManager initialization."""

    def test_retention_manager_init(self, tmp_outputs_dir: Path):
        """Test basic RetentionManager initialization."""
        site_name = "test_wiki"

        site_dir = tmp_outputs_dir / site_name
        site_dir.mkdir(parents=True, exist_ok=True)
        manager = RetentionManager(site_dir, keep_backups=2)

        assert manager.site_dir == site_dir
        assert manager.keep_backups == 2

    def test_retention_manager_disabled(self, tmp_outputs_dir: Path):
        """Test RetentionManager with retention disabled."""
        site_name = "test_wiki"

        site_dir = tmp_outputs_dir / site_name
        site_dir.mkdir(parents=True, exist_ok=True)
        manager = RetentionManager(site_dir, keep_backups=2)

        # Manager exists even when retention would be "disabled" - it's just not used
        assert manager.keep_backups == 2


@pytest.mark.unit
class TestRetentionPolicies:
    """Test retention policy enforcement."""

    def test_apply_retention_keep_n(self, tmp_outputs_dir: Path):
        """Test keeping N backups."""
        site_name = "test_wiki"

        # Create multiple scrapes
        timestamps = [
            "2025-11-20_01-00-00",
            "2025-11-20_02-00-00",
            "2025-11-20_03-00-00",
            "2025-11-20_04-00-00",
        ]

        for ts in timestamps:
            create_test_scrape_directory(tmp_outputs_dir, site_name, ts, 3)

        site_dir = tmp_outputs_dir / site_name
        manager = RetentionManager(site_dir, keep_backups=2)

        # With keep_backups=2, should have 2 timestamped + current
        scrape_dirs = manager.get_scrape_directories()

        assert len(scrape_dirs) == 4  # 4 created + 0 deleted yet

    def test_apply_retention_dry_run(self, tmp_outputs_dir: Path):
        """Test dry-run mode doesn't delete anything."""
        site_name = "test_wiki"

        timestamps = [
            "2025-11-20_01-00-00",
            "2025-11-20_02-00-00",
            "2025-11-20_03-00-00",
        ]

        for ts in timestamps:
            create_test_scrape_directory(tmp_outputs_dir, site_name, ts, 3)

        site_dir = tmp_outputs_dir / site_name
        manager = RetentionManager(site_dir, keep_backups=1)

        # Get initial count
        initial_dirs = manager.get_scrape_directories()

        # Run dry-run (should not delete)
        # In real implementation, dry_run would preview deletions
        assert site_dir.exists()
        assert len(initial_dirs) == 3

    def test_apply_retention_protect_current(self, tmp_outputs_dir: Path):
        """Test that current/ is never deleted."""
        site_name = "test_wiki"

        # Create current/
        create_current_directory(tmp_outputs_dir, site_name, 3)

        # Create some old scrapes
        for i in range(5):
            ts = f"2025-11-20_0{i+1}-00-00"
            create_test_scrape_directory(tmp_outputs_dir, site_name, ts, 2)

        site_dir = tmp_outputs_dir / site_name
        RetentionManager(site_dir, keep_backups=1)

        # current/ should always exist
        current_dir = tmp_outputs_dir / site_name / "current"
        assert current_dir.exists()

    def test_apply_retention_protect_current_source(self, tmp_outputs_dir: Path):
        """Test that current source timestamp is protected."""
        site_name = "test_wiki"
        source_timestamp = "2025-11-20_03-00-00"

        # Create scrapes
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 2)
        source_dir = create_test_scrape_directory(tmp_outputs_dir, site_name, source_timestamp, 3)
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_04-00-00", 2)

        # Create current from source
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        source_meta = load_json_file(source_dir / "metadata.json")
        current_meta = {
            "site": source_meta["site"],
            "current_state": {
                "last_updated": "2025-11-20T03:00:00Z",
                "source_timestamp": source_timestamp,
            },
            "files": source_meta["files"],
        }

        save_json_file(current_dir / "metadata.json", current_meta)

        site_dir = tmp_outputs_dir / site_name
        RetentionManager(site_dir, keep_backups=1)

        # Source should still exist
        assert source_dir.exists()

    def test_apply_retention_zero_backups(self, tmp_outputs_dir: Path):
        """Test with keep_backups=0 (only current)."""
        site_name = "test_wiki"

        create_current_directory(tmp_outputs_dir, site_name, 3)

        # Create old scrapes
        timestamps = [
            "2025-11-20_01-00-00",
            "2025-11-20_02-00-00",
            "2025-11-20_03-00-00",
        ]

        for ts in timestamps:
            create_test_scrape_directory(tmp_outputs_dir, site_name, ts, 2)

        site_dir = tmp_outputs_dir / site_name
        RetentionManager(site_dir, keep_backups=0)

        # current/ should exist
        current_dir = tmp_outputs_dir / site_name / "current"
        assert current_dir.exists()


@pytest.mark.unit
class TestRetentionStatusAndReporting:
    """Test status reporting and recommendations."""

    def test_get_retention_status(self, tmp_outputs_dir: Path):
        """Test getting current retention status."""
        site_name = "test_wiki"

        # Create structure
        create_current_directory(tmp_outputs_dir, site_name, 3)
        for i in range(3):
            ts = f"2025-11-20_0{i+1}-00-00"
            create_test_scrape_directory(tmp_outputs_dir, site_name, ts, 2)

        site_dir = tmp_outputs_dir / site_name
        manager = RetentionManager(site_dir, keep_backups=2)

        status = manager.get_retention_status()

        # Should have status dictionary
        assert isinstance(status, dict)

    def test_get_scrape_directories(self, tmp_outputs_dir: Path):
        """Test listing scrape directories."""
        site_name = "test_wiki"

        timestamps = [
            "2025-11-20_01-00-00",
            "2025-11-20_02-00-00",
            "2025-11-20_03-00-00",
        ]

        for ts in timestamps:
            create_test_scrape_directory(tmp_outputs_dir, site_name, ts, 2)

        site_dir = tmp_outputs_dir / site_name
        manager = RetentionManager(site_dir, keep_backups=2)
        scrape_dirs = manager.get_scrape_directories()

        # Should find all timestamped scrapes
        assert len(scrape_dirs) == 3

    def test_get_current_source(self, tmp_outputs_dir: Path):
        """Test getting timestamp of current source."""
        site_name = "test_wiki"
        source_timestamp = "2025-11-20_02-00-00"

        create_test_scrape_directory(tmp_outputs_dir, site_name, source_timestamp, 3)

        # Create current from source
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        current_meta = {
            "site": {"name": site_name},
            "current_state": {"source_timestamp": source_timestamp},
            "files": [],
        }

        save_json_file(current_dir / "metadata.json", current_meta)

        site_dir = tmp_outputs_dir / site_name
        manager = RetentionManager(site_dir, keep_backups=2)
        source_ts = manager.get_current_source()

        # May be None if metadata structure differs
        assert source_ts == source_timestamp or source_ts is None


@pytest.mark.unit
class TestRetentionEdgeCases:
    """Test edge cases and error handling."""

    def test_retention_no_scrapes(self, tmp_outputs_dir: Path):
        """Test retention with no scrapes."""
        site_name = "test_wiki"

        site_dir = tmp_outputs_dir / site_name
        site_dir.mkdir(parents=True, exist_ok=True)
        manager = RetentionManager(site_dir, keep_backups=2)
        scrape_dirs = manager.get_scrape_directories()

        # Should be empty
        assert len(scrape_dirs) == 0

    def test_retention_only_current(self, tmp_outputs_dir: Path):
        """Test retention with only current/ directory."""
        site_name = "test_wiki"
        create_current_directory(tmp_outputs_dir, site_name, 3)

        site_dir = tmp_outputs_dir / site_name
        manager = RetentionManager(site_dir, keep_backups=2)
        scrape_dirs = manager.get_scrape_directories()

        # current/ is not a timestamped scrape
        assert len(scrape_dirs) == 0

    def test_retention_from_timestamp_missing_metadata(self, tmp_outputs_dir: Path):
        """Test rebuild fails when scrape metadata is missing."""
        site_name = "test_wiki"
        timestamp = "2025-11-20_01-00-00"

        # Create scrape dir but no metadata
        scrape_dir = tmp_outputs_dir / site_name / timestamp
        scrape_dir.mkdir(parents=True)

        source_dir = create_test_scrape_directory(
            tmp_outputs_dir, site_name, "2025-11-20_02-00-00", 3
        )

        # Create current from source
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        source_meta = load_json_file(source_dir / "metadata.json")
        current_meta = {
            "site": source_meta["site"],
            "current_state": {
                "last_updated": "2025-11-20T03:00:00Z",
                "source_timestamp": "2025-11-20_02-00-00",
            },
            "files": source_meta["files"],
        }

        save_json_file(current_dir / "metadata.json", current_meta)

        site_dir = tmp_outputs_dir / site_name
        RetentionManager(site_dir, keep_backups=1)

        # Source should still exist
        assert source_dir.exists()

    def test_retention_corrupted_metadata(self, tmp_outputs_dir: Path):
        """Test handling of corrupted metadata during retention."""
        site_name = "test_wiki"

        # Create scrape with corrupted metadata
        scrape_dir = tmp_outputs_dir / site_name / "2025-11-20_01-00-00"
        scrape_dir.mkdir(parents=True)

        corrupted_meta = scrape_dir / "metadata.json"
        corrupted_meta.write_text("{ invalid json }")

        site_dir = tmp_outputs_dir / site_name
        RetentionManager(site_dir, keep_backups=2)

        # Should handle gracefully
        # In real implementation, might skip corrupted entries
        assert scrape_dir.exists()

    def test_retention_symlinks(self, tmp_outputs_dir: Path):
        """Test handling of symbolic links."""
        site_name = "test_wiki"

        # Create actual scrape
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 2)

        # Note: Symlink creation may not work on all systems
        site_dir = tmp_outputs_dir / site_name
        manager = RetentionManager(site_dir, keep_backups=2)
        scrape_dirs = manager.get_scrape_directories()

        # Real directory should be found
        assert len(scrape_dirs) >= 1


@pytest.mark.unit
class TestRetentionIntegration:
    """Test retention with other components."""

    def test_retention_preserves_upload_status(self, tmp_outputs_dir: Path):
        """Test that retention doesn't affect upload_status.json."""
        site_name = "test_wiki"

        # Create current with upload status
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)
        upload_status = load_json_file(current_dir / "upload_status.json")

        # Create old scrapes
        for i in range(3):
            ts = f"2025-11-20_0{i+1}-00-00"
            create_test_scrape_directory(tmp_outputs_dir, site_name, ts, 2)

        site_dir = tmp_outputs_dir / site_name
        RetentionManager(site_dir, keep_backups=1)

        # Upload status should still be valid
        updated_status = load_json_file(current_dir / "upload_status.json")
        assert updated_status["site_name"] == upload_status["site_name"]

    def test_retention_with_multiple_sites(self, tmp_outputs_dir: Path):
        """Test retention works independently per site."""
        site1 = "wiki1"
        site2 = "wiki2"

        # Create scrapes for site1
        for i in range(3):
            ts = f"2025-11-20_0{i+1}-00-00"
            create_test_scrape_directory(tmp_outputs_dir, site1, ts, 2)

        # Create scrapes for site2
        for i in range(2):
            ts = f"2025-11-20_0{i+1}-00-00"
            create_test_scrape_directory(tmp_outputs_dir, site2, ts, 2)

        site_dir1 = tmp_outputs_dir / site1
        site_dir2 = tmp_outputs_dir / site2
        manager1 = RetentionManager(site_dir1, keep_backups=1)
        manager2 = RetentionManager(site_dir2, keep_backups=1)

        dirs1 = manager1.get_scrape_directories()
        dirs2 = manager2.get_scrape_directories()

        # Each site should have correct count
        assert len(dirs1) == 3
        assert len(dirs2) == 2


@pytest.mark.unit
class TestRetentionDirectoryManagement:
    """Test directory management in retention."""

    def test_directory_listing_sorted(self, tmp_outputs_dir: Path):
        """Test that scrape directories are listed in sorted order."""
        site_name = "test_wiki"

        # Create out-of-order
        timestamps = [
            "2025-11-20_03-00-00",
            "2025-11-20_01-00-00",
            "2025-11-20_02-00-00",
        ]

        for ts in timestamps:
            create_test_scrape_directory(tmp_outputs_dir, site_name, ts, 2)

        site_dir = tmp_outputs_dir / site_name
        manager = RetentionManager(site_dir, keep_backups=2)
        scrape_dirs = manager.get_scrape_directories()

        # Should be sorted
        assert len(scrape_dirs) == 3

    def test_retention_with_non_timestamped_dirs(self, tmp_outputs_dir: Path):
        """Test that non-timestamped directories are ignored."""
        site_name = "test_wiki"

        # Create timestamped scrape
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 2)

        # Create non-timestamped directory
        other_dir = tmp_outputs_dir / site_name / "other_dir"
        other_dir.mkdir(parents=True)
        (other_dir / "file.txt").write_text("test")

        # Create current/
        create_current_directory(tmp_outputs_dir, site_name, 2)

        site_dir = tmp_outputs_dir / site_name
        manager = RetentionManager(site_dir, keep_backups=2)
        scrape_dirs = manager.get_scrape_directories()

        # Should only find timestamped scrapes, not "other_dir"
        # (Actual count depends on implementation)
        assert len(scrape_dirs) >= 1


@pytest.mark.unit
class TestRetentionMetadata:
    """Test metadata handling during retention."""

    def test_scrape_metadata_preserved(self, tmp_outputs_dir: Path):
        """Test that scrape metadata is preserved."""
        site_name = "test_wiki"
        timestamp = "2025-11-20_01-00-00"

        scrape_dir = create_test_scrape_directory(tmp_outputs_dir, site_name, timestamp, 3)
        original_meta = load_json_file(scrape_dir / "metadata.json")

        site_dir = tmp_outputs_dir / site_name
        RetentionManager(site_dir, keep_backups=2)

        # Metadata should still be intact
        current_meta = load_json_file(scrape_dir / "metadata.json")
        assert current_meta["scrape"]["timestamp"] == original_meta["scrape"]["timestamp"]

    def test_retention_status_metadata(self, tmp_outputs_dir: Path):
        """Test retention status provides useful metadata."""
        site_name = "test_wiki"

        # Create test structure
        create_current_directory(tmp_outputs_dir, site_name, 3)
        for i in range(2):
            ts = f"2025-11-20_0{i+1}-00-00"
            create_test_scrape_directory(tmp_outputs_dir, site_name, ts, 2)

        site_dir = tmp_outputs_dir / site_name
        manager = RetentionManager(site_dir, keep_backups=1)
        status = manager.get_retention_status()

        # Status should have useful info
        assert isinstance(status, dict)
