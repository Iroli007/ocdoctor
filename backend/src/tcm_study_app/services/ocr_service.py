"""OCR service for image text extraction."""
from PIL import Image


class OCRService:
    """Service for OCR text extraction from images."""

    def extract_text_from_image(self, image_path: str) -> str:
        """
        Extract text from image using OCR.

        Args:
            image_path: Path to the image file

        Returns:
            Extracted text from the image
        """
        # For MVP, return placeholder
        # TODO: Implement actual OCR using PaddleOCR or other library
        return self._mock_ocr(image_path)

    def extract_text_from_pil_image(self, image: Image.Image) -> str:
        """Extract text from PIL Image object."""
        # For MVP, return placeholder
        return "OCR结果占位符 - 请手动输入或校正文本"

    def _mock_ocr(self, image_path: str) -> str:
        """Mock OCR for MVP - returns placeholder text."""
        return "OCR结果占位符 - 请手动输入或校正文本"


ocr_service = OCRService()
