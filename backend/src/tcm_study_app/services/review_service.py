"""Review service."""
from datetime import datetime, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from tcm_study_app.models import KnowledgeCard, Quiz, ReviewRecord, StudyCollection


class ReviewService:
    """Service for managing review sessions."""

    def __init__(self, db: Session):
        self.db = db

    def submit_review(
        self,
        user_id: int,
        target_type: str,
        target_id: int,
        result: str,
        response: str | None = None,
    ) -> ReviewRecord:
        """
        Submit a review result.

        Args:
            user_id: User ID
            target_type: Target type (card/quiz/comparison)
            target_id: Target ID
            result: Review result (correct/wrong/skipped)
            response: User's response (optional)

        Returns:
            Created review record
        """
        record = ReviewRecord(
            user_id=user_id,
            target_type=target_type,
            target_id=target_id,
            result=result,
            response=response,
            reviewed_at=datetime.utcnow(),
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get_review_stats(self, user_id: int) -> dict:
        """Get review statistics for a user."""
        stats = (
            self.db.query(
                func.count(ReviewRecord.id).label("total"),
                func.sum(
                    func.case(
                        (ReviewRecord.result == "correct", 1), else_=0
                    )
                ).label("correct"),
                func.sum(
                    func.case(
                        (ReviewRecord.result == "wrong", 1), else_=0
                    )
                ).label("wrong"),
                func.sum(
                    func.sum(
                        func.case(
                            (ReviewRecord.result == "skipped", 1), else_=0
                        )
                    )
                ).label("skipped"),
            )
            .filter(ReviewRecord.user_id == user_id)
            .first()
        )

        total = stats.total or 0
        correct = stats.correct or 0
        accuracy = (correct / total * 100) if total > 0 else 0

        return {
            "total_reviews": total,
            "correct_count": correct,
            "wrong_count": stats.wrong or 0,
            "skipped_count": stats.skipped or 0,
            "accuracy": round(accuracy, 1),
        }

    def get_due_items(self, user_id: int, collection_id: int | None = None):
        """
        Get items due for review.

        For MVP, this returns:
        - Items not yet reviewed
        - Items that were wrong in recent reviews
        """
        query = self.db.query(KnowledgeCard).join(StudyCollection)

        if collection_id:
            query = query.filter(StudyCollection.id == collection_id)

        # Get cards with their review status
        cards = query.all()

        # Simple logic: return all cards for MVP
        # TODO: Implement spaced repetition logic
        return cards

    def get_wrong_items(self, user_id: int, collection_id: int | None = None):
        """Get items that were answered wrong recently."""
        wrong_records = (
            self.db.query(ReviewRecord)
            .filter(
                ReviewRecord.user_id == user_id,
                ReviewRecord.result == "wrong",
                ReviewRecord.target_type.in_(["card", "quiz"]),
            )
            .order_by(ReviewRecord.reviewed_at.desc())
            .limit(20)
            .all()
        )

        return wrong_records


def create_review_service(db: Session) -> ReviewService:
    """Factory function to create ReviewService."""
    return ReviewService(db)
