from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, Literal
from uuid import uuid4


TaskState = Literal[
    "queued",
    "warming_embeddings",
    "fetching_news_api",
    "extracting_article_text",
    "embedding_articles",
    "indexing_articles",
    "completed",
    "failed",
]

TERMINAL_TASK_STATES = {"completed", "failed"}
_UNSET = object()


@dataclass
class IngestionTask:
    task_id: str
    state: TaskState
    query: str
    created_at: str
    updated_at: str
    indexed_articles: int = 0
    error: str | None = None
    message: str | None = None
    progress_current: int = 0
    progress_total: int = 0
    meta: Dict[str, Any] = field(default_factory=dict)


class IngestionTaskStore:
    def __init__(self):
        self._lock = Lock()
        self._tasks: Dict[str, IngestionTask] = {}

    def create(self, query: str) -> IngestionTask:
        now = datetime.now(timezone.utc).isoformat()
        task = IngestionTask(
            task_id=uuid4().hex,
            state="queued",
            query=query,
            created_at=now,
            updated_at=now,
            message="Task queued.",
        )
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def update(
        self,
        task_id: str,
        state: TaskState,
        indexed_articles: int | None = None,
        error: str | None | object = _UNSET,
        message: str | None | object = _UNSET,
        progress_current: int | None | object = _UNSET,
        progress_total: int | None | object = _UNSET,
        meta: Dict[str, Any] | None = None,
        replace_meta: bool = False,
    ) -> IngestionTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            if task.state in TERMINAL_TASK_STATES and state not in TERMINAL_TASK_STATES:
                return task
            task.state = state
            task.updated_at = datetime.now(timezone.utc).isoformat()
            if indexed_articles is not None:
                task.indexed_articles = indexed_articles
            if error is not _UNSET:
                task.error = error
            if message is not _UNSET:
                task.message = message
            if progress_current is not _UNSET and progress_current is not None:
                task.progress_current = progress_current
            if progress_total is not _UNSET and progress_total is not None:
                task.progress_total = progress_total
            if meta is not None:
                if replace_meta:
                    task.meta = dict(meta)
                else:
                    task.meta.update(meta)
            return task

    def get(self, task_id: str) -> IngestionTask | None:
        with self._lock:
            return self._tasks.get(task_id)

    def is_terminal(self, task_id: str) -> bool:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return True
            return task.state in TERMINAL_TASK_STATES
