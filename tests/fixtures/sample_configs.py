"""
Test configuration data fixtures.

Provides predefined sample configurations for different site types
and scenarios to use in unit and integration tests.
"""

from typing import Any

# ============================================================================
# Site Configuration Samples
# ============================================================================

SIMPLE_SITE_CONFIG: dict[str, Any] = {
    "name": "simple",
    "display_name": "Simple Test Site",
    "base_url": "https://simple.example.com",
    "start_urls": ["https://simple.example.com"],
    "crawling": {
        "strategy": "recursive",
        "max_depth": 1,
        "requests_per_second": 2,
        "delay_between_requests": 0.5,
        "follow_patterns": ["^https://simple\\.example\\.com/.*"],
        "exclude_patterns": [],
    },
    "cleaning": {
        "profile": "none",
        "config": {},
    },
}


MEDIAWIKI_SITE_CONFIG: dict[str, Any] = {
    "name": "mediawiki",
    "display_name": "MediaWiki Test",
    "base_url": "https://wiki.example.com",
    "start_urls": ["https://wiki.example.com/wiki/Main_Page"],
    "crawling": {
        "strategy": "recursive",
        "max_depth": 2,
        "requests_per_second": 1,
        "delay_between_requests": 1.0,
        "follow_patterns": ["^https://wiki\\.example\\.com/wiki/[^:]+$"],
        "exclude_patterns": [
            ".*Special:.*",
            ".*User:.*",
            ".*Talk:.*",
            ".*File:.*",
            ".*Category:.*",
            ".*Template:.*",
        ],
    },
    "cleaning": {
        "profile": "mediawiki",
        "config": {
            "filter_dead_links": False,
            "remove_citations": True,
            "remove_categories": True,
            "remove_infoboxes": True,
            "remove_external_links": True,
        },
    },
}


FANDOM_SITE_CONFIG: dict[str, Any] = {
    "name": "fandom",
    "display_name": "Fandom Wiki Test",
    "base_url": "https://test.fandom.com",
    "start_urls": ["https://test.fandom.com/wiki/Main_Page"],
    "crawling": {
        "strategy": "recursive",
        "max_depth": 1,
        "requests_per_second": 1,
        "delay_between_requests": 1.0,
        "follow_patterns": ["^https://test\\.fandom\\.com/wiki/.*"],
        "exclude_patterns": [
            ".*Special:.*",
            ".*User:.*",
            ".*Talk:.*",
            ".*File:.*",
            ".*Category:.*",
        ],
    },
    "cleaning": {
        "profile": "fandomwiki",
        "config": {
            "remove_fandom_ads": True,
            "remove_fandom_promotions": True,
            "remove_community_content": True,
        },
    },
}


SELECTIVE_CRAWL_CONFIG: dict[str, Any] = {
    "name": "selective",
    "display_name": "Selective Crawl Test",
    "base_url": "https://selective.example.com",
    "start_urls": [
        "https://selective.example.com/docs/api",
        "https://selective.example.com/docs/guide",
    ],
    "crawling": {
        "strategy": "selective",
        "max_depth": 2,
        "requests_per_second": 2,
        "delay_between_requests": 0.5,
        "follow_patterns": [
            "^https://selective\\.example\\.com/docs/.*",
        ],
        "exclude_patterns": [
            ".*changelog.*",
            ".*archive.*",
        ],
    },
    "cleaning": {
        "profile": "none",
        "config": {},
    },
}


WITH_RETENTION_CONFIG: dict[str, Any] = {
    "name": "with_retention",
    "display_name": "With Retention Test",
    "base_url": "https://retention.example.com",
    "start_urls": ["https://retention.example.com"],
    "crawling": {
        "strategy": "recursive",
        "max_depth": 1,
        "requests_per_second": 2,
        "delay_between_requests": 0.5,
    },
    "cleaning": {
        "profile": "none",
        "config": {},
    },
    "retention": {
        "enabled": True,
        "keep_backups": 3,
        "auto_cleanup": True,
    },
}


WITH_SCHEDULING_CONFIG: dict[str, Any] = {
    "name": "with_schedule",
    "display_name": "With Schedule Test",
    "base_url": "https://schedule.example.com",
    "start_urls": ["https://schedule.example.com"],
    "crawling": {
        "strategy": "recursive",
        "max_depth": 1,
        "requests_per_second": 2,
        "delay_between_requests": 0.5,
    },
    "schedule": {
        "enabled": True,
        "type": "cron",
        "cron": "0 2 * * *",
        "timezone": "America/Los_Angeles",
    },
}


WITH_OPENWEBUI_CONFIG: dict[str, Any] = {
    "name": "with_openwebui",
    "display_name": "With OpenWebUI Test",
    "base_url": "https://docs.example.com",
    "start_urls": ["https://docs.example.com"],
    "crawling": {
        "strategy": "recursive",
        "max_depth": 2,
        "requests_per_second": 2,
        "delay_between_requests": 0.5,
    },
    "openwebui": {
        "knowledge_id": "test-kb-123",
        "knowledge_name": "Test Knowledge",
        "preserve_deleted_files": False,
        "auto_rebuild_state": True,
    },
}


# ============================================================================
# App Configuration Samples
# ============================================================================

MINIMAL_APP_CONFIG: dict[str, Any] = {
    "openwebui_base_url": "http://localhost:8000",
    "openwebui_api_key": "test-key-123",
}


COMPLETE_APP_CONFIG: dict[str, Any] = {
    "openwebui_base_url": "https://openwebui.example.com",
    "openwebui_api_key": "sk-test-key-very-long-string",
    "log_level": "DEBUG",
    "default_rate_limit": 2,
    "default_delay": 0.5,
}


# ============================================================================
# Configuration Collections
# ============================================================================

ALL_SITE_CONFIGS = {
    "simple": SIMPLE_SITE_CONFIG,
    "mediawiki": MEDIAWIKI_SITE_CONFIG,
    "fandom": FANDOM_SITE_CONFIG,
    "selective": SELECTIVE_CRAWL_CONFIG,
    "retention": WITH_RETENTION_CONFIG,
    "schedule": WITH_SCHEDULING_CONFIG,
    "openwebui": WITH_OPENWEBUI_CONFIG,
}


def get_site_config(self, config_type: str) -> dict[str, Any]:
    """
    Get a predefined site configuration.

    Args:
        config_type: Type of config (simple, mediawiki, fandom, etc.)

    Returns:
        Dict: Configuration dictionary

    Raises:
        KeyError: If config_type not found
    """
    if config_type not in ALL_SITE_CONFIGS:
        raise KeyError(
            f"Unknown config type: {config_type}. "
            f"Available: {', '.join(ALL_SITE_CONFIGS.keys())}"
        )

    # Return copy to prevent test pollution
    import copy

    return copy.deepcopy(ALL_SITE_CONFIGS[config_type])


def get_site_config_with_override(
    self,
    config_type: str,
    overrides: dict[str, Any],
) -> dict[str, Any]:
    """
    Get a predefined site configuration with overrides.

    Args:
        config_type: Type of config (simple, mediawiki, fandom, etc.)
        overrides: Dictionary of values to override

    Returns:
        Dict: Configuration dictionary with overrides applied
    """
    config = get_site_config(self, config_type)

    def deep_update(d: dict, u: dict) -> dict:
        """Recursively update dictionary."""
        for k, v in u.items():
            if isinstance(v, dict):
                d[k] = deep_update(d.get(k, {}), v)
            else:
                d[k] = v
        return d

    return deep_update(config, overrides)
