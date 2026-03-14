"""Vercel API entry point."""
import sys
from pathlib import Path

# Add backend/src to path
backend_path = Path(__file__).parent / "backend" / "src"
sys.path.insert(0, str(backend_path))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from tcm_study_app.api import (
    cards_router,
    health_router,
    import_router,
    quiz_router,
    review_router,
)

app = FastAPI(title="TCM Study App")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health_router)
app.include_router(import_router)
app.include_router(cards_router)
app.include_router(quiz_router)
app.include_router(review_router)

@app.get("/")
async def root():
    return {"message": "TCM Study App API"}

# For Vercel serverless
def handler(request):
    return app(request)
