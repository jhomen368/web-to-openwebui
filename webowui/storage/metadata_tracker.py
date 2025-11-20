"""
Metadata tracker for managing scrape history and incremental updates.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import cast

logger = logging.getLogger(__name__)


class MetadataTracker:
    """Track scrape metadata for incremental updates."""

    def __init__(self, base_output_dir: Path, site_name: str):
        self.base_output_dir = base_output_dir
        self.site_name = site_name
        self.site_dir = base_output_dir / site_name

    def get_all_scrapes(self) -> list[dict]:
        """Get list of all scrapes for this site."""
        if not self.site_dir.exists():
            return []

        scrapes = []
        for scrape_dir in sorted(self.site_dir.iterdir(), reverse=True):
            # Skip current directory - it has different metadata structure
            if scrape_dir.is_dir() and scrape_dir.name != "current":
                metadata_file = scrape_dir / "metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file) as f:
                            metadata = json.load(f)
                            metadata["scrape_dir"] = str(scrape_dir)
                            scrapes.append(metadata)
                    except Exception as e:
                        logger.warning(f"Failed to load metadata from {metadata_file}: {e}")

        return scrapes

    def get_latest_scrape(self) -> dict | None:
        """Get metadata from the most recent scrape."""
        scrapes = self.get_all_scrapes()
        return scrapes[0] if scrapes else None

    def get_scrape_by_timestamp(self, timestamp: str) -> dict | None:
        """Get metadata for a specific scrape by timestamp."""
        scrape_dir = self.site_dir / timestamp
        metadata_file = scrape_dir / "metadata.json"

        if not metadata_file.exists():
            return None

        try:
            with open(metadata_file) as f:
                metadata = json.load(f)
                metadata["scrape_dir"] = str(scrape_dir)
                return cast(dict | None, metadata)
        except Exception as e:
            logger.error(f"Failed to load metadata: {e}")
            return None

    def compare_scrapes(self, old_timestamp: str, new_timestamp: str) -> dict:
        """Compare two scrapes to identify changes."""
        old_scrape = self.get_scrape_by_timestamp(old_timestamp)
        new_scrape = self.get_scrape_by_timestamp(new_timestamp)

        if not old_scrape or not new_scrape:
            return {"error": "One or both scrapes not found"}

        old_files = {f["url"]: f for f in old_scrape.get("files", [])}
        new_files = {f["url"]: f for f in new_scrape.get("files", [])}

        old_urls = set(old_files.keys())
        new_urls = set(new_files.keys())

        # Identify changes
        added = new_urls - old_urls
        removed = old_urls - new_urls
        common = old_urls & new_urls

        # Check for modifications
        modified = set()
        for url in common:
            if old_files[url]["checksum"] != new_files[url]["checksum"]:
                modified.add(url)

        unchanged = common - modified

        return {
            "old_scrape": {
                "timestamp": old_timestamp,
                "total_files": len(old_files),
            },
            "new_scrape": {
                "timestamp": new_timestamp,
                "total_files": len(new_files),
            },
            "changes": {
                "added": list(added),
                "removed": list(removed),
                "modified": list(modified),
                "unchanged": list(unchanged),
            },
            "statistics": {
                "added_count": len(added),
                "removed_count": len(removed),
                "modified_count": len(modified),
                "unchanged_count": len(unchanged),
            },
        }

    def get_changed_files(self, base_timestamp: str | None = None) -> dict[str, set[str]]:
        """
        Get files that changed since a previous scrape.
        If base_timestamp is None, use the most recent scrape.
        """
        if base_timestamp:
            base_scrape = self.get_scrape_by_timestamp(base_timestamp)
        else:
            scrapes = self.get_all_scrapes()
            base_scrape = scrapes[1] if len(scrapes) > 1 else None

        latest_scrape = self.get_latest_scrape()

        if not latest_scrape:
            # Return empty sets instead of error string
            return {
                "added": set(),
                "modified": set(),
                "removed": set(),
            }

        if not base_scrape:
            # First scrape, everything is new
            return {
                "added": {f["url"] for f in latest_scrape.get("files", [])},
                "modified": set(),
                "removed": set(),
            }

        comparison = self.compare_scrapes(
            base_scrape["scrape"]["timestamp"], latest_scrape["scrape"]["timestamp"]
        )

        return {
            "added": set(comparison["changes"]["added"]),
            "modified": set(comparison["changes"]["modified"]),
            "removed": set(comparison["changes"]["removed"]),
        }

    def get_upload_status(self, timestamp: str) -> dict | None:
        """Get upload status for a scrape."""
        scrape = self.get_scrape_by_timestamp(timestamp)
        if not scrape:
            return None

        # Check for upload metadata file
        scrape_dir = Path(scrape["scrape_dir"])
        upload_file = scrape_dir / "upload_status.json"

        if not upload_file.exists():
            return {
                "uploaded": False,
                "timestamp": None,
                "files_uploaded": 0,
                "knowledge_id": None,
            }

        try:
            with open(upload_file) as f:
                return cast(dict | None, json.load(f))
        except Exception as e:
            logger.error(f"Failed to load upload status: {e}")
            return None

    def save_upload_status(self, timestamp: str, upload_info: dict):
        """Save upload status for a scrape."""
        scrape = self.get_scrape_by_timestamp(timestamp)
        if not scrape:
            logger.error(f"Scrape not found: {timestamp}")
            return

        scrape_dir = Path(scrape["scrape_dir"])
        upload_file = scrape_dir / "upload_status.json"

        upload_data = {"uploaded": True, "timestamp": datetime.now().isoformat(), **upload_info}

        try:
            with open(upload_file, "w") as f:
                json.dump(upload_data, f, indent=2)
            logger.info(f"Saved upload status to {upload_file}")
        except Exception as e:
            logger.error(f"Failed to save upload status: {e}")

    def cleanup_old_scrapes(self, keep_count: int = 5):
        """Remove old scrapes, keeping only the most recent ones."""
        scrapes = self.get_all_scrapes()

        if len(scrapes) <= keep_count:
            logger.info(f"Only {len(scrapes)} scrapes, nothing to clean up")
            return

        to_remove = scrapes[keep_count:]

        for scrape in to_remove:
            scrape_dir = Path(scrape["scrape_dir"])
            try:
                import shutil

                shutil.rmtree(scrape_dir)
                logger.info(f"Removed old scrape: {scrape_dir}")
            except Exception as e:
                logger.error(f"Failed to remove {scrape_dir}: {e}")
