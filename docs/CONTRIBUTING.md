# Contributing to web-to-openwebui

Thank you for contributing to web-to-openwebui. This guide covers environment setup, codebase structure, and contribution workflows.

## Table of Contents

- [Getting Started](#getting-started)
- [Virtual Environment](#virtual-environment)
- [Project Structure](#project-structure)
- [Running Tests](#running-tests)
- [Code Quality Tools](#code-quality-tools)
- [Development Workflow](#development-workflow)
- [CI/CD Pipeline](#cicd-pipeline)
- [Submitting Changes](#submitting-changes)
- [Testing Guidelines](#testing-guidelines)
- [Docker Development](#docker-development)
- [Style Guidelines](#style-guidelines)
- [Getting Help](#getting-help)

---

## Getting Started

### Prerequisites

- **Python 3.11 or higher**
- Git
- Docker (optional, for container testing)
- Ubuntu/Debian: `sudo apt install python3.11-venv python3.11-dev`

### Clone Repository

```bash
git clone https://github.com/jhomen368/web-to-openwebui.git
cd web-to-openwebui
```

### Create Virtual Environment

```bash
# Create virtual environment
python3.11 -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
venv\Scripts\activate
```

**Verify activation:**
```bash
which python3  # Should show: /path/to/venv/bin/python3
python3 --version
```

### Install Dependencies

```bash
# Upgrade pip
pip install --upgrade pip

# Install runtime dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt

# Install Playwright browser
playwright install chromium
```

### Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit with your OpenWebUI credentials (required for upload testing)
nano .env
```

**Required for testing uploads:**
```env
OPENWEBUI_BASE_URL=https://your-openwebui-instance.com
OPENWEBUI_API_KEY=sk-your-key-here
```

### Verify Installation

```bash
# All these should work without errors
./venv/bin/python -m webowui --help
./venv/bin/python -m webowui sites
./venv/bin/python -m webowui health

# If installed with pip install -e .
webowui --help
webowui sites
```

---

## Virtual Environment

### Correct Usage

```bash
# Linux/Mac - Always do this first
source venv/bin/activate
python -m webowui scrape --site mysite
pytest tests/ -v
pip install <package>

# Windows - Always do this first
venv\Scripts\activate
python -m webowui scrape --site mysite
pytest tests/ -v
pip install <package>
```

### Why Virtual Environment is Required

- ✅ Project dependencies isolated from system Python
- ✅ Prevents version conflicts with other projects
- ✅ Reproducible development environments
- ✅ All team members use identical versions
- ✅ Easy cleanup: just delete `venv/` directory

### Checking Virtual Environment Status

```bash
# These should show venv path:
which python
which pip
which pytest

# This should show your venv paths:
echo $VIRTUAL_ENV
```

---

## Project Structure

### Directory Layout

```
web-to-openwebui/
├── .github/
│   └── workflows/                    # CI/CD automation
│       ├── ci-cd.yml                # Main pipeline
│       └── security-scan-scheduled.yml # Daily security scans
│
├── webowui/                         # 🎯 All application code
│   ├── __init__.py
│   ├── __main__.py                  # Enables: python -m webowui
│   ├── cli.py                       # ⭐ CLI interface and commands
│   ├── config.py                    # Configuration loading
│   ├── scheduler.py                 # Scheduling daemon
│   │
│   ├── scraper/                     # Web scraping engine
│   │   ├── crawler.py              # Main crawler with crawl4ai
│   │   ├── content_cleaner.py      # Deprecated (see cleaning_profiles)
│   │   └── cleaning_profiles/      # ⭐ Modular content cleaning
│   │       ├── base.py             # BaseCleaningProfile abstract
│   │       ├── registry.py         # Profile auto-discovery
│   │       └── builtin_profiles/   # Built-in profile templates
│   │
│   ├── storage/                     # Data management
│   │   ├── output_manager.py       # File saving
│   │   ├── metadata_tracker.py     # Scrape history
│   │   ├── current_directory_manager.py # Current/ state
│   │   └── retention_manager.py    # Backup lifecycle
│   │
│   ├── uploader/                    # OpenWebUI integration
│   │   └── openwebui_client.py     # REST API client
│   │
│   ├── utils/                       # Utility functions
│   │   └── reclean.py              # Re-cleaning utility
│   │
│   └── config/                      # Built-in templates
│       └── examples/                # Auto-copied to data/config/
│
├── tests/                           # 🧪 Test suite (70%+ coverage required)
│   ├── __init__.py
│   ├── conftest.py                 # Pytest configuration & fixtures
│   ├── README.md                    # Test documentation
│   │
│   ├── unit/                        # Unit tests (isolated, fast)
│   │   ├── test_config.py
│   │   ├── test_crawler.py
│   │   ├── test_cleaning_profiles.py
│   │   ├── test_output_manager.py
│   │   ├── test_metadata_tracker.py
│   │   ├── test_current_directory_manager.py
│   │   └── test_retention_manager.py
│   │
│   ├── fixtures/                    # Test data fixtures
│   │   ├── __init__.py
│   │   ├── sample_configs.py        # Example configurations
│   │   └── sample_content.py        # Example content
│   │
│   ├── mocks/                       # Mock objects
│   │   ├── __init__.py
│   │   └── openwebui_mock.py        # Mocked OpenWebUI API
│   │
│   ├── utils/                       # Test utilities
│   │   ├── __init__.py
│   │   └── helpers.py               # Helper functions
│   │
│   ├── test_disaster_recovery.py    # Integration test
│   └── test_deletion_behavior.py    # API behavior test
│
├── data/                            # Runtime data (gitignored)
│   ├── config/sites/               # User site configurations
│   ├── config/profiles/            # User cleaning profiles
│   ├── outputs/                    # Scraped content
│   └── logs/                       # Application logs
│
├── docs/                            # Documentation
│   └── CONTRIBUTING.md             # This file
│
├── scripts/                         # Helper scripts
│   ├── run-tests.sh                # Run test suite
│   └── verify-ci-locally.sh        # Verify CI locally
│
├── .dockerignore
├── .env.example
├── .gitignore
├── .pre-commit-config.yaml         # Pre-commit hooks
├── docker-compose.yml              # Production
├── docker-compose.dev.yml          # Development
├── Dockerfile
├── Makefile                        # Development commands
├── pyproject.toml                  # Tool configuration
├── pytest.ini                      # Pytest settings
├── requirements.txt                # Runtime dependencies
├── requirements-dev.txt            # Dev dependencies
└── README.md                       # User documentation
```

### Project Documentation

- **[`README.md`](../README.md)**: Overview and quick start
- **[`docs/CONTRIBUTING.md`](CONTRIBUTING.md)**: Development guide
- **[`webowui/config/examples/README.md`](../webowui/config/examples/README.md)**: Configuration reference
- **[`webowui/scraper/cleaning_profiles/builtin_profiles/README.md`](../webowui/scraper/cleaning_profiles/builtin_profiles/README.md)**: Cleaning profiles reference

### Key Modules Explained

**[`webowui/cli.py`](../webowui/cli.py)** - Entry point for all CLI commands
- Contains Click commands for user interactions
- Routes to appropriate modules based on command
- Handles argument parsing and error display

**[`webowui/config.py`](../webowui/config.py)** - Configuration management
- Load site YAML files
- Validate configuration
- Provide config to all other modules
- **Templates:** [`webowui/config/examples/README.md`](../webowui/config/examples/README.md)

**[`webowui/scraper/crawler.py`](../webowui/scraper/crawler.py)** - Main scraping logic
- Uses **crawl4ai's deep crawling system** (BFS, DFS, BestFirst)
- Implements two-stage content filtering (HTML → Markdown → Profile)
- Handles rate limiting and result conversion

### Crawling System

The scraper uses **crawl4ai's deep crawling system** with three strategies:

- **BFS (Breadth-First):** Explores level-by-level (default, recommended)
- **DFS (Depth-First):** Explores branch-by-branch
- **BestFirst:** Keyword-based prioritization

**Implementation:** `webowui/scraper/crawler.py`

The `WikiCrawler` class:
1. Creates appropriate deep crawl strategy from config (`_create_deep_crawl_strategy()`)
2. Configures crawl4ai with content filtering (`_create_crawler_config()`)
3. Executes crawl via `AsyncWebCrawler.arun()`
4. Converts results to our `CrawlResult` format (`_convert_result()`)

**Key Design Decision:** We use crawl4ai's proven deep crawling instead of custom queue management. This provides:
- Streaming mode support
- Better content filtering (two-stage: HTML → Markdown)
- Keyword-based prioritization
- Automatic improvements as crawl4ai evolves

### Content Filtering (Two-Stage)

**Stage 1: HTML Filtering (`html_filtering`)**
- **When:** Before markdown conversion
- **Config:** `html_filtering` section
- **Purpose:** Remove generic HTML elements (nav, footer, ads)
- **Capabilities:** Tag removal, external link filtering, block pruning

**Stage 2: Markdown Cleaning (`markdown_cleaning`)**
- **When:** After markdown generation
- **Config:** `markdown_cleaning` section
- **Purpose:** Site-specific pattern removal (wiki markup, templates)
- **Capabilities:** Regex cleaning, structure manipulation via profiles

For detailed documentation on the filtering pipeline and available profiles, see the [Cleaning Profiles Reference](../webowui/scraper/cleaning_profiles/builtin_profiles/README.md).

**[`webowui/storage/output_manager.py`](../webowui/storage/output_manager.py)** - File management
- Saves scraped content to timestamped directories
- Organizes files in nested structure
- Applies cleaning profiles
- Generates metadata

**[`webowui/uploader/openwebui_client.py`](../webowui/uploader/openwebui_client.py)** - API integration
- REST API client for OpenWebUI
- Handles file uploads and knowledge base management
- Implements incremental upload logic
- Tracks upload state

**[`webowui/scraper/cleaning_profiles/`](../webowui/scraper/cleaning_profiles/)** - Content cleaning
- Modular profile system for content transformation
- Auto-discovery from `data/config/profiles/`
- Built-in profiles for MediaWiki, Fandom sites
- User can create custom profiles without code changes
- For a list of available profiles, see the [Cleaning Profiles Reference](../webowui/scraper/cleaning_profiles/builtin_profiles/README.md).

### Creating Cleaning Profiles

You can create custom cleaning profiles to handle site-specific content structures.

1. **Create a new file** in `data/config/profiles/` (e.g., `mysite_profile.py`)

2. **Use this template**:
```python
from webowui.scraper.cleaning_profiles.base import BaseCleaningProfile
from typing import Dict, Any, Optional
import re

class MySiteProfile(BaseCleaningProfile):
    """Describe what this profile cleans."""

    def clean(self, content: str, metadata: Optional[Dict] = None) -> str:
        """Clean content according to your rules."""
        # Your cleaning logic here
        lines = content.split('\n')
        cleaned_lines = []

        for line in lines:
            # Example: Skip lines containing "Advertisement"
            if "Advertisement" in line:
                continue
            cleaned_lines.append(line)

        return '\n'.join(cleaned_lines)

    @classmethod
    def get_config_schema(cls) -> Dict[str, Any]:
        """Define your configuration options."""
        return {
            "type": "object",
            "properties": {
                "remove_ads": {
                    "type": "boolean",
                    "default": True
                },
                "min_line_length": {
                    "type": "number",
                    "default": 10
                }
            }
        }
```

3. **Reference in your site config**:
```yaml
# config/sites/mysite.yaml
markdown_cleaning:
  profile: "mysite"
  config:
    remove_ads: true
    min_line_length: 15
```

4. **Restart or run next scrape** - your profile is automatically discovered!

### Adding New Features

**To add a new CLI command:**
1. Add function to [`webowui/cli.py`](../webowui/cli.py)
2. Use `@click.command()` decorator
3. Add tests to [`tests/unit/test_cli.py`](../tests/unit/)
4. Update README.md with examples

**Current CLI Commands:**
- `check-state` - Check health of local upload state
- `clean` - Remove old scrapes
- `daemon` - Run scheduler daemon
- `diff` - Compare two scrapes
- `health` - Enhanced healthcheck
- `list` - List all scrapes
- `rebuild-current` - Rebuild current/ directory
- `rebuild-state` - Rebuild state from OpenWebUI
- `reclean` - Re-clean scraped content
- `rollback` - Rollback to previous backup
- `schedules` - List configured schedules
- `scrape` - Scrape web content
- `show-current` - Show current directory status
- `sites` - List configured sites
- `sync` - Reconcile local/remote state
- `upload` - Upload content to OpenWebUI
- `validate` - Validate configuration

> **Note:** Run `python -m webowui --help` for the most up-to-date list of commands and options.

**To add new scraping capability:**
1. Modify [`webowui/scraper/crawler.py`](../webowui/scraper/crawler.py)
2. Update [`webowui/config.py`](../webowui/config.py) for new options
3. Add tests in [`tests/unit/`](../tests/unit/)
4. Add integration test for end-to-end verification

---

## Running Tests

### Test Organization

**70% minimum coverage required** for all changes.

**Test directory structure:**
- **`tests/unit/`** - Fast unit tests (isolated, no I/O)
- **`tests/fixtures/`** - Reusable test data and configurations
- **`tests/mocks/`** - Mock external services (OpenWebUI API)
- **`tests/utils/`** - Test helper utilities
- **`tests/test_*.py`** - Integration and full workflow tests

### Quick Test Commands

```bash
# Run all tests
pytest tests/ -v

# Run with coverage report
pytest tests/ -v --cov=webowui --cov-report=html

# Run specific test file
pytest tests/unit/test_config.py -v

# Run specific test
pytest tests/unit/test_config.py::test_load_site_config -v

# Run with detailed output and print statements
pytest tests/ -v -s

# Run only failing tests (from last run)
pytest tests/ --lf

# Run tests matching pattern
pytest tests/ -k "test_clean" -v
```

### Viewing Coverage Reports

```bash
# Generate HTML coverage report
pytest tests/ --cov=webowui --cov-report=html

# Open in browser
open htmlcov/index.html  # Mac
xdg-open htmlcov/index.html  # Linux
start htmlcov/index.html  # Windows
```

**Coverage requirements:**
- Minimum: 70% overall
- Critical modules (uploader, storage): 80%+
- Goal: 85%+ for future updates

### Test Organization Details

**[`tests/unit/`](../tests/unit/)** - Fast unit tests (no I/O, no external services)
```python
# tests/unit/test_config.py
def test_load_site_config():
    """Test site configuration loading."""
    config = load_config(sample_config_dict)
    assert config.site.name == "test"

def test_validate_config_schema():
    """Test configuration validation."""
    with pytest.raises(ValueError):
        load_config(invalid_config)
```

**[`tests/fixtures/`](../tests/fixtures/)** - Reusable test data
- [`sample_configs.py`](../tests/fixtures/sample_configs.py) - Example configurations
- [`sample_content.py`](../tests/fixtures/sample_content.py) - Example content
- Access in tests via pytest fixtures

**[`tests/mocks/`](../tests/mocks/)** - Mock external services
- [`openwebui_mock.py`](../tests/mocks/openwebui_mock.py) - Mocked OpenWebUI API
- Allows testing upload logic without real instance
- Used in upload tests

**[`tests/utils/`](../tests/utils/)** - Test helper utilities
- [`helpers.py`](../tests/utils/helpers.py) - Shared test functions
- Reduce duplication across test files

**Integration tests:**
- [`test_disaster_recovery.py`](../tests/test_disaster_recovery.py) - Full workflow
- [`test_deletion_behavior.py`](../tests/test_deletion_behavior.py) - API behavior

### Writing Tests

```python
# tests/unit/test_feature.py
import pytest
from webowui.module import function_to_test


class TestFeature:
    """Group related tests in a class."""

    def test_basic_functionality(self):
        """Test basic behavior."""
        result = function_to_test(input_data)
        assert result == expected_output

    def test_handles_invalid_input(self):
        """Test error handling."""
        with pytest.raises(ValueError):
            function_to_test(invalid_input)

    @pytest.mark.asyncio
    async def test_async_function(self):
        """Test async function."""
        result = await async_function()
        assert result is not None


# Fixture example
@pytest.fixture
def sample_config():
    """Provide sample config to tests."""
    return {
        "site": {"name": "test", "base_url": "https://example.com"},
        "strategy": {"type": "recursive", "max_depth": 1}
    }


def test_with_fixture(sample_config):
    """Use fixture in test."""
    config = parse_config(sample_config)
    assert config.site.name == "test"
```

**Test file naming:**
- Unit tests: `test_<module>.py` in `tests/unit/`
- Pattern: Match source file names
- Example: `webowui/config.py` → `tests/unit/test_config.py`

**Test function naming:**
- Pattern: `test_<what_is_being_tested>`
- Example: `test_load_site_config_validates_schema()`
- Descriptive names that explain the test

### Pytest Fixtures (conftest.py)

**Common fixtures:**

```python
# tests/conftest.py
@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary directory for output testing."""
    return tmp_path / "outputs"

@pytest.fixture
def mock_openwebui():
    """Mock OpenWebUI API client."""
    from tests.mocks.openwebui_mock import MockOpenWebUIClient
    return MockOpenWebUIClient()

@pytest.fixture
def sample_site_config():
    """Provide valid site configuration."""
    return {
        "site": {"name": "test", "base_url": "https://example.com"},
        "strategy": {"type": "recursive", "max_depth": 1},
        "cleaning": {"profile": "none"}
    }
```

**Using fixtures in tests:**

```python
def test_save_files(temp_output_dir):
    """Test file saving."""
    manager = OutputManager(temp_output_dir)
    manager.save_page(...)
    assert (temp_output_dir / "file.md").exists()

@pytest.mark.asyncio
async def test_upload(mock_openwebui):
    """Test upload with mocked API."""
    result = await upload_to_knowledge(mock_openwebui)
    assert result.success is True

def test_config_loading(sample_site_config):
    """Test configuration loading."""
    config = load_config(sample_site_config)
    assert config.site.name == "test"
```

### Manual Testing

**Test scraping:**
```bash
# Use test site with low depth
./venv/bin/python -m webowui scrape --site simple_test

# Verify output
./venv/bin/python -m webowui list --site simple_test
ls -la data/outputs/simple_test/
```

**Test upload (requires OpenWebUI):**
```bash
# Upload to test knowledge base
./venv/bin/python -m webowui upload --site simple_test --knowledge-name "Test KB"

# Check state
./venv/bin/python -m webowui check-state --site simple_test
```

**Test cleaning profiles:**
```bash
# Test with different profiles
./venv/bin/python -m webowui scrape --site simple_test --clean mediawiki
./venv/bin/python -m webowui scrape --site simple_test --clean fandomwiki
```

---

## Code Quality Tools

All tools configured in [`pyproject.toml`](../pyproject.toml).

### Quick Commands

```bash
# Show all available commands
make help

# Run all linting checks (CI simulation)
make lint

# Auto-fix issues and format code
make format

# Type checking only
make typecheck

# Run tests
make test

# Build Docker image locally
make docker-build

# Run full CI pipeline locally
make ci
```

### Manual Tool Usage

**Linting with ruff:**
```bash
# Check for issues
./venv/bin/ruff check webowui/

# Auto-fix issues
./venv/bin/ruff check webowui/ --fix

# Check specific file
./venv/bin/ruff check webowui/cli.py
```

**Formatting with black:**
```bash
# Check formatting
./venv/bin/black --check webowui/

# Format code
./venv/bin/black webowui/

# Format specific file
./venv/bin/black webowui/cli.py
```

**Type checking with mypy:**
```bash
# Check types
./venv/bin/mypy webowui/ --ignore-missing-imports

# Check specific file
./venv/bin/mypy webowui/cli.py --ignore-missing-imports

# Strict mode (more checks)
./venv/bin/mypy webowui/ --ignore-missing-imports --strict
```

### Pre-commit Hooks (Optional)

```bash
# Install pre-commit package
pip install pre-commit

# Install git hooks
pre-commit install

# Run manually
pre-commit run --all-files
```

Project includes [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) with:
- ruff linting and formatting
- mypy type checking
- Security scanning (bandit)
- Markdown linting
- YAML/JSON/TOML validation

---

## Development Workflow

### Start Development Session

```bash
# 1. Activate virtual environment
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows

# 2. Create feature branch
git checkout -b feature/description

# 3. Make changes and commit
```

### Making Changes

1. **Create feature branch:**
   ```bash
   git checkout -b feature/my-feature
   # or: git checkout -b fix/issue-name
   ```

2. **Write code and tests:**
   - Add tests for new functionality
   - Aim for 70%+ coverage
   - Keep changes focused and small

3. **Run quality checks:**
   ```bash
   make format  # Auto-fix and format
   make lint    # Verify all checks pass
   make test    # Run test suite
   ```

4. **Verify fix:**
   ```bash
   ./venv/bin/python -m webowui validate --site simple_test
   ./venv/bin/python -m webowui scrape --site simple_test
   ```

5. **Commit changes:**
   ```bash
   git add .
   git commit -m "feat(scraper): Add support for sitemap crawling"
   ```

6. **Push to GitHub:**
   ```bash
   git push origin feature/my-feature
   ```

7. **Create Pull Request**

### Commit Message Convention

Follow Conventional Commits format:

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

**Types:**
- `feat` - New feature
- `fix` - Bug fix
- `docs` - Documentation changes
- `style` - Code style (formatting)
- `refactor` - Code refactoring
- `test` - Test changes
- `chore` - Build/tooling changes
- `perf` - Performance improvement

**Examples:**
```
feat(scraper): Add sitemap-based crawling support
fix(uploader): Handle 404 errors during incremental upload
docs(contributing): Update development guide
refactor(storage): Simplify RetentionManager logic
test(profiles): Add unit tests for MediaWiki profile
perf(crawler): Improve concurrent request handling
```

### Branch Naming

- `feature/add-sitemap-support`
- `fix/upload-404-handling`
- `docs/docker-guide`
- `refactor/storage-layer`
- `test/add-profile-tests`

---

## CI/CD Pipeline

For detailed information about the CI/CD pipeline, including workflow architecture, optimization strategies, and security scanning details, see:

**📖 [GitHub Actions Workflows Documentation](../.github/workflows/README.md)**

**Quick Summary:**
- **Pull Requests:** Lint, test, build (no security scan for speed)
- **Push to Main:** All checks + security scan (blocks on CRITICAL only)
- **Git Tags:** Multi-arch build, publish to GHCR, create release

### Replicate CI Locally

```bash
# Run same checks as CI
make lint
make test
make docker-build

# Full CI simulation
make ci
```

### If CI Fails

1. **Check CI logs** in GitHub Actions tab
2. **Fix locally:**
   ```bash
   make format
   make lint
   make test
   ```
3. **Push fixes:**
   ```bash
   git add .
   git commit -am "fix: Address CI feedback"
   git push
   ```

---

## Submitting Changes

### Before Opening PR

**Checklist:**
- [ ] Code quality checks pass: `make lint`
- [ ] Tests pass: `make test`
- [ ] Coverage: 70%+ for changes
- [ ] Docker builds: `make docker-build`
- [ ] Documentation updated
- [ ] Commits are clean
- [ ] No breaking changes

### PR Description Template

```markdown
## Description
Brief description of changes and motivation.

## Type of Change
- [ ] New feature
- [ ] Bug fix
- [ ] Documentation
- [ ] Performance improvement
- [ ] Refactoring

## Changes
- Specific change 1
- Specific change 2

## Testing
- [ ] Manual testing
- [ ] Unit tests added
- [ ] Integration tests passed
- [ ] Docker build tested

## Checklist
- [ ] Code follows guidelines
- [ ] Self-review completed
- [ ] Comments added
- [ ] Documentation updated
- [ ] Tests added/updated
- [ ] Coverage maintained (70%+)

## Related Issues
Closes #123
```

### Review Process

1. **Automated checks** run first (CI/CD)
2. **Maintainer review** and feedback
3. **Address feedback** and push updates
4. **Approval** from maintainer
5. **Merge** to main

---

## Testing Guidelines

### When to Write Tests

**Always:**
- New public functions/classes
- Bug fixes (add test that verifies fix)
- API changes
- Business logic changes

**Recommended:**
- Utility functions
- Edge cases
- Error handling

### Test Structure

**Arrange-Act-Assert pattern:**

```python
def test_calculate_checksum():
    # Arrange: Set up test data
    test_file = Path("/tmp/test.txt")
    test_file.write_text("hello world")

    # Act: Execute code being tested
    result = calculate_checksum(test_file)

    # Assert: Verify results
    assert result == "5eb63bbbe01eeed093cb22bb8f5acdc3"


@pytest.mark.asyncio
async def test_upload_files():
    # Arrange
    mock_api = MockOpenWebUIClient()
    files = [Path("file1.md"), Path("file2.md")]

    # Act
    results = await upload_files(mock_api, files)

    # Assert
    assert len(results) == 2
    assert all(r.success for r in results)
```

### Fixtures Best Practices

```python
# ✅ Good: Specific, reusable fixture
@pytest.fixture
def sample_config_dict():
    """Provide minimal valid config."""
    return {
        "site": {
            "name": "test",
            "base_url": "https://example.com",
            "start_urls": ["https://example.com"]
        },
        "strategy": {
            "type": "recursive",
            "max_depth": 1
        }
    }

# ✅ Good: Fixture composition
@pytest.fixture
def loaded_config(sample_config_dict):
    """Provide parsed config object."""
    return load_config(sample_config_dict)

# Use in test
def test_config_validation(loaded_config):
    assert loaded_config.site.name == "test"
```

### Mocking Best Practices

```python
# ✅ Good: Mock only external dependencies
from tests.mocks.openwebui_mock import MockOpenWebUIClient


@pytest.mark.asyncio
async def test_upload_handles_errors():
    # Mock only the API, test real business logic
    api = MockOpenWebUIClient()
    api.set_error("api_error")

    # This tests real retry logic with mocked API
    result = await upload_with_retry(api)
    assert result.success is False
```

### Integration Test Pattern

```python
# tests/test_full_workflow.py
@pytest.mark.asyncio
async def test_scrape_upload_workflow():
    """Test complete scrape-to-upload workflow."""
    # 1. Load config
    config = load_config(test_config_path)

    # 2. Scrape content
    crawler = WikiCrawler(config)
    results = await crawler.crawl()

    # 3. Save locally
    manager = OutputManager(output_dir)
    manager.save_results(results)

    # 4. Upload with mock API
    api = MockOpenWebUIClient()
    upload_result = await upload_to_knowledge(api, output_dir)

    # Assert full workflow
    assert upload_result.success is True
    assert upload_result.files_uploaded > 0
```

---

## Docker Development

### Local Build

```bash
# Build development image
make docker-build
# OR
docker build -t web-to-openwebui:dev .

# Run development container
docker run --rm \
  -v $(pwd)/data:/app/data \
  -e OPENWEBUI_BASE_URL=$OPENWEBUI_BASE_URL \
  -e OPENWEBUI_API_KEY=$OPENWEBUI_API_KEY \
  web-to-openwebui:dev \
  scrape --site simple_test
```

### Development Compose

```bash
# Start both OpenWebUI and scraper
docker compose -f docker-compose.dev.yml up -d

# Execute commands in webowui container
docker compose -f docker-compose.dev.yml exec webowui python -m webowui sites
docker compose -f docker-compose.dev.yml exec webowui python -m webowui scrape --site simple_test

# Rebuild after code changes
docker compose -f docker-compose.dev.yml up --build webowui

# Build without cache (useful when dependencies change)
docker compose -f docker-compose.dev.yml build --no-cache webowui

# Stop the environment
docker compose -f docker-compose.dev.yml down
```

### Multi-architecture Builds

```bash
# Setup buildx (one-time)
docker buildx create --name multiarch --use
docker buildx inspect --bootstrap

# Build for amd64 and arm64
docker buildx build \
  --platform linux/amd64,linux/arm64 \
  -t web-to-openwebui:multi \
  --push \
  .
```

### Dockerfile Linting

```bash
# Install hadolint
sudo apt install hadolint  # Ubuntu/Debian
brew install hadolint      # Mac

# Run linting
hadolint Dockerfile
```

---

## Style Guidelines

### Python Code Style

Follow PEP 8 configured in `black` and `ruff`.

**Line length:** 100 characters

**Imports:**
```python
# Standard library
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional

# Third-party
import aiohttp
from rich.console import Console

# Local
from webowui.config import SiteConfig
from webowui.scraper.crawler import WikiCrawler
```

**Type hints:**
```python
def process_page(url: str, depth: int = 0) -> Optional[Dict[str, str]]:
    """Process a single page."""
    pass

async def upload_files(
    files: List[Path],
    batch_size: int = 10
) -> Dict[str, int]:
    """Upload files in batches."""
    pass
```

**Docstrings:**
```python
def calculate_checksum(file_path: Path) -> str:
    """
    Calculate MD5 checksum of file.

    Args:
        file_path: Path to file

    Returns:
        Hex string of MD5 checksum

    Raises:
        FileNotFoundError: If file doesn't exist
    """
    pass
```

**Error handling:**
```python
try:
    result = await api_call()
except aiohttp.ClientError as e:
    logger.error(f"API error: {e}")
    raise
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    return None
```

### Configuration Files

**YAML formatting:**
```yaml
# Descriptive comment
site:
  name: "example"
  display_name: "Example Site"
  base_url: "https://example.com"

# Another section
strategy:
  type: "recursive"
  max_depth: 3
```

**Indentation:** 2 spaces for YAML

### Documentation Style

**README sections:**
- Use H2 (`##`) for main sections
- Use H3 (`###`) for subsections
- Include code blocks with language tags

**Code documentation:**
- Docstrings for all public functions/classes
- Inline comments for complex logic
- Type hints for clarity

---

## Getting Help

**Before asking:**
1. Check existing documentation
2. Search closed issues
3. Search GitHub discussions

**Where to ask:**
- 💬 [GitHub Discussions](https://github.com/jhomen368/web-to-openwebui/discussions) - Questions
- 🐛 [GitHub Issues](https://github.com/jhomen368/web-to-openwebui/issues) - Bug reports
- 💡 [Feature Requests](https://github.com/jhomen368/web-to-openwebui/discussions/categories/ideas) - New features

**Maintainers:**
- Response time: Usually within 48 hours
- Be patient and respectful
- Provide context and examples

---

## Code of Conduct

**Expected behavior:**
- Be respectful and inclusive
- Welcome newcomers
- Accept constructive criticism
- Focus on what's best for the project

**Unacceptable behavior:**
- Harassment or discriminatory language
- Personal attacks
- Publishing private information
- Trolling or inflammatory comments

**Enforcement:**
Violations may result in temporary or permanent ban.

---

## License

By contributing, you agree your contributions will be licensed under the MIT License.

---

## Thank You! 🙏

Your contributions make this project better. We appreciate your time and effort!

If you find this project useful, please consider:
- ⭐ Starring the repository
- 💖 [Supporting development](https://www.paypal.com/donate?hosted_button_id=PBRD7FXKSKAD2)
- 📢 Sharing with others
