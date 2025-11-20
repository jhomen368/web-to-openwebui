"""
Unit tests for STATE_MANAGER module (webowui/state_manager.py).

Tests for:
- StateManager initialization
- State detection and auto-rebuild logic
- Remote rebuild with validation
- Confidence validation
- Health checking
- State info retrieval
"""

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from tests.utils.helpers import save_json_file
from webowui.state_manager import StateManager
from webowui.storage.current_directory_manager import CurrentDirectoryManager


def _create_test_metadata(site_name: str, timestamp: str, num_files: int = 3) -> dict[str, Any]:
    """Helper to create test metadata without file I/O."""
    files = []
    for i in range(num_files):
        files.append(
            {
                "url": f"https://example.com/page{i}",
                "filepath": f"content/page{i}.md",
                "checksum": f"hash{i:04d}",
                "size": 1024 * (i + 1),
            }
        )

    return {
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


@pytest.mark.unit
class TestStateManagerInitialization:
    """Test StateManager initialization."""

    def test_state_manager_init(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test basic initialization."""
        site_name = "test_wiki"
        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        state_mgr = StateManager(current_manager, mock_openwebui_client)

        assert state_mgr.current_manager == current_manager
        assert state_mgr.client == mock_openwebui_client


@pytest.mark.unit
class TestDetectStateStatus:
    """Test detect_state_status method."""

    @pytest.mark.asyncio
    async def test_detect_state_with_existing_state(
        self, tmp_outputs_dir: Path, mock_openwebui_client
    ):
        """Test when state already exists (no rebuild needed)."""
        site_name = "test_wiki"
        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        state_mgr = StateManager(current_manager, mock_openwebui_client)

        # Existing state (non-empty previous_file_map)
        previous_file_map = {"https://example.com/page1": "file-123"}

        needs_rebuild, kb_id, rebuilt = await state_mgr.detect_state_status(
            incremental=True,
            previous_file_map=previous_file_map,
            knowledge_id="kb-123",
            site_name=site_name,
            knowledge_name="Test KB",
        )

        assert needs_rebuild is False
        assert kb_id == "kb-123"
        assert rebuilt is None

    @pytest.mark.asyncio
    async def test_detect_state_non_incremental(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test non-incremental upload (no rebuild needed)."""
        site_name = "test_wiki"
        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        state_mgr = StateManager(current_manager, mock_openwebui_client)

        needs_rebuild, kb_id, rebuilt = await state_mgr.detect_state_status(
            incremental=False,  # Full upload
            previous_file_map={},
            knowledge_id="kb-123",
            site_name=site_name,
            knowledge_name="Test KB",
        )

        assert needs_rebuild is False
        assert kb_id == "kb-123"
        assert rebuilt is None

    @pytest.mark.asyncio
    async def test_detect_state_missing_with_knowledge_id(
        self, tmp_outputs_dir: Path, mock_openwebui_client
    ):
        """Test missing state with knowledge_id provided."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        # Create metadata for rebuild
        metadata = _create_test_metadata(site_name, "2025-11-20_01-00-00", 3)
        save_json_file(current_dir / "metadata.json", metadata)

        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Mock save_upload_status to avoid current_state dependency
        current_manager.save_upload_status = MagicMock()

        # Mock successful rebuild
        mock_openwebui_client._rebuild_state_inline = AsyncMock(
            return_value={
                "knowledge_id": "kb-123",
                "files_uploaded": 3,
                "rebuild_confidence": "high",
                "rebuild_match_rate": 1.0,
            }
        )

        state_mgr = StateManager(current_manager, mock_openwebui_client)

        needs_rebuild, kb_id, rebuilt = await state_mgr.detect_state_status(
            incremental=True,
            previous_file_map={},  # Missing state
            knowledge_id="kb-123",
            site_name=site_name,
            knowledge_name="Test KB",
            min_confidence="medium",
        )

        assert needs_rebuild is True
        assert kb_id == "kb-123"
        assert rebuilt is not None
        assert rebuilt["rebuild_confidence"] == "high"

    @pytest.mark.asyncio
    async def test_detect_state_missing_no_knowledge_id(
        self, tmp_outputs_dir: Path, mock_openwebui_client
    ):
        """Test missing state without knowledge_id (searches for it)."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        metadata = _create_test_metadata(site_name, "2025-11-20_01-00-00", 3)
        save_json_file(current_dir / "metadata.json", metadata)

        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Mock save_upload_status to avoid current_state dependency
        current_manager.save_upload_status = MagicMock()

        # Mock finding knowledge ID
        mock_openwebui_client.find_knowledge_by_content = AsyncMock(return_value="kb-found-456")
        mock_openwebui_client._rebuild_state_inline = AsyncMock(
            return_value={
                "knowledge_id": "kb-found-456",
                "files_uploaded": 3,
                "rebuild_confidence": "medium",
                "rebuild_match_rate": 0.9,
            }
        )

        state_mgr = StateManager(current_manager, mock_openwebui_client)

        needs_rebuild, kb_id, rebuilt = await state_mgr.detect_state_status(
            incremental=True,
            previous_file_map={},
            knowledge_id=None,  # Not provided
            site_name=site_name,
            knowledge_name="Test KB",
        )

        assert needs_rebuild is True
        assert kb_id == "kb-found-456"
        assert rebuilt is not None

    @pytest.mark.asyncio
    async def test_detect_state_cannot_find_knowledge(
        self, tmp_outputs_dir: Path, mock_openwebui_client
    ):
        """Test when knowledge base cannot be found."""
        site_name = "test_wiki"
        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Mock not finding knowledge
        mock_openwebui_client.find_knowledge_by_content = AsyncMock(return_value=None)

        state_mgr = StateManager(current_manager, mock_openwebui_client)

        needs_rebuild, kb_id, rebuilt = await state_mgr.detect_state_status(
            incremental=True,
            previous_file_map={},
            knowledge_id=None,
            site_name=site_name,
            knowledge_name="Test KB",
        )

        assert needs_rebuild is True
        assert kb_id is None
        assert rebuilt is None

    @pytest.mark.asyncio
    async def test_detect_state_rebuild_fails(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test when rebuild attempt fails."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        metadata = _create_test_metadata(site_name, "2025-11-20_01-00-00", 3)
        save_json_file(current_dir / "metadata.json", metadata)

        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Mock rebuild failure
        mock_openwebui_client._rebuild_state_inline = AsyncMock(return_value=None)

        state_mgr = StateManager(current_manager, mock_openwebui_client)

        needs_rebuild, kb_id, rebuilt = await state_mgr.detect_state_status(
            incremental=True,
            previous_file_map={},
            knowledge_id="kb-123",
            site_name=site_name,
            knowledge_name="Test KB",
        )

        assert needs_rebuild is True
        assert kb_id == "kb-123"
        assert rebuilt is None


@pytest.mark.unit
class TestRebuildFromRemote:
    """Test rebuild_from_remote method."""

    @pytest.mark.asyncio
    async def test_rebuild_success_with_autosave(
        self, tmp_outputs_dir: Path, mock_openwebui_client
    ):
        """Test successful rebuild with auto-save."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        metadata = _create_test_metadata(site_name, "2025-11-20_01-00-00", 3)
        save_json_file(current_dir / "metadata.json", metadata)

        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Mock save_upload_status to avoid current_state dependency
        current_manager.save_upload_status = MagicMock()

        # Mock successful rebuild
        rebuilt_status = {
            "knowledge_id": "kb-123",
            "files_uploaded": 3,
            "rebuild_confidence": "high",
            "rebuild_match_rate": 1.0,
            "files": [],
        }
        mock_openwebui_client._rebuild_state_inline = AsyncMock(return_value=rebuilt_status)

        state_mgr = StateManager(current_manager, mock_openwebui_client)

        success, rebuilt, error = await state_mgr.rebuild_from_remote(
            knowledge_id="kb-123",
            site_name=site_name,
            min_confidence="medium",
            auto_save=True,
        )

        assert success is True
        assert rebuilt is not None
        assert error is None

        # Verify save was called
        current_manager.save_upload_status.assert_called_once()

    @pytest.mark.asyncio
    async def test_rebuild_success_without_autosave(
        self, tmp_outputs_dir: Path, mock_openwebui_client
    ):
        """Test successful rebuild without auto-save."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        metadata = _create_test_metadata(site_name, "2025-11-20_01-00-00", 3)
        save_json_file(current_dir / "metadata.json", metadata)

        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Mock save_upload_status to avoid current_state dependency
        current_manager.save_upload_status = MagicMock()

        rebuilt_status = {
            "knowledge_id": "kb-123",
            "files_uploaded": 3,
            "rebuild_confidence": "medium",
            "rebuild_match_rate": 0.85,
        }
        mock_openwebui_client._rebuild_state_inline = AsyncMock(return_value=rebuilt_status)

        state_mgr = StateManager(current_manager, mock_openwebui_client)

        success, rebuilt, error = await state_mgr.rebuild_from_remote(
            knowledge_id="kb-123",
            site_name=site_name,
            min_confidence="medium",
            auto_save=False,
        )

        assert success is True
        assert rebuilt is not None
        assert error is None

        # Verify NOT saved
        upload_status = current_manager.get_upload_status()
        assert upload_status is None

    @pytest.mark.asyncio
    async def test_rebuild_missing_metadata(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test rebuild when metadata file missing."""
        site_name = "test_wiki"
        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        state_mgr = StateManager(current_manager, mock_openwebui_client)

        success, rebuilt, error = await state_mgr.rebuild_from_remote(
            knowledge_id="kb-123",
            site_name=site_name,
        )

        assert success is False
        assert rebuilt is None
        assert "metadata not found" in error

    @pytest.mark.asyncio
    async def test_rebuild_corrupted_metadata(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test rebuild with corrupted metadata file."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        # Write invalid JSON
        (current_dir / "metadata.json").write_text("{ invalid }")

        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        state_mgr = StateManager(current_manager, mock_openwebui_client)

        success, rebuilt, error = await state_mgr.rebuild_from_remote(
            knowledge_id="kb-123",
            site_name=site_name,
        )

        assert success is False
        assert rebuilt is None
        assert "Failed to load metadata" in error

    @pytest.mark.asyncio
    async def test_rebuild_api_failure(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test rebuild when API call fails."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        metadata = _create_test_metadata(site_name, "2025-11-20_01-00-00", 3)
        save_json_file(current_dir / "metadata.json", metadata)

        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Mock API failure
        mock_openwebui_client._rebuild_state_inline = AsyncMock(return_value=None)

        state_mgr = StateManager(current_manager, mock_openwebui_client)

        success, rebuilt, error = await state_mgr.rebuild_from_remote(
            knowledge_id="kb-123",
            site_name=site_name,
            min_confidence="high",
        )

        assert success is False
        assert rebuilt is None
        assert "confidence below" in error or "rebuild failed" in error

    @pytest.mark.asyncio
    async def test_rebuild_low_confidence(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test rebuild with confidence below threshold."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        metadata = _create_test_metadata(site_name, "2025-11-20_01-00-00", 3)
        save_json_file(current_dir / "metadata.json", metadata)

        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        # Mock save_upload_status to avoid current_state dependency
        current_manager.save_upload_status = MagicMock()

        # Return low confidence
        rebuilt_status = {
            "knowledge_id": "kb-123",
            "files_uploaded": 3,
            "rebuild_confidence": "low",
            "rebuild_match_rate": 0.5,
        }
        mock_openwebui_client._rebuild_state_inline = AsyncMock(return_value=rebuilt_status)

        state_mgr = StateManager(current_manager, mock_openwebui_client)

        success, rebuilt, error = await state_mgr.rebuild_from_remote(
            knowledge_id="kb-123",
            site_name=site_name,
            min_confidence="high",  # Require high
        )

        assert success is False
        assert rebuilt is not None  # Returned but not accepted
        assert "below threshold" in error


@pytest.mark.unit
class TestValidateRebuildConfidence:
    """Test validate_rebuild_confidence method."""

    def test_validate_confidence_meets_threshold_high(
        self, tmp_outputs_dir: Path, mock_openwebui_client
    ):
        """Test validation when confidence meets high threshold."""
        current_manager = CurrentDirectoryManager(tmp_outputs_dir, "test")
        state_mgr = StateManager(current_manager, mock_openwebui_client)

        rebuilt_status = {
            "rebuild_confidence": "high",
            "rebuild_match_rate": 1.0,
            "files_uploaded": 10,
        }

        is_valid, message = state_mgr.validate_rebuild_confidence(rebuilt_status, "high")

        assert is_valid is True
        assert "meets threshold" in message

    def test_validate_confidence_meets_threshold_medium(
        self, tmp_outputs_dir: Path, mock_openwebui_client
    ):
        """Test validation when confidence meets medium threshold."""
        current_manager = CurrentDirectoryManager(tmp_outputs_dir, "test")
        state_mgr = StateManager(current_manager, mock_openwebui_client)

        rebuilt_status = {
            "rebuild_confidence": "medium",
            "rebuild_match_rate": 0.8,
            "files_uploaded": 8,
        }

        is_valid, message = state_mgr.validate_rebuild_confidence(rebuilt_status, "medium")

        assert is_valid is True

    def test_validate_confidence_below_threshold(
        self, tmp_outputs_dir: Path, mock_openwebui_client
    ):
        """Test validation when confidence below threshold."""
        current_manager = CurrentDirectoryManager(tmp_outputs_dir, "test")
        state_mgr = StateManager(current_manager, mock_openwebui_client)

        rebuilt_status = {
            "rebuild_confidence": "low",
            "rebuild_match_rate": 0.5,
            "files_uploaded": 5,
        }

        is_valid, message = state_mgr.validate_rebuild_confidence(
            rebuilt_status, "high"  # Require high
        )

        assert is_valid is False
        assert "below threshold" in message

    def test_validate_confidence_missing_fields(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test validation with missing confidence fields."""
        current_manager = CurrentDirectoryManager(tmp_outputs_dir, "test")
        state_mgr = StateManager(current_manager, mock_openwebui_client)

        rebuilt_status = {}  # Missing all fields

        is_valid, message = state_mgr.validate_rebuild_confidence(rebuilt_status, "medium")

        # Should handle gracefully (defaults to none/0.0/0)
        assert is_valid is False


@pytest.mark.unit
class TestCheckHealth:
    """Test check_health method."""

    @pytest.mark.asyncio
    async def test_check_health_with_local_metadata(
        self, tmp_outputs_dir: Path, mock_openwebui_client
    ):
        """Test health check with provided local metadata."""
        site_name = "test_wiki"
        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        local_metadata = _create_test_metadata(site_name, "2025-11-20_01-00-00", 3)

        mock_openwebui_client.check_state_health = AsyncMock(
            return_value={
                "status": "healthy",
                "needs_rebuild": False,
            }
        )

        state_mgr = StateManager(current_manager, mock_openwebui_client)

        health = await state_mgr.check_health(
            knowledge_id="kb-123",
            site_name=site_name,
            local_metadata=local_metadata,
        )

        assert health["status"] == "healthy"
        assert health["needs_rebuild"] is False

    @pytest.mark.asyncio
    async def test_check_health_loads_metadata(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test health check loads metadata automatically."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        metadata = _create_test_metadata(site_name, "2025-11-20_01-00-00", 3)
        save_json_file(current_dir / "metadata.json", metadata)

        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)

        mock_openwebui_client.check_state_health = AsyncMock(
            return_value={
                "status": "degraded",
                "needs_rebuild": True,
                "issues": ["Some files missing"],
            }
        )

        state_mgr = StateManager(current_manager, mock_openwebui_client)

        health = await state_mgr.check_health(
            knowledge_id="kb-123",
            site_name=site_name,
            local_metadata=None,  # Will load automatically
        )

        assert health["status"] == "degraded"
        assert health["needs_rebuild"] is True


@pytest.mark.unit
class TestStateInfo:
    """Test state information methods."""

    def test_get_state_info_exists(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test getting existing state info."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        upload_status = {
            "site_name": site_name,
            "knowledge_id": "kb-123",
            "files": [{"file_id": "file-1"}],
        }
        save_json_file(current_dir / "upload_status.json", upload_status)

        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        state_mgr = StateManager(current_manager, mock_openwebui_client)

        info = state_mgr.get_state_info()

        assert info is not None
        assert info["knowledge_id"] == "kb-123"

    def test_get_state_info_missing(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test getting state info when missing."""
        site_name = "test_wiki"
        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        state_mgr = StateManager(current_manager, mock_openwebui_client)

        info = state_mgr.get_state_info()

        assert info is None

    def test_has_upload_state_true(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test has_upload_state when state exists."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        upload_status = {
            "site_name": site_name,
            "files": [{"file_id": "file-1"}],
        }
        save_json_file(current_dir / "upload_status.json", upload_status)

        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        state_mgr = StateManager(current_manager, mock_openwebui_client)

        has_state = state_mgr.has_upload_state()

        assert has_state is True

    def test_has_upload_state_false(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test has_upload_state when state missing."""
        site_name = "test_wiki"
        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        state_mgr = StateManager(current_manager, mock_openwebui_client)

        has_state = state_mgr.has_upload_state()

        assert has_state is False

    def test_has_upload_state_empty_files(self, tmp_outputs_dir: Path, mock_openwebui_client):
        """Test has_upload_state with empty files list."""
        site_name = "test_wiki"
        current_dir = tmp_outputs_dir / site_name / "current"
        current_dir.mkdir(parents=True)

        upload_status = {
            "site_name": site_name,
            "files": [],  # Empty
        }
        save_json_file(current_dir / "upload_status.json", upload_status)

        current_manager = CurrentDirectoryManager(tmp_outputs_dir, site_name)
        state_mgr = StateManager(current_manager, mock_openwebui_client)

        has_state = state_mgr.has_upload_state()

        assert has_state is False
