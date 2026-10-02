import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from .config import config


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


@contextmanager
def connection():
    config.data_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(config.db_path, timeout=20)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def initialize():
    config.media_dir.mkdir(parents=True, exist_ok=True)
    with connection() as conn:
        conn.execute("PRAGMA journal_mode=WAL")
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS collections (
                id TEXT PRIMARY KEY, name TEXT NOT NULL UNIQUE, color TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY, url TEXT NOT NULL, preset TEXT NOT NULL,
                collection_id TEXT NOT NULL REFERENCES collections(id),
                title TEXT NOT NULL DEFAULT '', platform TEXT NOT NULL DEFAULT '',
                duration REAL NOT NULL DEFAULT 0, thumbnail TEXT NOT NULL DEFAULT '',
                status TEXT NOT NULL DEFAULT 'queued', progress REAL NOT NULL DEFAULT 0,
                speed REAL NOT NULL DEFAULT 0, eta REAL NOT NULL DEFAULT 0,
                scheduled_at TEXT, clip_start REAL, clip_end REAL, rate_limit INTEGER DEFAULT 0,
                file_path TEXT, file_size INTEGER NOT NULL DEFAULT 0,
                error TEXT NOT NULL DEFAULT '', favorite INTEGER NOT NULL DEFAULT 0,
                tags TEXT NOT NULL DEFAULT '[]', notes TEXT NOT NULL DEFAULT '',
                transcript TEXT NOT NULL DEFAULT '', summary TEXT NOT NULL DEFAULT '',
                summary_mode TEXT NOT NULL DEFAULT '', lease_at TEXT,
                created_at TEXT NOT NULL, updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_queue ON tasks(status, scheduled_at, created_at);
            CREATE INDEX IF NOT EXISTS idx_url ON tasks(url, preset);
            CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        """)
        conn.execute("INSERT OR IGNORE INTO collections VALUES (?, ?, ?, ?)",
                     ("inbox", "我的收藏", "sage", now()))
        for key, value in {"default_preset": "everyday", "rate_limit": 0,
                           "storage_limit_gb": config.max_storage_gb}.items():
            conn.execute("INSERT OR IGNORE INTO settings VALUES (?, ?)",
                         (key, json.dumps(value)))


def serialize(row) -> dict:
    value = dict(row)
    value["favorite"] = bool(value["favorite"])
    value["tags"] = json.loads(value["tags"])
    value.pop("file_path", None)
    value.pop("lease_at", None)
    return value


def get_task(task_id: str, raw: bool = False) -> dict | None:
    with connection() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        return (dict(row) if raw else serialize(row)) if row else None


def list_tasks() -> list[dict]:
    with connection() as conn:
        return [serialize(r) for r in conn.execute("SELECT * FROM tasks ORDER BY created_at DESC")]


def update_task(task_id: str, values: dict, only_status: tuple | None = None) -> bool:
    allowed = {"title", "platform", "duration", "thumbnail", "status", "progress", "speed", "eta",
               "file_path", "file_size", "error", "favorite", "tags", "notes", "transcript",
               "summary", "summary_mode", "collection_id", "lease_at", "scheduled_at"}
    if not values or set(values) - allowed:
        raise ValueError("无效的任务字段")
    values = {**values, "updated_at": now()}
    if isinstance(values.get("tags"), list):
        values["tags"] = json.dumps(values["tags"], ensure_ascii=False)
    assignments = ", ".join(f"{key}=?" for key in values)
    sql = f"UPDATE tasks SET {assignments} WHERE id=?"
    params = [*values.values(), task_id]
    if only_status:
        sql += f" AND status IN ({','.join('?' for _ in only_status)})"
        params.extend(only_status)
    with connection() as conn:
        return conn.execute(sql, params).rowcount > 0


def create_tasks(request, urls: list[str]) -> tuple[list[dict], list[str]]:
    added, skipped = [], []
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT id FROM collections WHERE id=?", (request.collection_id,)).fetchone():
            raise ValueError("合集不存在")
        for url in urls:
            duplicate = conn.execute("""SELECT id FROM tasks WHERE url=? AND preset=?
                AND clip_start IS ? AND clip_end IS ? AND status NOT IN ('failed','cancelled')""",
                (url, request.preset, request.clip_start, request.clip_end)).fetchone()
            if duplicate:
                skipped.append(url)
                continue
            task_id, timestamp = str(uuid.uuid4()), now()
            conn.execute("""INSERT INTO tasks
                (id,url,preset,collection_id,scheduled_at,clip_start,clip_end,rate_limit,created_at,updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?)""", (
                    task_id, url, request.preset, request.collection_id,
                    request.scheduled_at.isoformat() if request.scheduled_at else None,
                    request.clip_start, request.clip_end, request.rate_limit, timestamp, timestamp))
            added.append(serialize(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()))
    return added, skipped


def claim_task() -> dict | None:
    with connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        timestamp = now()
        row = conn.execute("""SELECT * FROM tasks WHERE status='queued'
            AND (scheduled_at IS NULL OR scheduled_at<=?) ORDER BY created_at LIMIT 1""",
            (timestamp,)).fetchone()
        if not row:
            return None
        conn.execute("UPDATE tasks SET status='downloading',lease_at=?,updated_at=?,error='' WHERE id=?",
                     (timestamp, timestamp, row["id"]))
        return dict(row)


def recover_expired_tasks(seconds: int = 30):
    cutoff = (datetime.now(timezone.utc) - timedelta(seconds=seconds)).isoformat()
    with connection() as conn:
        conn.execute("""UPDATE tasks SET status='queued',speed=0,eta=0,lease_at=NULL,updated_at=?
            WHERE status IN ('downloading','processing') AND (lease_at IS NULL OR lease_at<?)""",
            (now(), cutoff))


def get_settings() -> dict:
    with connection() as conn:
        return {r["key"]: json.loads(r["value"]) for r in conn.execute("SELECT * FROM settings")}


def set_settings(values: dict):
    with connection() as conn:
        for key, value in values.items():
            conn.execute("INSERT OR REPLACE INTO settings VALUES (?,?)", (key, json.dumps(value)))
