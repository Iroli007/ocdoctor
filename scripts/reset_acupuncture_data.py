#!/usr/bin/env python
"""Clear acupuncture-generated data so OCR/import can be rerun cleanly."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend" / "src"))

from sqlalchemy.orm import Session

from tcm_study_app.db import SessionLocal
from tcm_study_app.models import CardRequest, KnowledgeCard, SourceDocument, StudyCollection


def build_parser() -> argparse.ArgumentParser:
    """Create the CLI parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Delete imported acupuncture documents and generated cards while keeping users "
            "and collections by default. Use this before rerunning improved OCR/import."
        )
    )
    parser.add_argument(
        "--drop-collections",
        action="store_true",
        help="Also delete acupuncture collections themselves instead of keeping the shells.",
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Skip the confirmation prompt.",
    )
    return parser


def main() -> int:
    """Run the reset flow."""
    parser = build_parser()
    args = parser.parse_args()

    db: Session = SessionLocal()
    try:
        acupuncture_collections = (
            db.query(StudyCollection)
            .filter(StudyCollection.subject == "针灸学")
            .order_by(StudyCollection.id.asc())
            .all()
        )
        if not acupuncture_collections:
            print("没有找到针灸学集合，不需要清理。")
            return 0

        collection_ids = [collection.id for collection in acupuncture_collections]
        document_count = (
            db.query(SourceDocument)
            .filter(SourceDocument.collection_id.in_(collection_ids))
            .count()
        )
        card_count = (
            db.query(KnowledgeCard)
            .filter(KnowledgeCard.collection_id.in_(collection_ids))
            .count()
        )
        request_count = (
            db.query(CardRequest)
            .filter(CardRequest.collection_id.in_(collection_ids))
            .count()
        )

        print("将清理以下针灸数据：")
        print(f"- 集合数: {len(collection_ids)}")
        print(f"- 文档数: {document_count}")
        print(f"- 卡片数: {card_count}")
        print(f"- 缺口登记数: {request_count}")
        if args.drop_collections:
            print("- 模式: 删除集合本身")
        else:
            print("- 模式: 保留集合，只删除导入文档/卡片/缺口登记")

        if not args.yes:
            answer = input("确认继续？输入 yes 执行: ").strip().lower()
            if answer != "yes":
                print("已取消。")
                return 1

        (
            db.query(CardRequest)
            .filter(CardRequest.collection_id.in_(collection_ids))
            .delete(synchronize_session=False)
        )

        if args.drop_collections:
            for collection in acupuncture_collections:
                db.delete(collection)
        else:
            (
                db.query(KnowledgeCard)
                .filter(KnowledgeCard.collection_id.in_(collection_ids))
                .delete(synchronize_session=False)
            )
            (
                db.query(SourceDocument)
                .filter(SourceDocument.collection_id.in_(collection_ids))
                .delete(synchronize_session=False)
            )

        db.commit()
        print("针灸数据已清理完成。现在可以重新导入改进版 OCR 数据。")
        return 0
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
