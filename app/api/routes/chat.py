from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from typing import Optional
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
from app.services.chat_session_service import ChatSessionService
import json

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.post("/message", response_model=ChatMessageResponse)
async def send_message(
    request: Request,
    req: ChatMessageRequest,
    current_user: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Send a chat message to existing or new session."""
    try:
        # Get optional session_id from request body or query param
        session_id = getattr(req, 'session_id', None)
        
        response = await chat_service.chat(
            user_id=current_user,
            message=req.message,
            analysis_id=req.analysis_id,
            db=db,
            session_id=session_id  # ✅ Pass session_id if provided
        )
        return response

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        logger.error(f"Chat error: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process message"
        )


@router.post("/sessions/new")
async def create_new_session(
    request: Request,
    analysis_id: Optional[int] = Query(None),
    current_user: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new chat session (frontend clicks 'New Chat' button)."""
    try:
        session = await ChatSessionService.create_session(
            db=db,
            user_id=current_user,
            analysis_id=analysis_id,
            #title=f"Analysis #{analysis_id}" if analysis_id else "New Chat"
        )
        
        return {
            "id": session.id,
            "title": session.title,
            "analysis_id": session.analysis_id,
            "session_type": session.session_type,
            "created_at": session.created_at.isoformat()
        }
    except Exception as e:
        logger.error(f"Error creating session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create session"
        )


@router.get("/sessions")
async def get_sessions(
    request: Request,
    analysis_id: Optional[int] = Query(None),  # ✅ Default is None
    current_user: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all sessions for current user (filtered by analysis_id)."""
    try:
        sessions = await ChatSessionService.get_user_sessions(
            db=db,
            user_id=current_user,
            analysis_id=analysis_id  # ✅ Passes None for universal, or specific ID
        )
        
        return [
            {
                "id": s.id,
                "title": s.title,
                "session_type": s.session_type,
                "analysis_id": s.analysis_id,
                "message_count": len(s.messages) if s.messages else 0,  # ✅ Safe access
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat()
            }
            for s in sessions
        ]
    except Exception as e:
        logger.error(f"Error fetching sessions: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sessions: {str(e)}"
        )


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    request: Request,
    session_id: int,
    current_user: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all messages in a specific session."""
    try:
        messages = await ChatSessionService.get_session_messages(
            db=db,
            session_id=session_id,
            user_id=current_user
        )
        
        return [
            {
                "id": msg.id,
                "session_id": msg.session_id,
                "analysis_id": msg.analysis_id,
                "user_message": msg.user_message,
                "assistant_response": msg.assistant_response,
                "created_at": msg.created_at.isoformat(),
                "sources": json.loads(msg.source_analyses) if msg.source_analyses else []
            }
            for msg in messages
        ]
    except Exception as e:
        logger.error(f"Error fetching session messages: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch messages: {str(e)}"
        )


@router.delete("/sessions/{session_id}")
async def delete_session(
    request: Request,
    session_id: int,
    current_user: int = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete a session (cascade deletes messages)."""
    try:
        success = await ChatSessionService.delete_session(
            db=db,
            session_id=session_id,
            user_id=current_user
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found"
            )
        
        return {"message": "Session deleted successfully"}
    except Exception as e:
        logger.error(f"Error deleting session: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete session"
        )