"""
Web scraping module using crawl4ai.
"""

from .crawler import WikiCrawler
from .strategies import CrawlStrategy, DepthLimitedStrategy, RecursiveStrategy, SelectiveStrategy

__all__ = [
    "WikiCrawler",
    "CrawlStrategy",
    "RecursiveStrategy",
    "SelectiveStrategy",
    "DepthLimitedStrategy",
]
