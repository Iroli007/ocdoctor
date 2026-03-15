"""Tests for the PDF splitting utility."""
from pathlib import Path

from pypdf import PdfReader, PdfWriter
import pytest

from tcm_study_app.services.pdf_splitter import SplitPart, split_pdf


def _make_pdf(path: Path, pages: int) -> None:
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=200, height=200)
    with path.open("wb") as handle:
        writer.write(handle)


def test_split_pdf_adds_boundary_overlap(tmp_path: Path):
    source_pdf = tmp_path / "source.pdf"
    output_dir = tmp_path / "splits"
    _make_pdf(source_pdf, pages=5)

    results = split_pdf(
        source_pdf,
        output_dir,
        [
            SplitPart(title="Warm Disease Overview", start_page=1, end_page=2),
            SplitPart(title="Pattern Differentiation", start_page=3, end_page=5),
        ],
        overlap_pages=1,
    )

    assert [item.page_count for item in results] == [3, 4]
    assert results[0].output_path.name == "01_Warm_Disease_Overview.pdf"
    assert results[1].output_path.name == "02_Pattern_Differentiation.pdf"
    assert len(PdfReader(str(results[0].output_path)).pages) == 3
    assert len(PdfReader(str(results[1].output_path)).pages) == 4


def test_split_pdf_rejects_overlapping_base_ranges(tmp_path: Path):
    source_pdf = tmp_path / "source.pdf"
    _make_pdf(source_pdf, pages=5)

    with pytest.raises(ValueError, match="ascending, non-overlapping"):
        split_pdf(
            source_pdf,
            tmp_path / "splits",
            [
                SplitPart(title="Part A", start_page=1, end_page=3),
                SplitPart(title="Part B", start_page=3, end_page=5),
            ],
        )
