from __future__ import annotations

from typing import List
import numpy as np


class InMemoryVectorStore:
    def __init__(self):
        self.ids: List[str] = []
        self.embeddings: list[np.ndarray] = []

    def upsert(self, item_id: str, embedding: np.ndarray) -> None:
        if item_id in self.ids:
            idx = self.ids.index(item_id)
            self.embeddings[idx] = embedding
        else:
            self.ids.append(item_id)
            self.embeddings.append(embedding)

    def search(self, query_embedding: np.ndarray, top_k: int) -> List[tuple[str, float]]:
        scores = []
        for item_id, emb in zip(self.ids, self.embeddings):
            score = float(np.dot(query_embedding, emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(emb) + 1e-8))
            scores.append((item_id, score))
        return sorted(scores, key=lambda x: x[1], reverse=True)[:top_k]
