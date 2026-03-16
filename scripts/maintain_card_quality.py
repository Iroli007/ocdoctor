#!/usr/bin/env python3
"""Normalize persisted cards after OCR imports."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from tcm_study_app.db.session import SessionLocal
from tcm_study_app.models import KnowledgeCard
from tcm_study_app.services.clinical_card_cleanup import (
    clean_clinical_card_payload,
    is_valid_clinical_card_payload,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Clean persisted OCR cards in place.")
    parser.add_argument("--collection-id", type=int, help="Only maintain one collection")
    parser.add_argument(
        "--template-key",
        default="clinical_treatment",
        help="Only maintain cards of this template key",
    )
    parser.add_argument(
        "--prune-invalid",
        action="store_true",
        help="Delete invalid cards instead of leaving them untouched",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without committing",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    db = SessionLocal()
    try:
        query = db.query(KnowledgeCard).filter(KnowledgeCard.category == args.template_key)
        if args.collection_id is not None:
            query = query.filter(KnowledgeCard.collection_id == args.collection_id)

        cleaned_count = 0
        deleted_count = 0
        for card in query.all():
            try:
                payload = json.loads(card.normalized_content_json or "{}")
            except (json.JSONDecodeError, TypeError, ValueError):
                payload = {}

            cleaned = clean_clinical_card_payload(
                {
                    "disease_name": payload.get("disease_name") or card.title,
                    "treatment_principle": payload.get("treatment_principle"),
                    "acupoint_prescription": payload.get("acupoint_prescription"),
                    "notes": payload.get("notes"),
                },
                source_text="\n\n".join(
                    [card.raw_excerpt or "", *[citation.quote or "" for citation in card.citations]]
                ),
            )
            if not is_valid_clinical_card_payload(cleaned):
                if args.prune_invalid:
                    db.delete(card)
                    deleted_count += 1
                continue

            next_payload = {
                "template_key": payload.get("template_key", args.template_key),
                "template_label": payload.get("template_label", "病证治疗卡"),
                **cleaned,
            }
            next_json = json.dumps(next_payload, ensure_ascii=False)
            if card.title != cleaned["disease_name"] or card.normalized_content_json != next_json:
                card.title = cleaned["disease_name"]
                card.normalized_content_json = next_json
                cleaned_count += 1

        if args.dry_run:
            db.rollback()
        else:
            db.commit()

        print(
            f"quality-maintenance complete: cleaned={cleaned_count} deleted={deleted_count} dry_run={args.dry_run}"
        )
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
