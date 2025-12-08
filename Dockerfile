# Debug: 
# docker build --target builder -t oneselect-builder-debug .
# docker run -it --rm oneselect-builder-debug sh
# /app # poetry config --list

# ======================================================================
# Stage 1 Builder
# ======================================================================

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
COPY pyproject.toml poetry.lock ./

# Setup Poetry with dependencies and install DB with default admin user if it does not exists
RUN poetry config virtualenvs.in-project true && poetry install --no-dev --no-root

# ======================================================================
# Stage 2 Runner - minimal Alpine image
# ======================================================================
FROM python:3.13-alpine

# Create non-root user
RUN addgroup -S oneselect && adduser -D -u 1000 oneselect -G oneselect && \
    mkdir -p /app/data && \
    chown -R oneselect:oneselect /app

WORKDIR /app

# Copy the virtual environment with dependencies from the builder stage
COPY --from=builder --chown=oneselect:oneselect /app/.venv ./.venv

# Copy only application code (not tests, docs, etc.)
COPY --chown=oneselect:oneselect app/ ./app/
COPY --chown=oneselect:oneselect alembic/ ./alembic/
COPY --chown=oneselect:oneselect alembic.ini ./

# Copy the new entrypoint script
COPY --chown=oneselect:oneselect docker-entrypoint.sh ./

# Set the PATH to use the Python interpreter from our virtual environment
ENV PATH="/app/.venv/bin:$PATH"

# Switch to non-root user
USER oneselect

# Set Python path
ENV PYTHONPATH=/app

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=120s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/docs').read()"

# Set the entrypoint to our script
ENTRYPOINT ["./docker-entrypoint.sh"]

# Run the application. This command is passed to the entrypoint script.
CMD ["uvicorn", "app.main:app", "--workers", "2", "--host", "0.0.0.0", "--port", "8000"]