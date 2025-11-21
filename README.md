# web-to-openwebui

> Flexible web content scraping for OpenWebUI Knowledge databases

[![Python](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Status](https://img.shields.io/badge/status-production%20ready-brightgreen.svg)]()
[![CI/CD](https://github.com/jhomen368/web-to-openwebui/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/jhomen368/web-to-openwebui/actions/workflows/ci-cd.yml)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg?logo=docker)](https://github.com/jhomen368/web-to-openwebui/pkgs/container/web-to-openwebui)
[![Security](https://github.com/jhomen368/web-to-openwebui/actions/workflows/security-scan-scheduled.yml/badge.svg)](https://github.com/jhomen368/web-to-openwebui/actions/workflows/security-scan-scheduled.yml)

Automatically scrape web content and upload to [OpenWebUI](https://github.com/open-webui/open-webui) for RAG-powered AI assistants. No code changes needed—just configure YAML files and let it run.

## 💖 Support This Project

If you find this tool useful, please consider supporting its development:

[![Donate with PayPal](https://img.shields.io/badge/Donate-PayPal-blue.svg?logo=paypal)](https://www.paypal.com/donate?hosted_button_id=PBRD7FXKSKAD2)

---

## ✨ Key Features

✅ **No Code Required** - Configure sites with simple YAML files  
✅ **Incremental Updates** - Only upload changed content  
✅ **Smart Content Cleaning** - Removes navigation/footers for optimal embeddings  
✅ **Multiple Sites** - Manage dozens of webowuis in one container  
✅ **Automatic Scheduling** - Built-in cron-based task execution  
✅ **Disaster Recovery** - Auto-rebuild from OpenWebUI after data loss  
✅ **Modular Profiles** - Custom cleaning profiles without code changes  
✅ **Docker Ready** - Everything pre-installed and configured  

---

## 🚀 Quick Start (5 minutes)

The fastest way to get scraping: Docker Compose with minimal setup.

### Prerequisites

- Docker and Docker Compose installed
- OpenWebUI instance with API access

### 1. Create Directory and Files

```bash
mkdir webowui && cd webowui
```

### 2. Create `docker-compose.yml`

```bash
cat > docker-compose.yml << 'EOF'
services:
  webowui:
    image: ghcr.io/jhomen368/web-to-openwebui:latest
    container_name: web-to-openwebui

    environment:
      - OPENWEBUI_BASE_URL=${OPENWEBUI_BASE_URL}
      - OPENWEBUI_API_KEY=${OPENWEBUI_API_KEY}
      - LOG_LEVEL=${LOG_LEVEL:-INFO}
      - TZ=${TZ:-America/Los_Angeles}

    volumes:
      - ./data:/app/data

    restart: unless-stopped
EOF
```

### 3. Create `.env` File

```bash
cat > .env << 'EOF'
OPENWEBUI_BASE_URL=https://your-openwebui.com
OPENWEBUI_API_KEY=sk-your-api-key-here
LOG_LEVEL=INFO
TZ=America/Los_Angeles
EOF

nano .env  # Edit with your actual credentials
```

**How to get your API key:**
1. Log into your OpenWebUI instance
2. Go to Settings → Account
3. Generate or copy your API key

### 4. Create a Site Configuration

```bash
mkdir -p data/config/sites

cat > data/config/sites/mysite.yaml << 'EOF'
site:
  name: "mysite"
  display_name: "My Website"
  base_url: "https://example.com"
  start_urls:
    - "https://example.com/docs/"

crawling:
  strategy: "bfs"
  max_depth: 3
  filters:
    follow_patterns:
      - ".*/docs/.*"

cleaning:
  profile: "none"

openwebui:
  knowledge_name: "My Website Knowledge"
  auto_upload: true

schedule:
  enabled: true
  type: "cron"
  cron: "0 2 * * *"          # Daily at 2 AM
  timezone: "America/Los_Angeles"
EOF

nano data/config/sites/mysite.yaml  # Edit with your site details
```

See examples in `data/config/sites/` for MediaWiki and Fandom sites.

### 5. Start the Container

```bash
docker compose up -d
docker compose logs -f          # View logs (Ctrl+C to stop)
docker compose ps               # Check status
```

Done! The container is running. It will automatically scrape and upload according to the schedule, or you can trigger them manually (see next section).

---

## Crawling Configuration

web-to-openwebui uses crawl4ai for deep crawling with three built-in strategies:

### Available Strategies

**1. BFS (Breadth-First Search)** - Recommended for 90% of sites
- Explores all pages at each depth level before going deeper
- Comprehensive coverage, discovers everything systematically
- Best for wikis, documentation sites, blogs

```yaml
crawling:
  strategy: "bfs"        # breadth-first (default)
  max_depth: 2           # how deep to crawl
  max_pages: 100         # optional limit
```

**2. DFS (Depth-First Search)** - For hierarchical exploration
- Follows one branch to its end before exploring others
- Good for deeply nested content structures

```yaml
crawling:
  strategy: "dfs"
  max_depth: 3
```

**3. BestFirst** - Intelligent keyword-based prioritization
- Crawls most relevant pages first based on keywords
- Perfect for targeted research or large sites

```yaml
crawling:
  strategy: "best_first"
  max_depth: 3
  max_pages: 50
  keywords: ["machine learning", "tutorial"]
  keyword_weight: 0.7
```

### Strategy Comparison

| Use Case | Strategy | Max Depth | Notes |
|----------|----------|-----------|-------|
| Wiki scraping | `bfs` | 2-3 | Comprehensive coverage |
| Documentation | `bfs` | 2 | Organized structure |
| Large research site | `best_first` | 3 | With keywords |
| Deep hierarchies | `dfs` | 3-4 | Follow branches |

See [configuration examples](webowui/config/examples/) for complete templates.

---

## 📋 Common Tasks

### Run Your First Scrape (Manual)

```bash
docker compose exec webowui python -m webowui scrape --site mysite
docker compose exec webowui python -m webowui list --site mysite
```

### View Scheduled Jobs

```bash
docker compose exec webowui python -m webowui schedules
```

### Upload to OpenWebUI

```bash
# Upload latest scrape
docker compose exec webowui python -m webowui upload --site mysite

# Or enable auto_upload in your site config
# openwebui:
#   auto_upload: true
```

### Add Another Site

```bash
cp data/config/sites/mediawiki.yml.example data/config/sites/newsite.yaml
nano data/config/sites/newsite.yaml
docker compose exec webowui python -m webowui validate --site newsite
docker compose exec webowui python -m webowui scrape --site newsite
```

### Stop or Update

```bash
docker compose down                          # Stop container
docker compose pull && docker compose up -d  # Update and restart
docker compose exec webowui python -m webowui cleanup --site mysite --dry-run
docker compose exec webowui python -m webowui cleanup --site mysite
```

---

## 🧠 Understanding Content Cleaning

Raw web content contains navigation menus, footers, and other UI elements that pollute LLM embeddings. web-to-openwebui removes this noise automatically using modular cleaning profiles.

The system includes built-in profiles for some  platforms and supports custom profiles.

👉 **See available profiles:** [`webowui/scraper/cleaning_profiles/builtin_profiles/README.md`](webowui/scraper/cleaning_profiles/builtin_profiles/README.md)

### Apply a Profile

```yaml
cleaning:
  profile: "mediawiki"
  config:
    filter_dead_links: true
    remove_citations: true
    remove_categories: true
```

### Create a Custom Profile

Advanced users can create custom cleaning profiles for site-specific needs. Custom profiles are automatically discovered and require no code changes to the application.

**For developers:** See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md#creating-cleaning-profiles) for the full guide on creating custom profiles.

---

## 📊 Understanding Incremental Updates

web-to-openwebui tracks what changed between scrapes and only uploads new/modified files.

**How it works:**
1. Scrape content using checksums to detect changes
2. Compare with previous scrape
3. Upload only: new files, updated files, deleted files
4. Reuse existing file IDs (saves API quota)

**Enable with:**
```bash
docker compose exec webowui python -m webowui upload --site mysite --incremental
```

Or use `--full` to upload everything:
```bash
docker compose exec webowui python -m webowui upload --site mysite --full
```

---

## 💾 Understanding Backup Management

web-to-openwebui keeps timestamped backups of each scrape. Older scrapes can be cleaned up automatically.

**How it works:**
1. Each scrape creates a timestamped directory
2. A `current/` directory always points to the latest version
3. Old scrapes are deleted based on retention policy
4. Can rollback to any previous timestamp

**Configure in your site YAML:**

```yaml
retention:
  enabled: true           # Enable automatic cleanup
  keep_backups: 2         # Keep last 2 backups
  auto_cleanup: true      # Run cleanup after each scrape
```

**Manual cleanup:**
```bash
docker compose exec webowui python -m webowui cleanup --site mysite --dry-run
docker compose exec webowui python -m webowui cleanup --site mysite
```

---

## 🎯 CLI Command Reference

All commands below assume you are running via Docker Compose.

**Syntax:**
```bash
docker compose exec webowui python -m webowui <command> [options]
```

### Scraping & Uploading

```bash
webowui scrape --site <name>              # Scrape one site
webowui scrape --all                      # Scrape all sites
webowui upload --site <name>              # Upload latest scrape
webowui upload --site <name> --incremental
webowui upload --site <name> --full
```

### Management

```bash
webowui list                      # List all scrapes
webowui list --site <name>       # List site scrapes
webowui sites                    # List configured sites
webowui validate --site <name>   # Validate configuration
webowui schedules                # Show scheduled jobs
```

### Inspection

```bash
webowui diff --site <name> --old <ts> --new <ts>
webowui show-current --site <name>
webowui check-state --site <name>        # Check upload state health
```

### State Management & Recovery

```bash
webowui rebuild-current --site <name>    # Rebuild current/ from latest scrape
webowui rebuild-state --site <name>      # Rebuild upload_status.json from OpenWebUI
webowui sync --site <name>               # Reconcile local vs remote state
webowui sync --site <name> --fix         # Auto-fix discrepancies
webowui verify-current --site <name>     # Verify current/ directory integrity
```

### Backup & Retention

```bash
webowui cleanup --site <name>            # Clean up old backups
webowui cleanup --site <name> --dry-run  # Preview what would be deleted
webowui rollback --site <name>           # Rollback to most recent backup
webowui rollback --site <name> --list    # List available backups
```

**For complete details:**
```bash
docker compose exec webowui python -m webowui --help
docker compose exec webowui python -m webowui <command> --help
```

**Top Commands:**

```bash
webowui scrape --site <name>              # Scrape a specific site
webowui upload --site <name>              # Upload scraped content
webowui list --site <name>                # List available scrapes
webowui validate --site <name>            # Validate configuration
webowui health                            # Check system health
```

For a complete list of commands and options, run:
```bash
docker compose exec webowui python -m webowui --help
```

---

## 📖 Example Workflows

The project includes ready-to-use configuration templates for common scenarios.

1. **Copy a template:**
   ```bash
   cp data/config/sites/mediawiki.yml.example data/config/sites/mywiki.yaml
   ```

2. **Edit configuration:**
   ```bash
   nano data/config/sites/mywiki.yaml
   ```

3. **Run:**
   ```bash
   docker compose exec webowui python -m webowui scrape --site mywiki
   ```

👉 **See all templates:** [`webowui/config/examples/README.md`](webowui/config/examples/README.md)

---

## 🛠️ Troubleshooting

### Container won't start

```bash
docker compose logs -f
docker --version
docker compose build --no-cache && docker compose up -d
```

### API connection failed

```bash
cat .env
curl -H "Authorization: Bearer $OPENWEBUI_API_KEY" \
     $OPENWEBUI_BASE_URL/api/v1/knowledge
```

### Scrape producing empty results

```bash
docker compose exec webowui python -m webowui validate --site mysite
docker compose logs -f webowui
# Edit config: increase max_depth, adjust follow_patterns
docker compose exec webowui python -m webowui list --site mysite
```

### Upload incomplete

```bash
docker compose exec webowui python -m webowui check-state --site mysite
docker compose exec webowui python -m webowui sync --site mysite --fix
docker compose exec webowui python -m webowui upload --site mysite
```

---

## 📚 Configuration Reference

Site configurations use YAML files in `data/config/sites/`.

👉 **Full Configuration Guide:** [`webowui/config/examples/README.md`](webowui/config/examples/README.md)

**Quick Reference:**
- `site.name` - Unique identifier
- `site.base_url` - Root URL
- `crawling.strategy` - `bfs`, `dfs`, or `best_first`
- `cleaning.profile` - Cleaning profile to use
- `openwebui.auto_upload` - Enable auto-upload

---

## 🧑‍💻 For Developers

This project is built with Python and includes a comprehensive test suite. To set up development or contribute:

👉 **See:** [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md)

---

## 📄 License

MIT License - See LICENSE file for details

---

## 🆘 Getting Help

**Stuck?**
- Review logs: `docker compose logs -f`
- Validate config: `docker compose exec webowui python -m webowui validate --site <name>`
- Check health: `docker compose exec webowui python -m webowui health`

**Have questions?**
- 🐛 [Report Issues](https://github.com/jhomen368/web-to-openwebui/issues)
- 💡 [Feature Requests](https://github.com/jhomen368/web-to-openwebui/discussions)
