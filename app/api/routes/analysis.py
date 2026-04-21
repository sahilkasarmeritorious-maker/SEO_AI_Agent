from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.analysis import AnalysisRequest, AnalysisResponse, AnalysisDetailResponse
from app.services.analysis_service import AnalysisService
from app.core.security import get_current_user
from app.core.logging import logger
from slowapi import Limiter
from slowapi.util import get_remote_address
import json

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(prefix="/api/analysis", tags=["Analysis"])


@router.post("/analyze", response_model=AnalysisResponse, status_code=status.HTTP_202_ACCEPTED)
@limiter.limit("10/minute")
def submit_analysis(
    request: Request,
    req: AnalysisRequest,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit URL for analysis."""
    logger.info(f"User {current_user_id} submitted analysis for {req.url}")
    
    analysis = AnalysisService.create_analysis(db, current_user_id, req.url)
    return analysis


@router.get("/results/{analysis_id}", response_model=AnalysisDetailResponse)
@limiter.limit("20/minute")
def get_analysis_results(
    request: Request,
    analysis_id: int,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analysis results."""
    analysis = AnalysisService.get_analysis_by_id(db, analysis_id)
    
    if not analysis:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
    
    if analysis.user_id != current_user_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
    
    response_data = {
        "id": analysis.id,
        "job_id": analysis.job_id,
        "url": analysis.url,
        "status": analysis.status,
        "overall_score": analysis.overall_score,
        "created_at": analysis.created_at,
        "completed_at": analysis.completed_at,
        "error": analysis.error,
        "processing_time_ms": analysis.processing_time_ms,
        "strengths": json.loads(analysis.strengths) if analysis.strengths else None,
        "weaknesses": json.loads(analysis.weaknesses) if analysis.weaknesses else None,
        "missing_elements": json.loads(analysis.missing_elements) if analysis.missing_elements else None,
        "recommendations": json.loads(analysis.recommendations) if analysis.recommendations else None,
        "json_file_path": analysis.json_file_path,
        "markdown_file_path": analysis.markdown_file_path,
    }
    
    return response_data


@router.get("/history")
@limiter.limit("30/minute")
def get_analysis_history(
    request: Request,
    skip: int = 0,
    limit: int = 10,
    current_user_id: int = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's analysis history."""
    analyses = AnalysisService.get_user_analyses(db, current_user_id, skip, limit)
    return analyses