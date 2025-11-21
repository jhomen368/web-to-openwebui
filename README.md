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

The fastest way to get scraping: Docker Compose with zero setup.

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

    healthcheck:
      test: ["CMD", "python", "-m", "webowui", "health"]
      interval: 60s
      timeout: 10s
      retries: 3
      start_period: 30s
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

strategy:
  type: "recursive"
  max_depth: 3
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
docker compose exec webowui /bin/bash        # Access shell
```

---

## 🧠 Understanding Content Cleaning

Raw web content contains navigation menus, footers, and other UI elements that pollute LLM embeddings. web-to-openwebui removes this noise automatically.

### Built-in Profiles

**`none`** (default) - No cleaning, pass-through raw content

**`mediawiki`** - For Wikipedia, wiki.js, and MediaWiki-based sites
- Removes: navigation, footers, categories, citations, edit links
- Configurable dead link filtering

**`fandomwiki`** - For Fandom wikis (gaming, TV, movies, etc.)
- Extends MediaWiki profile
- Additionally removes: Fandom ads, cross-promotions, community sections

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

---

## 📖 Example Workflows

### Workflow 1: MediaWiki Site

```bash
cp data/config/sites/mediawiki.yml.example data/config/sites/mywiki.yaml
nano data/config/sites/mywiki.yaml          # Set base_url, start_urls
docker compose exec webowui python -m webowui validate --site mywiki
docker compose exec webowui python -m webowui scrape --site mywiki
docker compose exec webowui python -m webowui upload --site mywiki
```

### Workflow 2: Custom Website

```bash
cat > data/config/sites/custom.yaml << 'EOF'
site:
  name: "custom"
  display_name: "My Custom Site"
  base_url: "https://example.com"
  start_urls:
    - "https://example.com/docs"

strategy:
  type: "recursive"
  max_depth: 2
  follow_patterns:
    - ".*/docs/.*"
  exclude_patterns:
    - ".*/api/.*"
    - ".*/admin/.*"

cleaning:
  profile: "none"

openwebui:
  knowledge_name: "Example Documentation"
  auto_upload: true

schedule:
  enabled: true
  type: "cron"
  cron: "0 2 * * *"
  timezone: "America/Los_Angeles"
EOF

docker compose exec webowui python -m webowui validate --site custom
docker compose exec webowui python -m webowui scrape --site custom
```

### Workflow 3: Multi-Site Setup

```bash
cp data/config/sites/mediawiki.yml.example data/config/sites/wiki1.yaml
cp data/config/sites/mediawiki.yml.example data/config/sites/wiki2.yaml
cp data/config/sites/mediawiki.yml.example data/config/sites/wiki3.yaml

# Edit each with different URLs and schedules

docker compose exec webowui python -m webowui scrape --all
docker compose exec webowui python -m webowui upload --all
```

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

**Key fields:**
- `site.name` - Unique identifier
- `site.base_url` - Root URL of website
- `site.start_urls` - Where to start scraping
- `strategy.type` - `recursive` (follow links) or `selective` (patterns only)
- `strategy.max_depth` - How deep to follow links
- `follow_patterns` - URL regex patterns to include
- `exclude_patterns` - URL regex patterns to skip
- `cleaning.profile` - `none`, `mediawiki`, or `fandomwiki`
- `openwebui.knowledge_name` - Name in OpenWebUI
- `openwebui.auto_upload` - Auto-upload after scraping (true/false)
- `schedule.cron` - Cron expression for automated runs

**Example templates:**
- `data/config/sites/simple_test.yml.example` - Minimal example
- `data/config/sites/mediawiki.yml.example` - MediaWiki sites
- `data/config/sites/example_site.yml.example` - Complete reference

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

**Want to help?**
- 💖 [Support Development](https://www.paypal.com/donate?hosted_button_id=PBRD7FXKSKAD2)
- 🔧 See [`docs/CONTRIBUTING.md`](docs/CONTRIBUTING.md) to contribute code
