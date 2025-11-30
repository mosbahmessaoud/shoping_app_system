#!/bin/bash
set -e

echo "🔄 Setting Python path..."
export PYTHONPATH=/app:$PYTHONPATH

echo "🔄 Running database migrations..."
alembic upgrade head

echo "🚀 Starting FastAPI application..."
exec uvicorn main:app --host 0.0.0.0 --port ${PORT}