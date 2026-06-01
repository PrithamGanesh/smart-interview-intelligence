"""ML model pre-loader - initializes models during app startup."""

import asyncio
import logging
from typing import Optional
from hashlib import sha256

logger = logging.getLogger(__name__)

_sentence_transformer_model = None
_embedding_cache = {}  # text_hash -> embedding vector
_cache_stats = {"hits": 0, "misses": 0, "size": 0}


async def preload_models() -> None:
    """Pre-load ML models during application startup.
    
    Eliminates 5-30 second cold start delay on first request.
    """
    global _sentence_transformer_model
    
    logger.info("Pre-loading ML models (this happens once at startup)...")
    
    try:
        from sentence_transformers import SentenceTransformer
        from app.core.config import get_settings
        
        settings = get_settings()
        
        logger.info(f"Loading {settings.embedding_model_name}...")
        _sentence_transformer_model = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: SentenceTransformer(settings.embedding_model_name)
        )
        logger.info(f"✓ Model loaded successfully ({settings.embedding_model_name})")
        
    except ImportError:
        logger.warning("sentence-transformers not installed, using TF-IDF fallback")
        _sentence_transformer_model = None
    except Exception as e:
        logger.warning(f"Failed to load Sentence Transformer: {e}, will use TF-IDF fallback")
        _sentence_transformer_model = None


def get_embedding_model():
    """Get pre-loaded Sentence Transformer model or None."""
    return _sentence_transformer_model


async def compute_embedding(text: str) -> Optional[list]:
    """Compute embedding with caching.
    
    Args:
        text: Text to embed
        
    Returns:
        Embedding vector as list, or None if model not available
    """
    global _embedding_cache, _cache_stats
    
    if not text or not text.strip():
        return None
    
    text_hash = sha256(text.encode()).hexdigest()
    
    # Check cache first
    if text_hash in _embedding_cache:
        _cache_stats["hits"] += 1
        logger.debug(f"Embedding cache hit for {text_hash}")
        return _embedding_cache[text_hash]
    
    _cache_stats["misses"] += 1
    
    model = get_embedding_model()
    if model is None:
        logger.debug("No embedding model available, returning None")
        return None
    
    try:
        # Compute in thread pool to avoid blocking event loop
        loop = asyncio.get_event_loop()
        embedding = await loop.run_in_executor(
            None,
            lambda: model.encode(text, convert_to_tensor=False).tolist()
        )
        
        # Cache with size limit (keep only 10K embeddings = ~40MB)
        if len(_embedding_cache) >= 10000:
            # Remove oldest entry (FIFO)
            oldest_key = next(iter(_embedding_cache))
            del _embedding_cache[oldest_key]
            logger.debug("Embedding cache exceeded 10K entries, removed oldest")
        
        _embedding_cache[text_hash] = embedding
        _cache_stats["size"] = len(_embedding_cache)
        
        return embedding
        
    except Exception as e:
        logger.error(f"Failed to compute embedding: {e}")
        return None


def get_cache_stats() -> dict:
    """Get embedding cache statistics."""
    return {
        "hits": _cache_stats["hits"],
        "misses": _cache_stats["misses"],
        "size": _cache_stats["size"],
        "hit_ratio": _cache_stats["hits"] / max(1, _cache_stats["hits"] + _cache_stats["misses"]),
    }


def clear_embedding_cache() -> None:
    """Clear embedding cache (for testing/cleanup)."""
    global _embedding_cache, _cache_stats
    _embedding_cache.clear()
    _cache_stats = {"hits": 0, "misses": 0, "size": 0}
    logger.info("Embedding cache cleared")
