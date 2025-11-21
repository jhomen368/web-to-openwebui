"""
Configuration loader for site configs and environment settings.
"""

import logging
import os
import shutil
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Setup logger
logger = logging.getLogger(__name__)


def ensure_example_configs(sites_dir: Path):
    """
    Copy example site configs from package to data directory on first run.

    This function copies template configuration files from the built-in examples
    directory to the user's sites configuration directory. Files are only copied
    if they don't already exist, preserving any user modifications.

    Args:
        sites_dir: Target directory for site configurations (data/config/sites/)
    """
    # Get examples directory from package (webowui/config/examples/)
    examples_dir = Path(__file__).parent / "config" / "examples"

    if not examples_dir.exists():
        logger.debug("No example configs found in package")
        return

    # Copy .yml.example files if they don't exist
    copied_count = 0
    for example_file in examples_dir.glob("*.yml.example"):
        target = sites_dir / example_file.name
        if not target.exists():
            logger.info(f"Copying example config: {example_file.name}")
            shutil.copy(example_file, target)
            copied_count += 1

    # Also copy README if present
    readme = examples_dir / "README.md"
    if readme.exists() and not (sites_dir / "README.md").exists():
        logger.info("Copying README.md to sites directory")
        shutil.copy(readme, sites_dir / "README.md")
        copied_count += 1

    if copied_count > 0:
        logger.info(f"Copied {copied_count} example file(s) to {sites_dir}")


class SiteConfig:
    """Configuration for a single site to scrape."""

    def __init__(self, config_dict: dict[str, Any], config_path: Path):
        self.config_path = config_path
        self._config = config_dict

        # Site info
        site_info = config_dict.get("site", {})
        self.name = site_info.get("name")
        self.display_name = site_info.get("display_name")
        self.base_url = site_info.get("base_url")
        self.start_urls = site_info.get("start_urls", [])

        # Crawling (NEW) - replaces "strategy"
        crawling = config_dict.get("crawling", {})
        self.crawl_strategy = crawling.get("strategy", "bfs")
        self.max_depth = crawling.get("max_depth", 3)
        self.max_pages = crawling.get("max_pages")
        self.use_streaming = crawling.get("streaming", False)

        # Filters (moved under crawling)
        filters = crawling.get("filters", {})
        self.follow_patterns = filters.get("follow_patterns", [])
        self.exclude_patterns = filters.get("exclude_patterns", [])
        self.exclude_domains = filters.get("exclude_domains", [])

        # Keywords for best_first
        self.crawl_keywords = crawling.get("keywords", [])
        self.crawl_keyword_weight = crawling.get("keyword_weight", 0.7)

        # Rate limiting
        rate_limit = crawling.get("rate_limit", {})
        self.requests_per_second = rate_limit.get("requests_per_second", 2)
        self.delay_between_requests = rate_limit.get("delay_between_requests", 0.5)
        self.max_retries = rate_limit.get("max_retries", 3)

        # ---------------------------------------------------------------------
        # PIPELINE STAGE 1: HTML Filtering
        # ---------------------------------------------------------------------
        html_filtering = config_dict.get("html_filtering", {})

        # Pruning filter (heuristic)
        pruning = html_filtering.get("pruning", {})
        self.pruning_enabled = pruning.get("enabled", False)
        self.pruning_threshold = pruning.get("threshold", 0.6)
        self.pruning_min_words = pruning.get("min_word_threshold", 50)

        # Basic HTML filtering (explicit)
        self.excluded_tags = html_filtering.get("excluded_tags", [])
        self.exclude_external_links = html_filtering.get("exclude_external_links", False)
        self.exclude_social_media = html_filtering.get("exclude_social_media", False)
        self.min_block_words = html_filtering.get("min_block_words", 10)

        # ---------------------------------------------------------------------
        # PIPELINE STAGE 2a: Markdown Conversion
        # ---------------------------------------------------------------------
        markdown_conversion = config_dict.get("markdown_conversion", {})
        self.content_selector = markdown_conversion.get("content_selector", "body")
        self.remove_selectors = markdown_conversion.get("remove_selectors", [])
        self.markdown_options = markdown_conversion.get("markdown_options", {})

        # ---------------------------------------------------------------------
        # PIPELINE STAGE 2b: Markdown Cleaning
        # ---------------------------------------------------------------------
        markdown_cleaning = config_dict.get("markdown_cleaning", {})
        self.cleaning_profile_name = markdown_cleaning.get("profile", "none")
        self.cleaning_profile_config = markdown_cleaning.get("config", {})

        # ---------------------------------------------------------------------
        # PIPELINE STAGE 3: Result Filtering
        # ---------------------------------------------------------------------
        result_filtering = config_dict.get("result_filtering", {})
        self.min_page_length = result_filtering.get("min_page_length", 100)
        self.max_page_length = result_filtering.get("max_page_length", 500000)
        self.allowed_content_types = result_filtering.get("allowed_content_types", ["text/html"])
        self.filter_dead_links = result_filtering.get("filter_dead_links", False)

        # Open Web UI
        openwebui = config_dict.get("openwebui", {})
        self.knowledge_id = openwebui.get("knowledge_id")  # Optional: specify existing knowledge ID
        self.knowledge_name = openwebui.get("knowledge_name", self.display_name)
        self.knowledge_description = openwebui.get("description", "")
        self.auto_upload = openwebui.get("auto_upload", False)
        self.batch_size = openwebui.get("batch_size", 10)
        self.preserve_deleted_files = openwebui.get(
            "preserve_deleted_files", False
        )  # Keep files when removed from scrape
        self.cleanup_untracked = openwebui.get("cleanup_untracked", False)

        # State reconstruction settings
        self.auto_rebuild_state = openwebui.get(
            "auto_rebuild_state", True
        )  # Auto-rebuild if upload_status.json missing
        self.rebuild_confidence_threshold = openwebui.get(
            "rebuild_confidence_threshold", "medium"
        )  # min confidence: high/medium/low

        # Retention
        retention = config_dict.get("retention", {})
        self.retention_enabled = retention.get("enabled", False)
        self.retention_keep_backups = retention.get("keep_backups", 2)
        self.retention_auto_cleanup = retention.get("auto_cleanup", True)

        # Schedule (NEW)
        schedule = config_dict.get("schedule", {})
        self.schedule_enabled = schedule.get(
            "enabled", True
        )  # Default: True for automated scraping
        self.schedule_type = schedule.get("type", "cron")  # "cron" or "interval"
        self.schedule_cron = schedule.get("cron", "0 2 * * *")  # 2 AM daily default
        self.schedule_interval = schedule.get("interval", {"hours": 6})  # 6 hours default
        self.schedule_timezone = schedule.get("timezone", "America/Los_Angeles")
        self.schedule_timeout_minutes = schedule.get("timeout_minutes", 60)

        # Schedule retry settings
        schedule_retry = schedule.get("retry", {})
        self.schedule_retry_enabled = schedule_retry.get("enabled", True)
        self.schedule_retry_max_attempts = schedule_retry.get("max_attempts", 3)
        self.schedule_retry_delay_minutes = schedule_retry.get("delay_minutes", 15)

        # Batch tracking if applicable
        self.current_batch_number = 0  # Default to 0 for fresh starts

    def validate(self) -> list[str]:
        """Validate configuration and return list of errors."""
        errors = []

        if not self.name:
            errors.append("Site name is required")
        if not self.base_url:
            errors.append("Base URL is required")
        if not self.start_urls:
            errors.append("At least one start URL is required")
        if self.crawl_strategy not in ["bfs", "dfs", "best_first"]:
            errors.append(f"Invalid crawl strategy: {self.crawl_strategy}")

        # Info about shared knowledge bases (now safe with folder isolation!)
        if self.knowledge_id:
            config_dir = self.config_path.parent
            sharing_sites = []

            for config_file in config_dir.glob("*.yaml"):
                if config_file == self.config_path:
                    continue

                try:
                    with open(config_file) as f:
                        import yaml

                        other_config = yaml.safe_load(f)

                    other_knowledge_id = other_config.get("openwebui", {}).get("knowledge_id")
                    other_site_name = other_config.get("site", {}).get("name")

                    if other_knowledge_id == self.knowledge_id and other_site_name:
                        sharing_sites.append(other_site_name)
                except Exception:  # nosec
                    continue

            if sharing_sites:
                errors.append(
                    f"📁 SHARED KNOWLEDGE INFO:\n"
                    f"   Knowledge base '{self.knowledge_id}' is shared with: {', '.join(sharing_sites)}\n"
                    f"   Your files will be organized in: {self.name}/\n"
                    + "".join([f"   Their files will be in: {s}/\n" for s in sharing_sites])
                    + "   ✅ Folder isolation ensures safe incremental updates for each site."
                )

        return errors

    def to_dict(self) -> dict[str, Any]:
        """Return configuration as dictionary."""
        return self._config


class AppConfig:
    """Application-wide configuration."""

    def __init__(self):
        # Paths - single mount point for all persistent data
        self.base_dir = Path(__file__).parent.parent
        self.data_dir = self.base_dir / "data"
        self.config_dir = self.data_dir / "config"
        self.sites_dir = self.config_dir / "sites"
        self.outputs_dir = self.data_dir / "outputs"
        self.logs_dir = self.data_dir / "logs"

        # Create data directory structure if it doesn't exist
        self.data_dir.mkdir(exist_ok=True)
        self.config_dir.mkdir(exist_ok=True)
        self.sites_dir.mkdir(exist_ok=True)
        self.outputs_dir.mkdir(exist_ok=True)
        self.logs_dir.mkdir(exist_ok=True)

        # Environment variables
        self.openwebui_base_url = os.getenv("OPENWEBUI_BASE_URL", "")
        self.openwebui_api_key = os.getenv("OPENWEBUI_API_KEY", "")
        self.log_level = os.getenv("LOG_LEVEL", "INFO")
        self.max_concurrent_requests = int(os.getenv("MAX_CONCURRENT_REQUESTS", "5"))
        self.default_rate_limit = float(os.getenv("DEFAULT_RATE_LIMIT", "2"))
        self.default_delay = float(os.getenv("DEFAULT_DELAY", "0.5"))

        # Ensure example configs
        ensure_example_configs(self.sites_dir)

    def load_site_config(self, site_name: str) -> SiteConfig:
        """Load configuration for a specific site."""
        config_path = self.sites_dir / f"{site_name}.yaml"

        if not config_path.exists():
            raise FileNotFoundError(f"Site configuration not found: {config_path}")

        with open(config_path) as f:
            config_dict = yaml.safe_load(f)

        return SiteConfig(config_dict, config_path)

    def list_sites(self) -> list[str]:
        """List all available site configurations."""
        if not self.sites_dir.exists():
            return []

        return [f.stem for f in self.sites_dir.glob("*.yaml")]

    def validate_openwebui_config(self) -> list[str]:
        """Validate Open Web UI configuration."""
        errors = []

        if not self.openwebui_base_url:
            errors.append("OPENWEBUI_BASE_URL not set in .env")
        if not self.openwebui_api_key:
            errors.append("OPENWEBUI_API_KEY not set in .env")

        return errors


# Global config instance
app_config = AppConfig()
