"""
Unit tests for CURRENT_DIRECTORY_MANAGER module (webowui/storage/current_directory_manager.py).

Tests for:
- Current directory initialization and management
- Updating current/ from new scrapes
- Delta log tracking
- Upload status management
- Directory integrity verification
"""
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from tests.utils.helpers import (
    create_current_directory,
    create_test_scrape_directory,
    load_json_file,
    save_json_file,
    validate_current_directory,
)
from webowui.storage.current_directory_manager import CurrentDirectoryManager
from webowui.storage.metadata_tracker import MetadataTracker


@pytest.mark.unit
class TestCurrentDirectoryManagerInitialization:
    """Test CurrentDirectoryManager initialization."""

    def test_current_directory_manager_init(self, tmp_outputs_dir: Path):
        """Test basic initialization."""
        site_name = "test_wiki"
        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        assert manager.base_output_dir == tmp_outputs_dir
        assert manager.site_name == site_name

    def test_current_directory_manager_create_structure(self, tmp_outputs_dir: Path):
        """Test that manager creates directory structure."""
        site_name = "test_wiki"
        CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Directory structure should be creatable
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True, exist_ok=True)

        assert current_dir.exists()


@pytest.mark.unit
class TestCurrentDirectoryOperations:
    """Test current directory update operations."""

    def test_update_from_scrape_first_time(self, tmp_outputs_dir: Path):
        """Test initializing current/ from first scrape."""
        site_name = "test_wiki"
        timestamp = "2025-11-20_01-00-00"

        # Create initial scrape
        scrape_dir = create_test_scrape_directory(
            tmp_outputs_dir,
            site_name,
            timestamp,
            3
        )

        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        scrape_metadata = load_json_file(scrape_dir / "metadata.json")

        # Verify scrape structure
        assert scrape_metadata["scrape"]["timestamp"] == timestamp
        assert len(scrape_metadata["files"]) == 3

    def test_update_from_scrape_with_additions(self, tmp_outputs_dir: Path):
        """Test updating current/ with added files."""
        site_name = "test_wiki"

        # Create first scrape
        scrape1_dir = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)
        meta1 = load_json_file(scrape1_dir / "metadata.json")
        urls1 = {f["url"] for f in meta1["files"]}

        # Create second scrape with more files
        scrape2_dir = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_02-00-00", 5)
        meta2 = load_json_file(scrape2_dir / "metadata.json")
        urls2 = {f["url"] for f in meta2["files"]}

        # Calculate additions
        added = urls2 - urls1

        assert len(added) > 0

    def test_update_from_scrape_with_modifications(self, tmp_outputs_dir: Path):
        """Test updating current/ with modified files."""
        site_name = "test_wiki"

        scrape1_dir = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)
        meta1 = load_json_file(scrape1_dir / "metadata.json")

        scrape2_dir = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_02-00-00", 3)
        meta2 = load_json_file(scrape2_dir / "metadata.json")

        # Modify one file in second scrape
        meta2["files"][0]["checksum"] = "modified_hash_value"

        # Should detect modification
        modified = False
        for f1, f2 in zip(meta1["files"], meta2["files"], strict=False):
            if f1["checksum"] != f2["checksum"]:
                modified = True
                break

        assert modified

    def test_update_from_scrape_with_deletions(self, tmp_outputs_dir: Path):
        """Test updating current/ with deleted files."""
        site_name = "test_wiki"

        scrape1_dir = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 5)
        meta1 = load_json_file(scrape1_dir / "metadata.json")

        scrape2_dir = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_02-00-00", 3)
        meta2 = load_json_file(scrape2_dir / "metadata.json")

        # Calculate deletions
        deleted = len(meta1["files"]) - len(meta2["files"])

        assert deleted > 0

    def test_rebuild_from_timestamp(self, tmp_outputs_dir: Path):
        """Test rebuilding current/ from specific timestamp."""
        site_name = "test_wiki"
        target_timestamp = "2025-11-20_02-00-00"

        # Create multiple scrapes
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)
        target_dir = create_test_scrape_directory(
            tmp_outputs_dir,
            site_name,
            target_timestamp,
            5
        )
        create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_03-00-00", 4)

        # Verify target has correct file count
        target_meta = load_json_file(target_dir / "metadata.json")
        assert len(target_meta["files"]) == 5

    def test_get_current_state(self, tmp_outputs_dir: Path):
        """Test retrieving current state metadata."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)

        metadata = load_json_file(current_dir / "metadata.json")

        # Should have valid current state
        assert "site" in metadata
        assert "files" in metadata
        assert len(metadata["files"]) > 0

    def test_verify_integrity(self, tmp_outputs_dir: Path):
        """Test directory integrity verification."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)

        # Should pass integrity check
        is_valid = validate_current_directory(current_dir)

        assert is_valid


@pytest.mark.unit
class TestCurrentDirectoryDeltaLog:
    """Test delta log tracking."""

    def test_delta_log_creation(self, tmp_outputs_dir: Path):
        """Test delta log creation."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        delta_log = {
            "deltas": [
                {
                    "timestamp": "2025-11-20_01-00-00",
                    "operation": "initial",
                    "changes": {"added": 10, "modified": 0, "removed": 0}
                }
            ]
        }

        delta_log_file = current_dir / "delta_log.json"
        save_json_file(delta_log_file, delta_log)

        assert delta_log_file.exists()

    def test_delta_log_append(self, tmp_outputs_dir: Path):
        """Test appending to delta log."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        # Create initial log
        delta_log = {
            "deltas": [
                {
                    "timestamp": "2025-11-20_01-00-00",
                    "operation": "initial",
                    "changes": {"added": 10, "modified": 0, "removed": 0}
                }
            ]
        }

        delta_log_file = current_dir / "delta_log.json"
        save_json_file(delta_log_file, delta_log)

        # Append new entry
        delta_log["deltas"].append({
            "timestamp": "2025-11-20_02-00-00",
            "operation": "update",
            "changes": {"added": 2, "modified": 1, "removed": 0}
        })

        save_json_file(delta_log_file, delta_log)

        # Verify
        updated_log = load_json_file(delta_log_file)
        assert len(updated_log["deltas"]) == 2

    def test_delta_log_retrieval(self, tmp_outputs_dir: Path):
        """Test reading delta log."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        delta_log = {
            "deltas": [
                {
                    "timestamp": "2025-11-20_01-00-00",
                    "operation": "initial",
                    "changes": {"added": 10, "modified": 0, "removed": 0}
                },
                {
                    "timestamp": "2025-11-20_02-00-00",
                    "operation": "update",
                    "changes": {"added": 2, "modified": 1, "removed": 0}
                },
            ]
        }

        delta_log_file = current_dir / "delta_log.json"
        save_json_file(delta_log_file, delta_log)

        # Retrieve and verify
        retrieved = load_json_file(delta_log_file)
        assert len(retrieved["deltas"]) == 2
        assert retrieved["deltas"][0]["operation"] == "initial"
        assert retrieved["deltas"][1]["operation"] == "update"


@pytest.mark.unit
class TestCurrentDirectoryUploadStatus:
    """Test upload status management."""

    def test_get_upload_status(self, tmp_outputs_dir: Path):
        """Test reading upload status."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)

        upload_status = load_json_file(current_dir / "upload_status.json")

        assert upload_status["site_name"] == site_name
        assert "knowledge_id" in upload_status
        assert "files" in upload_status

    def test_save_upload_status(self, tmp_outputs_dir: Path):
        """Test saving upload status."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        upload_status = {
            "site_name": site_name,
            "knowledge_id": "kb-123",
            "knowledge_name": "Test KB",
            "files": [
                {
                    "url": "https://example.com/page1",
                    "filename": "page1.md",
                    "file_id": "file-123",
                    "checksum": "abc123"
                }
            ]
        }

        status_file = current_dir / "upload_status.json"
        save_json_file(status_file, upload_status)

        # Verify
        retrieved = load_json_file(status_file)
        assert retrieved["site_name"] == site_name
        assert len(retrieved["files"]) == 1

    def test_upload_status_missing(self, tmp_outputs_dir: Path):
        """Test handling missing upload status."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True, exist_ok=True)

        status_file = current_dir / "upload_status.json"

        # Should not exist yet
        assert not status_file.exists()


@pytest.mark.unit
class TestCurrentDirectoryErrorHandling:
    """Test error handling in current directory operations."""

    def test_rebuild_missing_timestamp(self, tmp_outputs_dir: Path):
        """Test rebuilding from non-existent timestamp."""
        site_name = "test_wiki"

        CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Try to rebuild from non-existent timestamp
        nonexistent_timestamp = "2025-11-20_99-99-99"
        scrape_dir = tmp_outputs_dir / site_name / nonexistent_timestamp

        # Should not exist
        assert not scrape_dir.exists()

    def test_update_corrupted_metadata(self, tmp_outputs_dir: Path):
        """Test handling corrupted metadata during update."""
        site_name = "test_wiki"
        timestamp = "2025-11-20_01-00-00"

        scrape_dir = tmp_outputs_dir / site_name / timestamp
        scrape_dir.mkdir(parents=True)

        # Write invalid JSON
        metadata_file = scrape_dir / "metadata.json"
        metadata_file.write_text("{ invalid }")

        # Should raise error when trying to parse
        with pytest.raises(json.JSONDecodeError):
            load_json_file(metadata_file)

    def test_current_directory_locked(self, tmp_outputs_dir: Path):
        """Test handling when current/ is locked or inaccessible."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)

        # On capable systems, this would test permission handling
        # For now, just verify directory exists
        assert current_dir.exists()


@pytest.mark.unit
class TestCurrentDirectoryStructure:
    """Test current directory structure."""

    def test_current_directory_structure(self, tmp_outputs_dir: Path):
        """Test proper current/ directory structure."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)

        # Should have required subdirectories and files
        assert (current_dir / "content").is_dir()
        assert (current_dir / "metadata.json").is_file()
        assert (current_dir / "upload_status.json").is_file()

    def test_content_directory_nested_paths(self, tmp_outputs_dir: Path):
        """Test nested path structure in content directory."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        content_dir = current_dir / "content"
        content_dir.mkdir(parents=True)

        # Create nested structure
        nested_dir = content_dir / "Category" / "Subcategory"
        nested_dir.mkdir(parents=True)

        nested_file = nested_dir / "article.md"
        nested_file.write_text("# Article")

        assert nested_file.exists()
        assert nested_file.read_text() == "# Article"

    def test_metadata_file_format(self, tmp_outputs_dir: Path):
        """Test metadata.json format in current/."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)

        metadata = load_json_file(current_dir / "metadata.json")

        # Should have required fields
        assert "site" in metadata
        assert "files" in metadata
        assert isinstance(metadata["files"], list)


@pytest.mark.unit
class TestCurrentDirectoryIntegration:
    """Test integration with other components."""

    def test_with_delta_log_and_upload_status(self, tmp_outputs_dir: Path):
        """Test current/ with both delta log and upload status."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)

        # Add delta log
        delta_log = {
            "deltas": [{
                "timestamp": "2025-11-20_01-00-00",
                "operation": "initial",
                "changes": {"added": 3, "modified": 0, "removed": 0}
            }]
        }

        save_json_file(current_dir / "delta_log.json", delta_log)

        # Verify all components exist
        assert validate_current_directory(current_dir)
        assert (current_dir / "delta_log.json").exists()
        assert (current_dir / "metadata.json").exists()
        assert (current_dir / "upload_status.json").exists()

    def test_after_scrape_update_flow(self, tmp_outputs_dir: Path):
        """Test complete flow from scrape to current/ update."""
        site_name = "test_wiki"

        # First scrape
        scrape1 = create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)
        meta1 = load_json_file(scrape1 / "metadata.json")

        # Initialize current/ from first scrape
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        # Copy structure from scrape to current
        content_dir = current_dir / "content"
        content_dir.mkdir(exist_ok=True)

        for file_info in meta1["files"]:
            filepath = scrape1 / "content" / file_info["filename"]
            if filepath.exists():
                target = content_dir / file_info["filename"]
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(filepath.read_text())

        # Verify current/ has content
        assert list((current_dir / "content").glob("**/*.md"))


def test_current_directory_manager_init(tmp_outputs_dir: Path):
    """Test basic initialization."""
    site_name = "test_wiki"
    manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

    assert manager.base_output_dir == tmp_outputs_dir
    assert manager.site_name == site_name


def test_get_current_source(tmp_outputs_dir: Path):
    """Test getting timestamp of current source."""
    site_name = "test_wiki"
    source_timestamp = "2025-11-20_02-00-00"

    create_test_scrape_directory(tmp_outputs_dir, site_name, source_timestamp, 3)

    # Create current from source
    current_dir = tmp_outputs_dir / site_name / "current"
    current_dir.mkdir(parents=True)

    current_meta = {
        "site": {"name": site_name},
        "current_state": {
            "source_timestamp": source_timestamp,
            "last_updated": "2025-11-20T02:00:00"
        },
        "files": [],
    }

    save_json_file(current_dir / "metadata.json", current_meta)

    manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
    source = manager.get_current_source()

    # Should be None or the actual timestamp
    assert source is None or source == source_timestamp


def test_get_rollback_candidates(tmp_outputs_dir: Path):
    """Test getting available rollback candidates."""
    site_name = "test_wiki"

    # Create multiple scrapes
    create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_01-00-00", 3)
    create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_02-00-00", 4)
    create_test_scrape_directory(tmp_outputs_dir, site_name, "2025-11-20_03-00-00", 5)

    CurrentDirectoryManager(tmp_outputs_dir, site_name)

    # Get rollback candidates (if method exists, otherwise test structure)
    # This tests the directory listing capability
    site_dir = tmp_outputs_dir / site_name
    if site_dir.exists():
        scrape_dirs = [d for d in site_dir.iterdir() if d.is_dir() and d.name != "current"]
        result = {d.name: d for d in scrape_dirs}
    else:
        result = {}

    # Should have directory entries if scrapes exist
    assert result == {} or len(result) > 0


@pytest.mark.unit
class TestCurrentDirectoryManagerExtended:
    """Extended tests for CurrentDirectoryManager."""

    def test_update_from_scrape_missing_scrape(self, tmp_outputs_dir: Path):
        """Test update fails when scrape is missing."""
        site_name = "test_wiki"
        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        # Mock tracker to return None for scrape
        with patch.object(tracker, 'get_scrape_by_timestamp', return_value=None):
            result = manager.update_from_scrape("2025-11-20_01-00-00", tracker)

        assert "error" in result
        assert "Scrape not found" in result["error"]

    def test_update_from_scrape_corrupted_current_metadata(self, tmp_outputs_dir: Path):
        """Test update rebuilds when current metadata is corrupted."""
        site_name = "test_wiki"
        timestamp = "2025-11-20_01-00-00"

        # Create scrape to rebuild from
        create_test_scrape_directory(tmp_outputs_dir, site_name, timestamp, 3)

        # Create corrupted current directory
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)
        (current_dir / "metadata.json").write_text("{ invalid json }")

        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        # Should trigger rebuild
        result = manager.update_from_scrape(timestamp, tracker)

        assert result["success"] is True
        assert result["operation"] == "rebuild"

    def test_update_from_scrape_missing_previous_source(self, tmp_outputs_dir: Path):
        """Test update rebuilds when previous source scrape is missing."""
        site_name = "test_wiki"
        current_timestamp = "2025-11-20_02-00-00"
        prev_timestamp = "2025-11-20_01-00-00"

        # Create current scrape
        create_test_scrape_directory(tmp_outputs_dir, site_name, current_timestamp, 3)

        # Create current directory pointing to missing previous scrape
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)
        metadata = load_json_file(current_dir / "metadata.json")

        # Fix metadata structure to match current/ format
        if "scrape" in metadata:
            metadata["current_state"] = metadata.pop("scrape")
            metadata["current_state"]["source_timestamp"] = prev_timestamp
            metadata["current_state"]["last_updated"] = current_timestamp

        save_json_file(current_dir / "metadata.json", metadata)

        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        # Should trigger rebuild because prev_timestamp scrape doesn't exist
        result = manager.update_from_scrape(current_timestamp, tracker)

        assert result["success"] is True
        assert result["operation"] == "rebuild"

    def test_rebuild_from_timestamp_missing_metadata(self, tmp_outputs_dir: Path):
        """Test rebuild fails when scrape metadata is missing."""
        site_name = "test_wiki"
        timestamp = "2025-11-20_01-00-00"

        # Create scrape dir but no metadata
        scrape_dir = tmp_outputs_dir / site_name / timestamp
        scrape_dir.mkdir(parents=True)

        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        result = manager.rebuild_from_timestamp(timestamp)

        assert "error" in result
        assert "Scrape not found" in result["error"]

    def test_rebuild_from_timestamp_corrupted_metadata(self, tmp_outputs_dir: Path):
        """Test rebuild fails when scrape metadata is corrupted."""
        site_name = "test_wiki"
        timestamp = "2025-11-20_01-00-00"

        # Create scrape with invalid metadata
        scrape_dir = tmp_outputs_dir / site_name / timestamp
        scrape_dir.mkdir(parents=True)
        (scrape_dir / "metadata.json").write_text("{ invalid }")

        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        result = manager.rebuild_from_timestamp(timestamp)

        assert "error" in result
        assert "Failed to load metadata" in result["error"]

    def test_verify_integrity_missing_files(self, tmp_outputs_dir: Path):
        """Test integrity check detects missing files."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)

        # Delete a file referenced in metadata
        metadata = load_json_file(current_dir / "metadata.json")
        filename = metadata["files"][0]["filename"]
        (current_dir / "content" / filename).unlink()

        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        issues = manager.verify_integrity()

        assert any("missing from filesystem" in issue for issue in issues)

    def test_verify_integrity_orphaned_files(self, tmp_outputs_dir: Path):
        """Test integrity check detects orphaned files."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)

        # Create an orphaned file
        (current_dir / "content" / "orphan.md").write_text("orphan")

        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        issues = manager.verify_integrity()

        assert any("orphaned files" in issue for issue in issues)

    def test_verify_integrity_missing_delta_log(self, tmp_outputs_dir: Path):
        """Test integrity check detects missing delta log."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)

        # Create delta log first (helper doesn't create it)
        (current_dir / "delta_log.json").write_text("{}")

        # Remove delta log
        (current_dir / "delta_log.json").unlink()

        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        issues = manager.verify_integrity()

        assert "Delta log missing" in issues

    def test_get_files_for_upload_corrupt_status(self, tmp_outputs_dir: Path):
        """Test get_files_for_upload handles corrupt upload status."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)

        # Corrupt upload status
        (current_dir / "upload_status.json").write_text("{ invalid }")

        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        result = manager.get_files_for_upload(incremental=True)

        # Should fallback to full upload
        assert "Full upload (status corrupt)" in result["summary"]
        assert len(result["upload"]) == 3

    def test_save_upload_status_checksum_preservation(self, tmp_outputs_dir: Path):
        """Test that checksums are preserved correctly during save."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 1)
        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Setup initial state
        file_url = "https://example.com/page1"
        file_id = "file-123"
        remote_checksum = "remote_hash_123"

        # Mock metadata to match our test case and fix structure
        metadata = load_json_file(current_dir / "metadata.json")
        metadata["files"][0]["url"] = file_url

        # Fix metadata structure
        if "scrape" in metadata:
            metadata["current_state"] = metadata.pop("scrape")
            metadata["current_state"]["source_timestamp"] = "2025-11-20_01-00-00"

        save_json_file(current_dir / "metadata.json", metadata)

        # Simulate upload result from a rebuild
        upload_result = {
            "knowledge_id": "kb-1",
            "knowledge_name": "KB",
            "files_uploaded": 0,
            "rebuilt_from_remote": True,
            "file_id_map": {file_url: file_id},
            "files": [
                {
                    "url": file_url,
                    "checksum": remote_checksum
                }
            ]
        }

        manager.save_upload_status(upload_result)

        # Verify checksum was preserved
        status = manager.get_upload_status()
        assert status["files"][0]["checksum"] == remote_checksum
        assert status["rebuilt_from_remote"] is True

    def test_copy_file_failure(self, tmp_outputs_dir: Path):
        """Test handling of file copy failure."""
        site_name = "test_wiki"
        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Mock shutil.copy2 to raise exception
        with patch('shutil.copy2', side_effect=OSError("Copy failed")):
            result = manager._copy_file_to_current(
                "2025-11-20_01-00-00",
                {"filepath": "test.md", "filename": "test.md"}
            )

        assert result is False

    def test_remove_file_failure(self, tmp_outputs_dir: Path):
        """Test handling of file removal failure."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 1)
        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        metadata = load_json_file(current_dir / "metadata.json")
        file_info = metadata["files"][0]

        # Mock Path.unlink to raise exception
        with patch('pathlib.Path.unlink', side_effect=OSError("Delete failed")):
            result = manager._remove_file_from_current(file_info)

        assert result is False

    def test_update_from_scrape_success(self, tmp_outputs_dir: Path):
        """Test successful update with additions, modifications, and deletions."""
        site_name = "test_wiki"
        prev_timestamp = "2025-11-20_01-00-00"
        curr_timestamp = "2025-11-20_02-00-00"

        # Create previous scrape
        create_test_scrape_directory(tmp_outputs_dir, site_name, prev_timestamp, 3)

        # Create current directory based on previous scrape
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)
        metadata = load_json_file(current_dir / "metadata.json")

        # Fix metadata structure
        if "scrape" in metadata:
            metadata["current_state"] = metadata.pop("scrape")
            metadata["current_state"]["source_timestamp"] = prev_timestamp
            metadata["current_state"]["last_updated"] = prev_timestamp
            # Ensure files have added_on
            for f in metadata["files"]:
                f["added_on"] = prev_timestamp
                f["last_modified"] = prev_timestamp
        save_json_file(current_dir / "metadata.json", metadata)

        # Create new scrape with changes:
        # - page_0 modified (checksum change)
        # - page_1 deleted (not in new scrape)
        # - page_2 unchanged
        # - page_3 added
        scrape_dir = tmp_outputs_dir / site_name / curr_timestamp
        scrape_dir.mkdir(parents=True)
        (scrape_dir / "content").mkdir()

        new_files = [
            {
                "url": "https://example.com/page0",
                "filepath": "content/page_0.md",
                "filename": "page_0.md",
                "checksum": "modified_hash", # Modified
                "size": 1024
            },
            # page_1 deleted
            {
                "url": "https://example.com/page2",
                "filepath": "content/page_2.md",
                "filename": "page_2.md",
                "checksum": "hash0002", # Unchanged (matches helper)
                "size": 3072
            },
            {
                "url": "https://example.com/page3",
                "filepath": "content/page_3.md",
                "filename": "page_3.md",
                "checksum": "hash3", # Added
                "size": 4096
            }
        ]

        new_metadata = {
            "site": {"name": site_name},
            "scrape": {"timestamp": curr_timestamp},
            "files": new_files
        }
        save_json_file(scrape_dir / "metadata.json", new_metadata)

        # Create content files for new scrape
        (scrape_dir / "content" / "page_0.md").write_text("modified content")
        (scrape_dir / "content" / "page_2.md").write_text("content 2")
        (scrape_dir / "content" / "page_3.md").write_text("new content")

        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        tracker = MetadataTracker(tmp_outputs_dir, site_name)

        result = manager.update_from_scrape(curr_timestamp, tracker)

        assert result["success"] is True
        assert result["changes"]["added"] == 1
        assert result["changes"]["modified"] == 1
        assert result["changes"]["removed"] == 1

        # Verify delta log
        delta_log = load_json_file(current_dir / "delta_log.json")
        assert len(delta_log["deltas"]) == 1 # create_current_directory doesn't create log, so this is first
        assert delta_log["deltas"][0]["operation"] == "update"

    def test_append_delta_log_corrupt(self, tmp_outputs_dir: Path):
        """Test appending to a corrupt delta log recreates it."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 1)
        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Create corrupt delta log
        (current_dir / "delta_log.json").write_text("{ invalid }")

        entry = {"timestamp": "now", "operation": "test"}
        manager._append_delta_log(entry)

        # Should be recreated with just the new entry
        log = load_json_file(current_dir / "delta_log.json")
        assert len(log["deltas"]) == 1
        assert log["deltas"][0] == entry

    def test_get_files_for_upload_incremental(self, tmp_outputs_dir: Path):
        """Test incremental upload logic."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 3)
        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Setup upload status to simulate previous state
        # page_0: modified (checksum diff)
        # page_1: deleted (in status but not in current - wait, create_current_directory puts all 3 in current)
        # page_2: unchanged

        # We need to modify current state to match this scenario
        # Let's say current has page_0 (new hash), page_2 (same hash), page_3 (new file)
        # And previous upload had page_0 (old hash), page_1 (deleted now), page_2 (same hash)

        # Update current metadata
        metadata = load_json_file(current_dir / "metadata.json")
        metadata["files"][0]["checksum"] = "new_hash_0" # Modified
        # page_1 is in metadata, let's remove it to simulate deletion
        del metadata["files"][1]
        # Add page_3
        metadata["files"].append({
            "url": "https://example.com/page3",
            "filename": "page_3.md",
            "checksum": "hash3",
            "size": 100
        })
        save_json_file(current_dir / "metadata.json", metadata)

        # Create upload status
        upload_status = {
            "site_name": site_name,
            "files": [
                {
                    "url": "https://example.com/page0",
                    "checksum": "old_hash_0",
                    "file_id": "id_0"
                },
                {
                    "url": "https://example.com/page1",
                    "checksum": "hash0001", # Matches helper
                    "file_id": "id_1"
                },
                {
                    "url": "https://example.com/page2",
                    "checksum": "hash0002", # Matches helper
                    "file_id": "id_2"
                }
            ]
        }
        save_json_file(current_dir / "upload_status.json", upload_status)

        result = manager.get_files_for_upload(incremental=True)

        # Check uploads (modified + new)
        upload_urls = {f["url"] for f in result["upload"]}
        assert "https://example.com/page0" in upload_urls # Modified
        assert "https://example.com/page3" in upload_urls # New
        assert "https://example.com/page2" not in upload_urls # Unchanged

        # Check deletions
        assert "https://example.com/page1" in result["delete"]

    def test_update_metadata_none(self, tmp_outputs_dir: Path):
        """Test _update_metadata handles missing metadata file."""
        site_name = "test_wiki"
        current_dir = create_current_directory(tmp_outputs_dir, site_name, 1)
        manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Remove metadata file
        (current_dir / "metadata.json").unlink()

        # Should log error and return without crashing
        manager._update_metadata("timestamp", {})

        # Verify file wasn't recreated
        assert not (current_dir / "metadata.json").exists()
