# Troubleshooting

## Python not found
- **Symptom:** `python` or `python3` command fails.
- **Likely cause:** Python not installed or PATH not configured.
- **Fix:** Install Python 3.11+ and reopen terminal.

## python vs python3 confusion (Linux)
- **Symptom:** `python` fails, `python3` works.
- **Fix:** Use `python3 -m venv .venv` and `python3 -m pip ...`.

## PowerShell venv activation blocked
- **Symptom:** script execution disabled.
- **Fix:** `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`.

## Node/npm not installed
- **Symptom:** `npm` not recognized.
- **Fix:** Install Node.js LTS and verify with `node -v` and `npm -v`.

## Dependency install failures
- **Symptom:** `pip install` or `npm install` errors.
- **Fix:** Update pip (`python -m pip install --upgrade pip`) and retry.

## Windows dependency install fails on Python 3.14
- **Symptom:** backend dependencies fail to install, especially scientific packages.
- **Fix:** use the verified Python 3.13 environment under `backend/.venv313` for backend work and tests.

## Port already in use
- **Symptom:** backend or frontend startup failure.
- **Fix:** choose another port or stop existing process.

## Environment variables not loading
- **Symptom:** backend uses wrong defaults.
- **Fix:** ensure `.env` exists at repo root and variable names match `.env.example`.

## Live ingestion returns 503
- **Symptom:** `POST /api/ingest` returns `503 Live ingestion is not enabled`.
- **Causes:** `LIVE_INGESTION_ENABLED=false` or `NEWS_API_KEY` not set.
- **Fix:** 
  ```bash
  export LIVE_INGESTION_ENABLED=true
  export NEWS_API_KEY="your_newsapi_key"
  # Restart backend
  ```
- **Get API key:** https://newsapi.org/register (free tier: 500 requests/day)

## Live ingestion completes with failed status
- **Symptom:** `/api/status/{task_id}` returns `state: "failed"` with `error: "No new live articles were indexed for the query."`.
- **Causes:** 
  - Query too specific (news API returns no results)
  - All returned articles already indexed (URL duplicates)
  - Upstream provider rate limit hit
- **Fix:**
  1. Try a broader query: `"AI"` instead of `"specific AI regulation detail"`
  2. Clear vector store (restart app) to reset deduplication
  3. Check NewsAPI was called: `curl -s 'https://newsapi.org/v2/everything?q=test&apiKey=YOUR_KEY' | python -m json.tool | head`
  4. Monitor quota: https://newsapi.org/account (free tier: 500 requests/day)

## "ArticleSource has no attribute 'image_path'"
- **Symptom:** AttributeError during ingestion or retrieval.
- **Cause:** Schema mismatch between NewsAPI normalization and RankedArticle model.
- **Fix:** Verify all article dicts from `NewsIngestionService._normalize_article()` include:
  - `id`, `title`, `source`, `date`, `url`, `image_path`, `snippet`, `text`
  - All fields must be present (use None for optional fields)

## Embeddings are wrong dimension
- **Symptom:** "Embedding dimension mismatch: expected 768, got 32" error.
- **Cause:** Model has different output dimension than VECTOR_STORE_DIMENSION setting.
- **Fix:**
  ```bash
  # Verify model dimension:
  python -c "from sentence_transformers import SentenceTransformer; m = SentenceTransformer('all-mpnet-base-v2'); print(f'Dimension: {m.get_sentence_embedding_dimension()}')"
  
  # Should output: Dimension: 768
  # Update .env: VECTOR_STORE_DIMENSION=768
  ```

## Pgvector backend falls back to in-memory
- **Symptom:** Logs show "pgvector initialization failed, falling back to in-memory".
- **Causes:**
  - PostgreSQL not running
  - Database URL format is wrong
  - pgvector extension not installed
  - Connection refused
- **Fix:**
  ```bash
  # 1. Test database connection:
  psql $VECTOR_STORE_DATABASE_URL -c "SELECT 1"
  
  # 2. Verify pgvector extension:
  psql $VECTOR_STORE_DATABASE_URL -c "CREATE EXTENSION IF NOT EXISTS vector"
  
  # 3. Check URL format:
  # postgresql://user:password@host:5432/database
  
  # 4. Or use in-memory for now:
  export VECTOR_STORE_BACKEND=memory
  ```

## Newspaper3k extraction failing silently
- **Symptom:** Articles have only snippet text, not full body.
- **Cause:** newspaper3k not installed or article download fails.
- **Fix:**
  ```bash
  pip install newspaper3k
  # Or disable extraction fallback in config:
  export INGESTION_EXTRACT_FULL_TEXT=false  # faster, less content
  ```

## NewsAPI rate limit hit (429)
- **Symptom:** Ingestion fails with "429 Too Many Requests".
- **Cause:** Free tier limit (500 requests/day) exceeded.
- **Fix:**
  - Wait 24 hours for quota reset
  - Upgrade to paid plan at newsapi.org
  - Reduce concurrent requests
  - Increase `INGESTION_TIMEOUT_SECONDS` to allow retries

## Missing model runtimes (Ollama/OpenCLIP)
- **Symptom:** synthesis or vision runtime errors in non-mock mode.
- **Fix:** use `MOCK_MODE=true`, then install missing model runtimes.

## CORS issues between frontend/backend
- **Symptom:** browser blocks API request.
- **Fix:** set `FRONTEND_ORIGIN=http://localhost:5173`.

## Sample data/images not loading
- **Symptom:** retrieval empty or image paths invalid.
- **Fix:** verify `SAMPLE_DATA_PATH=sample_data/articles.json` and files exist under `sample_data/images`.
