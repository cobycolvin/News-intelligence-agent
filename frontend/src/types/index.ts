export interface NewsQuery {
  query: string
  max_articles: number
  topic?: string
  date_from?: string
  date_to?: string
}

export interface RankedArticle {
  id: string
  title: string
  source: string
  date: string
  url: string
  image_path?: string
  relevance_score: number
  snippet: string
  cleaned_text: string
}

export interface VisualInsight {
  article_id: string
  image_summary: string
  detected_theme: string
  relevance_to_article: string
  notable_visual_elements: string[]
  confidence_score: number
}

export interface ReportSection {
  heading: string
  content: string
  evidence: { article_id: string; title: string; url: string }[]
}

export interface FinalReport {
  query: string
  executive_summary: string
  sections: ReportSection[]
  markdown_export: string
  generated_at: string
  sources: {
    id: string
    title: string
    source: string
    date: string
    url: string
    image_path?: string
  }[]
}

export interface PipelineResponse {
  query: NewsQuery
  ranked_articles: RankedArticle[]
  visual_insights: VisualInsight[]
  final_report: FinalReport
}
