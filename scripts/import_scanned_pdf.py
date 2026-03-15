#!/usr/bin/env python
"""OCR a scanned PDF locally with PaddleOCR and upload page text to OCDOCTOR."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from urllib import error, request

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "OCR one scanned PDF or a directory of split PDFs locally, then upload the "
            "page text to the lightweight /api/import/ocr-pages endpoint."
        )
    )
    parser.add_argument("input_path", help="Path to one PDF file or a directory containing PDFs")
    parser.add_argument("--collection-id", type=int, required=True, help="Target collection ID")
    parser.add_argument(
        "--api-base",
        default="https://iroli1.online",
        help="OCDOCTOR API base URL (default: https://iroli1.online)",
    )
    parser.add_argument(
        "--render-scale",
        type=float,
        default=1.8,
        help="PDF page render scale for OCR quality (default: 1.8)",
    )
    parser.add_argument(
        "--glob",
        default="*.pdf",
        help="Glob pattern when input_path is a directory (default: *.pdf)",
    )
    return parser


def main() -> int:
    """Run the local OCR upload flow."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        from tcm_study_app.services.ocr_service import OCRService
    except ModuleNotFoundError as exc:
        missing = exc.name or "dependency"
        parser.exit(
            1,
            (
                f"Missing dependency: {missing}. "
                "Run this script with `uv run --group ocr python scripts/import_scanned_pdf.py ...` "
                "after `uv sync --group ocr`.\n"
            ),
        )

    ocr_service = OCRService()
    if not ocr_service.is_available():
        parser.exit(1, f"{ocr_service.get_installation_hint()}\n")

    input_path = Path(args.input_path).expanduser()
    pdf_files = _resolve_pdf_files(input_path, args.glob)
    api_base = args.api_base.rstrip("/")

    for pdf_path in pdf_files:
        print(f"OCR 中: {pdf_path}")
        pages = ocr_service.extract_pages_from_pdf(
            str(pdf_path),
            render_scale=args.render_scale,
        )
        payload = {
            "collection_id": args.collection_id,
            "file_name": pdf_path.name,
            "pages": [
                {"page_number": page.page_number, "text": page.text}
                for page in pages
            ],
        }
        response = _post_json(f"{api_base}/api/import/ocr-pages", payload)
        print(
            f"已导入 {pdf_path.name}: "
            f"document_id={response['document_id']} "
            f"page_count={response['page_count']} "
            f"chunk_count={response['chunk_count']}"
        )

    print(f"完成，共处理 {len(pdf_files)} 个 PDF。")
    return 0


def _resolve_pdf_files(input_path: Path, pattern: str) -> list[Path]:
    """Resolve one PDF or a sorted PDF list from a directory."""
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        pdf_files = sorted(path for path in input_path.glob(pattern) if path.is_file())
        if not pdf_files:
            raise SystemExit(f"目录里没有匹配到 PDF: {input_path}")
        return pdf_files
    raise SystemExit(f"找不到输入路径: {input_path}")


def _post_json(url: str, payload: dict) -> dict:
    """POST JSON and return the decoded response."""
    body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    req = request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with request.urlopen(req) as response:
            return json.loads(response.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"上传失败 {exc.code}: {detail}") from exc


if __name__ == "__main__":
    raise SystemExit(main())
