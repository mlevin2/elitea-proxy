# Use Python 3.12 slim image for smaller size
FROM python:3.12-slim

# The following line installs uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# Set working directory
WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1

# Copy pyproject.toml and uv.lock first for better Docker layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies
RUN uv sync --frozen --no-install-project --no-dev

# Copy application code
COPY elitea-proxy.py config.py ./

# Create non-root user for security
RUN useradd --create-home --shell /bin/bash app && \
    chown -R app:app /app
USER app

# Expose the default port
EXPOSE 4000

# Health check - Note: using uv run to ensure we use the virtualenv
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD uv run python -c "import requests; requests.get('http://localhost:4000/health', timeout=5)" || exit 1

# Run the application
CMD ["uv", "run", "python", "elitea-proxy.py"]
