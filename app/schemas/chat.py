from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional

class ChatMessageRequest(BaseModel):
    """User's question for RAG chatbot."""
    message: str = Field(..., min_length=1, max_length=1000)
    analysis_id: Optional[int] = Field(None, description="Optional: filter to specific analysis")

class SourceAnalysis(BaseModel):
    """Source analysis used in RAG response."""
    analysis_id: int
    url: str
    seo_score: int
    ux_score: int
    chunk_type: str
    relevance_score: float

class ChatMessageResponse(BaseModel):
    """RAG-generated response."""
    id: int
    user_message: str
    assistant_response: str
    sources: List[SourceAnalysis]
    created_at: datetime
    
    class Config:
        from_attributes = True

class ChatHistoryResponse(BaseModel):
    """Chat conversation history."""
    id: int
    user_message: str
    assistant_response: str
    created_at: datetime
    
    class Config:
        from_attributes = True