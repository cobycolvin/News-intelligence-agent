# API Documentation

## Base URL
`http://localhost:8000`

## Health Check
### `GET /api/health`
Response:
```json
{"status":"ok"}
```

## Analyze News Query
### `POST /api/analyze`
Runs full pipeline: retrieval → vision → synthesis.

Request body:
```json
{
  "query": "What are the latest developments in Red Sea shipping disruptions?",
  "max_articles": 5,
  "topic": "logistics",
  "date_from": "2026-03-01",
  "date_to": "2026-03-31"
}
```

Response fields (top-level):
- `query`
- `ranked_articles`
- `visual_insights`
- `final_report`

`final_report` includes:
- `executive_summary`
- `sections`
- `confidence`
- `sources`
- `markdown_export`
- `generated_at`
