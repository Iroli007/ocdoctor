"""API package."""
from tcm_study_app.api.routes_cards import router as cards_router
from tcm_study_app.api.routes_collections import router as collections_router
from tcm_study_app.api.routes_documents import router as documents_router
from tcm_study_app.api.routes_health import router as health_router
from tcm_study_app.api.routes_import import router as import_router
from tcm_study_app.api.routes_subjects import router as subjects_router
from tcm_study_app.api.routes_templates import router as templates_router

__all__ = [
    "health_router",
    "collections_router",
    "import_router",
    "documents_router",
    "cards_router",
    "subjects_router",
    "templates_router",
]
