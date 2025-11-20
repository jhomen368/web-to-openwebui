.PHONY: lint format typecheck test docker-build docker-build-no-cache ci help

# Default target - show available commands
help:
	@echo "Available commands:"
	@echo "  make lint                  - Run all linting checks (ruff, black, mypy)"
	@echo "  make format                - Auto-fix linting issues and format code"
	@echo "  make typecheck             - Run type checking only"
	@echo "  make test                  - Run tests with coverage"
	@echo "  make docker-build          - Build Docker image locally"
	@echo "  make docker-build-no-cache - Build Docker image locally without cache"
	@echo "  make ci                    - Run all CI checks locally"

# Run all checks (same as CI)
lint:
	@echo "Running ruff..."
	ruff check webowui/
	@echo "Checking black formatting..."
	black --check webowui/
	@echo "Running mypy type checking..."
	mypy webowui/ --ignore-missing-imports

# Auto-fix linting issues
format:
	@echo "Running ruff with --fix..."
	ruff check webowui/ --fix
	@echo "Formatting with black..."
	black webowui/

# Type checking only
typecheck:
	@echo "Running mypy..."
	mypy webowui/ --ignore-missing-imports

# Run tests
test:
	@echo "Running pytest with coverage..."
	pytest tests/ -v --cov=webowui

# Build Docker image locally without cache
docker-build-no-cache:
	@echo "Building Docker image..."
	docker build -t webowui:dev . --no-cache
	@echo "Docker image built successfully!"

# Build Docker image locally
docker-build:
	@echo "Building Docker image..."
	docker build -t webowui:dev .
	@echo "Docker image built successfully!"

# Run full CI locally
ci: lint test docker-build
	@echo "✅ All CI checks passed!"