from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
)
from sqlalchemy.orm import Session

from backend.app.db.database import get_db
from backend.app.schemas.risk import (
    RiskPredictionRequest,
    RiskPredictionResponse,
    BatchRiskPredictionRequest,
    BatchRiskPredictionResponse,
    ReviewCaseResponse,
    ReviewCaseListResponse,
    ReviewDecisionRequest,
    FeedbackResponse,
    FeedbackListResponse,
    ActualOutcomeRequest,
    MonitoringResponse,
    VisionAssessmentRequest,
    VisionAssessmentResponse,
    VisionAssessmentResult,
)
from backend.app.services.review_queue import (
    create_review_case,
    list_review_cases,
    list_review_analysis,
    get_review_case,
    resolve_review_case,
)
from backend.app.services.feedback import (
    save_prediction_feedback,
    update_feedback_decision,
    record_actual_outcome,
)
from backend.app.services.assessment import create_assessment, get_assessment
from backend.app.services.monitoring import (
    get_feedback_records,
    get_feedback_record,
    get_feedback_record_by_case_id,
    calculate_monitoring_metrics,
)
from backend.app.services.network import build_user_network
from backend.ml.decision.risk_decision import make_risk_decision
from backend.ml.decision.unified_risk import build_unified_risk_result
from backend.ml.inference.predictor import load_predictor
from backend.ml.vision.gemini_vision import GeminiVisionService


router = APIRouter(
    prefix="/api/v1/risk",
    tags=["Risk Assessment"],
)


predictor = load_predictor()
vision_service = GeminiVisionService()


def attach_review_case(
    db: Session,
    prediction: dict,
    data: dict,
) -> dict:
    """
    Create a HITL review case whenever the
    business decision is REVIEW.
    """

    if prediction.get("decision") == "REVIEW":
        case = create_review_case(
            db=db,
            prediction=prediction,
            data=data,
        )

        prediction["review_case_id"] = case["case_id"]

    else:
        prediction["review_case_id"] = None

    return prediction


@router.post(
    "/predict",
    response_model=RiskPredictionResponse,
)
def predict_risk(
    request: RiskPredictionRequest,
    db: Session = Depends(get_db),
) -> RiskPredictionResponse:

    try:
        if request.assessment_id:
            assessment = get_assessment(
                db=db,
                assessment_id=request.assessment_id,
            )

            if assessment is None:
                raise ValueError(
                    f"Assessment not found: {request.assessment_id}"
                )

            assessment_id = assessment.assessment_id

        else:
            assessment = create_assessment(
                db=db,
                assessment_type="SINGLE",
                total_records=1,
            )

            assessment_id = assessment.assessment_id

        result = predictor.predict(request.data)

        result["assessment_id"] = assessment_id

        decision = make_risk_decision(result)
        result.update(decision)

        unified = build_unified_risk_result(result)

        result["unified_evidence"] = unified.evidence.model_dump()

        result = attach_review_case(
            db=db,
            prediction=result,
            data=request.data,
        )

        save_prediction_feedback(
            db=db,
            prediction=result,
            data=request.data,
            assessment_id=assessment_id,
        )

        return RiskPredictionResponse(
            status="success",
            result=result,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@router.post(
    "/predict/batch",
    response_model=BatchRiskPredictionResponse,
)
def predict_risk_batch(
    request: BatchRiskPredictionRequest,
    db: Session = Depends(get_db),
) -> BatchRiskPredictionResponse:

    results = []

    try:
        if request.assessment_id:
            assessment = get_assessment(
                db=db,
                assessment_id=request.assessment_id,
            )

            if assessment is None:
                raise ValueError(
                    f"Assessment not found: {request.assessment_id}"
                )

            assessment_id = assessment.assessment_id

        else:
            assessment = create_assessment(
                db=db,
                assessment_type="BATCH",
                total_records=len(request.data),
            )

            assessment_id = assessment.assessment_id

        for data in request.data:
            prediction = predictor.predict(data)

            prediction["assessment_id"] = assessment_id

            decision = make_risk_decision(prediction)
            prediction.update(decision)

            unified = build_unified_risk_result(prediction)

            prediction["unified_evidence"] = unified.evidence.model_dump()

            prediction = attach_review_case(
                db=db,
                prediction=prediction,
                data=data,
            )

            save_prediction_feedback(
                db=db,
                prediction=prediction,
                data=data,
                assessment_id=assessment_id,
            )

            results.append(prediction)

        return BatchRiskPredictionResponse(
            status="success",
            results=results,
        )

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc


@router.post(
    "/vision-assess",
    response_model=VisionAssessmentResponse,
)
async def assess_return_image(
    image: UploadFile = File(...),
    return_reason: str | None = Form(default=None),
) -> VisionAssessmentResponse:

    if not image.content_type:
        raise HTTPException(
            status_code=400,
            detail="Image content type is required.",
        )

    if not image.content_type.startswith("image/"):
        raise HTTPException(
            status_code=400,
            detail="Uploaded file must be an image.",
        )

    image_bytes = await image.read()

    if not image_bytes:
        raise HTTPException(
            status_code=400,
            detail="Uploaded image is empty.",
        )

    result = vision_service.analyze_image(
        image_bytes=image_bytes,
        mime_type=image.content_type,
        return_reason=return_reason,
    )

    return VisionAssessmentResponse(
        status="success" if result["available"] else "unavailable",
        result=VisionAssessmentResult(**result),
    )


@router.get(
    "/review-queue",
    response_model=ReviewCaseListResponse,
)
def get_review_queue(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
) -> ReviewCaseListResponse:

    result = list_review_cases(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
    )

    return ReviewCaseListResponse(
        status="success",
        **result,
    )


@router.get(
    "/review-analysis",
    response_model=FeedbackListResponse,
)
def get_review_analysis(
    filter_type: str = Query("all"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    search: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict:

    result = list_review_analysis(
        db=db,
        filter_type=filter_type,
        page=page,
        page_size=page_size,
        search=search,
    )

    return {
        "status": "success",
        **result,
    }


@router.get(
    "/review-queue/{case_id}",
    response_model=ReviewCaseResponse,
)
def get_review_case_detail(
    case_id: str,
    db: Session = Depends(get_db),
) -> ReviewCaseResponse:

    case = get_review_case(db, case_id)

    if case is None:
        raise HTTPException(
            status_code=404,
            detail="Review case not found.",
        )

    return ReviewCaseResponse(
        **case
    )


@router.post(
    "/review-queue/{case_id}/decision",
    response_model=ReviewCaseResponse,
)
def decide_review_case(
    case_id: str,
    request: ReviewDecisionRequest,
    db: Session = Depends(get_db),
) -> ReviewCaseResponse:

    try:
        case = resolve_review_case(
            db=db,
            case_id=case_id,
            decision=request.decision,
            reason=request.reason,
        )

        feedback_record = get_feedback_record_by_case_id(
            db=db,
            case_id=case_id,
        )

        if feedback_record is None:
            raise ValueError(
                "Feedback record not found for review case."
            )

        update_feedback_decision(
            db=db,
            feedback_id=feedback_record.id,
            analyst_decision=request.decision,
            analyst_reason=request.reason,
        )

        return ReviewCaseResponse(
            **case
        )

    except ValueError as exc:
        db.rollback()

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=500,
            detail="Failed to persist review decision.",
        ) from exc


@router.get(
    "/feedback",
    response_model=FeedbackListResponse,
)
def get_feedback(
    db: Session = Depends(get_db),
) -> FeedbackListResponse:

    records = get_feedback_records(db)

    return FeedbackListResponse(
        status="success",
        records=[
            FeedbackResponse(
                id=record.id,
                case_id=record.case_id,
                prediction=record.prediction,
                predicted_label=record.predicted_label,
                abuse_probability=record.abuse_probability,
                risk_score=record.risk_score,
                risk_level=record.risk_level,
                model_decision=record.model_decision,
                analyst_decision=record.analyst_decision,
                actual_outcome=record.actual_outcome,
                analyst_reason=record.analyst_reason,
                input_data=record.input_data,
                created_at=record.created_at.isoformat(),
                outcome_recorded_at=(
                    record.outcome_recorded_at.isoformat()
                    if record.outcome_recorded_at
                    else None
                ),
            )
            for record in records
        ],
    )


@router.get(
    "/feedback/{feedback_id}",
    response_model=FeedbackResponse,
)
def get_feedback_detail(
    feedback_id: int,
    db: Session = Depends(get_db),
) -> FeedbackResponse:

    record = get_feedback_record(
        db,
        feedback_id,
    )

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Feedback record not found.",
        )

    return FeedbackResponse(
        id=record.id,
        case_id=record.case_id,
        prediction=record.prediction,
        predicted_label=record.predicted_label,
        abuse_probability=record.abuse_probability,
        risk_score=record.risk_score,
        risk_level=record.risk_level,
        model_decision=record.model_decision,
        analyst_decision=record.analyst_decision,
        actual_outcome=record.actual_outcome,
        analyst_reason=record.analyst_reason,
        input_data=record.input_data,
        created_at=record.created_at.isoformat(),
        outcome_recorded_at=(
            record.outcome_recorded_at.isoformat()
            if record.outcome_recorded_at
            else None
        ),
    )


@router.post(
    "/feedback/{feedback_id}/outcome",
    response_model=FeedbackResponse,
)
def submit_actual_outcome(
    feedback_id: int,
    request: ActualOutcomeRequest,
    db: Session = Depends(get_db),
) -> FeedbackResponse:

    try:
        record = record_actual_outcome(
            db=db,
            feedback_id=feedback_id,
            actual_outcome=request.actual_outcome,
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    return FeedbackResponse(
        id=record.id,
        case_id=record.case_id,
        prediction=record.prediction,
        predicted_label=record.predicted_label,
        abuse_probability=record.abuse_probability,
        risk_score=record.risk_score,
        risk_level=record.risk_level,
        model_decision=record.model_decision,
        analyst_decision=record.analyst_decision,
        actual_outcome=record.actual_outcome,
        analyst_reason=record.analyst_reason,
        input_data=record.input_data,
        created_at=record.created_at.isoformat(),
        outcome_recorded_at=(
            record.outcome_recorded_at.isoformat()
            if record.outcome_recorded_at
            else None
        ),
    )


@router.get(
    "/monitoring",
    response_model=MonitoringResponse,
)
def get_monitoring_metrics(
    db: Session = Depends(get_db),
) -> MonitoringResponse:

    metrics = calculate_monitoring_metrics(db)

    return MonitoringResponse(
        status="success",
        **metrics,
    )


@router.get(
    "/network/{user_id}",
)
def get_user_network(
    user_id: str,
):
    try:
        return build_user_network(user_id)

    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Internal network analysis error.",
        ) from exc
