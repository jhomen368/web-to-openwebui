"""
Cleaning profile for Maxroll.gg sites.
"""

import re
from typing import Any

from webowui.scraper.cleaning_profiles.base import BaseCleaningProfile


class MaxrollProfile(BaseCleaningProfile):
    """
    Cleaning profile for Maxroll.gg sites.

    Removes:
    - Global navigation sidebar
    - Top navigation bar
    - Footer
    - Social media links
    """

    def clean(self, content: str, metadata: dict | None = None) -> str:
        """
        Clean Maxroll content.

        Args:
            content: Raw scraped content
            metadata: Optional metadata

        Returns:
            Cleaned content
        """
        # Remove global navigation and sidebar (usually at the start)
        # Pattern: Starts with empty link to home, followed by list of games
        content = self._remove_global_nav(content)

        # Remove footer
        content = self._remove_footer(content)

        # Remove social media links
        content = self._remove_social_media(content)

        # Clean up excessive blank lines
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = content.strip()

        return content

    def _remove_global_nav(self, content: str) -> str:
        """Remove global navigation and sidebar."""
        lines = content.split("\n")
        cleaned_lines: list[str] = []

        # Heuristic: The global nav starts early and contains links to other games
        # We'll look for the start of the main content or specific nav markers

        # Common markers for Maxroll global nav
        nav_markers = [
            r"^\[\]\(https://maxroll\.gg/\)",
            r"^\s*\*\s*\[\]\(https://maxroll\.gg/",
            r"^Browse Games",
            r"^NEWS$",
            r"^ARPG$",
            r"^MMORPG$",
            r"^LOOTER SHOOTER$",
            r"^RPG$",
            r"^\[Store\]\(https://maxroll\.gg/shop\)",
            r"^\[Pinned Pages\]",
            r"^Create an account to be able to pin pages",
            r"^Powered By",
            r"^\[\]\(http://starforgesystems\.com",
            r"^\[Home\]\(https://maxroll\.gg/.*\)$",
            r"^\[Getting Started\]\(https://maxroll\.gg/.*\)$",
            r"^\[Build Guides\]\(https://maxroll\.gg/.*\)$",
            r"^\[Meta\]\(https://maxroll\.gg/.*\)$",
            r"^\[PoE2Planner\]\(https://maxroll\.gg/.*\)$",
            r"^\[Community Builds\]\(https://maxroll\.gg/.*\)$",
            r"^\[Team\]\(https://maxroll\.gg/.*\)$",
            r"^Resources$",
            r"^Tools$",
            # Match game list rows starting with image link
            r"^\[!\[",
            # Match game list rows starting with game name link
            r"^\[.*\]\(https://maxroll\.gg/.*\)$",
        ]

        # We want to skip everything until we hit the actual page content
        # The page content usually starts after the "Powered By" section or the breadcrumbs

        # Let's try to find the "Home" link for the specific game, e.g., [Home](https://maxroll.gg/poe2)
        # But that might be part of the nav too.

        # In the sample, the real content started around line 60 with "## Getting Started"
        # But that's specific to that page.

        # Strategy: Filter out known nav lines
        # Also filter out lines that are just links to other games or sections

        for line in lines:
            is_nav = False
            for marker in nav_markers:
                if re.search(marker, line):
                    # Special check for game links - only if they are in the nav section (top of file)
                    if marker == r"^\[.*\]\(https://maxroll\.gg/.*\)$":
                        if len(cleaned_lines) < 50:  # Only filter these at the top
                            is_nav = True
                    else:
                        is_nav = True
                    break

            if not is_nav:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _remove_footer(self, content: str) -> str:
        """Remove footer content."""
        lines = content.split("\n")

        # Footer usually starts with Terms of Service or Social Links
        footer_markers = [
            r"^Follow us on",
            r"^See more results",
            r"AdChoices",
            r"Do Not Sell My Personal Information",
            r"No part of this website or its content may be reproduced",
            r"\[Terms of Service\]",
            r"\[Privacy Policy\]",
            r"\[Accessibility\]",
            r"\[Refund Policy\]",
            r"\[Contact Us\]",
            r"\[Cookie Policy\]",
            r"© \d{4} Maxroll",
            r"Maxroll is a registered trademark",
            r"^\[\]\(https://twitter\.com/maxrollgg\)",
        ]

        # Find the start of the footer and truncate
        footer_start_index = -1
        for i, line in enumerate(lines):
            for marker in footer_markers:
                if re.search(marker, line):
                    footer_start_index = i
                    break
            if footer_start_index != -1:
                break

        if footer_start_index != -1:
            return "\n".join(lines[:footer_start_index])

        return "\n".join(lines)

    def _remove_social_media(self, content: str) -> str:
        """Remove social media links."""
        lines = content.split("\n")
        cleaned_lines: list[str] = []

        social_patterns = [
            r"twitter\.com",
            r"facebook\.com",
            r"discord\.gg",
            r"youtube\.com",
            r"twitch\.tv",
        ]

        for line in lines:
            is_social = False
            for pattern in social_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    is_social = True
                    break

            if not is_social:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "remove_nav": {"type": "boolean", "default": True},
                "remove_footer": {"type": "boolean", "default": True},
            },
        }
