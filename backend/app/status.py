import shutil
from datetime import datetime, timezone

from fastapi import APIRouter
from yt_dlp.version import __version__ as engine_version

from . import db
from .config import config
from .models import SettingsUpdate

router = APIRouter(prefix="/api")


def worker_healthy() -> bool:
    heartbeat = db.get_settings().get("worker_heartbeat")
    if not heartbeat:
        return False
    try:
        return (datetime.now(timezone.utc) - datetime.fromisoformat(heartbeat)).total_seconds() < 20
    except (ValueError, TypeError):
        return False


@router.get("/health")
def health():
    with db.connection() as conn:
        conn.execute("SELECT 1").fetchone()
    return {"status": "ok", "version": "1.0.0"}


@router.get("/status")
def status():
    from .worker import storage_bytes
    tasks = db.list_tasks()
    return {
        "worker_online": worker_healthy(), "engine_version": engine_version,
        "ffmpeg_available": bool(shutil.which("ffmpeg")), "ai_available": bool(config.deepseek_key),
        "cookies_configured": bool(config.cookie_file),
        "storage_bytes": storage_bytes(), "disk_free_bytes": shutil.disk_usage(config.data_dir).free,
        "total_tasks": len(tasks), "completed_tasks": sum(t["status"] == "completed" for t in tasks),
        "active_tasks": sum(t["status"] in {"queued", "downloading", "processing"} for t in tasks),
        "favorite_tasks": sum(t["favorite"] for t in tasks),
    }


@router.get("/settings")
def settings():
    values = db.get_settings()
    return {k: values[k] for k in ("default_preset", "rate_limit", "storage_limit_gb")}


@router.put("/settings")
def update_settings(data: SettingsUpdate):
    db.set_settings(data.model_dump())
    return data
