"""Quiz schemas."""

from pydantic import BaseModel, ConfigDict


class ComparisonPoint(BaseModel):
    """Comparison point schema."""

    dimension: str
    left: str
    right: str


class GenerateComparisonRequest(BaseModel):
    """Request schema for generating comparison."""

    collection_id: int
    left_entity: str
    right_entity: str


class ComparisonItemResponse(BaseModel):
    """Response schema for comparison item."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    left_entity: str
    right_entity: str
    comparison_points: list[ComparisonPoint]
    question_text: str | None = None
    answer_text: str | None = None


class QuizOption(BaseModel):
    """Quiz option schema."""

    key: str
    value: str


class GenerateQuizRequest(BaseModel):
    """Request schema for generating quiz."""

    collection_id: int
    count: int = 5
    difficulty: str = "medium"


class QuizResponse(BaseModel):
    """Response schema for quiz."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    question: str
    options: list[QuizOption] | None = None
    difficulty: str
