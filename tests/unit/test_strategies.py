"""
Unit tests for crawl strategies.

Tests the different crawl strategy implementations:
- RecursiveStrategy: Follow all matching links up to max depth
- SelectiveStrategy: Only crawl explicit patterns
- DepthLimitedStrategy: Strict depth enforcement from start URLs
"""
from unittest.mock import Mock

import pytest

from webowui.scraper.strategies import (
    CrawlStrategy,
    DepthLimitedStrategy,
    RecursiveStrategy,
    SelectiveStrategy,
    get_strategy,
)

# ============================================================================
# RecursiveStrategy Tests
# ============================================================================

@pytest.mark.unit
def test_recursive_strategy_initialization(mock_site_config_obj):
    """Test RecursiveStrategy initialization."""
    mock_site_config_obj.max_depth = 3
    strategy = RecursiveStrategy(mock_site_config_obj)

    assert strategy.config == mock_site_config_obj
    assert strategy.config.max_depth == 3


@pytest.mark.unit
def test_recursive_strategy_should_crawl_matching(mock_site_config_obj):
    """Test RecursiveStrategy crawls URLs matching patterns."""
    mock_site_config_obj.follow_patterns = ["^https://wiki\\.example\\.com/wiki/.*"]
    mock_site_config_obj.exclude_patterns = [".*Special:.*"]
    mock_site_config_obj.max_depth = 2

    strategy = RecursiveStrategy(mock_site_config_obj)

    url = "https://wiki.example.com/wiki/Page"
    assert strategy.should_crawl(url, depth=1) is True


@pytest.mark.unit
def test_recursive_strategy_exclude_patterns(mock_site_config_obj):
    """Test RecursiveStrategy excludes URLs matching exclusion patterns."""
    mock_site_config_obj.follow_patterns = ["^https://wiki\\.example\\.com/.*"]
    mock_site_config_obj.exclude_patterns = [".*Special:.*", ".*User:.*"]

    strategy = RecursiveStrategy(mock_site_config_obj)

    excluded_url = "https://wiki.example.com/wiki/Special:RecentChanges"
    assert strategy.should_crawl(excluded_url, depth=1) is False


@pytest.mark.unit
def test_recursive_strategy_depth_enforcement(mock_site_config_obj):
    """Test RecursiveStrategy enforces depth limits."""
    mock_site_config_obj.max_depth = 2
    mock_site_config_obj.follow_patterns = ["^https://wiki\\.example\\.com/.*"]

    strategy = RecursiveStrategy(mock_site_config_obj)

    url = "https://wiki.example.com/wiki/Page"

    # Within depth
    assert strategy.should_crawl(url, depth=2) is True

    # Exceeds depth
    assert strategy.should_crawl(url, depth=3) is False


@pytest.mark.unit
def test_recursive_strategy_visited_urls(mock_site_config_obj):
    """Test RecursiveStrategy skips visited URLs."""
    mock_site_config_obj.follow_patterns = ["^https://wiki\\.example\\.com/.*"]
    strategy = RecursiveStrategy(mock_site_config_obj)

    url = "https://wiki.example.com/wiki/Page"
    strategy.visited_urls.add(url)

    assert strategy.should_crawl(url, depth=1) is False


@pytest.mark.unit
def test_recursive_strategy_get_next_urls(mock_site_config_obj):
    """Test RecursiveStrategy extracts next URLs from content."""
    mock_site_config_obj.follow_patterns = ["^https://wiki\\.example\\.com/wiki/.*"]
    mock_site_config_obj.max_depth = 2

    strategy = RecursiveStrategy(mock_site_config_obj)

    current_url = "https://wiki.example.com/wiki/Start"
    links = [
        "https://wiki.example.com/wiki/Page1",
        "/wiki/Page2",  # Relative
        "https://external.com/page",  # External (should be skipped by default follow pattern)
    ]

    next_urls = strategy.get_next_urls(current_url, links, current_depth=1)

    assert len(next_urls) == 2
    assert ("https://wiki.example.com/wiki/Page1", 2) in next_urls
    assert ("https://wiki.example.com/wiki/Page2", 2) in next_urls


@pytest.mark.unit
def test_recursive_strategy_get_next_urls_max_depth(mock_site_config_obj):
    """Test RecursiveStrategy stops at max depth."""
    mock_site_config_obj.max_depth = 1
    strategy = RecursiveStrategy(mock_site_config_obj)

    current_url = "https://wiki.example.com/wiki/Start"
    links = ["https://wiki.example.com/wiki/Page1"]

    # Current depth 1, next depth 2 > max_depth 1 -> should return empty
    next_urls = strategy.get_next_urls(current_url, links, current_depth=1)
    assert len(next_urls) == 0


# ============================================================================
# SelectiveStrategy Tests
# ============================================================================

@pytest.mark.unit
def test_selective_strategy_initialization(mock_site_config_obj):
    """Test SelectiveStrategy initialization."""
    strategy = SelectiveStrategy(mock_site_config_obj)
    assert strategy.config == mock_site_config_obj


@pytest.mark.unit
def test_selective_strategy_only_explicit_urls(mock_site_config_obj):
    """Test SelectiveStrategy only crawls explicitly listed patterns."""
    mock_site_config_obj.follow_patterns = [
        "^https://wiki\\.example\\.com/wiki/Main",
        "^https://wiki\\.example\\.com/wiki/About"
    ]

    strategy = SelectiveStrategy(mock_site_config_obj)

    main_url = "https://wiki.example.com/wiki/Main"
    other_url = "https://wiki.example.com/wiki/Other"

    assert strategy.should_crawl(main_url) is True
    assert strategy.should_crawl(other_url) is False


@pytest.mark.unit
def test_selective_strategy_no_discovery(mock_site_config_obj):
    """Test SelectiveStrategy link discovery logic."""
    mock_site_config_obj.follow_patterns = ["^https://wiki\\.example\\.com/wiki/Main"]

    strategy = SelectiveStrategy(mock_site_config_obj)

    current_url = "https://wiki.example.com/wiki/Start"
    links = [
        "https://wiki.example.com/wiki/Main",  # Matches pattern
        "https://wiki.example.com/wiki/Other"  # Doesn't match
    ]

    next_urls = strategy.get_next_urls(current_url, links, current_depth=0)

    # Should only return the matching URL
    assert len(next_urls) == 1
    assert next_urls[0][0] == "https://wiki.example.com/wiki/Main"


@pytest.mark.unit
def test_selective_strategy_requires_patterns(mock_site_config_obj):
    """Test SelectiveStrategy warns if no patterns provided."""
    mock_site_config_obj.follow_patterns = []
    strategy = SelectiveStrategy(mock_site_config_obj)

    assert strategy.should_crawl("https://example.com") is False


# ============================================================================
# DepthLimitedStrategy Tests
# ============================================================================

@pytest.mark.unit
def test_depth_limited_strategy_initialization(mock_site_config_obj):
    """Test DepthLimitedStrategy initialization."""
    strategy = DepthLimitedStrategy(mock_site_config_obj)
    assert strategy.config == mock_site_config_obj


@pytest.mark.unit
def test_depth_limited_strategy_strict_depth(mock_site_config_obj):
    """Test DepthLimitedStrategy enforces strict depth limits."""
    mock_site_config_obj.max_depth = 1
    mock_site_config_obj.follow_patterns = ["^https://wiki\\.example\\.com/.*"]

    strategy = DepthLimitedStrategy(mock_site_config_obj)
    url = "https://wiki.example.com/wiki/Page"

    assert strategy.should_crawl(url, depth=1) is True
    assert strategy.should_crawl(url, depth=2) is False


@pytest.mark.unit
def test_depth_limited_strategy_get_next_urls(mock_site_config_obj):
    """Test DepthLimitedStrategy filters next URLs by depth."""
    mock_site_config_obj.max_depth = 2
    mock_site_config_obj.follow_patterns = ["^https://wiki\\.example\\.com/.*"]

    strategy = DepthLimitedStrategy(mock_site_config_obj)

    current_url = "https://wiki.example.com/wiki/Start"
    links = ["https://wiki.example.com/wiki/Page1"]

    # Depth 1 -> 2 (OK)
    next_urls = strategy.get_next_urls(current_url, links, current_depth=1)
    assert len(next_urls) == 1

    # Depth 2 -> 3 (Too deep)
    next_urls = strategy.get_next_urls(current_url, links, current_depth=2)
    assert len(next_urls) == 0


# ============================================================================
# Strategy Base Class Tests
# ============================================================================

@pytest.mark.unit
def test_strategy_base_class_is_abstract():
    """Test that CrawlStrategy base class is abstract."""
    try:
        CrawlStrategy(Mock())
        pytest.fail("Should not be able to instantiate abstract class")
    except TypeError:
        pass


@pytest.mark.unit
def test_normalize_url(mock_site_config_obj):
    """Test URL normalization logic."""
    strategy = RecursiveStrategy(mock_site_config_obj)
    base_url = "https://example.com/wiki/Base"

    # Relative URL
    assert strategy.normalize_url("/wiki/Page", base_url) == "https://example.com/wiki/Page"

    # Fragment removal
    assert strategy.normalize_url("https://example.com/page#section", base_url) == "https://example.com/page"

    # Trailing slash removal
    assert strategy.normalize_url("https://example.com/page/", base_url) == "https://example.com/page"

    # Invalid URL handling
    assert strategy.normalize_url(None, base_url) is None  # type: ignore


@pytest.mark.unit
def test_should_follow_url_default_domain(mock_site_config_obj):
    """Test default domain matching when no patterns specified."""
    mock_site_config_obj.follow_patterns = []
    mock_site_config_obj.exclude_patterns = []
    mock_site_config_obj.base_url = "https://example.com"

    strategy = RecursiveStrategy(mock_site_config_obj)

    # Same domain
    assert strategy.should_follow_url("https://example.com/page") is True

    # Different domain
    assert strategy.should_follow_url("https://other.com/page") is False


@pytest.mark.unit
def test_get_strategy_factory(mock_site_config_obj):
    """Test strategy factory function."""

    # Recursive
    mock_site_config_obj.strategy_type = "recursive"
    assert isinstance(get_strategy(mock_site_config_obj), RecursiveStrategy)

    # Selective
    mock_site_config_obj.strategy_type = "selective"
    assert isinstance(get_strategy(mock_site_config_obj), SelectiveStrategy)

    # Depth Limited
    mock_site_config_obj.strategy_type = "depth_limited"
    assert isinstance(get_strategy(mock_site_config_obj), DepthLimitedStrategy)

    # Default
    mock_site_config_obj.strategy_type = "unknown"
    assert isinstance(get_strategy(mock_site_config_obj), RecursiveStrategy)
