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

## Port already in use
- **Symptom:** backend or frontend startup failure.
- **Fix:** choose another port or stop existing process.

## Environment variables not loading
- **Symptom:** backend uses wrong defaults.
- **Fix:** ensure `.env` exists at repo root and variable names match `.env.example`.

## Missing model runtimes (Ollama/OpenCLIP)
- **Symptom:** synthesis or vision runtime errors in non-mock mode.
- **Fix:** use `MOCK_MODE=true`, then install missing model runtimes.

## CORS issues between frontend/backend
- **Symptom:** browser blocks API request.
- **Fix:** set `FRONTEND_ORIGIN=http://localhost:5173`.

## Sample data/images not loading
- **Symptom:** retrieval empty or image paths invalid.
- **Fix:** verify `SAMPLE_DATA_PATH=sample_data/articles.json` and files exist under `sample_data/images`.
