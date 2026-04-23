from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession  # ✅ Change this
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
async def submit_analysis(  # ✅ Make async
    request: Request,
    req: AnalysisRequest,
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)  # ✅ Change Session → AsyncSession
):
    """Submit URL for analysis."""
    logger.info(f"User {current_user_id} submitted analysis for {req.url}")
    
    analysis = await AnalysisService.create_analysis(db, current_user_id, req.url)  # ✅ Add await
    return analysis


@router.get("/results/{analysis_id}", response_model=AnalysisDetailResponse)
@limiter.limit("20/minute")
async def get_analysis_results(  # ✅ Make async
    request: Request,
    analysis_id: int,
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)  # ✅ Change Session → AsyncSession
):
    """Get analysis results."""
    try:
        logger.info(f"User {current_user_id} requesting analysis {analysis_id}")
        
        analysis = await AnalysisService.get_analysis_by_id(db, analysis_id)  # ✅ Add await
        
        if not analysis:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Analysis not found")
        
        # Convert to int to handle string/int mismatch
        if int(analysis.user_id) != int(current_user_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")
        
        return {
            "id": analysis.id,
            "analysis_id": analysis.analysis_id,
            "url": analysis.url,
            "status": analysis.status,
            "seo_overall_score": analysis.seo_overall_score,
            "seo_strengths": analysis.seo_strengths,
            "seo_weaknesses": analysis.seo_weaknesses,
            "seo_missing_elements": analysis.seo_missing_elements,
            "seo_recommendations": analysis.seo_recommendations,
            "ux_overall_score": analysis.ux_overall_score,
            "ux_strengths": analysis.ux_strengths,
            "ux_weaknesses": analysis.ux_weaknesses,
            "ux_missing_elements": analysis.ux_missing_elements,
            "ux_recommendations": analysis.ux_recommendations,
            "created_at": analysis.created_at,
            "completed_at": analysis.completed_at,
            "processing_time_ms": analysis.processing_time_ms,
            "error": analysis.error,
        }
    except Exception as e:
        logger.error(f"Error in get_analysis_results: {str(e)}")
        raise


@router.get("/history")
@limiter.limit("30/minute")
async def get_analysis_history(  # ✅ Make async
    request: Request,
    skip: int = 0,
    limit: int = 10,
    current_user_id: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)  # ✅ Change Session → AsyncSession
):
    """Get user's analysis history."""
    analyses = await AnalysisService.get_user_analyses(db, current_user_id, skip, limit)  # ✅ Add await
    return analyses