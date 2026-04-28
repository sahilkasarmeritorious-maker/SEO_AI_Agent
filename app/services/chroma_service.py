import chromadb
import json
import asyncio
from pathlib import Path
from app.core.logging import logger
from app.core.embeddings import generate_embedding
from concurrent.futures import ThreadPoolExecutor

# Thread pool for blocking Chroma operations
_executor = ThreadPoolExecutor(max_workers=3)

# Semaphore to limit concurrent Chroma operations
_semaphore = asyncio.Semaphore(5)

# Persistent storage path
CHROMA_PERSIST_PATH = "./chroma_db"


class ChromaService:
    """Async service for managing Chroma vector database (persistent)"""

    _instance = None
    _initialized = False  # FIX: separate flag so __init__ only runs once

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """Initialize Chroma client and collection — runs only once."""
        # FIX: guard with _initialized so re-calling ChromaService() never
        # reinitialises the client (old code used _client is None on a class
        # variable, but __init__ was still re-entered on every instantiation)
        if self._initialized:
            return

        logger.info("Initializing Chroma persistent client...")
        try:
            # FIX: Use PersistentClient so data survives restarts.
            # chromadb.Client() is purely in-memory — every restart loses everything.
            persist_path = Path(CHROMA_PERSIST_PATH)
            persist_path.mkdir(parents=True, exist_ok=True)

            self._client = chromadb.PersistentClient(path=str(persist_path))
            self._collection = self._client.get_or_create_collection(
                name="analyses",
                metadata={"hnsw:space": "cosine"}
            )
            ChromaService._initialized = True
            logger.info(f"Chroma initialized — persisting to '{persist_path.resolve()}'")
            logger.info(f"Collection 'analyses' has {self._collection.count()} existing documents")
        except Exception as e:
            logger.error(f"Chroma initialization failed: {e}")
            raise

    @property
    def client(self):
        return self._client

    @property
    def collection(self):
        return self._collection

    # ─────────────────────────────────────────────────────────────────────────
    # SAVE
    # ─────────────────────────────────────────────────────────────────────────

    async def save_analysis_to_chroma(self, user_id: int, analysis):
        """
        Save analysis data to Chroma as semantic chunks for RAG.

        Args:
            user_id:  User ID (from JWT) — stored as int for consistent filtering
            analysis: Analysis ORM object from PostgreSQL
        """
        logger.info(f"Saving analysis {analysis.id} for user {user_id} to Chroma")

        try:
            # FIX: ensure user_id is always a plain Python int (not np.int64 etc.)
            user_id = int(user_id)
            analysis_id = int(analysis.id)

            metadata_base = {
                "user_id": user_id,          # int — must be consistent with query filter
                "analysis_id": analysis_id,  # int
                "url": str(analysis.url),
                "seo_score": int(analysis.seo_overall_score or 0),
                "ux_score": int(analysis.ux_overall_score or 0),
                "status": str(analysis.status),
                "created_at": analysis.created_at.isoformat() if analysis.created_at else "",
            }

            # Map of (field_name, chunk_type_label) pairs to build chunks from
            field_map = [
                ("seo_strengths",      "SEO Strengths",       "seo_strengths"),
                ("seo_weaknesses",     "SEO Weaknesses",      "seo_weaknesses"),
                ("seo_missing_elements","SEO Missing Elements","seo_missing"),
                ("seo_recommendations","SEO Recommendations", "seo_recommendations"),
                ("ux_strengths",       "UX Strengths",        "ux_strengths"),
                ("ux_weaknesses",      "UX Weaknesses",       "ux_weaknesses"),
                ("ux_missing_elements","UX Missing Elements", "ux_missing"),
                ("ux_recommendations", "UX Recommendations",  "ux_recommendations"),
            ]

            chunks_to_add = []
            for attr, title, chunk_type in field_map:
                raw = getattr(analysis, attr, None)
                if not raw:
                    continue
                text = await self._format_findings(title, raw)
                chunks_to_add.append({
                    "id": f"analysis_{analysis_id}_{chunk_type}",
                    "document": text,
                    "metadata": {**metadata_base, "chunk_type": chunk_type},
                })

            if not chunks_to_add:
                logger.warning(f"No data to save for analysis {analysis_id}")
                return

            ids        = [c["id"]       for c in chunks_to_add]
            documents  = [c["document"] for c in chunks_to_add]
            metadatas  = [c["metadata"] for c in chunks_to_add]

            # FIX: use get_running_loop() instead of deprecated get_event_loop()
            loop = asyncio.get_running_loop()

            # Use upsert so re-running an analysis doesn't throw DuplicateIDError
            await loop.run_in_executor(
                _executor,
                lambda: self.collection.upsert(
                    ids=ids,
                    documents=documents,
                    metadatas=metadatas,
                )
            )

            # Verify the write actually landed
            count_after = await loop.run_in_executor(
                _executor,
                lambda: self.collection.count()
            )
            logger.info(
                f"Saved {len(ids)} chunks for analysis {analysis_id} to Chroma "
                f"(collection total: {count_after})"
            )

        except Exception as e:
            logger.error(f"Error saving analysis to Chroma: {e}", exc_info=True)
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # QUERY
    # ─────────────────────────────────────────────────────────────────────────

    async def query_user_analyses(self, user_id: int, question: str, n_results: int = 3):
        """
        Semantic search over a user's analyses.

        Args:
            user_id:   REQUIRED — filters results to this user only
            question:  Natural-language question
            n_results: How many chunks to return (capped to available docs)
        """
        if not user_id:
            raise ValueError("user_id is required for security")

        user_id = int(user_id)  # FIX: ensure consistent int type
        logger.info(f"Querying Chroma for user {user_id}: '{question}'")

        try:
            loop = asyncio.get_running_loop()
            question_embedding = await generate_embedding(question)

            # Use semaphore to limit concurrent Chroma operations
            async with _semaphore:
                results = await loop.run_in_executor(
                    _executor,
                    lambda: self.collection.query(
                        query_embeddings=[question_embedding],
                        n_results=n_results,
                        where={"user_id": {"$eq": user_id}},
                    )
                )

            # Security double-check: every returned doc must belong to this user
            if results and results.get("metadatas"):
                for meta_list in results["metadatas"]:
                    for meta in meta_list:
                        if int(meta.get("user_id", -1)) != user_id:
                            logger.error(
                                f"SECURITY BREACH: user {user_id} received "
                                f"data for user {meta.get('user_id')}"
                            )
                            raise PermissionError("Data isolation violation detected")

            found = len(results.get("ids", [[]])[0])
            logger.info(f"Chroma returned {found} results for user {user_id}")
            return results

        except Exception as e:
            logger.error(f"Error querying analyses: {e}", exc_info=True)
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # LIST
    # ─────────────────────────────────────────────────────────────────────────

    async def get_user_analyses_list(self, user_id: int) -> list:
        """Return one metadata entry per unique analysis for this user."""
        user_id = int(user_id)  # FIX: consistent int
        try:
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(
                _executor,
                lambda: self.collection.get(where={"user_id": {"$eq": user_id}})
            )

            analyses: dict = {}
            for metadata in (results.get("metadatas") or []):
                aid = metadata.get("analysis_id")
                if aid not in analyses:
                    analyses[aid] = metadata

            logger.info(f"Found {len(analyses)} unique analyses for user {user_id}")
            return list(analyses.values())

        except Exception as e:
            logger.error(f"Error getting user analyses: {e}", exc_info=True)
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # DELETE
    # ─────────────────────────────────────────────────────────────────────────

    async def delete_user_data(self, user_id: int):
        """Delete all Chroma data for a user."""
        user_id = int(user_id)
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                _executor,
                lambda: self.collection.delete(where={"user_id": {"$eq": user_id}})
            )
            logger.info(f"Deleted all Chroma data for user {user_id}")
        except Exception as e:
            logger.error(f"Error deleting user data: {e}", exc_info=True)
            raise

    async def delete_analysis(self, analysis_id: int):
        """Delete all chunks for a single analysis."""
        analysis_id = int(analysis_id)
        try:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                _executor,
                lambda: self.collection.delete(
                    where={"analysis_id": {"$eq": analysis_id}}
                )
            )
            logger.info(f"Deleted Chroma chunks for analysis {analysis_id}")
        except Exception as e:
            logger.error(f"Error deleting analysis {analysis_id}: {e}", exc_info=True)
            raise

    # ─────────────────────────────────────────────────────────────────────────
    # DEBUG HELPER
    # ─────────────────────────────────────────────────────────────────────────

    async def debug_collection_stats(self) -> dict:
        """Return basic stats — useful for diagnosing 'no data' issues."""
        loop = asyncio.get_running_loop()
        count = await loop.run_in_executor(_executor, lambda: self.collection.count())
        return {
            "collection": "analyses",
            "total_documents": count,
            "persist_path": str(Path(CHROMA_PERSIST_PATH).resolve()),
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PRIVATE HELPERS
    # ─────────────────────────────────────────────────────────────────────────

    async def _format_findings(self, title: str, json_data: str) -> str:
        """Convert JSON findings field to a readable text chunk."""
        try:
            loop = asyncio.get_running_loop()  # FIX: get_running_loop
            return await loop.run_in_executor(
                _executor,
                self._sync_format_findings,
                title,
                json_data,
            )
        except Exception as e:
            logger.error(f"Error formatting findings: {e}")
            return str(json_data)

    @staticmethod
    def _sync_format_findings(title: str, json_data) -> str:
        """Sync helper — runs in thread pool."""
        try:
            data = json.loads(json_data) if isinstance(json_data, str) else json_data
            lines = [f"{title}:"]

            if isinstance(data, list):
                for item in data:
                    if isinstance(item, dict):
                        text = item.get("finding") or item.get("recommendation") or str(item)
                    else:
                        text = str(item)
                    lines.append(f"- {text}")
            elif isinstance(data, dict):
                for k, v in data.items():
                    lines.append(f"- {k}: {v}")
            else:
                lines.append(str(data))

            return "\n".join(lines)
        except Exception:
            return str(json_data)


# Singleton instance
chroma_service = ChromaService()