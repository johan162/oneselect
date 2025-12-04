# Multi-stage build for smaller final image
FROM python:3.13-alpine as builder

# Install build dependencies
RUN apk add --no-cache \
    build-base \
    curl \
    libffi-dev

# Install Poetry and export plugin
RUN curl -sSL https://install.python-poetry.org | python3 - \
    && /root/.local/bin/poetry self add poetry-plugin-export
ENV PATH="/root/.local/bin:$PATH"

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock* ./

# Export requirements and install to a target directory
RUN poetry export -f requirements.txt --without-hashes --only main -o requirements.txt \
    && pip install --no-cache-dir --target=/app/dependencies -r requirements.txt

# Final stage - minimal Alpine image
FROM python:3.13-alpine

# Install only runtime dependencies if needed
# RUN apk add --no-cache postgresql-libs  # Uncomment if using PostgreSQL

# Create non-root user
RUN adduser -D -u 1000 oneselect && \
    mkdir -p /app/data && \
    chown -R oneselect:oneselect /app

# Set working directory
WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /app/dependencies /usr/local/lib/python3.13/site-packages

# Copy only application code (not tests, docs, etc.)
COPY --chown=oneselect:oneselect app/ ./app/
COPY --chown=oneselect:oneselect alembic/ ./alembic/
COPY --chown=oneselect:oneselect alembic.ini ./

# Switch to non-root user
USER oneselect

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs').read()"

# Run the application
CMD ["python", "-m", "uvicorn", "app.main:app", "--workers", "2", "--host", "0.0.0.0", "--port", "8000"]
