from fastapi import APIRouter, Depends

from app.core.dependencies import get_orchestrator
from app.models.schemas import NewsQuery, PipelineResponse
from app.services.orchestrator import NewsPipelineOrchestrator

router = APIRouter(prefix="/api", tags=["news"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/analyze", response_model=PipelineResponse)
async def analyze_news(
    payload: NewsQuery,
    orchestrator: NewsPipelineOrchestrator = Depends(get_orchestrator),
) -> PipelineResponse:
    return await orchestrator.run(payload)
