"""Document import and parsing service."""
from io import BytesIO
from pathlib import Path
import re

from pypdf import PdfReader
from sqlalchemy.orm import Session

from tcm_study_app.models import KnowledgeCard, OCRBlock, OCRPage, ParsedDocumentUnit, SourceDocument, StudyCollection
from tcm_study_app.models.document_chunk import DocumentChunk
from tcm_study_app.schemas.import_schema import OCRPageInput
from tcm_study_app.services.clinical_acupuncture_parser import (
    ClinicalAcupunctureSectionClassifier,
    MeridianAcupointParser,
    NeedlingTechniqueParser,
    OCRBlockBuilder,
    PARSER_VERSION,
    SOURCE_BOOK_KEY,
    TreatmentChapterParser,
)


class DocumentLibrary:
    """Service for importing documents and building a searchable chunk library."""

    def __init__(self, db: Session):
        self.db = db
        self._section_classifier = ClinicalAcupunctureSectionClassifier()
        self._block_builder = OCRBlockBuilder()
        self._meridian_parser = MeridianAcupointParser()
        self._technique_parser = NeedlingTechniqueParser()
        self._treatment_parser = TreatmentChapterParser()

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
        self._build_clinical_acupuncture_structure(document, "手动粘贴文本", [(1, normalized)])
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
        self._build_clinical_acupuncture_structure(
            document,
            filename,
            [(page_number, page_text) for page_number, page_text in enumerate(pages, start=1)],
        )
        self.db.commit()
        self.db.refresh(document)
        return document

    def import_ocr_document(
        self,
        collection_id: int,
        filename: str,
        pages: list[OCRPageInput] | list[dict[str, object]],
    ) -> SourceDocument:
        """Import OCR text that was extracted locally from a scanned PDF."""
        collection = self._require_collection(collection_id)
        normalized_pages = self._normalize_ocr_pages(pages)
        if not any(text.strip() for _, text in normalized_pages):
            raise ValueError("OCR pages are empty")

        raw_text = "\n\n".join(
            f"[第 {page_number} 页]\n{text}".strip()
            for page_number, text in normalized_pages
            if text.strip()
        )
        document = SourceDocument(
            collection_id=collection.id,
            type="pdf_ocr",
            raw_text=raw_text,
            image_url=filename,
            ocr_text=raw_text,
            source_book_key=SOURCE_BOOK_KEY,
            status="processed",
        )
        self.db.add(document)
        self.db.flush()
        self._create_chunks_from_page_entries(document, normalized_pages)
        self._build_clinical_acupuncture_structure(document, filename, normalized_pages, is_ocr=True)
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

    def delete_document(self, document_id: int) -> SourceDocument:
        """Delete one imported document and any cards generated from it."""
        document = self.get_document(document_id)
        (
            self.db.query(KnowledgeCard)
            .filter(KnowledgeCard.source_document_id == document.id)
            .delete(synchronize_session=False)
        )
        self.db.delete(document)
        self.db.commit()
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
        self._create_chunks_from_page_entries(
            document,
            [(page_number, page_text) for page_number, page_text in enumerate(pages, start=1)],
        )

    def _create_chunks_from_page_entries(
        self,
        document: SourceDocument,
        page_entries: list[tuple[int, str]],
    ) -> None:
        """Create chunk rows from explicit page number and text pairs."""
        for page_number, page_text in page_entries:
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

    def _normalize_ocr_pages(
        self,
        pages: list[OCRPageInput] | list[dict[str, object]],
    ) -> list[tuple[int, str]]:
        """Normalize OCR page payloads into sorted page-number/text tuples."""
        normalized_pages: list[tuple[int, str]] = []
        seen_page_numbers: set[int] = set()
        for entry in pages:
            if isinstance(entry, OCRPageInput):
                page_number = entry.page_number
                text = entry.text
            else:
                page_number = int(entry["page_number"])
                text = str(entry.get("text", ""))
            if page_number in seen_page_numbers:
                raise ValueError(f"Duplicate OCR page number: {page_number}")
            seen_page_numbers.add(page_number)
            normalized_pages.append((page_number, text.strip()))
        normalized_pages.sort(key=lambda item: item[0])
        return normalized_pages

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

    def _build_clinical_acupuncture_structure(
        self,
        document: SourceDocument,
        file_name: str,
        page_entries: list[tuple[int, str]],
        *,
        is_ocr: bool = False,
    ) -> None:
        """Build OCR pages, blocks, and parsed units for acupuncture sources."""
        if document.collection.subject != "针灸学":
            return

        section = self._section_classifier.classify_document(
            file_name,
            text="\n".join(text for _, text in page_entries),
        )
        document.source_book_key = section.source_book_key
        document.book_section = section.book_section
        document.section_confidence = section.confidence
        document.parser_version = PARSER_VERSION
        document.ocr_engine = "paddleocr" if is_ocr else "plain_text"

        page_analyses = [
            self._section_classifier.classify_page(
                page_number,
                text,
                fallback_section=section.book_section,
            )
            for page_number, text in page_entries
        ]
        blocks: list[tuple[OCRPage, OCRBlock]] = []
        block_candidates = []
        for page_analysis in page_analyses:
            ocr_page = OCRPage(
                source_document_id=document.id,
                page_number=page_analysis.page_number,
                raw_text=page_analysis.raw_text,
                page_kind=page_analysis.page_kind,
                book_section=page_analysis.book_section,
                quality_flags=",".join(page_analysis.quality_flags) if page_analysis.quality_flags else None,
            )
            self.db.add(ocr_page)
            self.db.flush()
            if page_analysis.page_kind != "noise":
                document.has_layout_blocks = True
            page_blocks = self._block_builder.build_blocks(page_analysis)
            for candidate in page_blocks:
                block = OCRBlock(
                    ocr_page_id=ocr_page.id,
                    block_type=candidate.block_type,
                    text=candidate.text,
                    sequence_no=candidate.sequence_no,
                )
                self.db.add(block)
                blocks.append((ocr_page, block))
                block_candidates.append(candidate)

        parsed_units = self._parse_units_for_section(section.book_section, page_analyses, block_candidates)
        for unit in parsed_units:
            self.db.add(
                ParsedDocumentUnit(
                    source_document_id=document.id,
                    page_number_start=unit.page_number_start,
                    page_number_end=unit.page_number_end,
                    book_section=unit.book_section,
                    unit_type=unit.unit_type,
                    source_heading=unit.source_heading,
                    source_text=unit.source_text,
                    sequence_no=unit.sequence_no,
                    parser_version=PARSER_VERSION,
                    validation_state=unit.validation_state,
                )
            )

    def _parse_units_for_section(
        self,
        book_section: str | None,
        page_analyses: list,
        blocks: list,
    ) -> list:
        """Route parsing to the right section parser."""
        if book_section == "meridian_acupoints":
            return self._meridian_parser.parse(page_analyses, blocks)
        if book_section == "needling_techniques":
            return self._technique_parser.parse(blocks)
        if book_section == "treatment":
            return self._treatment_parser.parse(blocks)
        return []

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
