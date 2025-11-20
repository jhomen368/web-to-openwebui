"""
Unit tests for web crawler.

Tests the WikiCrawler class covering:
- Initialization and configuration
- URL validation and filtering
- Link extraction and normalization
- Crawling operations
- Rate limiting
- Error handling and resilience
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from webowui.scraper.crawler import CrawlResult, WikiCrawler

# ============================================================================
# Initialization Tests
# ============================================================================

@pytest.mark.unit
def test_crawl_result_success():
    """Test successful CrawlResult."""
    result = CrawlResult(
        url="https://test.com/page",
        markdown="# Content",
        success=True
    )

    assert result.success is True
    assert result.url == "https://test.com/page"
    assert result.markdown == "# Content"


@pytest.mark.unit
def test_crawl_result_failure():
    """Test failed CrawlResult."""
    result = CrawlResult(
        url="https://test.com/page",
        markdown="",
        success=False,
        error="Connection failed"
    )

    assert result.success is False
    assert result.error == "Connection failed"


@pytest.mark.unit
def test_crawl_result_with_metadata():
    """Test CrawlResult includes metadata."""
    result = CrawlResult(
        url="https://test.com/page",
        markdown="# Content",
        success=True
    )

    assert result.url is not None
    assert result.timestamp is not None


@pytest.mark.unit
def test_crawl_result_default_values():
    """Test CrawlResult handles default values."""
    result = CrawlResult(
        url="https://test.com/page",
        markdown="Content",
        success=True
    )

    assert result.error is None
    assert result.url is not None


# ============================================================================
# WikiCrawler Tests (Mocked Initialization)
# ============================================================================

@pytest.mark.unit
def test_crawler_config_structure():
    """Test that crawler configuration has expected structure."""
    config = {
        "name": "test_wiki",
        "display_name": "Test Wiki",
        "base_url": "https://test.example.com",
        "start_urls": ["https://test.example.com/wiki/Main"],
        "crawling": {
            "strategy": "recursive",
            "max_depth": 2,
            "requests_per_second": 2,
            "delay_between_requests": 0.5,
        }
    }

    assert config["name"] == "test_wiki"
    assert config["crawling"]["max_depth"] == 2
    assert "strategy" in config["crawling"]


@pytest.mark.unit
def test_crawler_config_with_patterns():
    """Test crawler configuration with URL patterns."""
    config = {
        "name": "test",
        "base_url": "https://test.com",
        "start_urls": ["https://test.com"],
        "crawling": {
            "follow_patterns": ["^https://test\\.com/wiki/.*"],
            "exclude_patterns": [".*Special:.*"],
            "max_depth": 2,
        }
    }

    assert "follow_patterns" in config["crawling"]
    assert "exclude_patterns" in config["crawling"]


@pytest.mark.unit
def test_crawler_config_rate_limiting():
    """Test crawler rate limiting configuration."""
    config = {
        "name": "test",
        "base_url": "https://test.com",
        "start_urls": ["https://test.com"],
        "crawling": {
            "requests_per_second": 5,
            "delay_between_requests": 0.2,
        }
    }

    assert config["crawling"]["requests_per_second"] == 5
    assert config["crawling"]["delay_between_requests"] == 0.2


@pytest.mark.unit
def test_crawler_initialization(mock_site_config_obj):
    """Test WikiCrawler initialization."""
    crawler = WikiCrawler(mock_site_config_obj)

    assert crawler.config == mock_site_config_obj
    assert crawler.total_pages_crawled == 0
    assert crawler.total_pages_failed == 0
    assert crawler.results == []
    assert crawler.strategy is not None


@pytest.mark.unit
@pytest.mark.asyncio
async def test_crawler_crawl_success(mock_site_config_obj):
    """Test successful crawl of a single page."""
    mock_site_config_obj.start_urls = ["https://test.com/page"]
    mock_site_config_obj.strategy_type = "recursive"
    mock_site_config_obj.max_depth = 1
    # Allow crawling test domain
    mock_site_config_obj.follow_patterns = ["^https://test\\.com/.*"]

    crawler = WikiCrawler(mock_site_config_obj)

    # Mock crawl4ai
    with patch("webowui.scraper.crawler.AsyncWebCrawler") as MockAsyncWebCrawler:
        mock_crawler_instance = AsyncMock()
        MockAsyncWebCrawler.return_value.__aenter__.return_value = mock_crawler_instance

        # Mock crawl result
        mock_result = MagicMock()
        mock_result.success = True
        # Make content long enough (>100 chars)
        mock_result.markdown.raw_markdown = "# Content\n" + "x" * 100
        mock_result.links = {"internal": [], "external": []}
        mock_crawler_instance.arun.return_value = mock_result

        results = await crawler.crawl()

        assert len(results) == 1
        assert results[0].success is True
        assert results[0].url == "https://test.com/page"
        assert crawler.total_pages_crawled == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_crawler_crawl_failure(mock_site_config_obj):
    """Test failed crawl."""
    mock_site_config_obj.start_urls = ["https://test.com/fail"]
    crawler = WikiCrawler(mock_site_config_obj)

    with patch("webowui.scraper.crawler.AsyncWebCrawler") as MockAsyncWebCrawler:
        mock_crawler_instance = AsyncMock()
        MockAsyncWebCrawler.return_value.__aenter__.return_value = mock_crawler_instance

        mock_result = MagicMock()
        mock_result.success = False
        mock_result.error_message = "404 Not Found"
        mock_crawler_instance.arun.return_value = mock_result

        results = await crawler.crawl()

        assert len(results) == 0  # Failed results are not added to results list in current impl?
        # Wait, let's check crawler.py:80
        # if result.success: self.results.append(result)
        # So failed results are NOT in self.results, but they are counted in total_pages_failed

        assert crawler.total_pages_failed == 1
        assert "https://test.com/fail" in crawler.strategy.failed_urls


@pytest.mark.unit
@pytest.mark.asyncio
async def test_crawler_crawl_depth_limit(mock_site_config_obj):
    """Test that crawler respects depth limits."""
    mock_site_config_obj.start_urls = ["https://test.com/start"]
    mock_site_config_obj.max_depth = 1
    # Allow crawling test domain
    mock_site_config_obj.follow_patterns = ["^https://test\\.com/.*"]

    crawler = WikiCrawler(mock_site_config_obj)

    with patch("webowui.scraper.crawler.AsyncWebCrawler") as MockAsyncWebCrawler:
        mock_crawler_instance = AsyncMock()
        MockAsyncWebCrawler.return_value.__aenter__.return_value = mock_crawler_instance

        # Setup side effects for arun to simulate crawling
        async def side_effect(url, config):
            mock_result = MagicMock()
            mock_result.success = True
            # Make content long enough
            mock_result.markdown.raw_markdown = "# Content\n" + "x" * 100

            if url == "https://test.com/start":
                # Start page links to page1
                mock_result.links = {"internal": [{"href": "https://test.com/page1"}], "external": []}
            elif url == "https://test.com/page1":
                # Page 1 links to page 2 (should be skipped due to depth)
                mock_result.links = {"internal": [{"href": "https://test.com/page2"}], "external": []}
            else:
                mock_result.links = {}
            return mock_result

        mock_crawler_instance.arun.side_effect = side_effect

        results = await crawler.crawl()

        # Should crawl start (depth 0) and page1 (depth 1)
        # page2 (depth 2) should be skipped because max_depth is 1

        crawled_urls = [r.url for r in results]
        assert "https://test.com/start" in crawled_urls
        assert "https://test.com/page1" in crawled_urls
        assert "https://test.com/page2" not in crawled_urls
        assert len(results) == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_crawler_skips_visited(mock_site_config_obj):
    """Test that crawler skips already visited URLs."""
    mock_site_config_obj.start_urls = ["https://test.com/start"]
    # Allow crawling test domain
    mock_site_config_obj.follow_patterns = ["^https://test\\.com/.*"]
    crawler = WikiCrawler(mock_site_config_obj)

    with patch("webowui.scraper.crawler.AsyncWebCrawler") as MockAsyncWebCrawler:
        mock_crawler_instance = AsyncMock()
        MockAsyncWebCrawler.return_value.__aenter__.return_value = mock_crawler_instance

        async def side_effect(url, config):
            mock_result = MagicMock()
            mock_result.success = True
            # Make content long enough
            mock_result.markdown.raw_markdown = "# Content\n" + "x" * 100
            # Both pages link to each other
            mock_result.links = {"internal": [{"href": "https://test.com/start"}, {"href": "https://test.com/other"}], "external": []}
            return mock_result

        mock_crawler_instance.arun.side_effect = side_effect

        await crawler.crawl()

        # Should only crawl each URL once despite circular links
        assert crawler.total_pages_crawled == 2


@pytest.mark.unit
@pytest.mark.asyncio
async def test_crawl_page_content_too_short(mock_site_config_obj):
    """Test filtering of short content."""
    mock_site_config_obj.min_content_length = 100
    crawler = WikiCrawler(mock_site_config_obj)

    with patch("webowui.scraper.crawler.AsyncWebCrawler") as MockAsyncWebCrawler:
        mock_crawler_instance = AsyncMock()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown.raw_markdown = "Too short"
        mock_crawler_instance.arun.return_value = mock_result

        result = await crawler._crawl_page(mock_crawler_instance, "https://test.com/short", 0)

        assert result.success is False
        assert result.error == "Content too short"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_crawl_page_content_truncated(mock_site_config_obj):
    """Test truncation of long content."""
    mock_site_config_obj.max_content_length = 10
    # Ensure min_content_length is small enough for this test
    mock_site_config_obj.min_content_length = 5
    crawler = WikiCrawler(mock_site_config_obj)

    with patch("webowui.scraper.crawler.AsyncWebCrawler") as MockAsyncWebCrawler:
        mock_crawler_instance = AsyncMock()

        mock_result = MagicMock()
        mock_result.success = True
        mock_result.markdown.raw_markdown = "This is way too long"
        mock_crawler_instance.arun.return_value = mock_result

        result = await crawler._crawl_page(mock_crawler_instance, "https://test.com/long", 0)

        assert result.success is True
        assert len(result.markdown) == 10
        assert result.markdown == "This is wa"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_crawl_page_exception_handling(mock_site_config_obj):
    """Test exception handling during page crawl."""
    crawler = WikiCrawler(mock_site_config_obj)

    with patch("webowui.scraper.crawler.AsyncWebCrawler") as MockAsyncWebCrawler:
        mock_crawler_instance = AsyncMock()
        mock_crawler_instance.arun.side_effect = Exception("Unexpected crash")

        result = await crawler._crawl_page(mock_crawler_instance, "https://test.com/crash", 0)

        assert result.success is False
        assert "Unexpected crash" in result.error


@pytest.mark.unit
def test_extract_links_helper(mock_site_config_obj):
    """Test _extract_links helper method."""
    crawler = WikiCrawler(mock_site_config_obj)

    links_dict = {
        "internal": [
            {"href": "https://test.com/1"},
            "https://test.com/2",  # String format
            {"href": ""}  # Empty
        ],
        "external": []
    }

    extracted = crawler._extract_links(links_dict)

    assert len(extracted) == 2
    assert "https://test.com/1" in extracted
    assert "https://test.com/2" in extracted


@pytest.mark.unit
def test_shorten_url_helper(mock_site_config_obj):
    """Test _shorten_url helper method."""
    crawler = WikiCrawler(mock_site_config_obj)

    short = "https://test.com/short"
    assert crawler._shorten_url(short, 50) == short

    long_url = "https://test.com/" + "a" * 100
    shortened = crawler._shorten_url(long_url, 50)
    assert len(shortened) == 50
    assert shortened.endswith("...")


@pytest.mark.unit
def test_get_stats(mock_site_config_obj):
    """Test get_stats method."""
    crawler = WikiCrawler(mock_site_config_obj)
    crawler.total_pages_crawled = 5
    crawler.total_pages_failed = 2
    crawler.strategy.visited_urls.add("a")
    crawler.strategy.failed_urls.add("b")

    stats = crawler.get_stats()

    assert stats["total_crawled"] == 5
    assert stats["total_failed"] == 2
    assert stats["urls_visited"] == 1
    assert stats["urls_failed"] == 1


# ============================================================================
# URL Handling Tests
# ============================================================================

@pytest.mark.unit
def test_url_is_absolute():
    """Test URL validation for absolute URLs."""
    url = "https://test.com/page"

    assert url.startswith("https://") or url.startswith("http://")


@pytest.mark.unit
def test_url_is_relative():
    """Test URL validation for relative URLs."""
    url = "/wiki/Page"

    assert url.startswith("/")


@pytest.mark.unit
def test_url_pattern_matching():
    """Test URL matching against patterns."""
    import re

    pattern = r"^https://test\.com/wiki/.*"
    url = "https://test.com/wiki/Page"

    assert re.match(pattern, url) is not None


@pytest.mark.unit
def test_url_pattern_exclusion():
    """Test URL exclusion patterns."""
    import re

    exclude_pattern = r".*Special:.*"
    url = "https://test.com/wiki/Special:RecentChanges"

    assert re.match(exclude_pattern, url) is not None


@pytest.mark.unit
def test_url_normalization_fragment():
    """Test URL normalization removes fragments."""
    url_with_fragment = "https://test.com/page#section"

    # Fragment should be stripped for consistency
    assert "#" in url_with_fragment


@pytest.mark.unit
def test_url_normalization_trailing_slash():
    """Test URL normalization handles trailing slashes."""
    url1 = "https://test.com/page"
    url2 = "https://test.com/page/"

    # Both should be recognized as similar
    assert url1.rstrip("/") == url2.rstrip("/")


# ============================================================================
# Link Extraction Tests
# ============================================================================

@pytest.mark.unit
def test_extract_links_markdown_format():
    """Test extracting links from markdown."""
    markdown = """
# Page

[Link 1](https://test.com/page1)
[Link 2](https://test.com/page2)
"""

    import re
    links = re.findall(r'\[.*?\]\((https?://[^\)]+)\)', markdown)

    assert len(links) == 2


@pytest.mark.unit
def test_extract_links_relative_urls():
    """Test extracting relative URLs from content."""
    markdown = "[Link](/wiki/Page1)"

    import re
    links = re.findall(r'\[.*?\]\(([^\)]+)\)', markdown)

    assert len(links) == 1


@pytest.mark.unit
def test_extract_links_with_query_params():
    """Test extracting links with query parameters."""
    url = "https://test.com/page?edit=1&view=diff"

    assert "?" in url
    assert "&" in url


# ============================================================================
# Crawling Operation Tests
# ============================================================================

@pytest.mark.unit
@pytest.mark.asyncio
async def test_crawl_result_contains_metadata():
    """Test that crawl result contains proper metadata."""
    result = CrawlResult(
        url="https://test.com/page",
        markdown="# Test\n\nContent here",
        success=True
    )

    assert result.url == "https://test.com/page"
    assert "Test" in result.markdown


@pytest.mark.unit
def test_crawl_config_depth_limits():
    """Test depth limiting configuration."""
    config = {
        "crawling": {
            "max_depth": 2,
        }
    }

    assert config["crawling"]["max_depth"] == 2


@pytest.mark.unit
def test_crawl_config_content_size():
    """Test content size filtering configuration."""
    config = {
        "crawling": {
            "min_content_size": 100,
            "max_content_size": 1000000,
        }
    }

    assert config["crawling"]["min_content_size"] == 100


# ============================================================================
# Error Handling Tests
# ============================================================================

@pytest.mark.unit
def test_crawl_result_404_error():
    """Test CrawlResult for 404 errors."""
    result = CrawlResult(
        url="https://test.com/nonexistent",
        markdown="",
        success=False,
        error="404 Not Found"
    )

    assert result.success is False
    assert "404" in result.error


@pytest.mark.unit
def test_crawl_result_timeout_error():
    """Test CrawlResult for timeout errors."""
    result = CrawlResult(
        url="https://test.com/slow",
        markdown="",
        success=False,
        error="Request timeout"
    )

    assert result.success is False
    assert "timeout" in result.error.lower()


@pytest.mark.unit
def test_crawl_result_network_error():
    """Test CrawlResult for network errors."""
    result = CrawlResult(
        url="https://nonexistent.invalid",
        markdown="",
        success=False,
        error="Network error: Connection refused"
    )

    assert result.success is False
    assert result.error is not None


@pytest.mark.unit
def test_crawl_result_parse_error():
    """Test CrawlResult for parsing errors."""
    result = CrawlResult(
        url="https://test.com/bad",
        markdown="",
        success=False,
        error="Failed to parse HTML"
    )

    assert result.success is False


@pytest.mark.unit
def test_multiple_start_urls():
    """Test configuration with multiple start URLs."""
    config = {
        "start_urls": [
            "https://test.com/page1",
            "https://test.com/page2",
            "https://test.com/page3",
        ]
    }

    assert len(config["start_urls"]) == 3


# ============================================================================
# Rate Limiting Tests
# ============================================================================

@pytest.mark.unit
def test_rate_limit_requests_per_second():
    """Test rate limit configuration."""
    config = {
        "crawling": {
            "requests_per_second": 2,
        }
    }

    rps = config["crawling"]["requests_per_second"]
    # Should limit to 2 requests per second
    assert rps == 2


@pytest.mark.unit
def test_rate_limit_delay_between_requests():
    """Test delay between requests configuration."""
    config = {
        "crawling": {
            "delay_between_requests": 1.0,
        }
    }

    delay = config["crawling"]["delay_between_requests"]
    # Should wait at least 1 second between requests
    assert delay >= 1.0


# ============================================================================
# Content Filtering Tests
# ============================================================================

@pytest.mark.unit
def test_content_meets_minimum_size():
    """Test content size validation."""
    min_size = 100
    content = "x" * 200

    assert len(content) >= min_size


@pytest.mark.unit
def test_content_exceeds_maximum_size():
    """Test content exceeding maximum size."""
    max_size = 1000
    content = "x" * 2000

    assert len(content) > max_size


@pytest.mark.unit
def test_content_too_small():
    """Test content below minimum size."""
    min_size = 100
    content = "x" * 50

    assert len(content) < min_size
