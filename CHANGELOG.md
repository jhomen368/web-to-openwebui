# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-11-21

### Breaking Changes
- Config structure: `strategy` → `crawling`
- Strategy types renamed: `recursive` → `bfs`, `selective` → `dfs`, `depth_limited` → `bfs`
- Removed `webowui/scraper/strategies.py` (replaced by crawl4ai built-in strategies)

### Added
- ✨ **crawl4ai Deep Crawling Integration**
  - BFS (Breadth-First Search) strategy - recommended default
  - DFS (Depth-First Search) strategy
  - BestFirst strategy with keyword-based prioritization
  - Streaming mode support (`streaming: true` in config)
- ✨ **Two-Stage Content Filtering**
  - Stage 1: Generic HTML filtering via crawl4ai (optional)
  - Stage 2: Site-specific markdown cleaning via profiles (existing)
- ✨ **New Configuration Options**
  - `content_filtering` section for Stage 1 filtering
  - `max_pages` limit for large sites
  - `keywords` and `keyword_weight` for BestFirst strategy

### Changed
- ♻️ **Refactored Crawler Architecture**
  - Uses crawl4ai's AsyncWebCrawler with deep_crawl_strategy
  - Simplified from 442 lines to ~300 lines (33% reduction)
  - No custom queue management (uses proven library)
- ♻️ **Simplified MediaWikiProfile**
  - Focuses on MediaWiki-specific patterns only
  - Generic HTML filtering moved to crawl4ai Stage 1
  - Reduced from ~130 lines to ~50 lines in main method

### Removed
- 🗑️ **Deleted `webowui/scraper/strategies.py`** (183 lines)
  - Replaced by crawl4ai's BFSDeepCrawlStrategy, DFSDeepCrawlStrategy, BestFirstCrawlingStrategy
- 🗑️ **Deleted `tests/unit/test_strategies.py`** (303 lines)
  - Replaced with new tests for crawl4ai integration

### Fixed
- 🐛 Restored missing `_extract_links()` helper method in crawler
- 🐛 Fixed all linting issues (ruff, black, mypy)

### Developer Experience
- 📚 Updated all documentation (README, CONTRIBUTING, memory bank)
- ✅ All 45 crawler tests passing
- ✅ Full test suite validation
- 📝 Clear migration path from old to new config structure

### Performance
- 🚀 Automatic improvements as crawl4ai library evolves
- 🚀 Streaming mode reduces memory usage for large sites
- 🚀 Better content filtering reduces embedding noise

## [0.9.0] - Pre-release

Initial development version before crawl4ai integration.
