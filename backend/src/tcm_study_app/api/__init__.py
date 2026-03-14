"""API package."""
from tcm_study_app.api.routes_cards import router as cards_router
from tcm_study_app.api.routes_health import router as health_router
from tcm_study_app.api.routes_import import router as import_router
from tcm_study_app.api.routes_quiz import router as quiz_router
from tcm_study_app.api.routes_review import router as review_router

__all__ = [
    "health_router",
    "import_router",
    "cards_router",
    "quiz_router",
    "review_router",
]
