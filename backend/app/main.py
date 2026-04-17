import logging
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.api.routes import router
from app.core.config import get_settings

logging.basicConfig(level=logging.INFO)
settings = get_settings()

app = FastAPI(title=settings.app_name)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)
sample_data_dir = Path(settings.resolved_sample_data_dir)
if sample_data_dir.exists():
    app.mount("/sample_data", StaticFiles(directory=str(sample_data_dir)), name="sample_data")
else:
    logging.warning("Sample data directory not found: %s", sample_data_dir)
