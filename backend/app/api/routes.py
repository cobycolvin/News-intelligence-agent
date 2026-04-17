from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException

from app.core.dependencies import get_ingestion_task_store, get_orchestrator
from app.models.schemas import IngestionTaskRequest, IngestionTaskResponse, NewsQuery, PipelineResponse
from app.services.ingestion_tasks import IngestionTaskStore
from app.services.orchestrator import NewsPipelineOrchestrator

router = APIRouter(prefix="/api", tags=["news"])


def _ensure_live_ingestion_enabled(orchestrator: NewsPipelineOrchestrator) -> None:
    retrieval_agent = orchestrator.retrieval_agent
    if not retrieval_agent.live_ingestion_enabled or retrieval_agent.ingestion_service is None:
        raise HTTPException(
            status_code=503,
            detail="Live ingestion is not enabled. Configure live ingestion settings and a news API key first.",
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
    task_store.update(task_id, state="running")
    try:
        indexed_articles = orchestrator.retrieval_agent.ingest_query(query)
        if indexed_articles == 0:
            task_store.update(
                task_id,
                state="failed",
                indexed_articles=0,
                error="No new live articles were indexed for the query.",
            )
            return
        task_store.update(task_id, state="completed", indexed_articles=indexed_articles)
    except Exception as exc:
        task_store.update(task_id, state="failed", error=str(exc))


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
    return IngestionTaskResponse(
        task_id=task.task_id,
        state=task.state,
        query=task.query,
        indexed_articles=task.indexed_articles,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.get("/status/{task_id}", response_model=IngestionTaskResponse)
def ingestion_status(
    task_id: str,
    task_store: IngestionTaskStore = Depends(get_ingestion_task_store),
) -> IngestionTaskResponse:
    task = task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return IngestionTaskResponse(
        task_id=task.task_id,
        state=task.state,
        query=task.query,
        indexed_articles=task.indexed_articles,
        error=task.error,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )
