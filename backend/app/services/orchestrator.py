from __future__ import annotations

from app.agents.retrieval_agent import RetrievalAgent
from app.agents.synthesis_agent import SynthesisAgent
from app.agents.vision_agent import VisionAgent
from app.models.schemas import NewsQuery, PipelineResponse, SynthesisInput


class NewsPipelineOrchestrator:
    def __init__(self, retrieval_agent: RetrievalAgent, vision_agent: VisionAgent, synthesis_agent: SynthesisAgent):
        self.retrieval_agent = retrieval_agent
        self.vision_agent = vision_agent
        self.synthesis_agent = synthesis_agent

    async def run(self, query: NewsQuery) -> PipelineResponse:
        ranked_articles = self.retrieval_agent.run(query)
        visual_insights = await self.vision_agent.run(ranked_articles)
        synthesis_input = SynthesisInput(query=query, ranked_articles=ranked_articles, visual_insights=visual_insights)
        final_report = await self.synthesis_agent.run(synthesis_input)
        return PipelineResponse(
            query=query,
            ranked_articles=ranked_articles,
            visual_insights=visual_insights,
            final_report=final_report,
        )
