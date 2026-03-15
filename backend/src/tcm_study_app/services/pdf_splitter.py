"""Utilities for splitting large PDFs into chapter-sized parts."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import json
import re

from pypdf import PdfReader, PdfWriter


@dataclass(frozen=True)
class SplitPart:
    """One logical section from the original PDF."""

    title: str
    start_page: int
    end_page: int


@dataclass(frozen=True)
class SplitResult:
    """One emitted split file."""

    title: str
    output_path: Path
    start_page: int
    end_page: int
    page_count: int


def load_split_parts(spec_path: str | Path) -> list[SplitPart]:
    """Load split definitions from a JSON file."""
    payload = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    entries = payload["parts"] if isinstance(payload, dict) else payload
    if not isinstance(entries, list) or not entries:
        raise ValueError("Split spec must contain a non-empty list of parts")

    parts = []
    for entry in entries:
        if not isinstance(entry, dict):
            raise ValueError("Each split part must be an object")
        title = str(entry.get("title", "")).strip()
        start_page = int(entry.get("start_page", entry.get("start", 0)))
        end_page = int(entry.get("end_page", entry.get("end", 0)))
        if not title:
            raise ValueError("Each split part must include a title")
        parts.append(SplitPart(title=title, start_page=start_page, end_page=end_page))
    return parts


def split_pdf(
    input_path: str | Path,
    output_dir: str | Path,
    parts: list[SplitPart],
    *,
    overlap_pages: int = 0,
    prefix_width: int = 2,
) -> list[SplitResult]:
    """Split a PDF into multiple files using chapter-like page ranges."""
    if overlap_pages < 0:
        raise ValueError("overlap_pages must be >= 0")
    if not parts:
        raise ValueError("At least one split part is required")

    input_pdf = Path(input_path)
    reader = PdfReader(str(input_pdf))
    total_pages = len(reader.pages)
    _validate_parts(parts, total_pages)

    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)

    results: list[SplitResult] = []
    for index, part in enumerate(parts, start=1):
        start_page = part.start_page - (overlap_pages if index > 1 else 0)
        end_page = part.end_page + (overlap_pages if index < len(parts) else 0)
        start_page = max(1, start_page)
        end_page = min(total_pages, end_page)

        writer = PdfWriter()
        for page_number in range(start_page, end_page + 1):
            writer.add_page(reader.pages[page_number - 1])

        file_name = f"{index:0{prefix_width}d}_{_sanitize_title(part.title)}.pdf"
        output_path = output_root / file_name
        with output_path.open("wb") as handle:
            writer.write(handle)

        results.append(
            SplitResult(
                title=part.title,
                output_path=output_path,
                start_page=start_page,
                end_page=end_page,
                page_count=end_page - start_page + 1,
            )
        )

    return results


def _validate_parts(parts: list[SplitPart], total_pages: int) -> None:
    previous_end = 0
    for part in parts:
        if part.start_page < 1 or part.end_page < 1:
            raise ValueError("Page numbers must start at 1")
        if part.start_page > part.end_page:
            raise ValueError(f"Invalid range for '{part.title}': start_page > end_page")
        if part.end_page > total_pages:
            raise ValueError(
                f"Invalid range for '{part.title}': end_page exceeds total pages ({total_pages})"
            )
        if part.start_page <= previous_end:
            raise ValueError("Split parts must use ascending, non-overlapping base ranges")
        previous_end = part.end_page


def _sanitize_title(title: str) -> str:
    compact = re.sub(r"\s+", "_", title.strip())
    compact = re.sub(r'[\\/:*?"<>|]+', "", compact)
    compact = compact.strip("._")
    return compact or "part"
