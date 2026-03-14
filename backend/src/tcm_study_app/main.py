"""TCM Study App - Main application entry point."""
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from tcm_study_app.api import (
    cards_router,
    collections_router,
    health_router,
    import_router,
    quiz_router,
    review_router,
    subjects_router,
)
from tcm_study_app.config import settings
from tcm_study_app.db import init_db

FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"


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
    description="TCM Study Helper for formula, acupuncture, and warm-disease learning",
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
app.include_router(subjects_router)
app.include_router(collections_router)
app.include_router(import_router)
app.include_router(cards_router)
app.include_router(quiz_router)
app.include_router(review_router)

app.mount("/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="assets")


@app.get("/", include_in_schema=False)
async def root(request: Request):
    """Serve the frontend for browsers and JSON for API clients."""
    if "text/html" in request.headers.get("accept", ""):
        return FileResponse(FRONTEND_DIR / "index.html")

    return {
        "message": "Welcome to TCM Study App",
        "docs": "/docs",
        "app": "/",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "tcm_study_app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )
