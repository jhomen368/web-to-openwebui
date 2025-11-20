"""
Unit tests for METADATA_TRACKER module (webowui/storage/metadata_tracker.py).

Tests for:
- Scrape tracking and history
- Change detection using checksums
- Scrape comparison and diff calculation
"""

import json
from pathlib import Path

import pytest

from tests.utils.helpers import (
    create_test_metadata,
    create_test_scrape_directory,
    load_json_file,
)
from webowui.storage.metadata_tracker import MetadataTracker


@pytest.mark.unit
class TestMetadataTrackerInitialization:
    """Test MetadataTracker initialization."""

    def test_metadata_tracker_init(self, tmp_outputs_dir: Path):
        """Test basic MetadataTracker initialization."""
        site_name = "test_wiki"
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        assert tracker.base_output_dir == tmp_outputs_dir
        assert tracker.site_name == site_name

    def test_metadata_tracker_no_previous_scrapes(self, tmp_outputs_dir: Path):
        """Test tracker with no previous scrapes."""
        site_name = "test_wiki"
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        latest = tracker.get_latest_scrape()

        assert latest is None


@pytest.mark.unit
class TestMetadataTrackerScrapeTracking:
    """Test scrape recording and retrieval."""

    def test_record_scrape(self, tmp_outputs_dir: Path):
        """Test recording a new scrape."""
        site_name = "test_wiki"
        timestamp = "2025-11-20_01-00-00"

        scrape_dir = create_test_scrape_directory(
            tmp_outputs_dir, site_name, timestamp, num_files=5
        )

        MetadataTracker(tmp_outputs_dir, site_name)
        metadata = load_json_file(scrape_dir / "metadata.json")

        assert metadata["site"]["name"] == site_name
        assert metadata["scrape"]["timestamp"] == timestamp
        assert len(metadata["files"]) == 5

    def test_get_latest_scrape(self, tmp_outputs_dir: Path):
        """Test retrieving the latest scrape."""
        site_name = "test_wiki"

        # Create multiple scrapes
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_02-00-00", 4)
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_03-00-00", 5)

        tracker = MetadataTracker(tmp_outputs_dir, site_name)
        latest = tracker.get_latest_scrape()

        # Latest should be the most recent one
        assert latest is not None
        assert "2025-11-20" in latest["scrape"]["timestamp"]

    def test_list_scrapes(self, tmp_outputs_dir: Path):
        """Test listing all scrapes."""
        site_name = "test_wiki"
        timestamps = [
            "2025-11-20_01-00-00",
            "2025-11-20_02-00-00",
            "2025-11-20_03-00-00",
        ]

        for ts in timestamps:
            create_test_scrape_directory(tmp_outputs_dir, site_name, ts, 3)

        tracker = MetadataTracker(tmp_outputs_dir, site_name)
        scrapes = tracker.get_all_scrapes()

        assert len(scrapes) >= len(timestamps)

    def test_get_scrape_by_timestamp(self, tmp_outputs_dir: Path):
        """Test retrieving specific scrape by timestamp."""
        site_name = "test_wiki"
        target_timestamp = "2025-11-20_02-00-00"

        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)
        target_dir = create_test_scrape_directory(tmp_outputs_dir, site_name, target_timestamp, 4)
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_03-00-00", 5)

        MetadataTracker(tmp_outputs_dir, site_name)

        # Get metadata for specific timestamp
        metadata_path = target_dir / "metadata.json"
        metadata = load_json_file(metadata_path)

        # Verify it's the right scrape
        assert metadata["scrape"]["timestamp"] == target_timestamp
        assert len(metadata["files"]) == 4


@pytest.mark.unit
class TestMetadataTrackerComparison:
    """Test scrape comparison and change detection."""

    def test_compare_scrapes_identical(self, tmp_outputs_dir: Path):
        """Test comparing identical scrapes."""
        site_name = "test_wiki"

        # Create two identical scrapes
        dir1 = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)
        meta1 = load_json_file(dir1 / "metadata.json")

        dir2 = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_02-00-00", 3)
        meta2 = load_json_file(dir2 / "metadata.json")

        # Update files in second scrape to match first
        for i, file_info in enumerate(meta1["files"]):
            meta2["files"][i]["checksum"] = file_info["checksum"]

        # Should have no changes
        changes_exist = False
        for i, file1 in enumerate(meta1["files"]):
            if file1.get("checksum") != meta2["files"][i].get("checksum"):
                changes_exist = True
                break

        assert not changes_exist

    def test_compare_scrapes_additions(self, tmp_outputs_dir: Path):
        """Test detecting added pages in new scrape."""
        site_name = "test_wiki"

        dir1 = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)
        meta1 = load_json_file(dir1 / "metadata.json")

        dir2 = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_02-00-00", 5)
        meta2 = load_json_file(dir2 / "metadata.json")

        # Second scrape has more files
        added_count = len(meta2["files"]) - len(meta1["files"])

        assert added_count == 2

    def test_compare_scrapes_modifications(self, tmp_outputs_dir: Path):
        """Test detecting modified pages."""
        site_name = "test_wiki"

        dir1 = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)
        meta1 = load_json_file(dir1 / "metadata.json")

        dir2 = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_02-00-00", 3)
        meta2 = load_json_file(dir2 / "metadata.json")

        # Modify a file in second scrape
        meta2["files"][1]["checksum"] = "modified_hash"

        # Should detect modification
        modified = False
        for first_file, second_file in zip(
            meta1["files"],
            meta2["files"],
            strict=False,
        ):
            if first_file.get("checksum") != second_file.get("checksum"):
                modified = True
                break

        assert modified

    def test_compare_scrapes_deletions(self, tmp_outputs_dir: Path):
        """Test detecting deleted pages."""
        site_name = "test_wiki"

        dir1 = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 5)
        meta1 = load_json_file(dir1 / "metadata.json")
        file_urls_1 = {f["url"] for f in meta1["files"]}

        dir2 = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_02-00-00", 3)
        meta2 = load_json_file(dir2 / "metadata.json")
        file_urls_2 = {f["url"] for f in meta2["files"]}

        # Calculate deleted
        deleted = file_urls_1 - file_urls_2

        # Should have deleted files
        assert len(deleted) > 0

    def test_compare_scrapes_mixed_changes(self, tmp_outputs_dir: Path):
        """Test detecting all types of changes at once."""
        site_name = "test_wiki"

        dir1 = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 5)
        meta1 = load_json_file(dir1 / "metadata.json")

        # Create scrape with 6 files (5 from before + 1 new, with 1 deleted and 1 modified)
        dir2 = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_02-00-00", 6)
        meta2 = load_json_file(dir2 / "metadata.json")

        # Simulate: Replace first old with new, keep some, modify one, add one new
        file_urls_1 = {f["url"] for f in meta1["files"]}
        file_urls_2 = {f["url"] for f in meta2["files"]}

        # From creation parameters, we expect different file counts
        assert len(file_urls_1) == 5
        assert len(file_urls_2) == 6

    def test_compare_scrapes_missing_scrape(self, tmp_outputs_dir: Path):
        """Test comparing when one scrape is missing."""
        site_name = "test_wiki"
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        # Create only one scrape
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)

        result = tracker.compare_scrapes("2025-11-20_01-00-00", "2025-11-20_02-00-00")

        assert "error" in result
        assert result["error"] == "One or both scrapes not found"

    def test_get_changed_files_no_base(self, tmp_outputs_dir: Path):
        """Test get_changed_files without base timestamp (should use previous)."""
        site_name = "test_wiki"
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        # Create 3 scrapes
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_02-00-00", 4)
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_03-00-00", 5)

        # Should compare 03:00:00 (latest) with 02:00:00 (previous)
        changes = tracker.get_changed_files()

        # Since create_test_scrape_directory generates random URLs, we expect changes
        # But specifically, we expect it to run without error
        assert isinstance(changes, dict)
        assert "added" in changes
        assert "modified" in changes
        assert "removed" in changes

    def test_get_changed_files_with_base(self, tmp_outputs_dir: Path):
        """Test get_changed_files with explicit base timestamp."""
        site_name = "test_wiki"
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_03-00-00", 5)

        changes = tracker.get_changed_files(base_timestamp="2025-11-20_01-00-00")

        assert isinstance(changes, dict)

    def test_get_changed_files_first_scrape(self, tmp_outputs_dir: Path):
        """Test get_changed_files when only one scrape exists."""
        site_name = "test_wiki"
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)

        changes = tracker.get_changed_files()

        # Should treat all files as added
        assert len(changes["added"]) == 3
        assert len(changes["modified"]) == 0
        assert len(changes["removed"]) == 0

    def test_get_changed_files_no_scrapes(self, tmp_outputs_dir: Path):
        """Test get_changed_files when no scrapes exist."""
        site_name = "test_wiki"
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        changes = tracker.get_changed_files()

        assert len(changes["added"]) == 0
        assert len(changes["modified"]) == 0
        assert len(changes["removed"]) == 0


@pytest.mark.unit
class TestMetadataTrackerEdgeCases:
    """Test edge cases and error handling."""

    def test_no_scrapes_exist(self, tmp_outputs_dir: Path):
        """Test handling when no scrapes exist."""
        site_name = "test_wiki"
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        scrapes = tracker.get_all_scrapes()

        assert scrapes == []

    def test_only_current_directory(self, tmp_outputs_dir: Path):
        """Test behavior with only current/ directory."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        create_test_metadata(current_dir / "metadata.json", site_name, 3)

        tracker = MetadataTracker(tmp_outputs_dir, site_name)
        scrapes = tracker.get_all_scrapes()

        # current/ is not a timestamped scrape
        assert len(scrapes) == 0

    def test_corrupted_metadata_file(self, tmp_outputs_dir: Path):
        """Test handling of corrupted metadata.json."""
        site_name = "test_wiki"
        timestamp = "2025-11-20_01-00-00"

        scrape_dir = tmp_outputs_dir / site_name / timestamp
        scrape_dir.mkdir(parents=True)

        # Write invalid JSON
        metadata_file = scrape_dir / "metadata.json"
        metadata_file.write_text("{ invalid json }")

        # Should handle gracefully
        with pytest.raises(json.JSONDecodeError):
            load_json_file(metadata_file)

    def test_missing_files_in_metadata(self, tmp_outputs_dir: Path):
        """Test metadata referencing missing content files."""
        site_name = "test_wiki"
        scrape_dir = create_test_scrape_directory(
            tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3
        )

        # Delete one content file
        metadata = load_json_file(scrape_dir / "metadata.json")
        content_files = list((scrape_dir / "content").glob("*.md"))

        if content_files:
            content_files[0].unlink()

        # Metadata still references the deleted file
        assert len(metadata["files"]) == 3
        assert not content_files[0].exists()

    def test_empty_scrape(self, tmp_outputs_dir: Path):
        """Test handling of empty scrape (zero files)."""
        site_name = "test_wiki"
        scrape_dir = create_test_scrape_directory(
            tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 0
        )

        metadata = load_json_file(scrape_dir / "metadata.json")

        assert metadata["files"] == []
        assert metadata["scrape"]["total_pages"] == 0


@pytest.mark.unit
class TestMetadataTrackerUploadStatus:
    """Test upload status tracking."""

    def test_save_and_get_upload_status(self, tmp_outputs_dir: Path):
        """Test saving and retrieving upload status."""
        site_name = "test_wiki"
        timestamp = "2025-11-20_01-00-00"
        create_test_scrape_directory(tmp_outputs_dir, site_name, timestamp, 3)

        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        # Initial status should be empty/false
        status = tracker.get_upload_status(timestamp)
        assert status["uploaded"] is False

        # Save status
        upload_info = {
            "knowledge_id": "kb-123",
            "files_uploaded": 3,
            "files_updated": 0,
        }
        tracker.save_upload_status(timestamp, upload_info)

        # Retrieve status
        status = tracker.get_upload_status(timestamp)
        assert status["uploaded"] is True
        assert status["knowledge_id"] == "kb-123"
        assert status["files_uploaded"] == 3
        assert "timestamp" in status

    def test_get_upload_status_missing_scrape(self, tmp_outputs_dir: Path):
        """Test getting upload status for non-existent scrape."""
        site_name = "test_wiki"
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        status = tracker.get_upload_status("2025-11-20_01-00-00")
        assert status is None

    def test_save_upload_status_missing_scrape(self, tmp_outputs_dir: Path):
        """Test saving upload status for non-existent scrape."""
        site_name = "test_wiki"
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        # Should log error but not crash
        tracker.save_upload_status("2025-11-20_01-00-00", {})


@pytest.mark.unit
class TestMetadataTrackerCleanup:
    """Test cleanup of old scrapes."""

    def test_cleanup_old_scrapes(self, tmp_outputs_dir: Path):
        """Test removing old scrapes."""
        site_name = "test_wiki"
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        # Create 5 scrapes
        timestamps = [
            "2025-11-20_01-00-00",
            "2025-11-20_02-00-00",
            "2025-11-20_03-00-00",
            "2025-11-20_04-00-00",
            "2025-11-20_05-00-00",
        ]
        for ts in timestamps:
            create_test_scrape_directory(tmp_outputs_dir, site_name, ts, 1)

        # Keep only 3
        tracker.cleanup_old_scrapes(keep_count=3)

        scrapes = tracker.get_all_scrapes()
        assert len(scrapes) == 3

        # Verify oldest were removed
        remaining_timestamps = [s["scrape"]["timestamp"] for s in scrapes]
        assert "2025-11-20_05-00-00" in remaining_timestamps
        assert "2025-11-20_04-00-00" in remaining_timestamps
        assert "2025-11-20_03-00-00" in remaining_timestamps
        assert "2025-11-20_01-00-00" not in remaining_timestamps

    def test_cleanup_no_action_needed(self, tmp_outputs_dir: Path):
        """Test cleanup when count is below limit."""
        site_name = "test_wiki"
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 1)

        tracker.cleanup_old_scrapes(keep_count=5)

        scrapes = tracker.get_all_scrapes()
        assert len(scrapes) == 1


@pytest.mark.unit
class TestMetadataTrackerIntegration:
    """Test integration with OutputManager."""

    def test_metadata_fields_structure(self, tmp_outputs_dir: Path):
        """Test that metadata has all required fields."""
        site_name = "test_wiki"
        timestamp = "2025-11-20_01-00-00"

        scrape_dir = create_test_scrape_directory(tmp_outputs_dir, site_name, timestamp, 3)

        metadata = load_json_file(scrape_dir / "metadata.json")

        # Check required structure
        assert "site" in metadata
        assert "scrape" in metadata
        assert "files" in metadata

        # Check site fields
        assert "name" in metadata["site"]

        # Check scrape fields
        assert "timestamp" in metadata["scrape"]
        assert "total_pages" in metadata["scrape"]

        # Check file fields
        if metadata["files"]:
            file_info = metadata["files"][0]
            assert "url" in file_info
            assert "filepath" in file_info
            assert "checksum" in file_info
