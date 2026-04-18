from datetime import date
from typing import List, Literal, Optional
from pydantic import BaseModel, Field


class NewsQuery(BaseModel):
    query: str = Field(min_length=3)
    max_articles: int = Field(default=5, ge=1, le=15)
    report_depth: Literal["brief", "in_depth"] = "brief"
    topic: Optional[str] = None
    date_from: Optional[date] = None
    date_to: Optional[date] = None


class ArticleSource(BaseModel):
    id: str
    title: str
    source: str
    date: str
    url: str
    image_path: Optional[str] = None


class RankedArticle(ArticleSource):
    relevance_score: float
    snippet: str
    cleaned_text: str


class VisualInsight(BaseModel):
    article_id: str
    image_summary: str
    detected_theme: str
    relevance_to_article: str
    notable_visual_elements: List[str]
    confidence_score: float


class EvidenceRef(BaseModel):
    article_id: str
    title: str
    url: str


class ReportSection(BaseModel):
    heading: str
    content: str
    evidence: List[EvidenceRef] = Field(default_factory=list)


class ConfidenceAssessment(BaseModel):
    score: float
    notes: str
    uncertainty_factors: List[str] = Field(default_factory=list)


class SynthesisInput(BaseModel):
    query: NewsQuery
    ranked_articles: List[RankedArticle]
    visual_insights: List[VisualInsight]


class FinalReport(BaseModel):
    query: str
    executive_summary: str
    sections: List[ReportSection]
    confidence: ConfidenceAssessment
    sources: List[ArticleSource]
    markdown_export: str
    generated_at: str


class PipelineResponse(BaseModel):
    query: NewsQuery
    ranked_articles: List[RankedArticle]
    visual_insights: List[VisualInsight]
    final_report: FinalReport


class IngestionTaskRequest(BaseModel):
    query: str = Field(min_length=3)
    max_articles: int = Field(default=10, ge=1, le=50)


class IngestionTaskResponse(BaseModel):
    task_id: str
    state: str
    query: str
    indexed_articles: int = 0
    error: Optional[str] = None
    created_at: str
    updated_at: str
