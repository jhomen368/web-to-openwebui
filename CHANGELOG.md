# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.7] - 2026-02-23

### 🐛 Bug Fixes

- **Upload Result Mapping**: Fixed upload result mapping for files with nested directory paths.
  - **Root Cause**: Files with nested paths like `content/news/update.md` were not being correctly mapped to their upload results because the filename comparison was using the wrong field.
  - **Impact**: Files uploaded with nested paths weren't being tracked properly for incremental uploads, causing reconciliation failures.
  - **Fix**: Changed upload result comparison to use `upload_filename` field (flattened name) instead of `filename` field.

- **Reconciliation Filename Matching**: Fixed reconciliation filename matching with proper path flattening.
  - **Root Cause**: Local filenames like `content/news/update.md` weren't being flattened before comparison with remote filenames like `mysite_content_news_update.md`.
  - **Impact**: Reconciliation would fail to match files that existed in both local and remote storage.
  - **Fix**: Added proper filename flattening logic that converts nested paths to underscore-separated names.

- **Upload Result Comparison**: Fixed upload result comparison to use correct `upload_filename` field.
  - **Root Cause**: Code was comparing `filename` (e.g., `poe2/atlas-tree.md`) instead of `upload_filename` (e.g., `mysite_poe2_atlas-tree.md`).
  - **Impact**: File IDs weren't being correctly mapped after upload, breaking incremental update tracking.
  - **Fix**: Updated comparison logic to use the flattened `upload_filename` field.

### ✨ Added

- **Test Coverage**: Added comprehensive test coverage for nested path filename flattening scenarios.
  - 5 new test cases for filename flattening logic
  - Test coverage for nested path upload scenarios
  - Test coverage for Windows backslash path handling
  - Test coverage for ValueError fallback scenarios

### 📈 Improvements

- **Test Coverage**: Test coverage for `openwebui_client.py` increased to 79.45%.

### 📝 Technical Details

Files with nested paths like `content/news/update.md` are now correctly:
- Uploaded as `mysite_content_news_update.md` (flattened)
- Mapped to correct file_ids in upload results
- Matched during reconciliation with remote storage
- Tracked properly for incremental uploads

### 🔗 Related

These fixes ensure that sites with nested URL structures (like wikis with category paths) work correctly with the incremental upload and reconciliation features.

## [1.0.6] - 2026-02-22

### 🐛 Bug Fixes

- **Critical Path Resolution Fix**: Fixed a critical bug in incremental upload that caused all files to be skipped during upload to OpenWebUI.
  - **Root Cause**: The upload code was using the `filename` field (e.g., `poe2/atlas-tree.md`) to construct file paths, but files are actually stored in the `content/` subdirectory (e.g., `content/poe2/atlas-tree.md`).
  - **Impact**: All incremental uploads were failing silently - scheduler showed "30 files to upload" but uploaded 0 files.
  - **Fix**: Changed `openwebui_client.py` line 1210 to use the `filepath` field (which includes the `content/` prefix) with fallback to `filename` for backward compatibility.
  - **Verification**: All 379 unit tests pass, verified with local test data showing 10/10 files found after fix vs 0/10 before.
  - **Affects**: Kubernetes deployments where scheduled uploads were running but not actually uploading any files to the knowledge base.

### 📝 Notes

This is a critical bug fix for production deployments. If you've been running scheduled scrapes but noticed your OpenWebUI knowledge base wasn't updating, this release fixes that issue.

**How it was failing (before 1.0.6):**
1. Scheduler runs scrape successfully ✅
2. Shows "30 files to upload" in logs ✅
3. Tries to find files using wrong path (without `content/` prefix) ❌
4. All files skipped: "File not found" errors ❌
5. Knowledge base stays empty ❌

**How it works now (1.0.6):**
1. Scheduler runs scrape successfully ✅
2. Shows "30 files to upload" in logs ✅
3. Finds files using correct path (with `content/` prefix) ✅
4. Uploads all files successfully ✅
5. Knowledge base populated correctly ✅

## [1.0.5] - 2026-02-18

### 🔒 Security

- **System Library Updates**: Added `apt-get upgrade` to Docker build process to address critical base image vulnerabilities:

### � Bug Fixes

- **Upload Validation**: Fixed a critical bug where uploads would silently fail when knowledge base ID was stale (deleted or no longer exists in OpenWebUI).
  - Added automatic knowledge base validation before upload operations
  - Application now detects when a knowledge_id doesn't exist (400 error)
  - Automatically creates a new knowledge base instead of failing silently
  - Clear warning messages explain when and why a new KB was created
  - Prevents false success logs when upload actually failed
  - Affects both incremental and full upload methods

### 📝 Notes

This release includes security patches for the Docker base image and fixes a silent failure mode discovered in production.

**Upload Fix:** When a knowledge base was deleted from OpenWebUI (or OpenWebUI was reset), the scraper would continue attempting uploads to the non-existent KB, receiving 400 errors, but logging "✓ Upload complete!" - giving false success indicators.

**How it worked before (buggy):**
1. Pod scrapes successfully ✅
2. Attempts upload to stale knowledge_id (doesn't exist)
3. Gets 400 error from OpenWebUI ❌
4. Logs "✓ Upload complete!" despite failure ❌
5. No knowledge base in OpenWebUI ❌

**How it works now (fixed):**
1. Pod scrapes successfully ✅
2. Validates knowledge_id exists before upload ✅
3. If not found (400), warns user and creates new KB ✅
4. Uploads successfully to new KB ✅
5. Knowledge base populated correctly ✅

## [1.0.4] - 2026-02-18

### 🐛 Bug Fixes

- **Scheduler Initialization**: Fixed scheduler startup sequence where job loading was happening before scheduler initialization, causing jobs to not be registered properly.
  - Moved `load_schedules()` call to after scheduler initialization
  - Ensures all scheduled jobs are properly registered on startup
  - Prevents race condition in scheduler daemon

### 📝 Notes

This is a minor bug fix discovered during production deployment testing. The fix ensures scheduled scrapes start correctly on daemon startup.

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
