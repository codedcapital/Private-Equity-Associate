#!/bin/bash
set -e

echo "🚀 PE Platform Backend — Starting up..."

# Run database migrations
echo "📦 Running Alembic migrations..."
alembic upgrade head

# On free single-service hosts (e.g. Render free tier) we run the Celery
# worker in the SAME container as the API so agent pipeline jobs get
# processed without paying for a second service.
#
# Set RUN_CELERY_WORKER=0 to disable the in-container worker (e.g. if you
# run a dedicated worker elsewhere, or want to save memory).
# Only auto-start Celery if REDIS_URL is actually configured.
if [ "${RUN_CELERY_WORKER:-1}" = "1" ] && [ -n "${REDIS_URL:-}" ]; then
  echo "🛠  Starting in-container Celery worker..."
  celery -A core.celery_app worker --loglevel=info --concurrency=1 &
fi

# Start the FastAPI server (foreground / main process)
echo "🌐 Starting Uvicorn on port ${PORT:-8000}..."
exec uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1
