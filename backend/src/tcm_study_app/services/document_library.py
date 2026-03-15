"""Document import and parsing service."""
from io import BytesIO
from pathlib import Path
import re

from pypdf import PdfReader
from sqlalchemy.orm import Session

from tcm_study_app.models import DocumentChunk, SourceDocument, StudyCollection


class DocumentLibrary:
    """Service for importing documents and building a searchable chunk library."""

    def __init__(self, db: Session):
        self.db = db

    def import_text_document(self, collection_id: int, text: str) -> SourceDocument:
        """Import a plain-text document and chunk it immediately."""
        collection = self._require_collection(collection_id)
        normalized = text.strip()
        if not normalized:
            raise ValueError("Document text is empty")

        document = SourceDocument(
            collection_id=collection.id,
            type="text",
            raw_text=normalized,
            image_url="手动粘贴文本",
            status="processed",
        )
        self.db.add(document)
        self.db.flush()
        self._create_chunks(document, [normalized])
        self.db.commit()
        self.db.refresh(document)
        return document

    def import_pdf_document(
        self,
        collection_id: int,
        filename: str,
        content: bytes,
    ) -> SourceDocument:
        """Import a PDF, extract page text, and create chunks."""
        collection = self._require_collection(collection_id)
        pages = self._extract_pdf_pages(content)
        if not any(page.strip() for page in pages):
            raise ValueError("Could not extract text from PDF")

        raw_text = "\n\n".join(page.strip() for page in pages if page.strip())
        document = SourceDocument(
            collection_id=collection.id,
            type="pdf",
            raw_text=raw_text,
            image_url=filename,
            status="processed",
        )
        self.db.add(document)
        self.db.flush()
        self._create_chunks(document, pages)
        self.db.commit()
        self.db.refresh(document)
        return document

    def get_documents(self, collection_id: int) -> list[SourceDocument]:
        """List documents for a collection."""
        self._require_collection(collection_id)
        return (
            self.db.query(SourceDocument)
            .filter(SourceDocument.collection_id == collection_id)
            .order_by(SourceDocument.created_at.desc())
            .all()
        )

    def get_document(self, document_id: int) -> SourceDocument:
        """Fetch a document and ensure it exists."""
        document = self.db.get(SourceDocument, document_id)
        if not document:
            raise ValueError(f"Document {document_id} not found")
        return document

    def _require_collection(self, collection_id: int) -> StudyCollection:
        """Fetch a collection or raise a ValueError."""
        collection = self.db.get(StudyCollection, collection_id)
        if not collection:
            raise ValueError(f"Collection {collection_id} not found")
        return collection

    def _extract_pdf_pages(self, content: bytes) -> list[str]:
        """Extract text page-by-page from PDF bytes."""
        reader = PdfReader(BytesIO(content))
        pages = []
        for page in reader.pages:
            pages.append((page.extract_text() or "").strip())
        return pages

    def _create_chunks(self, document: SourceDocument, pages: list[str]) -> None:
        """Create chunk rows from page text."""
        for page_number, page_text in enumerate(pages, start=1):
            for chunk_index, chunk in enumerate(self._chunk_page_text(page_text), start=1):
                self.db.add(
                    DocumentChunk(
                        source_document_id=document.id,
                        page_number=page_number,
                        chunk_index=chunk_index,
                        heading=chunk["heading"],
                        content=chunk["content"],
                    )
                )

    def _chunk_page_text(self, page_text: str) -> list[dict[str, str | None]]:
        """Split one page into readable chunks with an optional heading."""
        normalized = page_text.replace("\r", "\n").strip()
        if not normalized:
            return []

        paragraphs = [
            block.strip()
            for block in re.split(r"\n\s*\n+", normalized)
            if block.strip()
        ]
        if len(paragraphs) <= 1:
            paragraphs = self._merge_lines_into_blocks(normalized.splitlines())

        chunks = []
        buffer = ""
        heading = None
        for paragraph in paragraphs:
            candidate_heading = self._guess_heading(paragraph)
            if candidate_heading and buffer:
                chunks.append({"heading": heading, "content": buffer})
                buffer = ""
                heading = None
            if candidate_heading and not buffer:
                heading = candidate_heading

            if len(buffer) + len(paragraph) <= 700:
                buffer = f"{buffer}\n\n{paragraph}".strip()
                continue

            chunks.append({"heading": heading, "content": buffer})
            buffer = paragraph
            heading = candidate_heading

        if buffer:
            chunks.append({"heading": heading, "content": buffer})
        return [chunk for chunk in chunks if chunk["content"]]

    def _merge_lines_into_blocks(self, lines: list[str]) -> list[str]:
        """Merge line-based PDFs into paragraph-like blocks."""
        blocks = []
        buffer = []
        for line in lines:
            cleaned = line.strip()
            if not cleaned:
                if buffer:
                    blocks.append(" ".join(buffer))
                    buffer = []
                continue
            buffer.append(cleaned)
            if len(" ".join(buffer)) >= 240:
                blocks.append(" ".join(buffer))
                buffer = []
        if buffer:
            blocks.append(" ".join(buffer))
        return blocks

    def _guess_heading(self, text: str) -> str | None:
        """Guess a short heading from the beginning of a chunk."""
        first_line = text.splitlines()[0].strip()
        if not first_line:
            return None
        compact = re.sub(r"\s+", "", first_line)
        if len(compact) > 18:
            return None
        if any(mark in compact for mark in "。；：;:，,"):
            return None
        return first_line


def create_document_library(db: Session) -> DocumentLibrary:
    """Factory for the document library service."""
    return DocumentLibrary(db)
