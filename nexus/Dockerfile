# NEXUS Backend Dockerfile
# Multi-stage build for optimized production image
# This Dockerfile should be built from the project root directory
# Build command: docker build -f nexus/Dockerfile .

# Builder stage
FROM python:3.11-slim-bullseye AS builder

# Set working directory
WORKDIR /app

# Update package lists and clean up
RUN apt-get update && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir --user -r requirements.txt

# Copy application code and config
COPY nexus/ ./nexus/
COPY config.default.yml ./

# Final stage
FROM python:3.11-slim-bullseye

# Set working directory
WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    libssl1.1 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN adduser --disabled-password --gecos "" nexususer

# Copy installed Python packages from builder stage
COPY --from=builder /root/.local /home/nexususer/.local

# Copy application code and config
COPY --from=builder /app/nexus ./nexus
COPY --from=builder /app/config.default.yml ./

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