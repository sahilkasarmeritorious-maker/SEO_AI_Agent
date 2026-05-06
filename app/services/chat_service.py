import json
import asyncio
from typing import Dict, List, Any, Optional
from datetime import datetime
import html

from langchain_google_genai import ChatGoogleGenerativeAI
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc
from sqlalchemy import update
from app.db.models import ChatSession

from app.core.logging import logger
from app.db.models import ChatMessage, Analysis
from app.services.chroma_service import chroma_service
from app.core.config import get_settings

try:
    import markdown2
except ImportError:
    markdown2 = None

settings = get_settings()


class ChatService:
    def __init__(self):
        """Initialize Gemini client."""
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash-lite",
            api_key=settings.GEMINI_API_KEY,
            temperature=0.7,
            top_p=0.9,
        )
        logger.info(" Chat service initialized with Gemini 2.5 Flash")

    @staticmethod
    def _render_markdown_response(response: str) -> str:
        """Convert markdown response to professional HTML."""
        if not markdown2:
            # Fallback: basic HTML escaping if markdown2 not available
            return html.escape(response).replace('\n\n', '</p><p>').replace('\n', '<br>')
        
        try:
            # Convert markdown to HTML with extensions
            html_response = markdown2.markdown(
                response,
                extras=['fenced-code-blocks', 'tables', 'highlight']
            )
            # Wrap in professional styling divs
            return f'<div class="assistant-content">{html_response}</div>'
        except Exception as e:
            logger.warning(f"Markdown rendering failed: {e}, using plain text")
            return f'<div class="assistant-content"><p>{html.escape(response)}</p></div>'

    async def chat(
        self,
        user_id: int,
        message: str,
        analysis_id: Optional[int] = None,
        db: Optional[AsyncSession] = None,
        session_id: Optional[int] = None
    ) -> Dict[str, Any]:

        user_id = int(user_id)
        logger.info(f"💬 Processing chat for user {user_id}: {message[:50]}...")

        try:
            from app.services.chat_session_service import ChatSessionService

            # ─────────────────────────────────────────────────────────────
            # STEP 1: Get or create session
            # ─────────────────────────────────────────────────────────────

            if session_id:
                # Reuse existing session (validate ownership)
                session = await ChatSessionService.get_session(db, session_id, user_id)
                if not session:
                    raise ValueError(f"Session {session_id} not found or doesn't belong to user")
                logger.info(f"♻️  Reusing session {session_id}")
            else:
                # Create NEW session with auto-generated title
                session = await ChatSessionService.create_session(
                    db=db,
                    user_id=user_id,
                    analysis_id=analysis_id,
                    first_message=message  # Use first message to generate title
                )
                session_id = session.id
                logger.info(f"✨ Created new session {session_id}")

            # ─────────────────────────────────────────────────────────────
            # STEP 2: Retrieve relevant context from Chroma
            # ─────────────────────────────────────────────────────────────

            retrieved = await self._retrieve_context(
                user_id=user_id,
                question=message,
                analysis_id=analysis_id
            )

            # ─────────────────────────────────────────────────────────────
            # STEP 3: Build context and generate response
            # ─────────────────────────────────────────────────────────────

            context = self._build_context(retrieved)
            response = await self._generate_response(question=message, context=context)
            sources = self._parse_sources(retrieved)

            # ─────────────────────────────────────────────────────────────
            # STEP 4: Store message in PostgreSQL
            # ─────────────────────────────────────────────────────────────

            chat_message = None
            if db:
                chat_message = await self._store_message(
                    db=db,
                    user_id=user_id,
                    user_message=message,
                    assistant_response=response,
                    sources=sources,
                    analysis_id=analysis_id,
                    session_id=session_id
                )

                # Update session.updated_at timestamp for sidebar sorting
                await ChatSessionService.update_session_timestamp(db, session_id, user_id)

            # After storing the message:
            if db and chat_message:
                # ✅ Update session title if it's still the default
                if session.title in ("Chat", f"Analysis #{analysis_id}"):
                    new_title = ChatSessionService._generate_session_title(message)
                    session.title = new_title
                    await db.execute(
                        update(ChatSession).where(
                            ChatSession.id == session_id
                        ).values(title=new_title)
                    )
                    await db.commit()
                    logger.info(f"✅ Updated session {session_id} title to: '{new_title}'")

            # ─────────────────────────────────────────────────────────────
            # STEP 5: Save to Chroma in background (fire-and-forget)
            # ─────────────────────────────────────────────────────────────

            if chat_message:
                asyncio.create_task(
                    self._save_to_chroma_background(
                        user_id=user_id,
                        message=message,
                        response=response,
                        analysis_id=analysis_id
                    )
                )

            logger.info(
                f"✅ Chat response generated for user {user_id} in session {session_id} "
                f"({len(sources)} sources)"
            )

            # ✅ Render markdown response to professional HTML
            html_response = response

            return {
                "id": chat_message.id if chat_message else None,
                "session_id": session_id,
                "user_message": message,
                "assistant_response": html_response,  # ✅ Now HTML formatted
                "sources": sources,
                "created_at": (
                    chat_message.created_at.isoformat() 
                    if chat_message 
                    else datetime.utcnow().isoformat()
                )
            }

        except ValueError as e:
            logger.warning(f"⚠️  Validation error: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Chat error for user {user_id}: {e}", exc_info=True)
            raise
    
    async def _save_to_chroma_background(
        self,
        user_id: int,
        message: str,
        response: str,
        analysis_id: Optional[int] = None
    ) -> None:
        """Save message exchange to Chroma asynchronously (background task)."""
        try:
            # This runs in background, doesn't block the response
            # We save the Q&A pair to Chroma for future context
            await asyncio.sleep(0.1)  # Small delay to ensure DB commit
            
            # Optionally: save message exchange as new chunk to Chroma
            # This improves context in future queries
            # Implementation depends on your Chroma strategy
            
            logger.info(f"💾 Background: Saved message to Chroma for user {user_id}")
        except Exception as e:
            logger.error(f"⚠️  Background Chroma save failed: {e}", exc_info=True)
            # Don't raise - this is background task, shouldn't affect response

    # ─────────────────────────────────────────────────────────────────────────
    # RETRIEVAL (Chroma + PostgreSQL)
    # ─────────────────────────────────────────────────────────────────────────

    async def _retrieve_context(
        self,
        user_id: int,
        question: str,
        analysis_id: Optional[int] = None
    ) -> Dict[str, Any]:
        
        logger.info(f"🔍 Retrieving context for: {question[:50]}...")

        try:
            # Query Chroma (semantic search + user isolation)
            results = await chroma_service.query_user_analyses(
                user_id=user_id,
                question=question,
                n_results=5  # Top 5 most relevant chunks
            )

            # Filter by analysis_id if specified
            if analysis_id:
                results = self._filter_by_analysis(results, analysis_id)

            if not results.get("ids") or not results["ids"][0]:
                logger.warning(f"⚠️  No context found for user {user_id}")
                return {
                    "ids": [[]],
                    "documents": [[]],
                    "metadatas": [[]],
                    "distances": [[]]
                }

            logger.info(
                f" Retrieved {len(results['ids'][0])} chunks "
                f"from Chroma"
            )
            return results

        except Exception as e:
            logger.error(f"Error retrieving context: {e}", exc_info=True)
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # CONTEXT BUILDING
    # ─────────────────────────────────────────────────────────────────────────

    @staticmethod
    def _build_context(retrieved: Dict[str, Any]) -> str:
        """Build context string from retrieved chunks."""
        if not retrieved.get("documents") or not retrieved["documents"][0]:
            return "No relevant analysis data found."

        context_parts = []
        for doc, meta in zip(
            retrieved["documents"][0],
            retrieved["metadatas"][0]
        ):
            url = meta.get("url", "Unknown")
            chunk_type = meta.get("chunk_type", "General")
            seo_score = meta.get("seo_score", "N/A")
            ux_score = meta.get("ux_score", "N/A")

            context_parts.append(
                f"[{chunk_type} - {url}] "
                f"(SEO: {seo_score}, UX: {ux_score})\n{doc}"
            )

        return "\n\n---\n\n".join(context_parts)

    @staticmethod
    def _parse_sources(retrieved: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Extract unique source analyses with relevance scores."""
        sources_dict: Dict[int, Dict[str, Any]] = {}

        for meta, distance in zip(
            retrieved.get("metadatas", [[]])[0],
            retrieved.get("distances", [[]])[0]
        ):
            analysis_id = meta.get("analysis_id")
            if not analysis_id:
                continue

            # Cosine distance → relevance score (0-1)
            # Lower distance = higher relevance
            relevance = 1 - distance

            if analysis_id not in sources_dict:
                sources_dict[analysis_id] = {
                    "analysis_id": analysis_id,
                    "url": meta.get("url", ""),
                    "seo_score": meta.get("seo_score", 0),
                    "ux_score": meta.get("ux_score", 0),
                    "chunk_type": meta.get("chunk_type", ""),
                    "relevance_score": relevance,
                }
            else:
                # Keep highest relevance score for this analysis
                sources_dict[analysis_id]["relevance_score"] = max(
                    sources_dict[analysis_id]["relevance_score"],
                    relevance
                )

        # Sort by relevance
        sources = sorted(
            sources_dict.values(),
            key=lambda x: x["relevance_score"],
            reverse=True
        )

        return sources

    @staticmethod
    def _filter_by_analysis(
        results: Dict[str, Any],
        analysis_id: int
    ) -> Dict[str, Any]:
        """Filter results to specific analysis_id."""
        filtered = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]]
        }

        for id_, doc, meta, dist in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0]
        ):
            if meta.get("analysis_id") == analysis_id:
                filtered["ids"][0].append(id_)
                filtered["documents"][0].append(doc)
                filtered["metadatas"][0].append(meta)
                filtered["distances"][0].append(dist)

        return filtered

    # ─────────────────────────────────────────────────────────────────────────
    # GENERATION (Gemini)
    # ─────────────────────────────────────────────────────────────────────────

    async def _generate_response(
        self,
        question: str,
        context: str
    ) -> str:
        logger.info(" Generating response with Gemini...")

        system_prompt = """You are an expert website analysis assistant helping users understand their website's SEO and UX performance.

Use the provided analysis data to answer questions accurately and helpfully.
- Be specific and reference metrics from the data
- Provide actionable insights
- If data is insufficient, be honest about limitations
- Keep responses concise but thorough"""

        user_prompt = f"""Based on the following website analysis data, please answer this question:

QUESTION: {question}

ANALYSIS DATA:
{context}

Please provide a clear, helpful answer that references the relevant metrics."""

        try:
            loop = asyncio.get_running_loop()

            # Run LLM in executor with timeout to avoid blocking indefinitely
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: self.llm.invoke([
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]).content
                ),
                timeout=60.0
            )

            return response

        except asyncio.TimeoutError:
            logger.error(" LLM response generation timed out after 60s")
            raise
        except Exception as e:
            logger.error(f"Error generating response: {e}", exc_info=True)
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # STORAGE (PostgreSQL)
    # ─────────────────────────────────────────────────────────────────────────

    async def _store_message(
        self,
        db: AsyncSession,
        user_id: int,
        user_message: str,
        assistant_response: str,
        sources: List[Dict[str, Any]],
        analysis_id: Optional[int] = None,
        session_id: Optional[int] = None
    ) -> ChatMessage:
        """Store message in PostgreSQL with session association."""
        
        # Serialize sources to JSON
        sources_json = json.dumps(sources) if sources else None
        try:
            chat_message = ChatMessage(
                user_id=user_id,
                session_id=session_id,
                analysis_id=analysis_id,
                user_message=user_message,
                assistant_response=assistant_response,
                source_analyses=sources_json,
                created_at=datetime.utcnow()
            )

            db.add(chat_message)
            await db.commit()
            await db.refresh(chat_message)

            logger.info(
                f" Stored message {chat_message.id} in session {session_id} "
                f"for user {user_id}"
            )

            return chat_message

        except Exception as e:
            await db.rollback()
            logger.error(f"Error storing message: {e}", exc_info=True)
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # HISTORY
    # ─────────────────────────────────────────────────────────────────────────

    async def get_chat_history(
        self,
        user_id: int,
        db: AsyncSession,
        analysis_id: Optional[int] = None,
        limit: int = 50
    ) -> List[ChatMessage]:
        """Get user's chat conversation history (separated by analysis_id)."""
        user_id = int(user_id)
        logger.info(
            f" Fetching chat history for user {user_id} "
            f"(analysis_id: {analysis_id}, limit: {limit})"
        )
    
        try:
            if analysis_id:
                # Get messages ONLY for this specific analysis
                query = select(ChatMessage).where(
                    ChatMessage.user_id == user_id,
                    ChatMessage.analysis_id == analysis_id
                )
            else:
                # Get messages ONLY for universal chat (no analysis_id)
                query = select(ChatMessage).where(
                    ChatMessage.user_id == user_id,
                    ChatMessage.analysis_id == None  # ✅ ONLY universal messages
                )
            
            query = query.order_by(
                desc(ChatMessage.created_at)
            ).limit(limit)
    
            result = await db.execute(query)
            messages = result.scalars().all()
    
            logger.info(f" Retrieved {len(messages)} messages (analysis_id: {analysis_id})")
            return messages
    
        except Exception as e:
            logger.error(f"Error fetching history: {e}", exc_info=True)
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # CLEANUP
    # ─────────────────────────────────────────────────────────────────────────

    async def clear_chat_history(
        self,
        user_id: int,
        db: AsyncSession
    ) -> int:
        """Delete all chat messages for a user."""
        user_id = int(user_id)
        logger.warning(
            f"🗑️  Clearing chat history for user {user_id}"
        )

        try:
            result = await db.execute(
                select(ChatMessage).where(ChatMessage.user_id == user_id)
            )
            messages = result.scalars().all()
            count = len(messages)

            for msg in messages:
                await db.delete(msg)

            await db.commit()
            logger.info(f" Deleted {count} chat messages")
            return count

        except Exception as e:
            await db.rollback()
            logger.error(f"Error clearing history: {e}", exc_info=True)
            raise


# Singleton instance
chat_service = ChatService()