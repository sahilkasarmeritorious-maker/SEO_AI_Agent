import asyncio
from sentence_transformers import SentenceTransformer
from app.core.logging import logger
from concurrent.futures import ThreadPoolExecutor

# Initialize once (singleton pattern)
_model = None
_executor = ThreadPoolExecutor(max_workers=2)

def get_embeddings_model():
    """Get or initialize sentence-transformers model"""
    global _model
    if _model is None:
        logger.info("Loading sentence-transformers model...")
        _model = SentenceTransformer('all-MiniLM-L6-v2')
        logger.info("Model loaded successfully")
    return _model

async def generate_embedding(text: str) -> list:
    """Async: Generate vector embedding for text"""
    loop = asyncio.get_event_loop()
    model = get_embeddings_model()
    
    # Run embedding generation in thread pool (non-blocking)
    embedding = await loop.run_in_executor(
        _executor,
        lambda: model.encode(text, convert_to_tensor=False)
    )
    return embedding.tolist()

async def generate_embeddings_batch(texts: list) -> list:
    """Async: Generate embeddings for multiple texts"""
    loop = asyncio.get_event_loop()
    model = get_embeddings_model()
    
    # Run batch encoding in thread pool
    embeddings = await loop.run_in_executor(
        _executor,
        lambda: model.encode(texts, convert_to_tensor=False)
    )
    return [e.tolist() for e in embeddings]