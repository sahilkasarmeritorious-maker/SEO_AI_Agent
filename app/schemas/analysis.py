from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class AnalysisRequest(BaseModel):
    url: str = Field(..., description="Website URL to analyze")
    
    class Config:
        json_schema_extra = {
            "example": {
                "url": "https://example.com"
            }
        }


class AnalysisResponse(BaseModel):
    id: int
    analysis_id: str
    url: str
    status: str
    seo_overall_score: Optional[int] = None
    ux_overall_score: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    class Config:
        from_attributes = True


class AnalysisDetailResponse(BaseModel):
    id: int
    analysis_id: str
    url: str
    status: str
    seo_overall_score: Optional[int] = None
    seo_strengths: Optional[str] = None
    seo_weaknesses: Optional[str] = None
    seo_missing_elements: Optional[str] = None
    seo_recommendations: Optional[str] = None
    ux_overall_score: Optional[int] = None
    ux_strengths: Optional[str] = None
    ux_weaknesses: Optional[str] = None
    ux_missing_elements: Optional[str] = None
    ux_recommendations: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    processing_time_ms: Optional[int] = None
    error: Optional[str] = None
    
    class Config:
        from_attributes = True