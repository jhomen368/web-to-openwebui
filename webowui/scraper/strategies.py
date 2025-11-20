"""
Crawling strategies for different scraping approaches.
"""

import logging
import re
from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, cast
from urllib.parse import urljoin, urlparse

if TYPE_CHECKING:
    from ..config import SiteConfig

logger = logging.getLogger(__name__)


class CrawlStrategy(ABC):
    """Base class for crawling strategies."""

    def __init__(self, site_config: "SiteConfig") -> None:
        self.config = site_config
        self.visited_urls: set[str] = set()
        self.queued_urls: set[str] = set()
        self.failed_urls: set[str] = set()

    @abstractmethod
    def should_crawl(self, url: str, depth: int = 0) -> bool:
        """Determine if a URL should be crawled."""
        pass

    @abstractmethod
    def get_next_urls(
        self, current_url: str, links: list[str], current_depth: int
    ) -> list[tuple[str, int]]:
        """Get next URLs to crawl with their depths."""
        pass

    def matches_patterns(self, url: str, patterns: list[str]) -> bool:
        """Check if URL matches any of the regex patterns."""
        return any(re.search(pattern, url) for pattern in patterns)

    def should_follow_url(self, url: str) -> bool:
        """Check if URL should be followed based on patterns."""
        # Check exclude patterns first
        if self.config.exclude_patterns and self.matches_patterns(
            url, self.config.exclude_patterns
        ):
            return False

        # If follow patterns specified, must match one
        if self.config.follow_patterns:
            return self.matches_patterns(url, self.config.follow_patterns)

        # Default: follow if same domain
        base_domain = urlparse(self.config.base_url).netloc
        url_domain = urlparse(url).netloc
        return cast(bool, base_domain == url_domain)

    def normalize_url(self, url: str, base_url: str) -> str | None:
        """Normalize and validate URL."""
        try:
            # Handle relative URLs
            if not url.startswith(("http://", "https://")):
                url = urljoin(base_url, url)

            # Remove fragment
            url = url.split("#")[0]

            # Remove trailing slash for consistency
            url = url.rstrip("/")

            return url
        except Exception as e:
            logger.warning(f"Failed to normalize URL {url}: {e}")
            return None


class RecursiveStrategy(CrawlStrategy):
    """Recursively follow all matching links up to max depth."""

    def should_crawl(self, url: str, depth: int = 0) -> bool:
        """Check if should crawl based on depth and patterns."""
        if depth > self.config.max_depth:
            return False

        if url in self.visited_urls or url in self.queued_urls:
            return False

        return self.should_follow_url(url)

    def get_next_urls(
        self, current_url: str, links: list[str], current_depth: int
    ) -> list[tuple[str, int]]:
        """Get next URLs to crawl."""
        next_urls: list[tuple[str, int]] = []
        next_depth = current_depth + 1

        if next_depth > self.config.max_depth:
            return next_urls

        for link in links:
            normalized = self.normalize_url(link, current_url)
            if normalized and self.should_crawl(normalized, next_depth):
                next_urls.append((normalized, next_depth))
                self.queued_urls.add(normalized)

        return next_urls


class SelectiveStrategy(CrawlStrategy):
    """Only crawl URLs matching specific patterns, more controlled."""

    def should_crawl(self, url: str, depth: int = 0) -> bool:
        """Must match follow patterns and not be visited."""
        if url in self.visited_urls or url in self.queued_urls:
            return False

        # Require explicit match with follow patterns
        if not self.config.follow_patterns:
            logger.warning("SelectiveStrategy requires follow_patterns to be specified")
            return False

        return self.matches_patterns(url, self.config.follow_patterns)

    def get_next_urls(
        self, current_url: str, links: list[str], current_depth: int
    ) -> list[tuple[str, int]]:
        """Get URLs that match selective criteria."""
        next_urls = []

        for link in links:
            normalized = self.normalize_url(link, current_url)
            if normalized and self.should_crawl(normalized, current_depth + 1):
                next_urls.append((normalized, current_depth + 1))
                self.queued_urls.add(normalized)

        return next_urls


class DepthLimitedStrategy(CrawlStrategy):
    """Crawl with strict depth limit from start URL."""

    def should_crawl(self, url: str, depth: int = 0) -> bool:
        """Check depth limit strictly."""
        if depth > self.config.max_depth:
            return False

        if url in self.visited_urls or url in self.queued_urls:
            return False

        return self.should_follow_url(url)

    def get_next_urls(
        self, current_url: str, links: list[str], current_depth: int
    ) -> list[tuple[str, int]]:
        """Get next URLs within depth limit."""
        next_urls: list[tuple[str, int]] = []
        next_depth = current_depth + 1

        if next_depth > self.config.max_depth:
            return next_urls

        for link in links:
            normalized = self.normalize_url(link, current_url)
            if normalized and self.should_crawl(normalized, next_depth):
                next_urls.append((normalized, next_depth))
                self.queued_urls.add(normalized)

        return next_urls


def get_strategy(site_config) -> RecursiveStrategy | SelectiveStrategy | DepthLimitedStrategy:
    """Factory function to get appropriate strategy."""
    strategy_map: dict[
        str, type[RecursiveStrategy] | type[SelectiveStrategy] | type[DepthLimitedStrategy]
    ] = {
        "recursive": RecursiveStrategy,
        "selective": SelectiveStrategy,
        "depth_limited": DepthLimitedStrategy,
    }

    strategy_class = strategy_map.get(site_config.strategy_type, RecursiveStrategy)
    return strategy_class(site_config)
