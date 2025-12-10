# NEXUS Backend Dockerfile
# Multi-stage build for optimized production image
# This Dockerfile should be built from the project root directory
# Build command: docker build -f nexus/Dockerfile .

# Builder stage - uses Poetry to export dependencies
FROM python:3.12-slim-bookworm AS builder

# Set working directory
WORKDIR /app

# Install Poetry
RUN pip install --no-cache-dir poetry==1.8.0

# Copy dependency files first to leverage Docker cache
COPY pyproject.toml poetry.lock ./

# Export dependencies to requirements.txt (no Poetry in runtime image)
RUN poetry export -f requirements.txt --output requirements.txt --without-hashes --only main

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy application code
COPY nexus/ ./nexus/

# Final stage
FROM python:3.12-slim-bookworm

# Set working directory
WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN adduser --disabled-password --gecos "" nexususer

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /home/nexususer/.local

# Copy application code
COPY --from=builder /app/nexus ./nexus

# Set environment variables
ENV PATH="/home/nexususer/.local/bin:${PATH}"
ENV PYTHONPATH="/app"

# Change ownership of the app directory to nexususer
RUN chown -R nexususer:nexususer /app

# Switch to non-root user
USER nexususer

# Expose the port the app runs on
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

# Command to run the application
CMD ["python", "-m", "nexus.main"]