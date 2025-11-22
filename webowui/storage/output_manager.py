"""
Output manager for saving scraped content.
"""

import hashlib
import json
import logging
from datetime import datetime
from pathlib import Path

from slugify import slugify  # type: ignore

from ..config import SiteConfig
from ..scraper.crawler import CrawlResult
from .current_directory_manager import CurrentDirectoryManager
from .metadata_tracker import MetadataTracker

logger = logging.getLogger(__name__)


class OutputManager:
    """Manages output directory structure and file saving."""

    def __init__(self, site_config: SiteConfig, base_output_dir: Path):
        self.config = site_config
        self.base_output_dir = base_output_dir

        # Create timestamped output directory
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.output_dir = base_output_dir / site_config.name / timestamp
        self.content_dir = self.output_dir / "content"

        # Create directories
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.content_dir.mkdir(exist_ok=True)

        self.files_saved: list[dict] = []
        self.timestamp = timestamp

    def save_results(self, results: list[CrawlResult]) -> dict:
        """Save all crawl results to files."""
        logger.info(f"Saving {len(results)} pages to {self.output_dir}")

        for result in results:
            if result.success and result.markdown:
                file_info = self._save_page(result)
                if file_info:
                    self.files_saved.append(file_info)

        # Save metadata
        metadata = self._create_metadata(results)
        self._save_metadata(metadata)

        # Save report
        report = self._create_report(results)
        self._save_report(report)

        logger.info(f"Saved {len(self.files_saved)} files to {self.content_dir}")

        save_info = {
            "output_dir": str(self.output_dir),
            "content_dir": str(self.content_dir),
            "files_saved": len(self.files_saved),
            "timestamp": self.timestamp,
        }

        # NEW: Auto-update current directory
        try:
            current_manager = CurrentDirectoryManager(self.base_output_dir, self.config.name)
            tracker = MetadataTracker(self.base_output_dir, self.config.name)
            update_result = current_manager.update_from_scrape(self.timestamp, tracker)
            save_info["current_updated"] = update_result
            logger.info(f"Updated current/ directory: {update_result.get('summary', 'Done')}")
        except Exception as e:
            logger.error(f"Failed to update current directory: {e}")
            save_info["current_updated"] = {"error": str(e)}

        return save_info

    def _save_page(self, result: CrawlResult) -> dict | None:
        """Save a single page as markdown file."""
        try:
            # Create filename from URL
            filename = self._url_to_filename(result.url)
            filepath = self.content_dir / filename

            # Ensure parent directory exists
            filepath.parent.mkdir(parents=True, exist_ok=True)

            # NEW: Get cleaning profile and apply
            from ..scraper.cleaning_profiles import CleaningProfileRegistry

            try:
                profile = CleaningProfileRegistry.get_profile(
                    self.config.cleaning_profile_name, self.config.cleaning_profile_config
                )

                cleaned_markdown = profile.clean(
                    result.markdown, metadata={"url": result.url, "site_config": self.config}
                )

                logger.debug(f"Applied {self.config.cleaning_profile_name} profile to {result.url}")
            except Exception as e:
                logger.error(
                    f"Failed to apply cleaning profile '{self.config.cleaning_profile_name}': {e}"
                )
                logger.warning(f"Using raw content for {result.url}")
                cleaned_markdown = result.markdown

            # Add frontmatter to cleaned markdown
            content = self._add_frontmatter(result, cleaned_markdown)

            # Write file
            filepath.write_text(content, encoding="utf-8")

            # Calculate checksum (using SHA-256 instead of deprecated MD5)
            checksum = hashlib.sha256(content.encode()).hexdigest()

            return {
                "url": result.url,
                "filepath": str(filepath.relative_to(self.output_dir)),
                "filename": filename,
                "size": len(content),
                "checksum": checksum,
                "timestamp": result.timestamp.isoformat(),
                "cleaned": True,  # Mark as cleaned for tracking
                "cleaning_profile": self.config.cleaning_profile_name,  # NEW: Track which profile was used
            }

        except Exception as e:
            logger.error(f"Failed to save {result.url}: {e}")
            return None

    def _url_to_filename(self, url: str) -> str:
        """Convert URL to safe filename."""
        # Extract path from URL
        from urllib.parse import unquote, urlparse

        parsed = urlparse(url)
        path = unquote(parsed.path)

        # Remove leading/trailing slashes
        path = path.strip("/")

        # Handle root/index pages
        if not path or path == "index":
            path = "index"

        # Replace slashes with dashes for directory structure
        # Maintain directory structure from URL paths
        parts = [slugify(p) for p in path.split("/") if p]

        if not parts:
            return "index.md"

        # Last part becomes filename
        filename = parts[-1] if parts else "index"

        # Create directory structure if multiple parts
        if len(parts) > 1:
            dir_path = "/".join(parts[:-1])
            return f"{dir_path}/{filename}.md"

        return f"{filename}.md"

    def _add_frontmatter(self, result: CrawlResult, markdown: str) -> str:
        """Add YAML frontmatter to markdown."""
        frontmatter = f"""---
url: {result.url}
site: {self.config.display_name}
cleaned: true
---

"""
        return frontmatter + markdown

    def _create_metadata(self, results: list[CrawlResult]) -> dict:
        """Create metadata for the scrape."""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        return {
            "site": {
                "name": self.config.name,
                "display_name": self.config.display_name,
                "base_url": self.config.base_url,
            },
            "scrape": {
                "timestamp": self.timestamp,
                "start_time": min(r.timestamp for r in results).isoformat() if results else None,
                "end_time": max(r.timestamp for r in results).isoformat() if results else None,
                "strategy": self.config.crawl_strategy,
                "max_depth": self.config.max_depth,
            },
            "statistics": {
                "total_pages": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "total_content_size": sum(len(r.markdown) for r in successful),
            },
            "files": self.files_saved,
            "failed_urls": [{"url": r.url, "error": r.error} for r in failed],
        }

    def _save_metadata(self, metadata: dict):
        """Save metadata as JSON."""
        filepath = self.output_dir / "metadata.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved metadata to {filepath}")

    def _create_report(self, results: list[CrawlResult]) -> dict:
        """Create human-readable report."""
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]

        return {
            "summary": {
                "site": self.config.display_name,
                "timestamp": self.timestamp,
                "total_pages": len(results),
                "successful": len(successful),
                "failed": len(failed),
                "success_rate": (
                    f"{(len(successful) / len(results) * 100):.1f}%" if results else "0%"
                ),
            },
            "successful_urls": [r.url for r in successful],
            "failed_urls": [{"url": r.url, "error": r.error} for r in failed],
        }

    def _save_report(self, report: dict):
        """Save report as JSON."""
        filepath = self.output_dir / "scrape_report.json"
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        logger.info(f"Saved report to {filepath}")

    def get_output_info(self) -> dict:
        """Get information about saved output."""
        return {
            "output_dir": str(self.output_dir),
            "content_dir": str(self.content_dir),
            "files_saved": len(self.files_saved),
            "timestamp": self.timestamp,
        }
