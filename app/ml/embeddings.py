"""Embedding and similarity utilities.

The blueprint calls for Sentence Transformers all-MiniLM-L6-v2. When that
package/model is available, it is used. Otherwise the project falls back to a
local TF-IDF cosine similarity so endpoints remain runnable offline.
"""

from __future__ import annotations

from functools import lru_cache
from hashlib import sha256

from app.core.config import get_settings


@lru_cache
def _sentence_transformer():
    try:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(get_settings().embedding_model_name)
    except Exception:
        return None


def cosine_similarity_score(left_text: str, right_text: str) -> float:
    """Return a 0-100 semantic similarity score."""
    return _cosine_similarity_by_hash(_hash_text(left_text), left_text, _hash_text(right_text), right_text)


def _hash_text(text: str) -> str:
    return sha256((text or "").encode("utf-8")).hexdigest()


@lru_cache(maxsize=512)
def _cosine_similarity_by_hash(left_hash: str, left_text: str, right_hash: str, right_text: str) -> float:
    """Cache similarity calculations by content hash.

    The hash arguments make cache keys stable and explicit while keeping the
    implementation simple for this prototype.
    """
    model = _sentence_transformer()
    if model is not None:
        from sklearn.metrics.pairwise import cosine_similarity

        embeddings = model.encode([left_text, right_text])
        return round(float(cosine_similarity([embeddings[0]], [embeddings[1]])[0][0]) * 100, 2)

    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    matrix = TfidfVectorizer().fit_transform([left_text, right_text])
    return round(float(cosine_similarity(matrix[0], matrix[1])[0][0]) * 100, 2)
