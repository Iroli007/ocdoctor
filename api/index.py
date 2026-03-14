"""Vercel API entry point."""
import sys
from pathlib import Path

# Add backend/src to path
backend_path = Path(__file__).resolve().parent.parent / "backend" / "src"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from tcm_study_app.main import app
