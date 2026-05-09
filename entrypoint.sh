#!/bin/sh
set -e
 
echo "Running Alembic migrations..."
alembic upgrade 94fa472ae583
 
echo "Starting Uvicorn..."
exec uvicorn backend.main:app --host 0.0.0.0 --port 8000 --workers 2