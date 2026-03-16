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
    documents_router,
    health_router,
    import_router,
    subjects_router,
    templates_router,
    users_router,
)
from tcm_study_app.api.routes_cards import migrate_importance_from_json_if_needed
from tcm_study_app.config import settings
from tcm_study_app.db import SessionLocal, init_db
from tcm_study_app.services import seed_demo_content_if_needed

FRONTEND_DIR = Path(__file__).resolve().parents[3] / "frontend"


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    # Startup
    init_db()
    seeded_count = seed_demo_content_if_needed()
    db = SessionLocal()
    try:
        migrate_importance_from_json_if_needed(db)
    finally:
        db.close()
    print("Database initialized")
    if seeded_count:
        print(f"Seeded {seeded_count} demo collections")
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
app.include_router(templates_router)
app.include_router(collections_router)
app.include_router(import_router)
app.include_router(documents_router)
app.include_router(cards_router)
app.include_router(users_router)

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
