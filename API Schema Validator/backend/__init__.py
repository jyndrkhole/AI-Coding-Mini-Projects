"""Re-export FastAPI app for uvicorn: `uvicorn backend.main:app`."""

from backend.main import app

__all__ = ["app"]
