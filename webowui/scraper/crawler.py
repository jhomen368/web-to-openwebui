"""
Main web crawler using crawl4ai.
"""

import asyncio
import logging
from datetime import datetime

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from ..config import SiteConfig
from .strategies import CrawlStrategy, get_strategy

logger = logging.getLogger(__name__)


class CrawlResult:
    """Result from crawling a single page."""

    def __init__(
        self,
        url: str,
        success: bool,
        markdown: str = "",
        links: list[str] | None = None,
        error: str | None = None,
    ):
        self.url = url
        self.success = success
        self.markdown = markdown
        self.links = links or []
        self.error = error
        self.timestamp = datetime.now()


class WikiCrawler:
    """Main crawler class for scraping wikis."""

    def __init__(self, site_config: SiteConfig):
        self.config = site_config
        self.strategy: CrawlStrategy = get_strategy(site_config)
        self.results: list[CrawlResult] = []
        self.total_pages_crawled = 0
        self.total_pages_failed = 0

    async def crawl(self, progress_callback=None) -> list[CrawlResult]:
        """Main crawl method."""
        logger.info(f"Starting crawl for {self.config.display_name}")
        logger.info(f"Strategy: {self.config.strategy_type}, Max depth: {self.config.max_depth}")

        # Initialize queue with start URLs
        url_queue = [(url, 0) for url in self.config.start_urls]

        async with AsyncWebCrawler(verbose=False, magic=True) as crawler:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                task = progress.add_task(f"Crawling {self.config.display_name}...", total=None)

                while url_queue:
                    current_url, depth = url_queue.pop(0)

                    # Skip if already visited
                    if current_url in self.strategy.visited_urls:
                        continue

                    progress.update(
                        task,
                        description=f"Crawling (depth {depth}): {self._shorten_url(current_url)}",
                    )

                    # Crawl the page
                    result = await self._crawl_page(crawler, current_url, depth)

                    if result.success:
                        self.results.append(result)
                        self.total_pages_crawled += 1
                        self.strategy.visited_urls.add(current_url)

                        # Add new URLs to queue
                        new_urls = self.strategy.get_next_urls(current_url, result.links, depth)
                        url_queue.extend(new_urls)

                        logger.info(f"✓ Crawled: {current_url} ({len(result.markdown)} chars)")
                    else:
                        self.total_pages_failed += 1
                        self.strategy.failed_urls.add(current_url)
                        logger.error(f"✗ Failed: {current_url} - {result.error}")

                    # Rate limiting
                    await asyncio.sleep(self.config.delay_between_requests)

                    if progress_callback:
                        progress_callback(self.total_pages_crawled, self.total_pages_failed)

        logger.info(
            f"Crawl complete: {self.total_pages_crawled} pages, {self.total_pages_failed} failures"
        )
        return self.results

    async def _crawl_page(self, crawler: AsyncWebCrawler, url: str, depth: int) -> CrawlResult:
        """Crawl a single page and extract content."""
        try:
            # Configure crawl with minimal settings to avoid CSS selector issues
            config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                markdown_generator=DefaultMarkdownGenerator(
                    options={
                        "heading_style": self.config.markdown_options.get("heading_style", "atx"),
                        "include_links": self.config.markdown_options.get("include_links", True),
                    }
                ),
                word_count_threshold=self.config.min_content_length,
                page_timeout=30000,  # 30 second timeout
                # Removed excluded_tags to avoid CSS selector issues
            )

            # Perform crawl
            result = await crawler.arun(url=url, config=config)

            if not result.success:
                return CrawlResult(url, False, error=result.error_message or "Unknown error")

            # Extract content - updated to use new API
            markdown = result.markdown.raw_markdown if result.markdown else ""

            # Filter by content length
            if len(markdown) < self.config.min_content_length:
                return CrawlResult(url, False, error="Content too short")

            if len(markdown) > self.config.max_content_length:
                logger.warning(f"Content truncated for {url} (too long)")
                markdown = markdown[: self.config.max_content_length]

            # Extract links
            links = self._extract_links(result.links) if hasattr(result, "links") else []

            return CrawlResult(url, True, markdown=markdown, links=links)

        except Exception as e:
            logger.error(f"Error crawling {url}: {str(e)}")
            return CrawlResult(url, False, error=str(e))

    def _extract_links(self, links_dict: dict) -> list[str]:
        """Extract and filter links from crawl result."""
        if not links_dict:
            return []

        internal_links = links_dict.get("internal", [])
        links_dict.get("external", [])

        # For wikis, we typically want internal links
        all_links = []

        for link in internal_links:
            url = link.get("href", "") if isinstance(link, dict) else str(link)

            if url:
                all_links.append(url)

        return all_links

    def _shorten_url(self, url: str, max_length: int = 60) -> str:
        """Shorten URL for display."""
        if len(url) <= max_length:
            return url
        return url[: max_length - 3] + "..."

    def get_stats(self) -> dict:
        """Get crawl statistics."""
        return {
            "total_crawled": self.total_pages_crawled,
            "total_failed": self.total_pages_failed,
            "urls_visited": len(self.strategy.visited_urls),
            "urls_failed": len(self.strategy.failed_urls),
        }
