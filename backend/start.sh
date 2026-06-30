#!/bin/bash
set -e

echo "🚀 PE Platform Backend — Starting up..."

# Run database migrations
echo "📦 Running Alembic migrations..."
alembic upgrade head

# Start the FastAPI server
echo "🌐 Starting Uvicorn..."
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
