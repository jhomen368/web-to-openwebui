"""
Main web crawler using crawl4ai.
"""

import logging
import math
import re
from datetime import datetime

from crawl4ai import AsyncWebCrawler, CacheMode, CrawlerRunConfig
from crawl4ai.deep_crawling import (
    BestFirstCrawlingStrategy,
    BFSDeepCrawlStrategy,
    DFSDeepCrawlStrategy,
)
from crawl4ai.deep_crawling.filters import DomainFilter, FilterChain, URLPatternFilter
from crawl4ai.deep_crawling.scorers import KeywordRelevanceScorer
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from rich.progress import BarColumn, Progress, SpinnerColumn, TaskProgressColumn, TextColumn

from ..config import SiteConfig

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
        self.results: list[CrawlResult] = []
        self.total_pages_crawled = 0
        self.total_pages_failed = 0

    async def crawl(self, progress_callback=None) -> list[CrawlResult]:
        """Main crawl method using crawl4ai deep crawling."""
        logger.info(f"Starting crawl for {self.config.display_name}")
        logger.info(f"Strategy: {self.config.crawl_strategy}, Max depth: {self.config.max_depth}")

        strategy = self._create_deep_crawl_strategy()
        config = self._create_crawler_config(strategy)

        async with AsyncWebCrawler(verbose=False, magic=True) as crawler:
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                task = progress.add_task(f"Crawling {self.config.display_name}...", total=None)

                # Use streaming if configured (defaulting to False for now until config update)
                use_streaming = getattr(self.config, "use_streaming", False)

                if use_streaming:
                    async for result in crawler.arun(url=self.config.start_urls[0], config=config):
                        crawl_result = self._convert_result(result)
                        self.results.append(crawl_result)

                        if crawl_result.success:
                            self.total_pages_crawled += 1
                            logger.info(
                                f"✓ Crawled: {crawl_result.url} ({len(crawl_result.markdown)} chars)"
                            )
                        else:
                            self.total_pages_failed += 1
                            logger.error(f"✗ Failed: {crawl_result.url} - {crawl_result.error}")

                        progress.update(
                            task,
                            description=f"Crawled: {self.total_pages_crawled} pages",
                            advance=1,
                        )

                        if progress_callback:
                            progress_callback(self.total_pages_crawled, self.total_pages_failed)
                else:
                    # Batch mode
                    raw_results = await crawler.arun(url=self.config.start_urls[0], config=config)

                    for result in raw_results:
                        crawl_result = self._convert_result(result)
                        self.results.append(crawl_result)

                        if crawl_result.success:
                            self.total_pages_crawled += 1
                            logger.info(
                                f"✓ Crawled: {crawl_result.url} ({len(crawl_result.markdown)} chars)"
                            )
                        else:
                            self.total_pages_failed += 1
                            logger.error(f"✗ Failed: {crawl_result.url} - {crawl_result.error}")

                        progress.update(
                            task,
                            description=f"Crawled: {self.total_pages_crawled} pages",
                            advance=1,
                        )

                        if progress_callback:
                            progress_callback(self.total_pages_crawled, self.total_pages_failed)

        logger.info(
            f"Crawl complete: {self.total_pages_crawled} pages, {self.total_pages_failed} failures"
        )
        return self.results

    def _create_deep_crawl_strategy(self):
        """Create crawl4ai strategy from site config."""
        # Build filter chain from config
        filters = []
        if self.config.follow_patterns:
            # Config patterns are regex (e.g. ^https://...), so we must compile them
            # and use use_glob=False
            compiled_follow = [re.compile(p) for p in self.config.follow_patterns]
            filters.append(URLPatternFilter(patterns=compiled_follow, use_glob=False))

        if self.config.exclude_patterns:
            # Config patterns are regex, so we compile them and use reverse=True for exclusion
            compiled_exclude = [re.compile(p) for p in self.config.exclude_patterns]
            filters.append(
                URLPatternFilter(patterns=compiled_exclude, reverse=True, use_glob=False)
            )

        exclude_domains = getattr(self.config, "exclude_domains", [])
        if exclude_domains:
            filters.append(DomainFilter(blocked_domains=exclude_domains))

        filter_chain = FilterChain(filters) if filters else None

        # Map strategy type
        strategy_type = self.config.crawl_strategy
        if strategy_type in ["recursive", "selective", "depth_limited"]:
            strategy_type = "bfs"  # Default to BFS for old types

        strategy_map = {
            "bfs": BFSDeepCrawlStrategy,
            "dfs": DFSDeepCrawlStrategy,
            "best_first": BestFirstCrawlingStrategy,
        }

        strategy_class = strategy_map.get(strategy_type, BFSDeepCrawlStrategy)

        # Create instance
        max_pages = getattr(self.config, "max_pages", None)
        if max_pages is None:
            max_pages = math.inf

        if strategy_class == BestFirstCrawlingStrategy:
            crawl_keywords = getattr(self.config, "crawl_keywords", [])
            crawl_keyword_weight = getattr(self.config, "crawl_keyword_weight", 0.7)
            scorer = KeywordRelevanceScorer(
                keywords=crawl_keywords,
                weight=crawl_keyword_weight,
            )
            return strategy_class(
                max_depth=self.config.max_depth,
                url_scorer=scorer,
                filter_chain=filter_chain,
                max_pages=max_pages,
            )
        else:
            return strategy_class(
                max_depth=self.config.max_depth,
                include_external=False,
                filter_chain=filter_chain,
                max_pages=max_pages,
            )

    def _create_crawler_config(self, deep_crawl_strategy):
        """Create CrawlerRunConfig from site config."""
        # Get new config fields with defaults
        use_streaming = getattr(self.config, "use_streaming", False)
        excluded_tags = getattr(self.config, "excluded_tags", [])
        # Ensure excluded_tags is a list of strings
        if excluded_tags is None:
            excluded_tags = []
        elif isinstance(excluded_tags, str):
            excluded_tags = [excluded_tags]

        exclude_external_links = getattr(self.config, "exclude_external_links", False)
        exclude_social_media = getattr(self.config, "exclude_social_media", False)

        return CrawlerRunConfig(
            deep_crawl_strategy=deep_crawl_strategy,
            stream=use_streaming,
            # Content filtering (Stage 1)
            excluded_tags=excluded_tags,
            exclude_external_links=exclude_external_links,
            exclude_social_media_links=exclude_social_media,
            word_count_threshold=getattr(self.config, "min_block_words", 10),
            # Markdown generation
            markdown_generator=self._create_markdown_generator(),
            cache_mode=CacheMode.BYPASS,
            page_timeout=30000,
        )

    def _create_markdown_generator(self):
        """Create markdown generator with optional content filter."""
        from crawl4ai.content_filter_strategy import PruningContentFilter

        pruning_enabled = getattr(self.config, "pruning_enabled", False)
        pruning_threshold = getattr(self.config, "pruning_threshold", 0.6)
        pruning_min_words = getattr(self.config, "pruning_min_words", 50)

        content_filter = None
        if pruning_enabled:
            content_filter = PruningContentFilter(
                threshold=pruning_threshold, min_word_threshold=pruning_min_words
            )

        return DefaultMarkdownGenerator(
            content_source="cleaned_html",
            content_filter=content_filter,
            options=self.config.markdown_options,
        )

    def _convert_result(self, crawl4ai_result) -> CrawlResult:
        """Convert crawl4ai result to our CrawlResult format."""
        if not crawl4ai_result.success:
            return CrawlResult(
                url=crawl4ai_result.url,
                success=False,
                markdown="",
                links=[],
                error=crawl4ai_result.error_message,
            )

        # Use fit_markdown if available (filtered), fallback to raw
        markdown = (
            crawl4ai_result.markdown.fit_markdown
            if crawl4ai_result.markdown and crawl4ai_result.markdown.fit_markdown
            else (crawl4ai_result.markdown.raw_markdown if crawl4ai_result.markdown else "")
        )

        # Apply page length filter
        min_length = getattr(self.config, "min_page_length", 100)
        max_length = getattr(self.config, "max_page_length", 500000)

        error_message = crawl4ai_result.error_message
        final_success = crawl4ai_result.success

        if len(markdown) < min_length:
            error_message = f"Content too short ({len(markdown)} chars < {min_length})"
            final_success = False
            markdown = ""  # Discard content
        elif len(markdown) > max_length:
            error_message = f"Content too long ({len(markdown)} chars > {max_length})"
            final_success = False
            markdown = ""  # Discard content

        return CrawlResult(
            url=crawl4ai_result.url,
            success=final_success,
            markdown=markdown,
            links=self._extract_links(crawl4ai_result.links),
            error=error_message,
        )

    def _extract_links(self, links_dict: dict) -> list[str]:
        """Extract links from crawl4ai links dictionary."""
        extracted: list[str] = []
        if not links_dict:
            return extracted

        # Process internal links
        for link in links_dict.get("internal", []):
            if isinstance(link, dict):
                href = link.get("href")
                if href:
                    extracted.append(href)
            elif isinstance(link, str):
                extracted.append(link)

        return extracted

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
            "urls_visited": self.total_pages_crawled + self.total_pages_failed,
            "urls_failed": self.total_pages_failed,
        }
