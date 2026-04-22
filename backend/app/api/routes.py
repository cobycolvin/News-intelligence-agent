import logging
from threading import Event, Lock, Thread
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.core.dependencies import get_ingestion_task_store, get_orchestrator
from app.models.schemas import IngestionTaskRequest, IngestionTaskResponse, NewsQuery, PipelineResponse
from app.services.ingestion_tasks import IngestionTask, IngestionTaskStore, TERMINAL_TASK_STATES
from app.services.orchestrator import NewsPipelineOrchestrator

router = APIRouter(prefix="/api", tags=["news"])
logger = logging.getLogger(__name__)
_MISSING = object()


def _ensure_live_ingestion_enabled(orchestrator: NewsPipelineOrchestrator) -> None:
    retrieval_agent = orchestrator.retrieval_agent
    if not retrieval_agent.live_ingestion_enabled or retrieval_agent.ingestion_service is None:
        raise HTTPException(
            status_code=503,
            detail="Live ingestion is not enabled. Configure live ingestion settings and a news API key first.",
        )


def _task_to_response(task: IngestionTask) -> IngestionTaskResponse:
    progress_percent: float | None = None
    if task.progress_total > 0:
        progress_percent = round(min(100.0, max(0.0, (task.progress_current / task.progress_total) * 100.0)), 2)
    return IngestionTaskResponse(
        task_id=task.task_id,
        state=task.state,
        query=task.query,
        indexed_articles=task.indexed_articles,
        error=task.error,
        message=task.message,
        progress_current=task.progress_current,
        progress_total=task.progress_total,
        progress_percent=progress_percent,
        meta=dict(task.meta),
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/analyze", response_model=PipelineResponse)
async def analyze_news(
    payload: NewsQuery,
    orchestrator: NewsPipelineOrchestrator = Depends(get_orchestrator),
) -> PipelineResponse:
    return await orchestrator.run(payload)


def _run_ingestion_job(orchestrator: NewsPipelineOrchestrator, task_store: IngestionTaskStore, task_id: str, query: NewsQuery) -> None:
    snapshot_lock = Lock()
    heartbeat_stop = Event()
    snapshot: dict[str, Any] = {
        "state": "warming_embeddings",
        "message": "Preparing embedding model and baseline index.",
        "progress_current": 0,
        "progress_total": 1,
        "meta": {},
    }

    def _publish(
        *,
        state: str,
        message: str | None = None,
        progress_current: int | None = None,
        progress_total: int | None = None,
        indexed_articles: int | None = None,
        error: str | None | object = _MISSING,
        meta: dict[str, Any] | None = None,
    ) -> None:
        with snapshot_lock:
            current_meta = dict(snapshot.get("meta") or {})
            if meta:
                current_meta.update(meta)
            snapshot["state"] = state
            if message is not None:
                snapshot["message"] = message
            if progress_current is not None:
                snapshot["progress_current"] = progress_current
            if progress_total is not None:
                snapshot["progress_total"] = progress_total
            snapshot["meta"] = current_meta
            update_kwargs: dict[str, Any] = {
                "state": snapshot["state"],
                "message": snapshot.get("message"),
                "progress_current": snapshot.get("progress_current"),
                "progress_total": snapshot.get("progress_total"),
                "indexed_articles": indexed_articles,
                "meta": current_meta,
            }
            if error is not _MISSING:
                update_kwargs["error"] = error
        task_store.update(task_id=task_id, **update_kwargs)

    def _heartbeat() -> None:
        while not heartbeat_stop.wait(2):
            with snapshot_lock:
                if snapshot.get("state") in TERMINAL_TASK_STATES:
                    return
                state = snapshot.get("state", "warming_embeddings")
                message = snapshot.get("message")
                progress_current = snapshot.get("progress_current")
                progress_total = snapshot.get("progress_total")
                meta = dict(snapshot.get("meta") or {})
            task_store.update(
                task_id=task_id,
                state=state,
                message=message,
                progress_current=progress_current,
                progress_total=progress_total,
                meta=meta,
            )

    def _progress_callback(**kwargs: Any) -> None:
        _publish(
            state=kwargs.get("state", "indexing_articles"),
            message=kwargs.get("message"),
            progress_current=kwargs.get("progress_current"),
            progress_total=kwargs.get("progress_total"),
            meta=kwargs.get("meta"),
        )

    heartbeat_thread = Thread(target=_heartbeat, daemon=True)
    try:
        _publish(
            state="warming_embeddings",
            message="Preparing embedding model and baseline index.",
            progress_current=0,
            progress_total=1,
            meta={"query": query.query},
        )
        heartbeat_thread.start()
        indexed_articles = orchestrator.retrieval_agent.ingest_query(query, progress_callback=_progress_callback)
        if indexed_articles == 0:
            _publish(
                state="failed",
                indexed_articles=0,
                message="Ingestion finished but no new live articles were indexed.",
                error="No new live articles were indexed for the query.",
                progress_current=1,
                progress_total=1,
            )
            return
        _publish(
            state="completed",
            indexed_articles=indexed_articles,
            message=f"Live ingestion completed. Indexed {indexed_articles} articles.",
            error=None,
            progress_current=1,
            progress_total=1,
            meta={"indexed_articles": indexed_articles},
        )
    except Exception as exc:
        logger.exception("Live ingestion task failed for query=%s", query.query)
        _publish(
            state="failed",
            message="Live ingestion failed.",
            error=str(exc),
            progress_current=1,
            progress_total=1,
        )
    finally:
        heartbeat_stop.set()
        heartbeat_thread.join(timeout=2)
        task = task_store.get(task_id)
        if task is not None and task.state not in TERMINAL_TASK_STATES:
            task_store.update(
                task_id=task_id,
                state="failed",
                message="Live ingestion stopped before reaching a terminal state.",
                error="Ingestion ended unexpectedly before completion.",
                progress_current=1,
                progress_total=1,
            )


@router.post("/ingest", response_model=IngestionTaskResponse)
def start_ingestion(
    payload: IngestionTaskRequest,
    background_tasks: BackgroundTasks,
    orchestrator: NewsPipelineOrchestrator = Depends(get_orchestrator),
    task_store: IngestionTaskStore = Depends(get_ingestion_task_store),
) -> IngestionTaskResponse:
    _ensure_live_ingestion_enabled(orchestrator)
    query = NewsQuery(query=payload.query, max_articles=payload.max_articles)
    task = task_store.create(payload.query)
    background_tasks.add_task(_run_ingestion_job, orchestrator, task_store, task.task_id, query)
    return _task_to_response(task)


@router.get("/status/{task_id}", response_model=IngestionTaskResponse)
def ingestion_status(
    task_id: str,
    task_store: IngestionTaskStore = Depends(get_ingestion_task_store),
) -> IngestionTaskResponse:
    task = task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return _task_to_response(task)
