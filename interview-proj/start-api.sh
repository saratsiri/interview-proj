#!/bin/bash

# Production startup script for FastAPI on Render
export PYTHONPATH="/opt/render/project/src:$PYTHONPATH"

# Start the FastAPI application
exec uvicorn src.api.main:app --host 0.0.0.0 --port ${PORT:-8000}