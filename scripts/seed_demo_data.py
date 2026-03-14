#!/usr/bin/env python
"""Seed demo data for TCM Study App."""
import sys
from pathlib import Path

# Add backend/src to path
sys.path.insert(0, str(Path(__file__).parent / "backend" / "src"))

from datetime import datetime
from sqlalchemy.orm import Session

from tcm_study_app.db import SessionLocal
from tcm_study_app.models import User, StudyCollection, SourceDocument, KnowledgeCard, FormulaCard


def seed_demo_data():
    """Seed demo data."""
    db: Session = SessionLocal()

    try:
        # Create demo user
        user = User(
            email="demo@example.com",
            name="Demo User",
        )
        db.add(user)
        db.flush()

        # Create demo collection
        collection = StudyCollection(
            user_id=user.id,
            title="方剂学-解表剂",
            subject="方剂学",
            description="解表剂学习卡片集合",
        )
        db.add(collection)
        db.flush()

        # Create sample source documents
        sample_formulas = [
            {
                "name": "桂枝汤",
                "composition": "桂枝、芍药、生姜、大枣、甘草",
                "effect": "解肌发表，调和营卫",
                "indication": "外感风寒表虚证",
                "pathogenesis": "风寒外袭，营卫不和",
                "usage_notes": "服药后啜热粥以助药力",
                "memory_tip": "桂枝+芍药 = 调和营卫",
            },
            {
                "name": "麻黄汤",
                "composition": "麻黄、桂枝、杏仁、甘草",
                "effect": "发汗解表，宣肺平喘",
                "indication": "外感风寒表实证",
                "pathogenesis": "风寒束表，肺气不宣",
                "usage_notes": "麻黄先煎去沫",
                "memory_tip": "麻黄+桂枝 = 发汗解表",
            },
            {
                "name": "银翘散",
                "composition": "金银花、连翘、桔梗、薄荷、竹叶、生甘草、荆芥穗、淡豆豉、牛蒡子",
                "effect": "辛凉透表，清热解毒",
                "indication": "温病初起",
                "pathogenesis": "风热袭表，热毒内盛",
                "usage_notes": "香气大出，即取服",
                "memory_tip": "银花+连翘 = 清热解毒",
            },
        ]

        for formula in sample_formulas:
            # Create source document
            doc = SourceDocument(
                collection_id=collection.id,
                type="text",
                raw_text=f"{formula['name']}：组成-{formula['composition']}，功效-{formula['effect']}",
                status="processed",
            )
            db.add(doc)
            db.flush()

            # Create knowledge card
            card = KnowledgeCard(
                collection_id=collection.id,
                source_document_id=doc.id,
                title=formula["name"],
                category="formula",
                raw_excerpt=f"组成：{formula['composition']}\n功效：{formula['effect']}",
            )
            db.add(card)
            db.flush()

            # Create formula card
            formula_card = FormulaCard(
                knowledge_card_id=card.id,
                formula_name=formula["name"],
                composition=formula["composition"],
                effect=formula["effect"],
                indication=formula["indication"],
                pathogenesis=formula["pathogenesis"],
                usage_notes=formula["usage_notes"],
                memory_tip=formula["memory_tip"],
            )
            db.add(formula_card)

        db.commit()
        print("Demo data seeded successfully!")
        print(f"User ID: {user.id}")
        print(f"Collection ID: {collection.id}")
        print(f"Created {len(sample_formulas)} formula cards")

    except Exception as e:
        db.rollback()
        print(f"Error seeding demo data: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_demo_data()
