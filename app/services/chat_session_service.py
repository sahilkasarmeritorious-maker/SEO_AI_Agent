from datetime import datetime
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from app.db.models import ChatSession, ChatMessage
from app.core.logging import logger


class ChatSessionService:
    
    @staticmethod
    def _generate_session_title(message: str, max_length: int = 50) -> str:
        """Auto-generate session title from first message."""
        # Truncate to first 50 chars OR first 3 words
        if len(message) <= max_length:
            title = message
        else:
            # Try to cut at word boundary
            truncated = message[:max_length]
            last_space = truncated.rfind(' ')
            title = truncated[:last_space] if last_space > 0 else truncated
        
        return title.strip()
    
    @staticmethod
    async def create_session(
        db: AsyncSession,
        user_id: int,
        analysis_id: Optional[int] = None,
        title: Optional[str] = None,
        first_message: Optional[str] = None
    ) -> ChatSession:
        """ALWAYS create a new session (ChatGPT-style)."""
        user_id = int(user_id)
        
        # Auto-generate title from first message if not provided
        if not title and first_message:
            title = ChatSessionService._generate_session_title(first_message)
        else:
            title = title or (f"Analysis #{analysis_id}" if analysis_id else "Chat")
        
        session_type = "specific" if analysis_id else "universal"
        
        new_session = ChatSession(
            user_id=user_id,
            analysis_id=analysis_id,
            title=title,
            session_type=session_type,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        
        db.add(new_session)
        await db.commit()
        await db.refresh(new_session)
        
        logger.info(f"✨ Created new session {new_session.id}: '{title}' for user {user_id}")
        return new_session
    
    @staticmethod
    async def get_session(
        db: AsyncSession,
        session_id: int,
        user_id: int
    ) -> Optional[ChatSession]:
        """Get session by ID with ownership check."""
        result = await db.execute(
            select(ChatSession).where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            )
        )
        session = result.scalars().first()
        
        if session:
            logger.info(f"📖 Retrieved session {session_id} for user {user_id}")
        return session
    
    @staticmethod
    async def get_session_messages(
        db: AsyncSession,
        session_id: int,
        user_id: int
    ) -> list[ChatMessage]:
        """Get all active messages in a session (excludes soft-deleted)."""
        result = await db.execute(
            select(ChatMessage).where(
                ChatMessage.session_id == session_id,
                ChatMessage.user_id == user_id,
                ChatMessage.is_deleted == False  # ✅ Exclude soft-deleted
            ).order_by(ChatMessage.created_at)
        )
        messages = result.scalars().all()
        logger.info(f"📨 Retrieved {len(messages)} active messages from session {session_id}")
        return messages
    
    @staticmethod
    async def get_user_sessions(
        db: AsyncSession,
        user_id: int,
        analysis_id: Optional[int] = None
    ) -> list[ChatSession]:
        """Get all sessions for user, optionally filtered by analysis_id.
        Ordered by updated_at DESC (most recent first)."""
        from sqlalchemy.orm import selectinload
        
        try:
            if analysis_id:
                result = await db.execute(
                    select(ChatSession)
                    .where(
                        ChatSession.user_id == user_id,
                        ChatSession.analysis_id == analysis_id
                    )
                    .options(selectinload(ChatSession.messages))
                    .order_by(ChatSession.updated_at.desc())
                )
            else:
                # ✅ FIX: Explicitly filter for universal sessions (analysis_id IS NULL)
                result = await db.execute(
                    select(ChatSession)
                    .where(
                        ChatSession.user_id == user_id,
                        ChatSession.analysis_id.is_(None)  # ✅ Only universal sessions
                    )
                    .options(selectinload(ChatSession.messages))
                    .order_by(ChatSession.updated_at.desc())
                )
            
            sessions = result.scalars().unique().all()
            logger.info(f"📚 Retrieved {len(sessions)} sessions for user {user_id} (analysis_id={analysis_id})")
            return sessions
            
        except Exception as e:
            logger.error(f"Error fetching sessions: {e}", exc_info=True)
            raise
    
    @staticmethod
    async def update_session_timestamp(
        db: AsyncSession,
        session_id: int,
        user_id: int
    ) -> None:
        """Update session's updated_at timestamp (called when new message added)."""
        await db.execute(
            update(ChatSession)
            .where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            )
            .values(updated_at=datetime.utcnow())
        )
        await db.commit()
        logger.info(f"🔄 Updated timestamp for session {session_id}")
    
    @staticmethod
    async def delete_session(
        db: AsyncSession,
        session_id: int,
        user_id: int
    ) -> bool:
        """Soft-delete a session AND all its messages."""
        session = await ChatSessionService.get_session(db, session_id, user_id)

        if not session:
            logger.warning(f"Session {session_id} not found or already deleted for user {user_id}")
            return False

        now = datetime.utcnow()

        #  Soft-delete all messages in this session
        await db.execute(
            update(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .values(is_deleted=True, deleted_at=now)
        )

        #  Soft-delete the session
        await db.execute(
            update(ChatSession)
            .where(
                ChatSession.id == session_id,
                ChatSession.user_id == user_id
            )
            .values(is_deleted=True, deleted_at=now)
        )

        await db.commit()

        logger.info(f"🗑️  Soft-deleted session {session_id} and all its messages for user {user_id}")
        return True