"""Import routes."""
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from tcm_study_app.db import get_db
from tcm_study_app.models import SourceDocument, StudyCollection
from tcm_study_app.schemas import (
    ImportImageResponse,
    ImportTextRequest,
    ImportTextResponse,
    OCRResultRequest,
)
from tcm_study_app.services import ocr_service

router = APIRouter(prefix="/api/import", tags=["import"])


@router.post("/text", response_model=ImportTextResponse)
async def import_text(request: ImportTextRequest, db: Session = Depends(get_db)):
    """Import text content."""
    # Verify collection exists
    collection = db.get(StudyCollection, request.collection_id)
    if not collection:
        raise HTTPException(
            status_code=404,
            detail=f"Collection {request.collection_id} not found",
        )

    # Create source document
    doc = SourceDocument(
        collection_id=request.collection_id,
        type="text",
        raw_text=request.text,
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return ImportTextResponse(document_id=doc.id, status=doc.status)


@router.post("/image", response_model=ImportImageResponse)
async def import_image(
    collection_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
):
    """Upload image and perform OCR."""
    # Verify collection exists
    collection = db.get(StudyCollection, collection_id)
    if not collection:
        raise HTTPException(status_code=404, detail=f"Collection {collection_id} not found")

    # For MVP, just save the file reference
    # TODO: Actually save the file and run OCR
    image_path = f"/tmp/{file.filename}"

    # Save uploaded file
    content = await file.read()
    with open(image_path, "wb") as f:
        f.write(content)

    # Run OCR
    ocr_text = ocr_service.extract_text_from_image(image_path)

    # Create source document
    doc = SourceDocument(
        collection_id=collection_id,
        type="image",
        image_url=image_path,
        ocr_text=ocr_text,
        status="pending",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    return ImportImageResponse(
        document_id=doc.id, ocr_text=doc.ocr_text, status=doc.status
    )


@router.post("/ocr/correct")
async def correct_ocr(request: OCRResultRequest, db: Session = Depends(get_db)):
    """Submit corrected OCR text."""
    doc = db.get(SourceDocument, request.document_id)
    if not doc:
        raise HTTPException(status_code=404, detail=f"Document {request.document_id} not found")

    doc.ocr_text = request.corrected_text
    db.commit()
    db.refresh(doc)

    return {"status": "ok", "document_id": doc.id}
