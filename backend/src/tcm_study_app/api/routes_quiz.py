"""Quiz routes."""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from tcm_study_app.db import get_db
from tcm_study_app.schemas import (
    ComparisonItemResponse,
    ComparisonPoint,
    GenerateComparisonRequest,
    GenerateQuizPaperRequest,
    GenerateQuizRequest,
    QuizOption,
    QuizPaperQuestionResponse,
    QuizPaperResponse,
    QuizPaperSectionResponse,
    QuizResponse,
)
from tcm_study_app.services import (
    create_comparison_generator,
    create_quiz_generator,
)

router = APIRouter(prefix="/api", tags=["quiz"])


@router.post("/comparisons/generate", response_model=ComparisonItemResponse)
async def generate_comparison(request: GenerateComparisonRequest, db: Session = Depends(get_db)):
    """Generate a comparison between two entities."""
    generator = create_comparison_generator(db)
    try:
        comparison = generator.generate_comparison(
            request.collection_id,
            request.left_entity,
            request.right_entity,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    points = []
    if comparison.comparison_points_json:
        points_data = json.loads(comparison.comparison_points_json)
        points = [
            ComparisonPoint(
                dimension=p["dimension"],
                left=p["left"],
                right=p["right"],
            )
            for p in points_data
        ]

    return ComparisonItemResponse(
        id=comparison.id,
        left_entity=comparison.left_entity,
        right_entity=comparison.right_entity,
        comparison_points=points,
        question_text=comparison.question_text,
        answer_text=comparison.answer_text,
    )


@router.get("/comparisons", response_model=list[ComparisonItemResponse])
async def get_comparisons(
    collection_id: int = Query(..., description="Collection ID"),
    db: Session = Depends(get_db),
):
    """Get all comparisons for a collection."""
    generator = create_comparison_generator(db)
    comparisons = generator.get_comparisons_by_collection(collection_id)

    result = []
    for comp in comparisons:
        points = []
        if comp.comparison_points_json:
            points_data = json.loads(comp.comparison_points_json)
            points = [
                ComparisonPoint(
                    dimension=p["dimension"],
                    left=p["left"],
                    right=p["right"],
                )
                for p in points_data
            ]

        result.append(
            ComparisonItemResponse(
                id=comp.id,
                left_entity=comp.left_entity,
                right_entity=comp.right_entity,
                comparison_points=points,
                question_text=comp.question_text,
                answer_text=comp.answer_text,
            )
        )

    return result


@router.post("/quizzes/generate", response_model=list[QuizResponse])
async def generate_quiz(request: GenerateQuizRequest, db: Session = Depends(get_db)):
    """Generate quiz questions for a collection."""
    generator = create_quiz_generator(db)
    try:
        quizzes = generator.generate_quizzes(
            request.collection_id, request.count, request.difficulty
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    result = []
    for quiz in quizzes:
        options = None
        if quiz.options_json:
            options_data = json.loads(quiz.options_json)
            options = [QuizOption(key=o["key"], value=o["value"]) for o in options_data]

        result.append(
            QuizResponse(
                id=quiz.id,
                type=quiz.type,
                question=quiz.question,
                options=options,
                difficulty=quiz.difficulty,
                answer=quiz.answer,
                explanation=quiz.explanation,
            )
        )

    return result


@router.post("/quizzes/generate-paper", response_model=QuizPaperResponse)
async def generate_quiz_paper(
    request: GenerateQuizPaperRequest,
    db: Session = Depends(get_db),
):
    """Generate a structured practice paper for a collection."""
    generator = create_quiz_generator(db)
    try:
        paper = generator.generate_paper(
            request.collection_id,
            mode=request.mode,
            difficulty=request.difficulty,
            template=request.template,
        )
    except ValueError as exc:
        message = str(exc)
        status_code = 404 if "not found" in message.lower() else 400
        raise HTTPException(status_code=status_code, detail=message) from exc

    return QuizPaperResponse(
        paper_title=paper["paper_title"],
        subject_key=paper["subject_key"],
        subject_display_name=paper["subject_display_name"],
        mode=paper["mode"],
        total_score=paper["total_score"],
        exam_notice=paper["exam_notice"],
        sections=[
            QuizPaperSectionResponse(
                title=section["title"],
                instructions=section["instructions"],
                total_score=section["total_score"],
                question_count=section["question_count"],
                questions=[
                    QuizPaperQuestionResponse(
                        id=question["id"],
                        type=question["type"],
                        question=question["question"],
                        options=[
                            QuizOption(key=option["key"], value=option["value"])
                            for option in question.get("options", [])
                        ]
                        or None,
                        score=question["score"],
                        answer=question.get("answer"),
                        explanation=question.get("explanation"),
                        rubric=question.get("rubric", []),
                        answer_template=question.get("answer_template"),
                    )
                    for question in section["questions"]
                ],
            )
            for section in paper["sections"]
        ],
    )


@router.get("/quizzes", response_model=list[QuizResponse])
async def get_quizzes(
    collection_id: int = Query(..., description="Collection ID"),
    limit: int = Query(10, description="Limit number of quizzes"),
    db: Session = Depends(get_db),
):
    """Get quizzes for a collection."""
    generator = create_quiz_generator(db)
    quizzes = generator.get_quizzes_by_collection(collection_id, limit)

    result = []
    for quiz in quizzes:
        options = None
        if quiz.options_json:
            options_data = json.loads(quiz.options_json)
            options = [QuizOption(key=o["key"], value=o["value"]) for o in options_data]

        result.append(
            QuizResponse(
                id=quiz.id,
                type=quiz.type,
                question=quiz.question,
                options=options,
                difficulty=quiz.difficulty,
                answer=quiz.answer,
                explanation=quiz.explanation,
            )
        )

    return result
