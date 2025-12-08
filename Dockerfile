# JP 2024-06-12
# Dockerfile for OneSelect Backend Application
# ---------------------------------------------------------------
# This Dockerfile uses a multi-stage build to create a minimal final run imaege.
# The first stage (builder) installs all application dependencies using Poetry
# and creates a virtual environment. The second stage (runner) copies the virtual
# environment and application code into a minimal Alpine-based image.
#
# == Verification steps for the builder stage: 
# podman build --target builder -t oneselect-builder-debug .
# podman run -it --rm oneselect-builder-debug sh
# /app $ poetry config --list
#
# == Verification steps for the final stage:
# podman build -t oneselect-backend:latest 
# Create the container and bypass the defined entry script and be able to run the commands manually and verify it works
# podman run -it --rm --entrypoint sh oneselect-backend:latest
# /app $ whoami
# /app $ ls -la
# /app $ which elambic
# /app $ which uvicorn

# ======================================================================
# Stage 1 Builder
# ======================================================================
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
RUN poetry config virtualenvs.in-project true && poetry install --no-root --only=main

# ======================================================================
# Stage 2 Runner - minimal Alpine image
# ======================================================================
FROM python:3.13-alpine

# Harden he image step 1: remove python build tools
RUN python -m pip uninstall -y pip setuptools wheel

# Harden the image step 2: remove the APK package manager to prevent installation of new packages at runtime
RUN apk del --purge && rm -rf /var/cache/apk /etc/apk /lib/apk

# Create non-root user
RUN addgroup -S oneselect && adduser -D -u 1000 oneselect -G oneselect && \
    mkdir -p /app/data && \
    chown -R oneselect:oneselect /app

WORKDIR /app

# Copy the virtual environment with dependencies from the builder stage
COPY --from=builder --chown=oneselect:oneselect /app/.venv ./.venv

# Remove pip and other installation tools not needed in the runtime image
RUN ./.venv/bin/python -m pip uninstall -y pip

# Copy only application code (not tests, docs, etc.)
COPY --chown=oneselect:oneselect app/ ./app/
COPY --chown=oneselect:oneselect alembic/ ./alembic/
COPY --chown=oneselect:oneselect alembic.ini ./

# Remove Python bytecode cache
RUN find /app -type d -name "__pycache__" -exec rm -r {} + && \
    find /app -type f -name "*.pyc" -exec rm -f {} +

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