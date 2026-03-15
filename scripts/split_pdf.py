#!/usr/bin/env python
"""Split a large PDF into chapter-sized files with optional overlap pages."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from tcm_study_app.services.pdf_splitter import load_split_parts, split_pdf


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Split a large PDF into smaller chapter files. "
            "Use a JSON spec with title/start_page/end_page for each part."
        )
    )
    parser.add_argument("input_pdf", help="Path to the source PDF")
    parser.add_argument(
        "--spec",
        required=True,
        help="Path to a JSON file describing split parts",
    )
    parser.add_argument(
        "--output-dir",
        required=True,
        help="Directory for the emitted PDF parts",
    )
    parser.add_argument(
        "--overlap-pages",
        type=int,
        default=1,
        help="Pages of overlap added around boundaries (default: 1)",
    )
    parser.add_argument(
        "--prefix-width",
        type=int,
        default=2,
        help="Zero-padding width for output numbering (default: 2)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the split plan without writing files",
    )
    return parser


def main() -> int:
    """Run the CLI."""
    parser = build_parser()
    args = parser.parse_args()

    parts = load_split_parts(args.spec)
    if args.dry_run:
        for index, part in enumerate(parts, start=1):
            print(
                f"{index:02d}. {part.title}: "
                f"base pages {part.start_page}-{part.end_page}, "
                f"overlap={args.overlap_pages}"
            )
        return 0

    results = split_pdf(
        args.input_pdf,
        args.output_dir,
        parts,
        overlap_pages=args.overlap_pages,
        prefix_width=args.prefix_width,
    )
    for result in results:
        print(
            f"Wrote {result.output_path} "
            f"(pages {result.start_page}-{result.end_page}, {result.page_count} pages)"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
