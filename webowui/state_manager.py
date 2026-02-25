"""
State management module for centralizing upload state operations.

This module provides a clean abstraction layer for state detection, rebuilding,
and validation, eliminating duplicate code and improving maintainability.
"""

import json
import logging
from typing import cast

logger = logging.getLogger(__name__)


class StateManager:
    """
    Centralized state management for upload and rebuild operations.

    This class provides a clean abstraction for:
    - Detecting missing upload state
    - Rebuilding state from OpenWebUI
    - Validating rebuild confidence
    - Checking state health

    It eliminates duplicate logic between upload and rebuild-state commands.
    """

    def __init__(self, current_manager, client):
        """
        Initialize StateManager with dependencies.

        Args:
            current_manager: CurrentDirectoryManager instance for local state
            client: OpenWebUIClient instance for remote API operations
        """
        self.current_manager = current_manager
        self.client = client

    async def detect_state_status(
        self,
        incremental: bool,
        previous_file_map: dict,
        knowledge_id: str | None,
        site_name: str,
        knowledge_name: str,
        min_confidence: str = "medium",
    ) -> tuple[bool, str | None, dict | None]:
        """
        Detect if upload state is missing and attempt automatic recovery.

        This method implements the auto-rebuild logic that was previously
        duplicated in _upload_scrape(). It:
        1. Checks if state is missing (incremental + no previous_file_map)
        2. Attempts to find knowledge_id if not provided
        3. Loads local metadata for hash matching
        4. Calls rebuild logic with validation
        5. Returns results for caller to handle

        Args:
            incremental: Whether this is an incremental upload
            previous_file_map: Dict of URL -> file_id mappings from previous upload
            knowledge_id: Optional knowledge ID to rebuild from
            site_name: Site name for folder filtering
            knowledge_name: Knowledge base name for search
            min_confidence: Minimum match confidence threshold

        Returns:
            Tuple of (needs_rebuild, effective_knowledge_id, rebuilt_status):
            - needs_rebuild: Whether rebuild was needed and attempted
            - effective_knowledge_id: Knowledge ID found or provided
            - rebuilt_status: Rebuilt upload_status dict if successful, None if failed
        """
        # Only attempt auto-rebuild for incremental uploads with no state
        if not incremental or len(previous_file_map) > 0:
            return (False, knowledge_id, None)

        logger.info("Upload state missing - attempting automatic rebuild from OpenWebUI")

        # Try to find knowledge_id if not provided
        effective_knowledge_id = knowledge_id
        if not effective_knowledge_id:
            logger.info("No knowledge_id configured - searching for existing knowledge base...")
            effective_knowledge_id = await self.client.find_knowledge_by_content(
                site_name, knowledge_name
            )
            if effective_knowledge_id:
                logger.info(f"Found knowledge base: {effective_knowledge_id}")

        # If still no knowledge_id, can't rebuild
        if not effective_knowledge_id:
            logger.warning("Could not find knowledge base for auto-rebuild")
            return (True, None, None)

        # Attempt rebuild from remote
        success, rebuilt_status, error = await self.rebuild_from_remote(
            effective_knowledge_id,
            site_name,
            min_confidence=min_confidence,
            auto_save=True,  # Save immediately on success
        )

        if success and rebuilt_status:
            logger.info(
                f"State rebuilt successfully: {rebuilt_status['files_uploaded']} files matched "
                f"(confidence: {rebuilt_status['rebuild_confidence']})"
            )
            return (True, effective_knowledge_id, rebuilt_status)
        else:
            logger.warning(f"Auto-rebuild failed: {error}")
            return (True, effective_knowledge_id, None)

    async def rebuild_from_remote(
        self,
        knowledge_id: str,
        site_name: str,
        min_confidence: str = "medium",
        auto_save: bool = True,
    ) -> tuple[bool, dict | None, str | None]:
        """
        Rebuild upload state from OpenWebUI with validation.

        This wraps OpenWebUIClient._rebuild_state_inline() with additional
        validation and optional auto-save functionality.

        Args:
            knowledge_id: Knowledge base ID to rebuild from
            site_name: Site name for folder filtering
            min_confidence: Minimum match confidence ('high', 'medium', 'low')
            auto_save: Whether to automatically save rebuilt state

        Returns:
            Tuple of (success, rebuilt_status, error_message):
            - success: True if rebuild succeeded and confidence met threshold
            - rebuilt_status: Reconstructed upload_status dict if successful
            - error_message: Error description if failed, None if successful
        """
        # Load local metadata for hash matching
        metadata_file = self.current_manager.metadata_file
        if not metadata_file.exists():
            return (False, None, "Current directory metadata not found")

        try:
            with open(metadata_file) as f:
                local_metadata = json.load(f)
        except Exception as e:
            return (False, None, f"Failed to load metadata: {e}")

        # Perform rebuild using API client
        rebuilt_status = await self.client._rebuild_state_inline(
            knowledge_id,
            site_name,
            local_metadata,
            min_confidence=min_confidence,
        )

        if not rebuilt_status:
            return (
                False,
                None,
                f"Match confidence below '{min_confidence}' threshold or rebuild failed",
            )

        # Validate rebuild quality
        is_valid, validation_msg = self.validate_rebuild_confidence(rebuilt_status, min_confidence)

        if not is_valid:
            return (False, rebuilt_status, validation_msg)

        # Auto-save if requested
        if auto_save:
            try:
                self.current_manager.save_upload_status(rebuilt_status)
                logger.info("Rebuilt state saved to upload_status.json")
            except Exception as e:
                logger.error(f"Failed to save rebuilt state: {e}")
                return (False, rebuilt_status, f"Rebuild succeeded but save failed: {e}")

        return (True, rebuilt_status, None)

    def validate_rebuild_confidence(
        self, rebuilt_status: dict, min_confidence: str
    ) -> tuple[bool, str]:
        """
        Check if rebuild confidence meets the minimum threshold.

        Args:
            rebuilt_status: Rebuilt upload_status dict with confidence level
            min_confidence: Minimum required confidence level

        Returns:
            Tuple of (is_valid, message):
            - is_valid: True if confidence meets threshold
            - message: Description of validation result
        """
        confidence = rebuilt_status.get("rebuild_confidence", "none")
        match_rate = rebuilt_status.get("rebuild_match_rate", 0.0)
        files_matched = rebuilt_status.get("files_uploaded", 0)

        # Confidence hierarchy
        confidence_levels = ["very_low", "low", "medium", "high"]

        min_idx = (
            confidence_levels.index(min_confidence) if min_confidence in confidence_levels else 1
        )
        actual_idx = confidence_levels.index(confidence) if confidence in confidence_levels else 0

        if actual_idx < min_idx:
            return (
                False,
                f"Confidence '{confidence}' ({match_rate*100:.1f}%, {files_matched} files) "
                f"below threshold '{min_confidence}'",
            )

        return (
            True,
            f"Confidence '{confidence}' ({match_rate*100:.1f}%, {files_matched} files) meets threshold",
        )

    async def check_health(
        self, knowledge_id: str, site_name: str, local_metadata: dict | None = None
    ) -> dict:
        """
        Check health of local upload state vs remote OpenWebUI state.

        This is a thin wrapper around OpenWebUIClient.check_state_health() that
        automatically loads local metadata if not provided.

        Args:
            knowledge_id: Knowledge base ID to check
            site_name: Site name for folder filtering
            local_metadata: Optional local metadata (loaded automatically if None)

        Returns:
            Health status dict with:
            - status: 'healthy', 'missing', 'corrupted', 'degraded'
            - needs_rebuild: bool
            - issues: list of issues found
            - remote_file_count: count of remote files
            - local_file_count: count of local files
        """
        # Load local metadata if not provided
        if local_metadata is None:
            metadata_file = self.current_manager.metadata_file
            if metadata_file.exists():
                try:
                    with open(metadata_file) as f:
                        local_metadata = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load metadata: {e}")
                    local_metadata = None

        # Call API client health check
        return cast(
            dict, await self.client.check_state_health(knowledge_id, site_name, local_metadata)
        )

    def get_state_info(self) -> dict | None:
        """
        Get current upload state information.

        Returns:
            Upload status dict if exists, None otherwise
        """
        return cast(dict | None, self.current_manager.get_upload_status())

    def has_upload_state(self) -> bool:
        """
        Check if upload state file exists.

        Returns:
            True if upload_status.json exists and is valid
        """
        upload_status = self.current_manager.get_upload_status()
        return upload_status is not None and len(upload_status.get("files", [])) > 0

    async def sync_state(
        self, site_name: str, knowledge_id: str | None = None, auto_fix: bool = False
    ) -> dict:
        """
        Reconcile local state with OpenWebUI remote state.

        Args:
            site_name: Site name for folder filtering
            knowledge_id: Optional knowledge ID (uses local state if not provided)
            auto_fix: Whether to automatically fix discrepancies

        Returns:
            Dict with sync results:
            - success: bool
            - local_count: int
            - remote_count: int
            - in_sync_count: int
            - missing_remote: list of file_ids
            - extra_remote: list of file_ids
            - fixed_count: int (if auto_fix=True)
            - error: str (if failed)
        """
        # Get local state
        upload_status = self.current_manager.get_upload_status()
        if not upload_status:
            return {"success": False, "error": "No upload status found - nothing to sync"}

        # Use knowledge_id from parameter or upload status
        target_kb_id = knowledge_id or upload_status.get("knowledge_id")
        if not target_kb_id:
            return {"success": False, "error": "No knowledge_id found"}

        logger.info(f"Syncing {site_name} with knowledge {target_kb_id}")

        # Get remote state from OpenWebUI (filtered by site folder)
        remote_files = await self.client.get_knowledge_files(target_kb_id, site_folder=site_name)
        if remote_files is None:
            return {"success": False, "error": "Failed to get remote knowledge state"}

        # Build remote file_id set
        remote_file_ids = {f["id"] for f in remote_files}

        # Build local file_id map
        local_file_map = {}  # file_id -> file_info
        for file_info in upload_status.get("files", []):
            if "file_id" in file_info:
                local_file_map[file_info["file_id"]] = file_info

        local_file_ids = set(local_file_map.keys())

        # Calculate differences
        missing_remote = local_file_ids - remote_file_ids  # In local but not remote
        extra_remote = remote_file_ids - local_file_ids  # In remote but not local

        result = {
            "success": True,
            "local_count": len(local_file_ids),
            "remote_count": len(remote_file_ids),
            "in_sync_count": len(local_file_ids & remote_file_ids),
            "missing_remote": list(missing_remote),
            "extra_remote": list(extra_remote),
            "fixed_count": 0,
            "local_file_map": local_file_map,  # Include map for reporting details
            "remote_files": remote_files,  # Include remote files for reporting details
        }

        # Auto-fix if requested
        if auto_fix and missing_remote:
            logger.info(f"Fixing: Removing {len(missing_remote)} deleted files from local state...")
            # Remove from upload_status
            updated_files = [
                f for f in upload_status["files"] if f.get("file_id") not in missing_remote
            ]
            upload_status["files"] = updated_files
            self.current_manager.save_upload_status(upload_status)
            result["fixed_count"] = len(missing_remote)
            logger.info(f"Removed {len(missing_remote)} files from local state")

        return result
