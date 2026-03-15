"""Card template routes."""
from fastapi import APIRouter, Query

from tcm_study_app.core import list_templates_for_subject
from tcm_study_app.schemas import CardTemplateResponse

router = APIRouter(prefix="/api/templates", tags=["templates"])


@router.get("", response_model=list[CardTemplateResponse])
async def list_templates(
    subject: str = Query(..., description="Subject key"),
):
    """List fixed card templates for a subject."""
    return [
        CardTemplateResponse(
            key=template.key,
            subject_key=template.subject_key,
            label=template.label,
            description=template.description,
            fields=list(template.fields),
        )
        for template in list_templates_for_subject(subject)
    ]
