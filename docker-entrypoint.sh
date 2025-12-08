#!/bin/sh

# Exit immediately if a command exits with a non-zero status.
set -e

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Run the initial data script to create the first superuser
echo "Initializing data..."
python app/initial_data.py

# Now, execute the command passed to the script (e.g., uvicorn)
# The 'exec' command replaces the shell process with the new process,
# which is a best practice for container entrypoints.
exec "$@"
