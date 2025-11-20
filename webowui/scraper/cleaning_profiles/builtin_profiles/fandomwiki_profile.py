"""
Cleaning profile for Fandom wiki sites.
Extends MediaWikiProfile with Fandom-specific cleaning.
"""

import re
from typing import Any

from webowui.scraper.cleaning_profiles.builtin_profiles.mediawiki_profile import MediaWikiProfile


class FandomWikiProfile(MediaWikiProfile):
    """
    Cleaning profile for Fandom wiki sites (fandom.com).

    Extends MediaWikiProfile with Fandom-specific cleaning for:
    - Advertising and promotional content
    - Community feed elements
    - Cross-wiki promotions
    - Fandom global navigation
    - Interactive widgets

    Fandom wikis use MediaWiki engine as their base, so all MediaWiki
    cleaning methods (8 methods) work automatically. This profile adds
    5 additional Fandom-specific cleaning methods on top.
    """

    def clean(self, content: str, metadata: dict | None = None) -> str:
        """
        Clean Fandom wiki content.

        Process:
        1. Apply MediaWiki cleaning (inherited - all 8 methods)
        2. Add Fandom-specific cleaning (5 new methods)

        Args:
            content: Raw scraped content
            metadata: Optional metadata (url, site_config, etc.)

        Returns:
            Cleaned content ready for embedding
        """
        # Get Fandom-specific configuration
        remove_fandom_ads = self.config.get("remove_fandom_ads", True)
        remove_fandom_promotions = self.config.get("remove_fandom_promotions", True)
        remove_community_content = self.config.get("remove_community_content", True)
        remove_related_wikis = self.config.get("remove_related_wikis", True)
        remove_fandom_footer = self.config.get("remove_fandom_footer", True)

        # Step 1: Apply parent MediaWiki cleaning (8 methods)
        content = super().clean(content, metadata)

        # Step 2: Fandom-specific cleaning (5 new methods)
        if remove_fandom_ads:
            content = self._remove_fandom_ads(content)

        if remove_fandom_promotions:
            content = self._remove_fandom_promotions(content)

        if remove_community_content:
            content = self._remove_community_content(content)

        if remove_related_wikis:
            content = self._remove_related_wikis(content)

        if remove_fandom_footer:
            content = self._remove_fandom_footer(content)

        # Final cleanup
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = content.strip()

        return content

    def _remove_fandom_ads(self, content: str) -> str:
        """
        Remove Fandom advertising and sponsored content.

        Removes "Advertisement" markers that appear throughout Fandom pages.
        These are ad placeholders with zero content value.

        Args:
            content: Content with potential ad markers

        Returns:
            Content with ad markers removed
        """
        ad_patterns = [
            r"^Advertisement\s*$",
            r"^\s*\[Ad\]\s*$",
        ]

        lines = content.split("\n")
        cleaned_lines = []

        for line in lines:
            should_skip = False
            for pattern in ad_patterns:
                if re.match(pattern, line, re.IGNORECASE):
                    should_skip = True
                    break

            if not should_skip:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _remove_fandom_promotions(self, content: str) -> str:
        """
        Remove Fandom cross-promotional content.

        Removes branding and cross-promotional sections like:
        - "FANDOM powered by Wikia"
        - "More Fandom" sections
        - "Fan Central" promotions
        - "Explore other fandoms" widgets

        Args:
            content: Content with potential promotions

        Returns:
            Content with promotions removed
        """
        promotion_patterns = [
            r"FANDOM powered by",
            r"More Fandom",
            r"Fan Central",
            r"Fandom Apps",
            r"Explore.*[Ff]andom",
            r"What is Fandom\?",
            r"Explore properties",
        ]

        lines = content.split("\n")
        cleaned_lines = []

        for line in lines:
            should_skip = False
            for pattern in promotion_patterns:
                if re.search(pattern, line):
                    should_skip = True
                    break

            if not should_skip:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _remove_community_content(self, content: str) -> str:
        """
        Remove community feed and user-generated content sections.

        Truncates content at sections like:
        - "## Community"
        - "## Discussions"
        - Discord widgets (200+ lines of user lists)
        - Community licensing text

        Args:
            content: Content with potential community sections

        Returns:
            Content with community sections removed
        """
        # Section headers to truncate at
        community_patterns = [
            r"^##\s+.*Discord\s*$",  # Discord widget sections
            r"^##\s+Community\s*$",
            r"^##\s+Discussions?\s*$",
            r"^##\s+Comments?\s*$",
            r"^##\s+Recent\s+Images\s*$",  # Recent activity widgets
            r"Community content is available",
            r"\*\*\d+\*\*\s+Users\s+Online",  # Discord user count
        ]

        lines = content.split("\n")

        for i, line in enumerate(lines):
            for pattern in community_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    # Truncate content here
                    return "\n".join(lines[:i]).rstrip()

        return content

    def _remove_related_wikis(self, content: str) -> str:
        """
        Remove related wikis and cross-wiki suggestions.

        Truncates content at sections promoting other Fandom wikis:
        - "Related wikis" sidebars
        - Cross-wiki article suggestions
        - Fandom discovery widgets

        Args:
            content: Content with potential related wiki sections

        Returns:
            Content with related wiki sections removed
        """
        related_patterns = [
            r"^##\s+Related\s+[Ww]ikis?\s*$",
            r"See also.*other wikis",
            r"More from Fandom",
        ]

        lines = content.split("\n")

        for i, line in enumerate(lines):
            for pattern in related_patterns:
                if re.search(pattern, line):
                    return "\n".join(lines[:i]).rstrip()

        return content

    def _remove_fandom_footer(self, content: str) -> str:
        """
        Remove Fandom global footer navigation.

        Truncates content at Fandom corporate footer with:
        - "Games • Movies • TV • Video" navigation
        - "Follow Us" social media links
        - "Contact • Explore • Advertise" footer
        - Fandom Inc. corporate information

        This removes 50+ lines of corporate navigation/promotion.

        Args:
            content: Content with potential Fandom footer

        Returns:
            Content with Fandom footer removed
        """
        footer_patterns = [
            r"###\s+Follow\s+Us",
            r"###\s+Overview",
            r"###\s+Advertise",
            r"Fandom.*Inc\.",
            r"View Mobile Site",
            r"is a Fandom\s+(Games|TV|Movies|Comics|Books)\s+Community",
        ]

        lines = content.split("\n")

        for i, line in enumerate(lines):
            for pattern in footer_patterns:
                if re.search(pattern, line):
                    return "\n".join(lines[:i]).rstrip()

        return content

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """
        Extend parent MediaWiki schema with Fandom-specific options.

        Returns all MediaWiki configuration options (8) plus
        Fandom-specific options (5) for a total of 13 configuration options.

        Returns:
            Schema dictionary with all MediaWiki + Fandom configuration options
        """
        # Get parent MediaWiki schema (8 options)
        schema = super().get_config_schema()

        # Add Fandom-specific properties (5 new options)
        schema["properties"].update(
            {
                "remove_fandom_ads": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove Fandom advertising and sponsored content",
                },
                "remove_fandom_promotions": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove Fandom cross-promotional content (More Fandom, Fan Central, etc.)",
                },
                "remove_community_content": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove community feed and user-generated content sections",
                },
                "remove_related_wikis": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove related wikis and cross-wiki suggestions",
                },
                "remove_fandom_footer": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove Fandom global footer navigation",
                },
            }
        )

        return schema
