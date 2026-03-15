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


class GenerateQuizPaperRequest(BaseModel):
    """Request schema for generating a structured practice paper."""

    collection_id: int
    mode: str = "final_mock"
    difficulty: str = "medium"
    template: str | None = None


class QuizResponse(BaseModel):
    """Response schema for quiz."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    question: str
    options: list[QuizOption] | None = None
    difficulty: str
    answer: str | None = None
    explanation: str | None = None


class QuizPaperQuestionResponse(BaseModel):
    """Structured paper question schema."""

    id: int | None = None
    type: str
    question: str
    options: list[QuizOption] | None = None
    score: int
    answer: str | None = None
    explanation: str | None = None
    rubric: list[str] = []
    answer_template: str | None = None


class QuizPaperSectionResponse(BaseModel):
    """A section inside a generated practice paper."""

    title: str
    instructions: str
    total_score: int
    question_count: int
    questions: list[QuizPaperQuestionResponse]


class QuizPaperResponse(BaseModel):
    """Structured practice paper schema."""

    paper_title: str
    subject_key: str
    subject_display_name: str
    mode: str
    total_score: int
    exam_notice: str
    sections: list[QuizPaperSectionResponse]
