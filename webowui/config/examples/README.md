# Site Configuration Templates

This directory contains example configuration templates for different types of websites. These templates are automatically copied to your `data/config/sites/` directory when you first run the application.

## Quick Start

### Using a Template

1. **List Available Sites:**
   ```bash
   ls data/config/sites/*.yml.example
   ```

2. **Copy Template to Create Your Config:**
   ```bash
   cp data/config/sites/mediawiki.yml.example data/config/sites/mysite.yaml
   ```

3. **Edit Your Configuration:**
   ```bash
   nano data/config/sites/mysite.yaml
   # Or use your favorite editor
   ```

4. **Customize Required Fields:**
   - `site.name` - Internal identifier (lowercase, no spaces)
   - `site.display_name` - Human-readable name
   - `site.base_url` - Base URL of the website
   - `site.start_urls` - Starting pages for scraping
   - `strategy.follow_patterns` - URL patterns to follow

5. **Validate Configuration:**
   ```bash
   webowui validate --site mysite
   ```

6. **Test Scrape:**
   ```bash
   webowui scrape --site mysite
   ```

## Two-Stage Filtering Model

web-to-openwebui uses a two-stage approach to ensure clean, embedding-ready content:

### Stage 1: HTML Pre-filtering (crawl4ai)
**Config:** `content_filtering` section
- Applied **before** markdown conversion
- Removes HTML tags (nav, footer, scripts)

### Stage 2: Markdown Cleaning (Profiles)
**Config:** `cleaning` section
- Applied **after** markdown generation
- Uses site-specific profiles (MediaWiki, Fandom, etc.)
- Removes boilerplate while preserving content
- **Recommendation:** Use this as your primary cleaning method

## Content Processing Pipeline

web-to-openwebui uses a multi-stage pipeline to ensure clean, embedding-ready content:

### Stage 1: HTML Filtering (`html_filtering`)
- **Applied:** Before markdown conversion
- **Purpose:** Remove HTML tags, links, and low-density blocks
- **Key Options:** `excluded_tags`, `min_block_words`, `pruning.enabled`

### Stage 2: Markdown Processing
- **2a: Conversion (`markdown_conversion`)**: Controls HTML → Markdown (selectors, options)
- **2b: Cleaning (`markdown_cleaning`)**: Applies site-specific profiles (MediaWiki, Fandom)
- **Recommendation:** Use profiles as your primary cleaning method

### Stage 3: Result Filtering (`result_filtering`)
- **Applied:** Final check on generated markdown
- **Purpose:** Filter out stubs, redirects, or oversized pages
- **Key Options:** `min_page_length`, `max_page_length`

## Available Templates

### `mediawiki.yml.example`
**Purpose:** Generic template for MediaWiki-based sites

**Best For:**
- Wikipedia and Wikimedia projects
- Fandom wikis
- Self-hosted MediaWiki installations
- Miraheze wikis
- Any MediaWiki v1.35+ site

**Features:**
- Comprehensive MediaWiki content cleaning
- Standard exclusion patterns (Special:, User:, Talk:, etc.)
- Optimized for RAG/embedding generation
- Tested with Monster Hunter Wiki and Path of Exile 2 Wiki

**Quick Config:**
```yaml
site:
  name: "mywiki"
  base_url: "https://example.com"
  start_urls: ["https://example.com/wiki/Main_Page"]

crawling:
  strategy: "bfs"
  filters:
    follow_patterns: ["^https://example\\.com/wiki/.*"]
```

### `fandomwiki.yml.example`
**Purpose:** Optimized template for Fandom-hosted wikis

**Best For:**
- Any wiki hosted on fandom.com (formerly Wikia)
- Gaming wikis (Escape from Tarkov, Fallout, etc.)
- TV/Movie wikis (Star Wars, Marvel, etc.)

**Features:**
- Extends MediaWiki cleaning with Fandom-specific logic
- Removes ads, "More Fandom" bars, and community feeds
- Handles Fandom's unique HTML structure
- Tested with Escape from Tarkov Wiki

**Quick Config:**
```yaml
site:
  name: "myfandom"
  base_url: "https://yourwiki.fandom.com"
  start_urls: ["https://yourwiki.fandom.com/wiki/Main_Page"]

markdown_cleaning:
  profile: "fandomwiki"
```

### `maxroll.yml.example`
**Purpose:** Template for Maxroll.gg gaming guides

**Best For:**
- Maxroll build guides
- Maxroll resource pages
- Structured gaming guides

**Features:**
- Preserves guide structure while removing noise
- Removes navigation, social bars, and comments
- Optimized for "bfs" or "selective" crawling
- Tested with Path of Exile 2 Guides

**Quick Config:**
```yaml
site:
  name: "myguide"
  base_url: "https://maxroll.gg"
  start_urls: ["https://maxroll.gg/poe2/category/guides"]

markdown_cleaning:
  profile: "maxroll"
```

### `simple_test.yml.example`
**Purpose:** Minimal example for testing and learning

**Best For:**
- First-time users
- Testing the scraper
- Simple single-page sites
- Quick validation

### `example_site.yml.example`
**Purpose:** Comprehensive reference with all available options

**Best For:**
- Understanding all configuration options
- Advanced use cases
- Custom implementations
- Documentation reference

## File Naming Convention

### Template Files (Tracked in Git)
- **Pattern:** `*.yml.example`
- **Location:** `webowui/config/examples/` (in Docker image)
- **Auto-Copied To:** `data/config/sites/` (on first run)
- **Purpose:** User-facing templates to copy from

### Working Configuration Files (Gitignored)
- **Pattern:** `*.yaml`
- **Location:** `data/config/sites/` (your edits)
- **Tracked:** No (in `.gitignore`)
- **Purpose:** Your actual site configurations

**Why Two Extensions?**
- `.yml.example` = Templates (don't edit directly, copy first)
- `.yaml` = Working configs (your customizations)

## Docker Usage

### Auto-Copy Behavior

When you start the Docker container, templates are automatically copied to `data/config/sites/` if they don't already exist. This happens in `AppConfig.__init__()`.

**First Run:**
```bash
docker compose up -d

# Templates automatically copied to data/config/sites/
# - mediawiki.yml.example
# - simple_test.yml.example
# - example_site.yml.example
# - README.md
```

### Creating Configs in Docker

**Method 1: Copy Inside Container**
```bash
docker compose exec scraper cp /app/data/config/sites/mediawiki.yml.example /app/data/config/sites/mysite.yaml
docker compose exec scraper vi /app/data/config/sites/mysite.yaml
```

**Method 2: Copy from Host (if volume mounted)**
```bash
cp data/config/sites/mediawiki.yml.example data/config/sites/mysite.yaml
nano data/config/sites/mysite.yaml
```

**Method 3: Download from GitHub**
```bash
curl -o data/config/sites/mysite.yaml \
  https://raw.githubusercontent.com/jhomen368/web-to-openwebui/main/webowui/config/examples/mediawiki.yml.example
```

## Configuration Structure

All site configurations follow this basic structure:

```yaml
# 1. Site Information
site:
  name: "internal-id"
  display_name: "Human Name"
  base_url: "https://..."
  start_urls: [...]

# 2. Crawling Strategy
strategy:
  type: "recursive"
  max_depth: 3
  follow_patterns: [...]
  exclude_patterns: [...]

# 3. Content Extraction
extraction:
  content_selector: "body"
  remove_selectors: [...]

# 4. Content Cleaning
markdown_cleaning:
  profile: "mediawiki"
  config: {}

# 5. OpenWebUI Integration
openwebui:
  knowledge_name: "..."
  auto_upload: false

# 6. Backup Retention
retention:
  enabled: true
  keep_backups: 2

# 7. Scheduling
schedule:
  enabled: true
  cron: "0 2 * * *"
```

## Common Patterns

### MediaWiki Sites

**Wikipedia:**
```yaml
base_url: "https://en.wikipedia.org"
follow_patterns: ["^https://en\\.wikipedia\\.org/wiki/.*"]
```

**Fandom:**
```yaml
base_url: "https://yourwiki.fandom.com"
follow_patterns: ["^https://yourwiki\\.fandom\\.com/wiki/.*"]
cleaning:
  profile: "fandomwiki"  # Fandom-specific cleaning
```

**Self-Hosted:**
```yaml
base_url: "https://wiki.company.com"
follow_patterns: ["^https://wiki\\.company\\.com/wiki/.*"]
```

### Common Exclusions

Most MediaWiki sites should exclude:
```yaml
exclude_patterns:
  - ".*Special:.*"      # Special pages
  - ".*User:.*"         # User pages
  - ".*Talk:.*"         # Discussion pages
  - ".*File:.*"         # File pages
  - ".*Template:.*"     # Templates
  - ".*Category:.*"     # Categories
  - ".*action=edit.*"   # Edit pages
  - ".*action=history.*" # History
```

## Testing Strategy

### 1. Start Small
```yaml
strategy:
  max_depth: 1  # Only follow links from start page
```

### 2. Validate First
```bash
webowui validate --site mysite
```

### 3. Test Scrape
```bash
webowui scrape --site mysite
```

### 4. Review Results
```bash
webowui list --site mysite
webowui show-current --site mysite
```

### 5. Increase Depth
```yaml
strategy:
  max_depth: 3  # Once patterns work, increase depth
```

## Troubleshooting

### "No sites configured" Error
**Cause:** Template hasn't been copied yet or wrong directory

**Solution:**
```bash
# Check if templates exist
ls data/config/sites/*.yml.example

# If missing, start container to trigger auto-copy
docker compose up -d

# Or manually copy
cp webowui/config/examples/mediawiki.yml.example data/config/sites/mysite.yaml
```

### "Site configuration not found" Error
**Cause:** Config file not created or wrong extension

**Solution:**
```bash
# Must use .yaml extension for working configs
cp data/config/sites/mediawiki.yml.example data/config/sites/mysite.yaml
#                                                                    ^^^^^ .yaml not .yml.example
```

### Scraper Follows Unwanted Pages
**Cause:** Exclude patterns not specific enough

**Solution:**
```yaml
# Add more specific exclusions
exclude_patterns:
  - ".*Special:.*"
  - ".*YourSpecificPattern.*"  # Add site-specific exclusions
```

### Content Too Noisy
**Cause:** Cleaning profile not aggressive enough

**Solution:**
```yaml
cleaning:
  profile: "mediawiki"
  config:
    remove_infoboxes: true       # Enable all cleaners
    remove_external_links: true
    remove_table_of_contents: true
    # ... etc
```

## Best Practices

1. **Always Start with max_depth: 1** for testing
2. **Validate Before Scraping** (`webowui validate`)
3. **Use Descriptive Site Names** (lowercase, no spaces)
4. **Respect Rate Limits** (1 req/sec for public sites)
5. **Test Cleaning Profile** with small scrape first
6. **Enable Retention** to keep backup history
7. **Use Scheduling** for automatic updates in Docker

## Getting Help

**Command Documentation:**
```bash
webowui --help
webowui scrape --help
```

**Validation:**
```bash
webowui validate --site mysite
```

**GitHub Issues:**
https://github.com/jhomen368/web-to-openwebui/issues

**Project Documentation:**
- Docker Guide: `docs/DOCKER.md`
- Kubernetes Guide: `docs/KUBERNETES.md`
- Contributing: `docs/CONTRIBUTING.md`

## Template Updates

Templates are updated with new releases. To get latest templates:

**Docker Pull:**
```bash
docker compose pull
docker compose up -d
# New templates auto-copied on restart
```

**Manual Download:**
```bash
curl -o data/config/sites/mediawiki.yml.example \
  https://raw.githubusercontent.com/jhomen368/web-to-openwebui/main/webowui/config/examples/mediawiki.yml.example
```

## Contributing Templates

Have a template for a different platform? Contribute it!

1. Create template in `webowui/config/examples/`
2. Use `.yml.example` extension
3. Add comprehensive comments
4. Test with real site
5. Submit pull request

**Template Checklist:**
- [ ] Comprehensive comments explaining options
- [ ] Tested with at least one real site
- [ ] Follows naming convention (*.yml.example)
- [ ] Includes common pitfalls and solutions
- [ ] Documents compatible platforms/versions
