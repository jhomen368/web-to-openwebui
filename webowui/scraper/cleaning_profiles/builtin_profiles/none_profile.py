"""
Pass-through cleaning profile - no cleaning applied.
"""

from typing import Any

from webowui.scraper.cleaning_profiles.base import BaseCleaningProfile


class NoneProfile(BaseCleaningProfile):
    """Pass-through profile - no cleaning applied (default)."""

    def clean(self, content: str, metadata: dict | None = None) -> str:
        """
        Return content unchanged.

        Args:
            content: Raw scraped content
            metadata: Optional metadata (unused)

        Returns:
            Original content without any modifications
        """
        return content

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """
        Return empty schema - no configuration needed.

        Returns:
            Empty schema dictionary
        """
        return {}
