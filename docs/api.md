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

When `LIVE_INGESTION_ENABLED=true`, retrieval automatically fetches live articles before ranking (synchronous). When disabled, uses sample data only.

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

Response time:
- **Mock mode**: ~200-500ms (no network I/O)
- **Live mode**: ~2-8s (depends on NewsAPI latency and article extraction)

Empty-result semantics:
- Returns `200 OK` even when no ranked articles are found.
- `ranked_articles` and `visual_insights` may be empty lists.
- `final_report.sources` may be empty when no supporting articles are available.

`final_report` includes:
- `executive_summary`
- `sections`
- `confidence`
- `sources`
- `markdown_export`
- `generated_at`

Error semantics:
- `400 Bad Request`: Invalid query (min_length=3 for query string)
- `503 Service Unavailable`: Synthesis provider misconfigured (LLM unavailable)

## Start Live Ingestion
### `POST /api/ingest`
Queues a background live-ingestion job for the provided query.

**Requires**: `LIVE_INGESTION_ENABLED=true` and valid `NEWS_API_KEY`

Request body:
```json
{
  "query": "latest maritime disruption updates",
  "max_articles": 10
}
```

Success response (`200 OK`):
```json
{
  "task_id": "c2a5...",
  "state": "queued",
  "query": "latest maritime disruption updates",
  "indexed_articles": 0,
  "error": null,
  "created_at": "2026-04-16T18:40:00+00:00",
  "updated_at": "2026-04-16T18:40:00+00:00"
}
```

Behavior notes:
- Returns `503 Service Unavailable` when live ingestion is not enabled or the backend has no configured news API client.
- Background ingestion marks the task as `completed` when at least one new article is indexed.
- Background ingestion marks the task as `failed` when no new articles are indexed or an exception occurs.
- You **must poll** `/status/{task_id}` to check job progress.

State transitions:
```
queued → running → completed (success)
      ↓           ↓ failed (error or no articles)
```

Typical flow:
1. POST /api/ingest → get task_id
2. Poll GET /status/{task_id} every 1-2 seconds
3. When state == 'completed' or 'failed', read indexed_articles and error

Estimated duration: 5-15 seconds depending on article extraction

## Ingestion Status
### `GET /api/status/{task_id}`
Returns the latest state for a live-ingestion task.

Possible `state` values:
- `queued` - Task waiting to start
- `running` - Background ingestion in progress
- `completed` - Success! Check `indexed_articles` for count
- `failed` - Error occurred, check `error` field

Response example (completed):
```json
{
  "task_id": "c2a5...",
  "state": "completed",
  "query": "AI regulation",
  "indexed_articles": 15,
  "error": null,
  "created_at": "2026-04-16T18:40:00+00:00",
  "updated_at": "2026-04-16T18:40:15+00:00"
}
```

Response example (failed):
```json
{
  "task_id": "c2a5...",
  "state": "failed",
  "query": "AI regulation",
  "indexed_articles": 0,
  "error": "NewsAPI request failed: unauthorized (401)",
  "created_at": "2026-04-16T18:40:00+00:00",
  "updated_at": "2026-04-16T18:40:03+00:00"
}
```

Error semantics:
- `404 Not Found` - Task ID does not exist or expired
- `200 OK` with `state: "failed"` - Job completed with error (check `error` field)
