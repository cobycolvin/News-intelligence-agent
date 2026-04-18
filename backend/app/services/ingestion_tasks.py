from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from typing import Dict, Literal
from uuid import uuid4


TaskState = Literal["queued", "running", "completed", "failed"]


@dataclass
class IngestionTask:
    task_id: str
    state: TaskState
    query: str
    created_at: str
    updated_at: str
    indexed_articles: int = 0
    error: str | None = None


class IngestionTaskStore:
    def __init__(self):
        self._lock = Lock()
        self._tasks: Dict[str, IngestionTask] = {}

    def create(self, query: str) -> IngestionTask:
        now = datetime.now(timezone.utc).isoformat()
        task = IngestionTask(task_id=uuid4().hex, state="queued", query=query, created_at=now, updated_at=now)
        with self._lock:
            self._tasks[task.task_id] = task
        return task

    def update(
        self,
        task_id: str,
        state: TaskState,
        indexed_articles: int | None = None,
        error: str | None = None,
    ) -> IngestionTask | None:
        with self._lock:
            task = self._tasks.get(task_id)
            if task is None:
                return None
            task.state = state
            task.updated_at = datetime.now(timezone.utc).isoformat()
            if indexed_articles is not None:
                task.indexed_articles = indexed_articles
            task.error = error
            return task

    def get(self, task_id: str) -> IngestionTask | None:
        with self._lock:
            return self._tasks.get(task_id)
