"""
Simple retention manager for scrape directories.
Implements count-based retention: keep last N timestamped backups, current/ always kept.
"""

import json
import logging
import shutil
from pathlib import Path
from typing import cast

logger = logging.getLogger(__name__)


class RetentionManager:
    """
    Simple retention manager - keep last N timestamped backups.

    The current/ directory is ALWAYS kept (it's the active state, not a backup).
    keep_backups controls how many timestamped backup directories to preserve.
    """

    def __init__(self, site_dir: Path, keep_backups: int = 2):
        """
        Initialize retention manager for a site.

        Args:
            site_dir: Path to site's output directory
            keep_backups: Number of timestamped backup dirs to keep (default: 2)
                         Valid range: 0+ (0 = delete all backups, keep only current/)
        """
        self.site_dir = site_dir
        self.keep_backups = max(0, keep_backups)  # Allow 0 or more
        self.current_dir = site_dir / "current"

    def get_scrape_directories(self) -> list[Path]:
        """
        Get all timestamped scrape directories (excluding current/).

        Returns:
            List of scrape directory paths, sorted by timestamp (newest first)
        """
        if not self.site_dir.exists():
            return []

        scrapes = []
        for item in self.site_dir.iterdir():
            if item.is_dir() and item.name != "current" and self._is_timestamp_dir(item.name):
                scrapes.append(item)

        # Sort by name (timestamp format YYYY-MM-DD_HH-MM-SS sorts correctly)
        scrapes.sort(reverse=True)
        return scrapes

    def _is_timestamp_dir(self, name: str) -> bool:
        """Check if directory name looks like a timestamp."""
        # Format: YYYY-MM-DD_HH-MM-SS
        parts = name.split("_")
        if len(parts) != 2:
            return False
        date_part = parts[0].split("-")
        time_part = parts[1].split("-")
        return len(date_part) == 3 and len(time_part) == 3

    def get_current_source(self) -> str | None:
        """
        Get timestamp that current/ was built from.

        Returns:
            Source timestamp or None if current/ doesn't exist
        """
        if not self.current_dir.exists():
            return None

        metadata_file = self.current_dir / "metadata.json"
        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
            return cast(str | None, metadata.get("current_state", {}).get("source_timestamp"))
        except Exception as e:
            logger.error(f"Failed to read current/ metadata: {e}")
            return None

    def apply_retention(self, dry_run: bool = False) -> dict:
        """
        Apply retention policy - keep last N timestamped backups, delete rest.
        current/ is always kept regardless of keep_backups setting.

        Args:
            dry_run: If True, only report what would be deleted

        Returns:
            Summary of retention action with keys:
            - action: 'none', 'dry_run', or 'cleaned'
            - kept: number of scrapes kept
            - kept_timestamps: list of kept timestamps
            - deleted: number of scrapes deleted
            - deleted_timestamps: list of deleted timestamps
            - current_source: source timestamp of current/
            - summary: human-readable summary
        """
        # Get all timestamped directories
        scrapes = self.get_scrape_directories()

        if len(scrapes) <= self.keep_backups:
            return {
                "action": "none",
                "reason": f"Only {len(scrapes)} backups, keeping all",
                "kept": len(scrapes),
                "kept_timestamps": [d.name for d in scrapes],
                "deleted": 0,
                "deleted_timestamps": [],
                "current_source": self.get_current_source(),
                "summary": f"No cleanup needed - only {len(scrapes)} backups exist",
            }

        # Identify current/ source for protection
        current_source = self.get_current_source()
        current_source_dir = None
        if current_source:
            current_source_dir = self.site_dir / current_source

        # Determine which to keep/delete
        to_keep = scrapes[: self.keep_backups]
        to_delete = scrapes[self.keep_backups :]

        # Protection rule: ensure current/ source is kept (if within policy)
        if current_source_dir and current_source_dir in to_delete:
            logger.info(f"Protecting current/ source: {current_source}")
            to_delete.remove(current_source_dir)

            # Remove oldest kept item to maintain count (unless it's also the source)
            if len(to_keep) >= self.keep_backups and self.keep_backups > 0:
                oldest_kept = to_keep[-1]
                if oldest_kept != current_source_dir:
                    to_keep.remove(oldest_kept)
                    to_delete.append(oldest_kept)

            to_keep.append(current_source_dir)
            # Re-sort to_keep
            to_keep.sort(reverse=True)

        # Delete marked directories
        deleted = []
        for scrape_dir in to_delete:
            if not dry_run:
                try:
                    shutil.rmtree(scrape_dir)
                    logger.info(f"Deleted backup: {scrape_dir.name}")
                except Exception as e:
                    logger.error(f"Failed to delete {scrape_dir.name}: {e}")
                    continue
            deleted.append(scrape_dir.name)

        return {
            "action": "dry_run" if dry_run else "cleaned",
            "kept": len(to_keep),
            "kept_timestamps": [d.name for d in to_keep],
            "deleted": len(deleted),
            "deleted_timestamps": deleted,
            "current_source": current_source,
            "summary": (
                f"Would delete {len(deleted)} old backups"
                if dry_run
                else f"Kept {len(to_keep)} backups, deleted {len(deleted)}"
            ),
        }

    def get_retention_status(self) -> dict:
        """
        Get current retention status and recommendations.

        Returns:
            Status dictionary with keys:
            - total_backups: number of timestamped backup directories
            - keep_backups: configured keep count
            - current_source: source timestamp of current/
            - total_size_mb: total size of all backups in MB
            - will_delete: number of backups that would be deleted
            - status: 'clean' or 'needs_cleanup'
            - recommendation: human-readable recommendation
        """
        scrapes = self.get_scrape_directories()
        current_source = self.get_current_source()

        # Calculate total size
        total_size = 0
        for scrape_dir in scrapes:
            try:
                total_size += sum(f.stat().st_size for f in scrape_dir.rglob("*") if f.is_file())
            except Exception as e:
                logger.warning(f"Failed to calculate size for {scrape_dir.name}: {e}")

        # Calculate what would be deleted
        excess = max(0, len(scrapes) - self.keep_backups)

        return {
            "total_backups": len(scrapes),
            "keep_backups": self.keep_backups,
            "current_source": current_source,
            "total_size_mb": total_size / (1024 * 1024),
            "will_delete": excess,
            "status": "clean" if excess == 0 else "needs_cleanup",
            "recommendation": (
                "No cleanup needed"
                if excess == 0
                else f"Run cleanup to remove {excess} old backups"
            ),
        }
