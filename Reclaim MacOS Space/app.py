"""Local web portal for safe macOS developer junk cleanup."""

from __future__ import annotations

import shutil
import webbrowser
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from cleanup.cleaner import clean_category
from cleanup.fsutil import format_bytes
from cleanup.scanner import scan_all

APP_DIR = Path(__file__).resolve().parent
STATIC_DIR = APP_DIR / "static"

app = FastAPI(title="Reclaim macOS Space", version="1.0.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


class CleanRequest(BaseModel):
    category_ids: list[str] = Field(min_length=1)
    use_sudo: bool = False
    confirmed: bool = False


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/disk")
def disk_summary() -> dict:
    usage = shutil.disk_usage(Path.home())
    return {
        "total_bytes": usage.total,
        "used_bytes": usage.used,
        "free_bytes": usage.free,
        "total_human": format_bytes(usage.total),
        "used_human": format_bytes(usage.used),
        "free_human": format_bytes(usage.free),
    }


@app.get("/api/scan")
def scan() -> dict:
    results = scan_all()
    total = sum(item.size_bytes for item in results)
    return {
        "categories": [item.__dict__ for item in results],
        "total_reclaimable_bytes": total,
        "total_reclaimable_human": format_bytes(total),
    }


@app.post("/api/clean")
def clean(body: CleanRequest) -> dict:
    if not body.confirmed:
        raise HTTPException(status_code=400, detail="Confirmation required")

    outcomes = []
    total_freed = 0
    for category_id in body.category_ids:
        result = clean_category(category_id, use_sudo=body.use_sudo)
        outcomes.append(
            {
                "id": result.id,
                "success": result.success,
                "message": result.message,
                "freed_bytes": result.freed_bytes,
                "freed_human": format_bytes(result.freed_bytes),
            }
        )
        total_freed += result.freed_bytes

    return {
        "results": outcomes,
        "total_freed_bytes": total_freed,
        "total_freed_human": format_bytes(total_freed),
    }


def main() -> None:
    import threading
    import time
    import urllib.error
    import urllib.request

    import uvicorn

    host = "127.0.0.1"
    port = 8765
    url = f"http://{host}:{port}"

    try:
        with urllib.request.urlopen(f"{url}/api/disk", timeout=1) as response:
            if response.status == 200:
                webbrowser.open(url)
                return
    except (urllib.error.URLError, TimeoutError, OSError):
        pass

    def open_when_ready() -> None:
        for _ in range(60):
            try:
                with urllib.request.urlopen(f"{url}/api/disk", timeout=0.5):
                    webbrowser.open(url)
                    return
            except (urllib.error.URLError, TimeoutError, OSError):
                time.sleep(0.15)

    threading.Thread(target=open_when_ready, daemon=True).start()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
