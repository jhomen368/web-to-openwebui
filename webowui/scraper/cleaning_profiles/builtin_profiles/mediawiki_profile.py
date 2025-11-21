"""
Cleaning profile for MediaWiki-based sites.
"""

import re
from typing import Any

from webowui.scraper.cleaning_profiles.base import BaseCleaningProfile


class MediaWikiProfile(BaseCleaningProfile):
    """Cleaning profile for MediaWiki-based sites (Wikipedia, wiki.js, etc.)."""

    def clean(self, content: str, metadata: dict | None = None) -> str:
        """
        Clean MediaWiki content (Stage 2 of two-stage filtering).

        Stage 1 (crawl4ai): Generic HTML filtering via content_filtering config
        Stage 2 (this profile): MediaWiki-specific pattern removal

        Args:
            content: Markdown content (already filtered by crawl4ai if enabled)
            metadata: Optional metadata (url, site_config, etc.)

        Returns:
            Cleaned content ready for embedding
        """
        # Get configuration
        filter_dead_links = self.config.get("filter_dead_links", False)
        remove_citations = self.config.get("remove_citations", True)
        remove_categories = self.config.get("remove_categories", True)
        remove_infoboxes = self.config.get("remove_infoboxes", True)
        remove_external_links = self.config.get("remove_external_links", True)
        remove_table_of_contents = self.config.get("remove_table_of_contents", True)
        remove_version_history = self.config.get("remove_version_history", True)
        remove_wiki_meta = self.config.get("remove_wiki_meta", True)
        remove_navigation_boilerplate = self.config.get("remove_navigation_boilerplate", True)
        remove_template_links = self.config.get("remove_template_links", True)
        remove_media = self.config.get("remove_media", True)
        remove_references_section = self.config.get("remove_references_section", True)
        remove_header_navigation = self.config.get("remove_header_navigation", True)

        # Step 1: Remove wiki meta messages early (before main extraction)
        if remove_wiki_meta:
            content = self._remove_wiki_meta(content)

        # Step 2: Remove navigation boilerplate
        if remove_navigation_boilerplate:
            content = self._remove_navigation_boilerplate(content)

        # Step 3: Remove header navigation (Anonymous, Search, etc.)
        if remove_header_navigation:
            content = self._remove_header_navigation(content)

        # Step 4: Remove table of contents
        if remove_table_of_contents:
            content = self._remove_table_of_contents(content)

        # Step 5: Remove infoboxes early (before main content extraction)
        if remove_infoboxes:
            content = self._remove_infoboxes(content)

        # Step 6: Extract main content (existing logic with updated patterns)
        content = self._extract_main_content(content, remove_citations, remove_categories)

        # Step 7: Remove external links section
        if remove_external_links:
            content = self._remove_external_links_section(content)

        # Step 8: Remove version history
        if remove_version_history:
            content = self._remove_version_history(content)

        # Step 9: Remove template editing links
        if remove_template_links:
            content = self._remove_template_links(content)

        # Step 10: Remove media sections
        if remove_media:
            content = self._remove_media_sections(content)

        # Step 11: Remove references section
        if remove_references_section:
            content = self._remove_references_section(content)

        # Step 12: Filter dead links if requested (existing logic)
        if filter_dead_links:
            content = self._remove_dead_links(content)

        # Step 13: Clean up excessive blank lines (existing logic)
        content = re.sub(r"\n{3,}", "\n\n", content)
        content = content.strip()

        return content

    def _remove_media_sections(self, content: str) -> str:
        """
        Remove media sections (Gallery, Images, Videos).

        Args:
            content: Content with potential media sections

        Returns:
            Content with media sections removed
        """
        # Section headers to truncate at or remove
        # We truncate because these are usually at the bottom
        section_patterns = [
            r"^##\s+Media\s*$",
            r"^##\s+Gallery\s*$",
            r"^##\s+Images\s*$",
            r"^##\s+Videos\s*$",
        ]

        lines = content.split("\n")
        for i, line in enumerate(lines):
            for pattern in section_patterns:
                if re.match(pattern, line.strip()):
                    # Truncate content here
                    return "\n".join(lines[:i]).rstrip()

        return content

    def _remove_references_section(self, content: str) -> str:
        """
        Remove References/Notes sections.

        Args:
            content: Content with potential references section

        Returns:
            Content with references section removed
        """
        section_patterns = [
            r"^##\s+References\s*$",
            r"^##\s+Notes\s*$",
            r"^##\s+Footnotes\s*$",
        ]

        lines = content.split("\n")
        for i, line in enumerate(lines):
            for pattern in section_patterns:
                if re.match(pattern, line.strip()):
                    # Truncate content here
                    return "\n".join(lines[:i]).rstrip()

        return content

    def _remove_infoboxes(self, content: str) -> str:
        """
        Remove infobox metadata tables from top of content.

        Infoboxes are typically markdown tables at the start of articles
        containing structured metadata that's not useful for embeddings.

        Args:
            content: Content with potential infoboxes

        Returns:
            Content with infoboxes removed
        """
        lines = content.split("\n")
        cleaned_lines = []
        in_table = False
        table_start = -1
        lines_since_last_content = 0

        for i, line in enumerate(lines):
            # Detect table start (must be near top of document)
            if i < 50 and "|" in line and ("---" in line or line.strip().startswith("|")):
                if not in_table:
                    in_table = True
                    table_start = i
                    # Check if this looks like an infobox (has key-value pairs)
                    continue
            elif in_table:
                # Still in table
                if "|" in line:
                    continue
                else:
                    # Table ended - was it an infobox?
                    # Infoboxes are typically short (< 30 lines) and at document start
                    table_length = i - table_start
                    if table_length < 30 and table_start < 20:
                        # Likely an infobox, skip it (already not added to cleaned_lines)
                        pass
                    else:
                        # Not an infobox, add the table lines back
                        cleaned_lines.extend(lines[table_start:i])
                    in_table = False
                    table_start = -1

            # Add non-table lines
            if not in_table:
                cleaned_lines.append(line)
                if line.strip():
                    lines_since_last_content = 0
                else:
                    lines_since_last_content += 1

        return "\n".join(cleaned_lines)

    def _remove_external_links_section(self, content: str) -> str:
        """
        Remove "External Links" and "See also" sections from end of content.

        These sections contain links to external sites that are not useful
        for embedding-based retrieval.

        Args:
            content: Content with potential external links section

        Returns:
            Content with external links section removed
        """
        # Section headers to truncate at
        section_patterns = [
            r"^##\s+External\s+[Ll]inks?\s*$",
            r"^##\s+See\s+[Aa]lso\s*$",
            r"^##\s+Further\s+[Rr]eading\s*$",
            r"^##\s+External\s+[Rr]esources\s*$",
        ]

        lines = content.split("\n")

        for i, line in enumerate(lines):
            for pattern in section_patterns:
                if re.match(pattern, line.strip()):
                    # Truncate content here
                    return "\n".join(lines[:i]).rstrip()

        return content

    def _remove_header_navigation(self, content: str) -> str:
        """
        Remove top-of-page navigation elements (Anonymous, Search, etc.).

        Args:
            content: Content with potential header navigation

        Returns:
            Content with header navigation removed
        """
        lines = content.split("\n")
        cleaned_lines = []

        # Patterns to skip at the start of the file
        skip_patterns = [
            r"^##\s+Anonymous\s*$",
            r"^###\s+Not\s+logged\s+in\s*$",
            r"^###\s+Search\s*$",
            r"^###\s+Namespaces\s*$",
            r"^###\s+Page\s+actions\s*$",
            r"^###\s+More\s*$",
            r"^\[Create\s+account\]",
            r"^\[Log\s+in\]",
            r"^\[Read\]",
            r"^\[View\s+source\]",
            r"^\[History\]",
        ]

        # Also skip lines that are just a single link at the start (navigation menus)
        # e.g. [Armor](...)

        content_started = False

        for i, line in enumerate(lines):
            if content_started:
                cleaned_lines.append(line)
                continue

            # Check if line matches skip patterns
            should_skip = False
            for pattern in skip_patterns:
                if re.match(pattern, line.strip()):
                    should_skip = True
                    break

            if should_skip:
                continue

            # Check for navigation links (lines that are just a link)
            # But be careful not to skip the main title or intro text
            # Heuristic: If it's a link and we haven't seen a header or long text yet
            if re.match(r"^\[.*?\]\(.*?\)\s*$", line.strip()):
                # It's a single link. Is it navigation?
                # If it's followed by "Equipment ▼" or similar, it's nav.
                if "▼" in line or "Equipment" in line or "Items" in line or "Locales" in line:
                    continue
                # If it's just a link, it might be a breadcrumb or nav link
                # Let's skip it if we are still in the "header zone" (first 50 lines)
                if i < 50:
                    continue

            # If we reached here, it's likely content
            # But wait, frontmatter is handled separately.
            # If line is empty, skip
            if not line.strip():
                continue

            # If line is "---", it might be frontmatter or horizontal rule
            # We assume frontmatter is already handled or will be handled by _extract_main_content
            # But _extract_main_content runs AFTER this.
            # So we should preserve frontmatter.
            if line.strip() == "---":
                cleaned_lines.append(line)
                content_started = True  # Wait, if it's frontmatter start, we are in content?
                # Actually, let's just append it and let _extract_main_content handle it
                continue

            # If we found real content, stop skipping
            cleaned_lines.append(line)
            content_started = True

        return "\n".join(cleaned_lines)

    def _remove_table_of_contents(self, content: str) -> str:
        """
        Remove auto-generated table of contents sections.

        Pattern: "## Contents" followed by numbered lists of internal links.
        These are navigation elements, not main content.

        Args:
            content: Content with potential TOC

        Returns:
            Content with TOC removed
        """
        lines = content.split("\n")
        cleaned_lines = []
        in_toc = False

        for line in lines:
            # Detect TOC start
            if re.match(r"^##\s+Contents?\s*$", line.strip()):
                in_toc = True
                continue

            # If in TOC, skip numbered list items
            if in_toc:
                # TOC typically has numbered lists like "1. [Link](#anchor)"
                if re.match(r"^\s*\d+\.\s+\[.*?\]\(#.*?\)", line):
                    continue
                # End of TOC when we hit non-list content
                elif line.strip() and not line.strip().startswith("*"):
                    in_toc = False

            if not in_toc:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _remove_version_history(self, content: str) -> str:
        """
        Remove "Version history" sections from end of content.

        These contain changelogs that are not relevant to the main article content.

        Args:
            content: Content with potential version history

        Returns:
            Content with version history removed
        """
        # Truncate at version history section
        pattern = r"^##\s+Version\s+[Hh]istory\s*$"

        lines = content.split("\n")
        for i, line in enumerate(lines):
            if re.match(pattern, line.strip()):
                # Truncate content here
                return "\n".join(lines[:i]).rstrip()

        return content

    def _remove_wiki_meta(self, content: str) -> str:
        """
        Remove wiki meta messages and help banners.

        Patterns like "The wiki is currently a work in progress..."
        These are template boilerplate, not article content.

        Args:
            content: Content with potential meta messages

        Returns:
            Content with meta messages removed
        """
        # Common wiki meta message patterns
        patterns = [
            r".*[Ww]iki.*work in progress.*",
            r".*[Pp]lease.*contribute.*",
            r".*[Hh]elp.*expand this.*",
            r".*[Ss]tub.*article.*",
            r".*[Ii]ncomplete.*expand.*",
        ]

        lines = content.split("\n")
        cleaned_lines = []

        for line in lines:
            should_skip = False
            for pattern in patterns:
                if re.search(pattern, line):
                    should_skip = True
                    break

            if not should_skip:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _remove_navigation_boilerplate(self, content: str) -> str:
        """
        Remove MediaWiki navigation boilerplate.

        Patterns like "Jump to navigation", "Jump to search" are
        UI elements, not content.

        Args:
            content: Content with potential navigation boilerplate

        Returns:
            Content with navigation boilerplate removed
        """
        patterns = [
            r"Jump to navigation",
            r"Jump to search",
            r"Jump to:",
        ]

        lines = content.split("\n")
        cleaned_lines = []

        for line in lines:
            should_skip = False
            for pattern in patterns:
                if pattern in line:
                    should_skip = True
                    break

            if not should_skip:
                cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _remove_template_links(self, content: str) -> str:
        """
        Remove template editing links like [v], [t], [e].

        These are MediaWiki editing interface links, not article content.

        Args:
            content: Content with potential template links

        Returns:
            Content with template links removed
        """
        # Pattern: [v], [t], [e] links at end of lines or in isolation
        # Often appear as: "[v] • [t] • [e]" or "\n[v]\n"
        patterns = [
            r"\[\s*[vte]\s*\]",  # Individual [v], [t], or [e]
            r"\[\s*[vte]\s*\]\s*•\s*",  # With bullet separator
        ]

        for pattern in patterns:
            content = re.sub(pattern, "", content)

        return content

    def _extract_main_content(
        self, content: str, remove_citations: bool, remove_categories: bool
    ) -> str:
        """
        Extract only the main article content, removing navigation and footers.

        Focuses on MediaWiki-specific patterns. Generic HTML elements
        (nav, footer, ads) should be removed via content_filtering in config.

        Args:
            content: Full scraped content
            remove_citations: Whether to stop at citation markers
            remove_categories: Whether to stop at categories

        Returns:
            Main content only
        """
        lines = content.split("\n")

        # Step 1: Skip frontmatter (only at the very beginning)
        content_start = 0
        if len(lines) > 0 and lines[0].strip() == "---":
            for i in range(1, len(lines)):
                if lines[i].strip() == "---":
                    content_start = i + 1
                    break

        # Step 2: Build cleaned content line by line
        cleaned_lines = []

        for i in range(content_start, len(lines)):
            line = lines[i].strip()

            # MediaWiki-specific footer markers
            if remove_categories and line.startswith("## Categories"):
                break

            if remove_citations and (line.startswith("1. [↑]") or line.startswith("  1. [↑]")):
                break

            # Wiki-specific patterns
            skip_patterns = [
                r"From .* Wiki$",
                r"Retrieved from",
            ]

            if any(re.search(p, line) for p in skip_patterns):
                continue

            # Add line to content (preserve original formatting)
            cleaned_lines.append(lines[i])

        return "\n".join(cleaned_lines)

    def _remove_dead_links(self, text: str) -> str:
        """
        Remove markdown links to non-existent pages.
        Pattern: [text](url&redlink=1 "title (page does not exist)")

        Args:
            text: Content with potential dead links

        Returns:
            Content with dead links removed
        """
        # Match dead links
        pattern = r'\[[^\]]+\]\([^"]*&redlink=1[^"]*"[^"]*"\)'

        # Remove the links
        cleaned = re.sub(pattern, "", text)

        # Remove empty list items left behind
        cleaned = re.sub(r"^\s*\*\s*$", "", cleaned, flags=re.MULTILINE)

        # Remove lines that now only have whitespace
        lines = cleaned.split("\n")
        cleaned_lines = [line for line in lines if line.strip()]
        cleaned = "\n".join(cleaned_lines)

        return cleaned

    @classmethod
    def get_config_schema(cls) -> dict[str, Any]:
        """
        Return JSON schema for MediaWiki profile configuration.

        Returns:
            Schema dictionary with configuration options
        """
        return {
            "type": "object",
            "properties": {
                "filter_dead_links": {
                    "type": "boolean",
                    "default": False,
                    "description": "Remove links to pages that don't exist",
                },
                "remove_citations": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove citation markers and references",
                },
                "remove_categories": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove category listings",
                },
                "remove_infoboxes": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove infobox metadata tables",
                },
                "remove_external_links": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove 'External Links' and 'See also' sections",
                },
                "remove_table_of_contents": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove auto-generated table of contents",
                },
                "remove_version_history": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove version history and changelog sections",
                },
                "remove_wiki_meta": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove wiki meta messages and help banners",
                },
                "remove_navigation_boilerplate": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove 'Jump to navigation' and similar UI elements",
                },
                "remove_template_links": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove template editing links like [v], [t], [e]",
                },
                "remove_media": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove Media, Gallery, Images, and Videos sections",
                },
                "remove_references_section": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove References, Notes, and Footnotes sections",
                },
                "remove_header_navigation": {
                    "type": "boolean",
                    "default": True,
                    "description": "Remove top-of-page navigation (Anonymous, Search, etc.)",
                },
            },
        }
