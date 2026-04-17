# Demo Walkthrough

## Goal
Show end-to-end multi-agent pipeline with source transparency in under 5 minutes.

## Pre-demo checklist
1. Backend running on port `8000`.
2. Frontend running on port `5173`.
3. `MOCK_MODE=true` for deterministic demo.
   - **Optional live mode:** set `NEWS_API_KEY=<key>`, `LIVE_INGESTION_ENABLED=true`, and `MOCK_MODE=false` in `.env` to use real-time NewsAPI articles instead of sample data. Trigger ingestion via `POST /api/ingest` before the demo. See `README.md § 16a` for the full quick-start.

## Demo script
1. Open `http://localhost:5173`.
2. Enter sample query: `What are the latest developments in Red Sea shipping disruptions?`
3. Click **Run Pipeline**.
4. Explain retrieval panel:
   - relevance scores,
   - source/date metadata,
   - direct article links.
5. Explain vision panel:
   - `detected_theme`,
   - `notable_visual_elements`,
   - confidence.
6. Explain final report panel:
   - executive summary,
   - cross-article themes,
   - uncertainty notes,
   - source evidence.
7. Export report as Markdown.

## Talking points for instructors
- Distinct agents with typed handoffs.
- Local-first stack with mock fallback.
- Explainable report with citations/URLs.
- Extendable provider architecture (Ollama/OpenCLIP/Chroma).
