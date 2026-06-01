"""Optimized embeddings with normalized cache keys and deduplication."""

import logging
from functools import lru_cache
from hashlib import sha256
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)


def _normalize_text(text: str) -> str:
    """Normalize text for consistent hashing and caching.
    
    Ensures that "python developer" and "developer python" produce
    the same cache key (normalized to "developer python").
    
    Args:
        text: Raw text
        
    Returns:
        Normalized text (lowercase, deduplicated words, sorted)
    """
    if not text:
        return ""
    
    # Lowercase and split
    words = text.lower().split()
    
    # Remove duplicates while preserving some order (deduplicate by set, then sort)
    unique_words = sorted(set(words))
    
    # Join back
    return " ".join(unique_words)


def _hash_text(text: str) -> str:
    """Compute SHA256 hash of normalized text.
    
    Args:
        text: Text to hash
        
    Returns:
        SHA256 hex digest
    """
    normalized = _normalize_text(text)
    return sha256(normalized.encode("utf-8")).hexdigest()


def _get_model():
    """Get or load Sentence Transformer model (uses preloaded version if available)."""
    try:
        from app.ml.model_loader import get_embedding_model
        model = get_embedding_model()
        if model is not None:
            return model
    except ImportError:
        pass
    
    # Fallback to loading on demand
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer(get_settings().embedding_model_name)
        logger.info(f"Loaded Sentence Transformer model: {get_settings().embedding_model_name}")
        return model
    except Exception as exc:
        logger.warning(f"Failed to load Sentence Transformer, using TF-IDF: {exc}")
        return None


@lru_cache(maxsize=512)
def _cosine_similarity_by_hash(
    left_hash: str,
    left_normalized: str,
    right_hash: str,
    right_normalized: str,
) -> float:
    """Cache similarity calculations by content hash (normalized).
    
    ✅ OPTIMIZATION: Uses normalized text so order doesn't matter
    "python developer" and "developer python" hit same cache entry
    
    Args:
        left_hash: SHA256 of left text
        left_normalized: Normalized left text
        right_hash: SHA256 of right text
        right_normalized: Normalized right text
        
    Returns:
        Similarity score 0-100
    """
    # Quick check: if hashes match, texts are identical
    if left_hash == right_hash:
        return 100.0
    
    model = _get_model()
    
    if model is not None:
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            
            # Encode normalized texts
            embeddings = model.encode([left_normalized, right_normalized])
            similarity = cosine_similarity(
                [embeddings[0]],
                [embeddings[1]]
            )[0][0]
            
            return round(float(similarity) * 100, 2)
        except Exception as e:
            logger.error(f"Error computing embedding similarity: {e}")
    
    # Fallback to TF-IDF
    try:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.metrics.pairwise import cosine_similarity
        
        matrix = TfidfVectorizer().fit_transform([left_normalized, right_normalized])
        similarity = cosine_similarity(matrix[0], matrix[1])[0][0]
        
        return round(float(similarity) * 100, 2)
    except Exception as e:
        logger.error(f"Error computing TF-IDF similarity: {e}")
        return 0.0


def cosine_similarity_score(left_text: str, right_text: str) -> float:
    """Return a 0-100 semantic similarity score with caching.
    
    ✅ OPTIMIZATION FEATURES:
    - Normalized text comparison (order doesn't matter)
    - Content-aware caching (same content = same cache key)
    - Deduplication (no double computation)
    - Uses pre-loaded model if available
    
    Args:
        left_text: First text (e.g., resume)
        right_text: Second text (e.g., job description)
        
    Returns:
        Similarity score from 0 to 100
    """
    if not left_text or not right_text:
        return 0.0
    
    left_normalized = _normalize_text(left_text)
    right_normalized = _normalize_text(right_text)
    
    left_hash = _hash_text(left_text)
    right_hash = _hash_text(right_text)
    
    return _cosine_similarity_by_hash(left_hash, left_normalized, right_hash, right_normalized)


def get_similarity_cache_stats() -> dict:
    """Get similarity calculation cache statistics."""
    return {
        "cache_info": _cosine_similarity_by_hash.cache_info()._asdict(),
        "cache_size": len(_cosine_similarity_by_hash.cache_info()),
    }


def clear_similarity_cache() -> None:
    """Clear similarity cache (for testing)."""
    _cosine_similarity_by_hash.cache_clear()
    logger.info("Similarity cache cleared")
