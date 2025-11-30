#!/bin/bash

# Run database migrations
echo "Running database migrations..."
alembic upgrade head

# Start the application
echo "Starting FastAPI application..."
python -m uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}