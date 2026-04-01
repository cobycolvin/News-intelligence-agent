from __future__ import annotations

import logging
from typing import List
import numpy as np

logger = logging.getLogger(__name__)


class EmbeddingService:
    def __init__(self, model_name: str, mock_mode: bool = False):
        self.model_name = model_name
        self.mock_mode = mock_mode
        self._model = None
        if not mock_mode:
            try:
                from sentence_transformers import SentenceTransformer

                self._model = SentenceTransformer(model_name)
            except Exception as exc:  # graceful fallback
                logger.warning("Embedding model unavailable (%s). Falling back to hash embeddings.", exc)
                self.mock_mode = True

    def embed(self, texts: List[str]) -> np.ndarray:
        if self.mock_mode or self._model is None:
            return np.array([self._hash_embed(text) for text in texts], dtype=float)
        vectors = self._model.encode(texts, normalize_embeddings=True)
        return np.array(vectors)

    def _hash_embed(self, text: str, dim: int = 32) -> np.ndarray:
        vec = np.zeros(dim)
        for i, token in enumerate(text.lower().split()):
            vec[(hash(token) + i) % dim] += 1.0
        norm = np.linalg.norm(vec)
        return vec / norm if norm else vec
