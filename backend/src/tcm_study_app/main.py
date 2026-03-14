"""TCM Study App - Main application entry point."""
import sys
from pathlib import Path

# Add backend/src to path
backend_path = Path(__file__).parent / "backend" / "src"
if str(backend_path) not in sys.path:
    sys.path.insert(0, str(backend_path))

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from tcm_study_app.api import (
    cards_router,
    health_router,
    import_router,
    quiz_router,
    review_router,
)
from tcm_study_app.config import settings
from tcm_study_app.db import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    init_db()
    print("Database initialized")
    yield
    # Shutdown
    print("Application shutting down")


app = FastAPI(
    title=settings.app_name,
    description="TCM Study Helper for formula learning and card generation",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
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
    """Root endpoint."""
    return {
        "message": "Welcome to TCM Study App",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "tcm_study_app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
