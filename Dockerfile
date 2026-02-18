# Stage 1: Builder - Install dependencies
FROM python:3.12-slim-bookworm AS builder
WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --upgrade pip --no-cache-dir && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime - Minimal production image
FROM python:3.12-slim-bookworm AS runtime
WORKDIR /app

# Upgrade system packages to get latest security patches
RUN apt-get update && \
    apt-get upgrade -y && \
    rm -rf /var/lib/apt/lists/*

# Install runtime dependencies for Playwright/Chromium
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libcups2 \
    libdbus-1-3 \
    libdrm2 \
    libgbm1 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder (system site-packages)
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Create non-root user (uid 1000 for consistency with host)
RUN useradd -m -u 1000 -s /bin/bash scraper && \
    mkdir -p /app/data/config/sites /app/data/config/profiles /app/data/outputs /app/data/logs && \
    chown -R scraper:scraper /app

# Copy application code
COPY --chown=scraper:scraper . /app/

# Switch to non-root user
USER scraper

# Install Playwright browser as scraper user (system deps already installed above)
# This installs to /home/scraper/.cache/ where it will be found at runtime
RUN playwright install chromium

# Single volume for all persistent data
VOLUME ["/app/data"]

# Environment variables
ENV PYTHONUNBUFFERED=1 \
    LOG_LEVEL=INFO

# Healthcheck
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD python -m webowui health || exit 1

# Entry point - allows docker exec to use short commands like "sites"
ENTRYPOINT ["python", "-m", "webowui"]

# Default: Run scheduler daemon
CMD ["daemon"]
