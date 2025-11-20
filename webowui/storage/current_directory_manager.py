"""
Current directory manager for maintaining up-to-date content state.
"""

import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import cast

from .metadata_tracker import MetadataTracker

logger = logging.getLogger(__name__)


class CurrentDirectoryManager:
    """Manages the current/ directory containing latest file versions."""

    def __init__(self, base_output_dir: Path, site_name: str):
        """
        Initialize manager for a site's current directory.

        Args:
            base_output_dir: Base outputs directory
            site_name: Name of the site
        """
        self.base_output_dir = base_output_dir
        self.site_name = site_name
        self.site_dir = base_output_dir / site_name
        self.current_dir = self.site_dir / "current"
        self.content_dir = self.current_dir / "content"
        self.metadata_file = self.current_dir / "metadata.json"
        self.delta_log_file = self.current_dir / "delta_log.json"

    def update_from_scrape(self, scrape_timestamp: str, metadata_tracker: MetadataTracker) -> dict:
        """
        Update current/ directory from a new scrape using diff.

        Args:
            scrape_timestamp: Timestamp of the new scrape
            metadata_tracker: MetadataTracker instance for comparison

        Returns:
            Summary of changes applied
        """
        logger.info(f"Updating current/ from scrape {scrape_timestamp}")

        # Get new scrape metadata
        new_scrape = metadata_tracker.get_scrape_by_timestamp(scrape_timestamp)
        if not new_scrape:
            return {"error": f"Scrape not found: {scrape_timestamp}"}

        # Check if current/ exists
        if not self.current_dir.exists():
            # First time - rebuild from scratch
            logger.info("Current directory doesn't exist, building from scratch")
            return self.rebuild_from_timestamp(scrape_timestamp)

        # Get current state
        current_metadata = self._load_metadata()
        if not current_metadata:
            # Corrupted, rebuild
            logger.warning("Current metadata corrupted, rebuilding")
            return self.rebuild_from_timestamp(scrape_timestamp)

        # Get previous scrape for comparison
        previous_timestamp = current_metadata["current_state"]["source_timestamp"]
        previous_scrape = metadata_tracker.get_scrape_by_timestamp(previous_timestamp)

        if not previous_scrape:
            # Previous source missing, rebuild
            logger.warning(f"Previous source {previous_timestamp} not found, rebuilding")
            return self.rebuild_from_timestamp(scrape_timestamp)

        # Compare scrapes to find changes
        comparison = metadata_tracker.compare_scrapes(previous_timestamp, scrape_timestamp)

        changes = comparison["changes"]
        new_files = {f["url"]: f for f in new_scrape.get("files", [])}

        # Apply changes
        added_count = 0
        modified_count = 0
        removed_count = 0

        # Add new files
        for url in changes["added"]:
            file_info = new_files[url]
            if self._copy_file_to_current(scrape_timestamp, file_info):
                added_count += 1

        # Update modified files
        for url in changes["modified"]:
            file_info = new_files[url]
            if self._copy_file_to_current(scrape_timestamp, file_info):
                modified_count += 1

        # Remove deleted files
        old_files = {f["url"]: f for f in current_metadata.get("files", [])}
        for url in changes["removed"]:
            if url in old_files and self._remove_file_from_current(old_files[url]):
                removed_count += 1

        # Update metadata
        self._update_metadata(scrape_timestamp, new_scrape)

        # Append to delta log
        delta_entry = {
            "timestamp": scrape_timestamp,
            "operation": "update",
            "changes": {"added": added_count, "modified": modified_count, "removed": removed_count},
            "details": {
                "added": list(changes["added"]),
                "modified": list(changes["modified"]),
                "removed": list(changes["removed"]),
            },
        }
        self._append_delta_log(delta_entry)

        result = {
            "success": True,
            "operation": "update",
            "source_timestamp": scrape_timestamp,
            "changes": {"added": added_count, "modified": modified_count, "removed": removed_count},
            "summary": f"Updated: +{added_count} ~{modified_count} -{removed_count} files",
        }

        logger.info(f"Current directory updated: {result['summary']}")
        return result

    def rebuild_from_timestamp(self, timestamp: str) -> dict:
        """
        Completely rebuild current/ from a specific timestamp.

        Args:
            timestamp: Timestamp to rebuild from

        Returns:
            Summary of rebuild operation
        """
        logger.info(f"Rebuilding current/ from {timestamp}")

        # Get scrape metadata
        scrape_dir = self.site_dir / timestamp
        metadata_file = scrape_dir / "metadata.json"

        if not metadata_file.exists():
            return {"error": f"Scrape not found: {timestamp}"}

        try:
            with open(metadata_file) as f:
                scrape_metadata = json.load(f)
        except Exception as e:
            return {"error": f"Failed to load metadata: {e}"}

        # Clear current directory
        if self.current_dir.exists():
            shutil.rmtree(self.current_dir)

        # Create fresh directories
        self.current_dir.mkdir(parents=True, exist_ok=True)
        self.content_dir.mkdir(exist_ok=True)

        # Copy all files
        source_content_dir = scrape_dir / "content"
        files_copied = 0

        for file_info in scrape_metadata.get("files", []):
            source_file = source_content_dir / file_info["filename"]
            if source_file.exists():
                dest_file = self.content_dir / file_info["filename"]
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, dest_file)
                files_copied += 1

        # Create metadata
        self._create_initial_metadata(timestamp, scrape_metadata)

        # Create delta log with initial entry
        delta_entry = {
            "timestamp": timestamp,
            "operation": "initial",
            "changes": {"added": files_copied, "modified": 0, "removed": 0},
        }
        self._create_delta_log(delta_entry)

        result = {
            "success": True,
            "operation": "rebuild",
            "source_timestamp": timestamp,
            "files_copied": files_copied,
            "summary": f"Rebuilt with {files_copied} files from {timestamp}",
        }

        logger.info(f"Current directory rebuilt: {result['summary']}")
        return result

    def get_current_state(self) -> dict | None:
        """
        Get information about current directory state.

        Returns:
            Current state info or None if doesn't exist
        """
        if not self.current_dir.exists():
            return None

        metadata = self._load_metadata()
        if not metadata:
            return None

        # Calculate actual size
        total_size = sum(f.stat().st_size for f in self.content_dir.rglob("*.md") if f.is_file())

        return {
            "exists": True,
            "source_timestamp": metadata["current_state"]["source_timestamp"],
            "last_updated": metadata["current_state"]["last_updated"],
            "total_files": len(metadata.get("files", [])),
            "total_size": total_size,
            "site": metadata["site"],
        }

    def get_current_source(self) -> str | None:
        """
        Get timestamp of current source.

        Returns:
            Source timestamp or None if doesn't exist
        """
        state = self.get_current_state()
        if state:
            return cast(str, state["source_timestamp"])
        return None

    def verify_integrity(self) -> list[str]:
        """
        Verify current/ directory integrity.

        Returns:
            List of issues found (empty = healthy)
        """
        issues = []

        if not self.current_dir.exists():
            issues.append("Current directory does not exist")
            return issues

        if not self.metadata_file.exists():
            issues.append("Metadata file missing")
            return issues

        metadata = self._load_metadata()
        if not metadata:
            issues.append("Metadata file corrupted")
            return issues

        # Check all files in metadata exist
        missing_files = []
        for file_info in metadata.get("files", []):
            file_path = self.content_dir / file_info["filename"]
            if not file_path.exists():
                missing_files.append(file_info["filename"])

        if missing_files:
            issues.append(
                f"{len(missing_files)} files referenced in metadata but missing from filesystem"
            )

        # Check for orphaned files (in filesystem but not in metadata)
        metadata_files = {f["filename"] for f in metadata.get("files", [])}
        actual_files = set()
        for file_path in self.content_dir.rglob("*.md"):
            rel_path = file_path.relative_to(self.content_dir)
            actual_files.add(str(rel_path))

        orphaned = actual_files - metadata_files
        if orphaned:
            issues.append(f"{len(orphaned)} orphaned files in filesystem not in metadata")

        # Verify delta log
        if not self.delta_log_file.exists():
            issues.append("Delta log missing")

        return issues

    def _copy_file_to_current(self, scrape_timestamp: str, file_info: dict) -> bool:
        """Copy a file from scrape to current directory."""
        try:
            source_file = self.site_dir / scrape_timestamp / file_info["filepath"]
            dest_file = self.content_dir / file_info["filename"]

            # Create parent directory if needed
            dest_file.parent.mkdir(parents=True, exist_ok=True)

            # Copy file
            shutil.copy2(source_file, dest_file)
            return True
        except Exception as e:
            logger.error(f"Failed to copy {file_info['filename']}: {e}")
            return False

    def _remove_file_from_current(self, file_info: dict) -> bool:
        """Remove a file from current directory."""
        try:
            file_path = self.content_dir / file_info["filename"]
            if file_path.exists():
                file_path.unlink()

                # Remove empty parent directories
                parent = file_path.parent
                while parent != self.content_dir:
                    if not any(parent.iterdir()):
                        parent.rmdir()
                        parent = parent.parent
                    else:
                        break

                return True
            return False
        except Exception as e:
            logger.error(f"Failed to remove {file_info['filename']}: {e}")
            return False

    def _load_metadata(self) -> dict | None:
        """Load current metadata."""
        if not self.metadata_file.exists():
            return None

        try:
            with open(self.metadata_file) as f:
                return cast(dict | None, json.load(f))
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return None

    def _create_initial_metadata(self, timestamp: str, scrape_metadata: dict):
        """Create initial metadata for current directory."""
        metadata = {
            "site": scrape_metadata["site"],
            "current_state": {
                "last_updated": datetime.now().isoformat(),
                "source_timestamp": timestamp,
                "total_files": len(scrape_metadata.get("files", [])),
                "total_size": sum(f["size"] for f in scrape_metadata.get("files", [])),
            },
            "files": [
                {**file_info, "added_on": timestamp, "last_modified": timestamp}
                for file_info in scrape_metadata.get("files", [])
            ],
        }

        with open(self.metadata_file, "w") as f:
            json.dump(metadata, f, indent=2)

    def _update_metadata(self, timestamp: str, scrape_metadata: dict):
        """Update metadata after applying changes."""
        current_metadata = self._load_metadata()

        # Add None check
        if not current_metadata:
            logger.error("Cannot update metadata: current metadata is None")
            return

        # Create lookup of current files
        current_files = {f["url"]: f for f in current_metadata.get("files", [])}

        # Update with new scrape files
        new_files = []
        for file_info in scrape_metadata.get("files", []):
            url = file_info["url"]
            if url in current_files:
                # Existing file - update last_modified
                updated_file = {
                    **file_info,
                    "added_on": current_files[url].get("added_on", timestamp),
                    "last_modified": timestamp,
                }
            else:
                # New file
                updated_file = {**file_info, "added_on": timestamp, "last_modified": timestamp}
            new_files.append(updated_file)

        # Update metadata
        current_metadata["current_state"] = {
            "last_updated": datetime.now().isoformat(),
            "source_timestamp": timestamp,
            "total_files": len(new_files),
            "total_size": sum(f["size"] for f in new_files),
        }
        current_metadata["files"] = new_files

        with open(self.metadata_file, "w") as f:
            json.dump(current_metadata, f, indent=2)

    def _create_delta_log(self, initial_entry: dict):
        """Create new delta log with initial entry."""
        delta_log = {"deltas": [initial_entry]}

        with open(self.delta_log_file, "w") as f:
            json.dump(delta_log, f, indent=2)

    def _append_delta_log(self, delta_entry: dict):
        """Append entry to delta log."""
        if not self.delta_log_file.exists():
            self._create_delta_log(delta_entry)
            return

        try:
            with open(self.delta_log_file) as f:
                delta_log = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load delta log: {e}")
            self._create_delta_log(delta_entry)
            return

        delta_log["deltas"].append(delta_entry)

        with open(self.delta_log_file, "w") as f:
            json.dump(delta_log, f, indent=2)

    def get_files_for_upload(self, incremental: bool = True) -> dict:
        """
        Get files that need to be uploaded, updated, or deleted.

        Args:
            incremental: If True, only return changed files. If False, return all files.

        Returns:
            Dictionary with files to upload, file_id_map from previous upload, and summary
        """
        if not self.current_dir.exists():
            return {"error": "Current directory does not exist"}

        metadata = self._load_metadata()
        if not metadata:
            return {"error": "Failed to load metadata"}

        current_files = {f["url"]: f for f in metadata.get("files", [])}

        if not incremental:
            # Full upload - return all current files
            return {
                "upload": list(current_files.values()),
                "delete": [],
                "previous_file_map": {},
                "summary": f"Full upload: {len(current_files)} files",
            }

        # Incremental upload - compare with last upload
        upload_status_file = self.current_dir / "upload_status.json"

        if not upload_status_file.exists():
            # First upload - all files are new
            return {
                "upload": list(current_files.values()),
                "delete": [],
                "previous_file_map": {},
                "summary": f"Initial upload: {len(current_files)} files",
            }

        try:
            with open(upload_status_file) as f:
                upload_status = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load upload status: {e}")
            # If can't read upload status, do full upload
            return {
                "upload": list(current_files.values()),
                "delete": [],
                "previous_file_map": {},
                "summary": f"Full upload (status corrupt): {len(current_files)} files",
            }

        # Build file_id_map and checksum map from previous upload
        previous_file_map = {}  # URL -> file_id
        last_uploaded = {}  # URL -> checksum

        for file_info in upload_status.get("files", []):
            url = file_info["url"]
            last_uploaded[url] = file_info["checksum"]
            if "file_id" in file_info:
                previous_file_map[url] = file_info["file_id"]

        # Find files to upload (new or modified)
        to_upload = []
        for url, file_info in current_files.items():
            if url not in last_uploaded:
                # New file
                to_upload.append(file_info)
            elif file_info["checksum"] != last_uploaded[url]:
                # Modified file
                to_upload.append(file_info)

        # Find files to delete (in last upload but not in current)
        current_urls = set(current_files.keys())
        last_urls = set(last_uploaded.keys())
        to_delete_urls = list(last_urls - current_urls)

        # Get knowledge_id from previous upload
        knowledge_id = upload_status.get("knowledge_id")

        return {
            "upload": to_upload,
            "delete": to_delete_urls,
            "previous_file_map": previous_file_map,
            "knowledge_id": knowledge_id,
            "summary": f"Incremental: {len(to_upload)} to upload, {len(to_delete_urls)} to delete",
        }

    def save_upload_status(self, upload_result: dict):
        """
        Save upload status after successful upload.

        Args:
            upload_result: Result from upload operation including file_id_map
        """
        if not self.current_dir.exists():
            logger.error("Cannot save upload status: current directory doesn't exist")
            return

        metadata = self._load_metadata()
        if not metadata:
            logger.error("Cannot save upload status: failed to load metadata")
            return

        # Get file_id_map from result (URL -> file_id mapping)
        file_id_map = upload_result.get("file_id_map", {})

        # BUGFIX: Load previous upload_status to check for rebuild metadata and checksums
        previous_upload_status = self.get_upload_status()
        was_rebuild = previous_upload_status and previous_upload_status.get(
            "rebuilt_from_remote", False
        )

        # BUGFIX #2: Check if CURRENT upload is a rebuild (not previous)
        # This is critical for the FIRST save after rebuild
        is_current_rebuild = upload_result.get("rebuilt_from_remote", False)

        # Enhance file metadata with file_ids
        files_with_ids = []
        for file_info in metadata.get("files", []):
            url = file_info["url"]
            file_entry = file_info.copy()

            # Add file_id if available
            if url in file_id_map:
                file_entry["file_id"] = file_id_map[url]

            # BUGFIX #2: If THIS is a current rebuild, DO NOT overwrite the checksums!
            # The checksums in upload_result may belong to uploaded remote hashes.
            if is_current_rebuild:
                # Check if this file was in the upload_result files with checksum
                for result_file in upload_result.get("files", []):
                    if result_file.get("url") == url and "checksum" in result_file:
                        # Use checksum from rebuilt state (may be remote hash)
                        file_entry["checksum"] = result_file["checksum"]
                        logger.debug(f"Preserving rebuilt checksum for {file_info.get('filename')}")
                        break

            # BUGFIX (continued): If previous upload was a rebuild and no remote checksum for this file,
            # fallback to preserving the remote hash from the previous
            # rebuild.
            if was_rebuild and previous_upload_status:
                for prev_file in previous_upload_status.get("files", []):
                    if prev_file["url"] == url and "checksum" in prev_file:
                        if url not in file_id_map:
                            file_entry["checksum"] = prev_file["checksum"]
                            logger.debug(
                                f"Falling back to previous checksum for {file_info.get('filename')}"
                            )
                        break

            files_with_ids.append(file_entry)

        upload_status = {
            "last_upload": datetime.now().isoformat(),
            "knowledge_id": upload_result.get("knowledge_id"),
            "knowledge_name": upload_result.get("knowledge_name"),
            "site_name": self.site_name,
            "site_folder": upload_result.get("site_folder", f"{self.site_name}/"),
            "files_uploaded": upload_result.get("files_uploaded", 0),
            "files_updated": upload_result.get("files_updated", 0),
            "files_deleted": upload_result.get("files_deleted", 0),
            "source_timestamp": metadata["current_state"]["source_timestamp"],
            "files": files_with_ids,
        }

        # BUGFIX #1: Preserve rebuild metadata from upload_result
        if upload_result.get("rebuilt_from_remote"):
            upload_status["rebuilt_from_remote"] = upload_result["rebuilt_from_remote"]
            upload_status["rebuild_confidence"] = upload_result.get("rebuild_confidence")
            upload_status["rebuild_match_rate"] = upload_result.get("rebuild_match_rate")
            logger.info(
                f"Preserved rebuild metadata: confidence={upload_status['rebuild_confidence']}, "
                f"match_rate={upload_status['rebuild_match_rate']}"
            )

        upload_status_file = self.current_dir / "upload_status.json"

        try:
            with open(upload_status_file, "w") as f:
                json.dump(upload_status, f, indent=2)
            logger.info(
                f"Saved upload status with {len(files_with_ids)} file IDs to {upload_status_file}"
            )
        except Exception as e:
            logger.error(f"Failed to save upload status: {e}")

    def get_upload_status(self) -> dict | None:
        """
        Get last upload status.

        Returns:
            Upload status dictionary or None if never uploaded
        """
        upload_status_file = self.current_dir / "upload_status.json"

        if not upload_status_file.exists():
            return None

        try:
            with open(upload_status_file) as f:
                return cast(dict | None, json.load(f))
        except Exception as e:
            logger.error(f"Failed to load upload status: {e}")
            return None
