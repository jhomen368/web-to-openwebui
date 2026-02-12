# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.3] - 2026-02-12

### 🐛 Bug Fixes

- **File Upload**: Fixed OpenWebUI file naming to use underscores instead of URL-encoded forward slashes in filenames.
  - Changed from: `poe2wiki%2Fwiki%2FArmour-equipment.md` (URL-encoded)
  - Changed to: `poe2wiki_wiki_Armour-equipment.md` (readable)
  - Improves readability in OpenWebUI knowledge base file listings
  - Preserves logical folder structure in flat filename format
  - References: Aligns with industry-standard bulk upload approach used in PowerShell scripts

### 📝 Notes

This is a minor bug fix release that improves the readability of uploaded filenames in OpenWebUI knowledge bases. The fix applies to all new uploads; existing files with URL-encoded names can be re-uploaded using incremental upload mode.

## [1.0.2] - 2026-01-22

### 🛠️ Maintenance

- **Docker Image Rebuild**: Rebuilt Docker image with latest base image security patches to address vulnerabilities detected in weekly security scan.

### 📝 Notes

This is a maintenance release focused on security updates and version consistency. No functional changes to the application.

**Security**: Users are encouraged to pull the latest Docker image (`ghcr.io/jhomen368/web-to-openwebui:latest`) to benefit from the latest security patches in the base Python image.

## [1.0.1] - 2026-01-04

### 🐛 Bug Fixes

- **Scheduler**: Fixed a critical issue where the scheduler would crash with `FileNotFoundError` if a site configuration file was removed but its job remained in the persistent database.
  - Implemented automatic pruning of stale jobs on startup.
  - The scheduler now synchronizes its job database with the currently available configuration files every time it starts.

## [1.0.0] - 2025-12-26

### 🎉 First Stable Release

web-to-openwebui is now production-ready! This release represents a complete, tested system for scraping web content and uploading it to OpenWebUI knowledge bases with intelligent content filtering and incremental updates.

### ⚠️ Breaking Changes

- **OpenWebUI API Update**: Fixed compatibility with latest OpenWebUI API changes (Knowledge Files endpoint changed from `/knowledge/{id}` to `/knowledge/{id}/files` and response format changed to `{"items": [...]}`).

If upgrading from pre-release versions, note these configuration changes:

- **Configuration structure updated**: The `strategy` section is now `crawling` with new options
- **Crawling strategies renamed** for clarity:
  - `recursive` → `bfs` (Breadth-First Search - recommended default)
  - `selective` → `dfs` (Depth-First Search)
  - `depth_limited` → `bfs` with `max_depth` parameter
- **Migration**: Update your site configuration files to use the new `crawling` section format (see examples in `webowui/config/examples/`)

### ✨ Features

#### Intelligent Web Crawling
- **Modern crawling strategies** powered by crawl4ai:
  - **BFS (Breadth-First)**: Comprehensive coverage, discovers content level-by-level (recommended for most sites)
  - **DFS (Depth-First)**: Deep exploration of specific branches
  - **BestFirst**: Keyword-based prioritization for targeted scraping
- **Streaming mode**: Process pages as they're crawled, reducing memory usage for large sites
- **Page limits**: Configure `max_pages` to control scrape size on massive wikis

#### Advanced Content Filtering
- **Three-stage content pipeline** for optimal embedding quality:
  1. **HTML Filtering** (optional): Remove generic noise (nav, footer, ads) before markdown conversion
  2. **Markdown Conversion**: Clean HTML to markdown transformation
  3. **Profile Cleaning**: Site-specific pattern removal (MediaWiki TOCs, Fandom ads, etc.)
- **New cleaning profiles**:
  - **MaxRoll Profile**: Optimized for gaming guide websites (maxroll.gg and similar)
  - **Enhanced MediaWiki Profile**: Removes TOCs, version history, wiki meta, and navigation boilerplate
  - **Enhanced Fandom Profile**: Handles Fandom-specific advertising and promotional content
- **Configurable filtering**: Enable/disable specific cleaning steps per site

#### Deployment & Operations
- **Kubernetes support**: Complete deployment guides and manifests for production clusters
- **Enhanced Docker setup**: Improved healthchecks, security scanning, and container optimization
- **Automated scheduling**: Built-in scheduler daemon for periodic scraping (via `webowui daemon`)
- **Incremental uploads**: Intelligent change detection uploads only new/modified content

#### Developer Experience
- **Professional CI/CD pipeline**:
  - Automated security scanning with Trivy
  - Code quality enforcement (Ruff, Black, Mypy)
  - Automated release notes extraction
  - Multi-architecture Docker builds (amd64/arm64)
- **Pre-commit hooks**: Code quality checks before commits
- **Comprehensive test suite**: 45+ unit tests with high coverage

### 🚀 Improvements

#### Performance
- **Crawler optimization**: Reduced code complexity by 33% (442 → ~300 lines) while adding features
- **Better memory efficiency**: Streaming mode for large sites
- **Automatic improvements**: Benefit from ongoing crawl4ai library enhancements

#### Content Quality
- **Cleaner markdown output**: Two-stage filtering removes more noise
- **Better embeddings**: Optimized content for RAG systems
- **Flexible configuration**: Fine-tune cleaning behavior per site

#### Security
- **Container hardening**: Non-root user, minimal base image, dropped capabilities
- **Vulnerability scanning**: Automated Trivy scans in CI/CD
- **Least-privilege permissions**: GitHub Actions follow security best practices

### 🐛 Bug Fixes

- Fixed incremental upload functionality with proper keyword argument handling
- Restored missing link extraction helper methods in crawler
- Corrected configuration documentation and examples
- Fixed all linting issues (Ruff, Black, Mypy)
- Resolved Docker healthcheck command issues
- Fixed CI/CD pipeline Python version compatibility

### 📚 Documentation

- **Complete user documentation**: Docker-first README with quick start guides
- **Kubernetes deployment guide**: Production-ready cluster setup
- **Contributing guide**: Comprehensive developer documentation (1,158 lines)
- **Configuration reference**: Detailed documentation for all options
- **Cleaning profile guide**: How to create custom profiles for new site types
- **Security policy**: Vulnerability management and reporting

### 🔧 Configuration Updates

New configuration options available:

```yaml
crawling:
  strategy: "bfs"              # bfs, dfs, or best_first
  max_pages: 500               # Limit total pages crawled
  streaming: false             # Enable streaming mode
  keywords: []                 # For best_first strategy
  keyword_weight: 0.7          # Relevance scoring

content_filtering:             # Stage 1: HTML filtering
  enabled: false
  excluded_tags: [nav, footer, aside]
  exclude_external_links: false
  min_word_threshold: 50

markdown_cleaning:             # Stage 3: Profile cleaning
  profile: "mediawiki"         # none, mediawiki, fandomwiki, maxroll
```

### 🎯 What's Next

This v1.0.0 release establishes a stable foundation. Future releases will focus on:
- Additional cleaning profiles for more site types
- Web UI for configuration management
- Enhanced monitoring and metrics
- Performance optimizations

### 📦 Installation

```bash
# Docker (recommended)
docker compose up -d

# Or via pip (when published to PyPI)
pip install web-to-openwebui
```

See [README.md](README.md) for complete installation and usage instructions.

### 🙏 Acknowledgments

Thank you to the crawl4ai team for their excellent crawling library, and to the OpenWebUI community for building an amazing RAG platform.

---

## [0.9.0] - 2025-11-15

Pre-release development version. Initial implementation of core features before production hardening.
