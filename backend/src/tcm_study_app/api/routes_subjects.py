"""Subject metadata routes."""
from fastapi import APIRouter

from tcm_study_app.core import list_subject_definitions
from tcm_study_app.schemas import SubjectResponse

router = APIRouter(prefix="/api/subjects", tags=["subjects"])


@router.get("", response_model=list[SubjectResponse])
async def list_subjects():
    """Return the supported study subjects."""
    return [
        SubjectResponse(
            key=subject.key,
            display_name=subject.display_name,
            entity_label=subject.entity_label,
        )
        for subject in list_subject_definitions()
    ]
