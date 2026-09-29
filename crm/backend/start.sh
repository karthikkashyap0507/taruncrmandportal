#!/bin/bash
# CRM Backend startup script
set -e

echo "Starting JobsNexGen CRM Backend..."

# Install dependencies if needed
pip install -r requirements.txt

# Run DB migrations
alembic upgrade head

# Start server
uvicorn app.main:app --host 0.0.0.0 --port 8001 --workers 2
