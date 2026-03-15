"""OCR service for local image/PDF OCR extraction."""
from __future__ import annotations

from dataclasses import dataclass
from importlib.util import find_spec
from pathlib import Path
from tempfile import TemporaryDirectory

from PIL import Image


@dataclass(frozen=True)
class OCRPageResult:
    """OCR text for one PDF page."""

    page_number: int
    text: str


class OCRService:
    """Service for OCR text extraction from images and scanned PDFs."""

    def __init__(self) -> None:
        self._engine = None

    def is_available(self) -> bool:
        """Return whether the local OCR stack is installed."""
        return bool(find_spec("paddleocr")) and bool(find_spec("fitz"))

    def get_installation_hint(self) -> str:
        """Return a short installation hint for the local OCR stack."""
        return (
            "需要先安装本地 OCR 依赖。项目现在默认使用 Python 3.13，"
            "请执行 `uv sync --group ocr` 安装 PaddleOCR / PaddlePaddle / PyMuPDF。"
        )

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from image using PaddleOCR when available.

        Args:
            image_path: Path to the image file

        Returns:
            Extracted text from the image
        """
        engine = self._get_engine()
        try:
            result = engine.ocr(image_path)
        except TypeError:
            result = engine.ocr(image_path, cls=True)
        return "\n".join(self._collect_text_lines(result)).strip()

    def extract_text_from_pil_image(self, image: Image.Image) -> str:
        """Extract text from PIL Image object."""
        with TemporaryDirectory(prefix="ocdoctor-ocr-image-") as temp_dir:
            image_path = Path(temp_dir) / "image.png"
            image.save(image_path)
            return self.extract_text_from_image(str(image_path))

    def extract_pages_from_pdf(
        self,
        pdf_path: str,
        *,
        start_page: int = 1,
        end_page: int | None = None,
        render_scale: float = 1.8,
    ) -> list[OCRPageResult]:
        """Render a scanned PDF into page images and OCR each page locally."""
        if start_page < 1:
            raise ValueError("start_page must be >= 1")
        fitz = self._require_module("fitz")
        document = fitz.open(pdf_path)
        final_page = end_page or len(document)
        if final_page > len(document):
            raise ValueError(f"end_page exceeds total pages ({len(document)})")
        if final_page < start_page:
            raise ValueError("end_page must be >= start_page")

        results: list[OCRPageResult] = []
        with TemporaryDirectory(prefix="ocdoctor-ocr-pdf-") as temp_dir:
            temp_root = Path(temp_dir)
            for page_number in range(start_page, final_page + 1):
                page = document.load_page(page_number - 1)
                pixmap = page.get_pixmap(
                    matrix=fitz.Matrix(render_scale, render_scale),
                    alpha=False,
                )
                image_path = temp_root / f"page_{page_number:04d}.png"
                pixmap.save(image_path)
                results.append(
                    OCRPageResult(
                        page_number=page_number,
                        text=self.extract_text_from_image(str(image_path)),
                    )
                )
        return results

    def _get_engine(self):
        """Lazily create a PaddleOCR engine."""
        if self._engine is not None:
            return self._engine
        if not self.is_available():
            raise RuntimeError(self.get_installation_hint())

        paddleocr = self._require_module("paddleocr")
        try:
            self._engine = paddleocr.PaddleOCR(
                lang="ch",
                use_textline_orientation=True,
            )
        except TypeError:
            self._engine = paddleocr.PaddleOCR(
                use_angle_cls=True,
                lang="ch",
            )
        return self._engine

    def _require_module(self, module_name: str):
        """Import one optional OCR dependency or raise a friendly error."""
        module = __import__(module_name)
        if module is None:
            raise RuntimeError(self.get_installation_hint())
        return module

    def _collect_text_lines(self, payload) -> list[str]:
        """Flatten PaddleOCR result payloads across supported versions."""
        if payload is None:
            return []
        if isinstance(payload, dict):
            if "rec_texts" in payload and isinstance(payload["rec_texts"], list):
                return [str(item).strip() for item in payload["rec_texts"] if str(item).strip()]
            lines: list[str] = []
            for value in payload.values():
                lines.extend(self._collect_text_lines(value))
            return lines
        if isinstance(payload, tuple):
            if payload and isinstance(payload[0], str):
                line = payload[0].strip()
                return [line] if line else []
            lines = []
            for item in payload:
                lines.extend(self._collect_text_lines(item))
            return lines
        if isinstance(payload, list):
            if len(payload) == 2 and isinstance(payload[1], tuple):
                return self._collect_text_lines(payload[1])
            lines = []
            for item in payload:
                lines.extend(self._collect_text_lines(item))
            return lines
        return []


ocr_service = OCRService()
