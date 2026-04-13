# Production-ready Dockerfile for OpsMind AI FastAPI Backend
# Based on python:3.11-slim for minimal image size

FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
# Prevents Python from writing pyc files and buffering stdout/stderr
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Install system dependencies required by packages
# - gcc, python3-dev: For compiling Python packages from source
# - postgresql-client: For database connectivity utilities (for debugging)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements.txt and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY app/ app/
COPY scripts/ scripts/

# Create non-root user for security (principle of least privilege)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port 8000 for the API
EXPOSE 8000

# Health check: Curl the /health endpoint every 30 seconds
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Production server command using Gunicorn with UvicornWorker
# - workers: 4 (adjust based on CPU cores: 2-4 per vCPU)
# - worker-class: uvicorn.workers.UvicornWorker (async ASGI worker)
# - bind: 0.0.0.0:8000 (listen on all interfaces)
# - max-requests: 1000 (restart worker after 1000 requests for memory safety)
# - max-requests-jitter: 100 (randomize to prevent thundering herd)
# - timeout: 120 (request timeout in seconds)
# - graceful-timeout: 30 (graceful shutdown timeout)
CMD ["gunicorn", \
     "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--timeout", "120", \
     "--graceful-timeout", "30", \
     "--access-logfile", "-", \
     "--error-logfile", "-"]
