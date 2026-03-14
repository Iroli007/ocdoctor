#!/bin/bash
# Development script for TCM Study App

cd "$(dirname "$0")/.." || exit 1

export PYTHONPATH="backend/src:$PYTHONPATH"

# Check if database exists, if not seed demo data
if [ ! -f "tcm_study.db" ]; then
    echo "Database not found, seeding demo data..."
    python scripts/seed_demo_data.py
fi

# Start the server
uv run uvicorn tcm_study_app.main:app --host 0.0.0.0 --port 8000 --reload
