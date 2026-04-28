import json
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.security import get_current_user
from app.db.session import get_db
from app.schemas.chat import (
    ChatMessageRequest,
    ChatMessageResponse,
    ChatHistoryResponse
)
from app.services.chat_service import chat_service

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: ChatMessageRequest,
    current_user: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):

    try:
        response = await chat_service.chat(
            user_id=current_user,
            message=request.message,
            analysis_id=request.analysis_id,
            db=db
        )
        return response

    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )


@router.get("/history", response_model=list[ChatHistoryResponse])
async def get_history(
    current_user: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    analysis_id: Optional[str] = Query(None),
    limit: int = 50
):
    
    try:
        # Convert analysis_id from string to int if provided
        analysis_id_int = None
        if analysis_id and analysis_id.strip():
            analysis_id_int = int(analysis_id)
        
        messages = await chat_service.get_chat_history(
            user_id=current_user,
            db=db,
            analysis_id=analysis_id_int,
            limit=limit
        )
        
        # Parse JSON fields and return with sources
        return [
            {
                "id": msg.id,
                "analysis_id": msg.analysis_id,  # ADDED
                "user_message": msg.user_message,
                "assistant_response": msg.assistant_response,
                "created_at": msg.created_at,
                "sources": json.loads(msg.source_analyses) if msg.source_analyses else []
            }
            for msg in messages
        ]

    except Exception as e:
        logger.error(f"History error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch history"
        )


@router.delete("/clear")
async def clear_history(
    current_user: int = Depends(get_current_user),  # Already an int!
    db: AsyncSession = Depends(get_db)
):
    """Delete all chat messages for user."""
    try:
        count = await chat_service.clear_chat_history(
            user_id=current_user,  # Already an int!
            db=db
        )
        return {
            "message": "Chat history cleared",
            "deleted_messages": count
        }

    except Exception as e:
        logger.error(f"Clear error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to clear history"
        )