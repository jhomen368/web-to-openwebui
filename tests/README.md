# Testing Guide

This directory contains the comprehensive test suite for web-to-openwebui with 229+ unit tests enforcing 70% minimum code coverage.

## Quick Start

Before committing, verify CI/CD checks locally:

```bash
# Run full CI/CD verification (recommended before committing)
./scripts/verify-ci-locally.sh

# Or run tests manually
./scripts/run-tests.sh

# Run with coverage report
./venv/bin/python -m pytest tests/unit/ --cov=webowui --cov-report=html

# View coverage HTML report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
firefox htmlcov/index.html  # Firefox
```

## Test Organization

```
tests/
├── conftest.py              # Shared pytest configuration
├── pytest.ini              # Pytest settings
├── unit/                   # Unit tests (229+ tests)
│   ├── test_config.py
│   ├── test_output_manager.py
│   ├── test_metadata_tracker.py
│   ├── test_current_directory_manager.py
│   ├── test_retention_manager.py
│   ├── test_openwebui_client.py
│   ├── test_crawler.py
│   ├── test_strategies.py
│   └── test_cleaning_profiles.py
├── mocks/                  # Mock implementations
│   └── openwebui_mock.py  # MockOpenWebUIClient for testing
├── fixtures/               # Test data and fixtures
│   ├── sample_configs.py
│   └── sample_content.py
├── utils/                  # Test helpers
│   └── helpers.py
└── test_disaster_recovery.py  # Integration test
```

## Running Tests

### Fast Unit Tests (Default for CI/CD)
```bash
# Run fast unit tests only (excludes slow tests)
./scripts/run-tests.sh

# Same as:
pytest tests/unit/ -m "unit and not slow" -v
```

### All Unit Tests
```bash
pytest tests/unit/ -v
```

### Specific Test File
```bash
pytest tests/unit/test_config.py -v
```

### Tests Matching Pattern
```bash
pytest tests/unit/ -k "config" -v
```

### Test Markers

Tests are organized by markers for filtering:

```bash
# Unit tests only (isolated, fast)
pytest -m unit -v

# Slow tests (>5 seconds)
pytest -m slow -v

# Integration tests
pytest -m integration -v

# Tests requiring OpenWebUI instance
pytest -m requires_openwebui -v

# End-to-end tests
pytest -m e2e -v
```

## Coverage Reports

### Generate HTML Coverage Report
```bash
pytest tests/unit/ --cov=webowui --cov-report=html

# View report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Terminal Coverage Report
```bash
# Show critical missing areas
pytest tests/unit/ --cov=webowui --cov-report=term-missing

# Check if meets minimum (70%)
pytest tests/unit/ --cov=webowui --cov-fail-under=70
```

### CI/CD Coverage Report
```bash
# Generate all report formats (used by CI/CD)
pytest tests/unit/ \
  --cov=webowui \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=xml \
  --cov-fail-under=70
```

## Advanced Test Commands

### Parallel Execution
```bash
# Run with 4 parallel workers (faster)
pytest tests/unit/ -n 4
```

### Detailed Output
```bash
# Very verbose with long tracebacks
pytest tests/unit/ -vv --tb=long

# With print statements visible during test
pytest tests/unit/ -v -s
```

### Debug Mode
```bash
# Drop into Python debugger on failure
pytest tests/unit/ --pdb

# Drop into debugger on first failure
pytest tests/unit/ -x --pdb
```

### Timeout Protection
```bash
# Fail tests taking >10 seconds (prevents hanging)
pytest tests/unit/ --timeout=10
```

### Pytest Watch (Auto-rerun)
```bash
# Requires: pip install pytest-watch
ptw tests/unit/ -- -v
```

## Test Structure

### Unit Test Template

```python
import pytest
from webowui.module import function

def test_function_behavior():
    """Test description - what should happen."""
    result = function(input_data)
    assert result == expected_output

@pytest.mark.asyncio
async def test_async_function():
    """Test async functions with pytest.mark.asyncio."""
    result = await async_function()
    assert result is not None

@pytest.mark.slow
def test_slow_operation():
    """Mark slow tests with @pytest.mark.slow."""
    # Test that takes >5 seconds
    pass

@pytest.mark.requires_openwebui
def test_uses_api_credentials(env_config):
    """Tests needing env vars use pytest fixtures."""
    assert env_config.openwebui_api_key
```

### Test File Naming
- `test_*.py` - Test discovery pattern
- `*_test.py` - Alternative pattern
- Place in `tests/` directory or mirrored subdirectories

### Fixtures

Common fixtures defined in `conftest.py`:

```python
@pytest.fixture
def sample_config():
    """Provides test site configuration."""
    return SiteConfig({"name": "test"})

@pytest.fixture
def temp_output_dir(tmp_path):
    """Temporary directory for test outputs."""
    return tmp_path / "outputs"
```

## CI/CD Integration

Tests run automatically on:
- **Push to main** - Full suite runs
- **Pull Requests** - Full suite runs, must pass to merge
- **Tagged releases** - Full suite + multi-arch builds

**Quality Gate:** Tests must pass AND achieve 70%+ coverage before Docker build proceeds.

**Pipeline Order:**
1. Python Linting (ruff, black, mypy) ← Fails here = no tests run
2. **Unit Tests with Coverage** ← 70% minimum required
3. Docker Build (only if tests pass)
4. Security Scan (only if build succeeds)

## Writing Tests

### Best Practices

**✅ DO:**
- Write descriptive test names
- Test one thing per test
- Use meaningful assertions
- Mock external dependencies
- Use fixtures for setup

**❌ DON'T:**
- Make tests depend on each other
- Use global state
- Make external API calls
- Test implementation details
- Leave hardcoded paths/credentials

### Testing OpenWebUI Integration

Use the mock client to test without real API:

```python
from tests.mocks.openwebui_mock import MockOpenWebUIClient

@pytest.mark.asyncio
async def test_upload_workflow():
    """Test upload without real OpenWebUI."""
    client = MockOpenWebUIClient()

    result = await client.upload_files(files)
    assert result.success
    assert len(result.file_ids) == len(files)
```

## Development Workflow

### Before Committing

1. **Run local verification:**
   ```bash
   ./scripts/verify-ci-locally.sh
   ```

2. **Fix any issues:**
   ```bash
   ./venv/bin/python -m ruff check webowui/ --fix
   ./venv/bin/python -m black webowui/
   ```

3. **Re-verify:**
   ```bash
   ./scripts/verify-ci-locally.sh
   ```

4. **Commit when passing:**
   ```bash
   git add .
   git commit -m "feat: Add new feature"
   git push origin feature/branch
   ```

### Continuous Development

```bash
# Quick test during development
./scripts/run-tests.sh -k "test_function" -vv

# Auto-rerun on file changes (requires pytest-watch)
ptw tests/unit/test_config.py

# Debug specific test
pytest tests/unit/test_config.py::test_specific -vv --pdb
```

## Test Markers Reference

| Marker | Use Case | Speed |
|--------|----------|-------|
| `@pytest.mark.unit` | Isolated unit tests | ⚡ Fast |
| `@pytest.mark.slow` | Tests >5 seconds | 🐢 Slow |
| `@pytest.mark.integration` | Multiple components | ⚙️ Medium |
| `@pytest.mark.e2e` | Full workflows | 🚀 Very Slow |
| `@pytest.mark.requires_openwebui` | Need API credentials | 🌐 External |

## Coverage Requirements

- **Minimum:** 70% code coverage enforced (CI/CD gate)
- **Target:** 80%+ for high-quality code
- **Report:** Terminal + HTML + XML (for tracking)

**Where to check:**
- Terminal: `coverage.py` output
- HTML: `htmlcov/index.html`
- CI/CD: GitHub Actions workflow results
- Tracking: Codecov.io integration

## Troubleshooting

### Tests Hanging
```bash
# Add timeout to prevent hangs
pytest tests/unit/ --timeout=10
```

### Import Errors
```bash
# Ensure venv is activated
source venv/bin/activate

# Reinstall dependencies
pip install -r requirements-dev.txt
```

### Fixture Errors
```bash
# Check conftest.py is in tests/
ls -la tests/conftest.py

# Ensure fixtures are defined
grep "@pytest.fixture" tests/conftest.py
```

### Coverage Not Detected
```bash
# Clear coverage cache
rm .coverage htmlcov/ -rf

# Regenerate
pytest tests/unit/ --cov=webowui --cov-report=html
```

## CI/CD Verification Commands

These are the exact commands run by GitHub Actions:

```bash
# 1. Linting checks
python -m ruff check webowui/
python -m black --check webowui/
python -m mypy webowui/ --ignore-missing-imports

# 2. Unit tests with coverage gate
python -m pytest tests/unit/ \
  -v \
  --cov=webowui \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-fail-under=70 \
  -m "unit and not slow"
```

**Replicate locally:**
```bash
./scripts/verify-ci-locally.sh
```

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Coverage.py Documentation](https://coverage.readthedocs.io/)
- [Python Testing Best Practices](https://docs.python-guide.org/writing/tests/)
- [AsyncIO Testing](https://docs.pytest.org/en/stable/asyncio.html)
