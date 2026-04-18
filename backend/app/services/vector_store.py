from __future__ import annotations

import logging
import re
from typing import List, Protocol
import numpy as np

logger = logging.getLogger(__name__)


class VectorStore(Protocol):
    def upsert(self, item_id: str, embedding: np.ndarray) -> None:
        ...

    def search(self, query_embedding: np.ndarray, top_k: int) -> List[tuple[str, float]]:
        ...

    def clear(self) -> None:
        ...


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

    def clear(self) -> None:
        self.ids.clear()
        self.embeddings.clear()


class PgVectorStore:
    def __init__(self, database_url: str, table_name: str = "article_embeddings", dimension: int = 32):
        self.database_url = database_url
        self.table_name = self._validate_table_name(table_name)
        self.dimension = max(1, int(dimension))
        self._enabled = False
        self._psycopg = None
        self._sql = None
        self._init_driver_and_table()

    @property
    def enabled(self) -> bool:
        return self._enabled

    def _init_driver_and_table(self) -> None:
        try:
            import psycopg  # type: ignore
            from psycopg import sql as psycopg_sql  # type: ignore

            self._psycopg = psycopg
            self._sql = psycopg_sql
        except Exception as exc:
            logger.warning("psycopg is unavailable, pgvector store disabled: %s", exc)
            self._enabled = False
            return

        try:
            with self._psycopg.connect(self.database_url) as conn:
                with conn.cursor() as cur:
                    cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
                    cur.execute(
                        self._sql.SQL(
                            "CREATE TABLE IF NOT EXISTS {} (item_id TEXT PRIMARY KEY, embedding VECTOR({}) NOT NULL)"
                        ).format(
                            self._sql.Identifier(self.table_name),
                            self._sql.SQL(str(self.dimension)),
                        )
                    )
                    conn.commit()
            self._enabled = True
        except Exception as exc:
            logger.warning("pgvector initialization failed, falling back to in-memory: %s", exc)
            self._enabled = False

    def upsert(self, item_id: str, embedding: np.ndarray) -> None:
        if not self._enabled or self._psycopg is None:
            return
        emb = self._to_pgvector(embedding)
        with self._psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    self._sql.SQL(
                        "INSERT INTO {} (item_id, embedding) VALUES (%s, %s::vector) "
                        "ON CONFLICT (item_id) DO UPDATE SET embedding = EXCLUDED.embedding"
                    ).format(self._sql.Identifier(self.table_name)),
                    (item_id, emb),
                )
                conn.commit()

    def search(self, query_embedding: np.ndarray, top_k: int) -> List[tuple[str, float]]:
        if not self._enabled or self._psycopg is None:
            return []
        emb = self._to_pgvector(query_embedding)
        with self._psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    self._sql.SQL(
                        "SELECT item_id, 1 - (embedding <=> %s::vector) AS score "
                        "FROM {} ORDER BY embedding <=> %s::vector LIMIT %s"
                    ).format(self._sql.Identifier(self.table_name)),
                    (emb, emb, top_k),
                )
                rows = cur.fetchall()
        return [(row[0], float(row[1])) for row in rows]

    def clear(self) -> None:
        if not self._enabled or self._psycopg is None:
            return
        with self._psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(self._sql.SQL("TRUNCATE TABLE {}").format(self._sql.Identifier(self.table_name)))
                conn.commit()

    def _to_pgvector(self, embedding: np.ndarray) -> str:
        vector = np.asarray(embedding, dtype=float)
        if vector.size != self.dimension:
            raise ValueError(
                f"Embedding dimension mismatch: expected {self.dimension}, got {vector.size}. "
                "Update VECTOR_STORE_DIMENSION or embedding model."
            )
        return "[" + ",".join(f"{x:.8f}" for x in vector.tolist()) + "]"

    def _validate_table_name(self, table_name: str) -> str:
        candidate = (table_name or "").strip()
        if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", candidate):
            raise ValueError("Invalid vector store table name")
        return candidate


def create_vector_store(
    backend: str,
    database_url: str | None = None,
    table_name: str = "article_embeddings",
    dimension: int = 32,
) -> VectorStore:
    normalized = (backend or "memory").strip().lower()
    if normalized == "pgvector" and database_url:
        pg_store = PgVectorStore(database_url=database_url, table_name=table_name, dimension=dimension)
        if pg_store.enabled:
            return pg_store
        logger.warning("Using in-memory vector store because pgvector backend is unavailable.")
    return InMemoryVectorStore()
