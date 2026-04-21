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
    job_id: str
    url: str
    status: str
    overall_score: Optional[int] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    class Config:
        from_attributes = True


class AnalysisDetailResponse(AnalysisResponse):
    strengths: Optional[List] = None
    weaknesses: Optional[List] = None
    missing_elements: Optional[List] = None
    recommendations: Optional[List] = None
    processing_time_ms: Optional[int] = None