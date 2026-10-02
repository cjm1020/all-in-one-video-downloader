"""Additive knowledge schema, initialized in the existing library transaction."""

import hashlib

from . import db


def initialize(conn):
    # Execute individually: executescript implicitly commits an existing transaction.
    statements = [
        """CREATE TABLE IF NOT EXISTS transcript_cues (
            task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            ordinal INTEGER NOT NULL, start REAL, end REAL, text TEXT NOT NULL,
            PRIMARY KEY(task_id, ordinal))""",
        """CREATE TABLE IF NOT EXISTS knowledge_markers (
            id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            position REAL NOT NULL CHECK(position>=0), label TEXT NOT NULL,
            notes TEXT NOT NULL DEFAULT '', color TEXT NOT NULL DEFAULT 'sage',
            created_at TEXT NOT NULL)""",
        """CREATE INDEX IF NOT EXISTS idx_markers_task
            ON knowledge_markers(task_id, position)""",
        """CREATE TABLE IF NOT EXISTS study_cards (
            id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
            question TEXT NOT NULL, answer TEXT NOT NULL, source_hash TEXT NOT NULL DEFAULT '',
            due_at TEXT NOT NULL, interval_days INTEGER NOT NULL DEFAULT 0,
            repetitions INTEGER NOT NULL DEFAULT 0, created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, UNIQUE(task_id, question, answer))""",
        "CREATE INDEX IF NOT EXISTS idx_cards_due ON study_cards(due_at)",
    ]
    for statement in statements:
        conn.execute(statement)


def source_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def replace_transcript(
    task_id: str, cleaned: str, cues: list[dict], only_status: tuple | None = None,
    media_values: dict | None = None,
) -> bool:
    """Atomically update text, cue index, summary, and generated-card validity."""
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        values = {"transcript": cleaned, "summary": "", "summary_mode": "", "updated_at": db.now()}
        allowed_media = {"status", "progress", "speed", "eta", "file_path", "file_size", "duration", "thumbnail", "error"}
        if media_values:
            if set(media_values) - allowed_media:
                raise ValueError("无效媒体完成字段")
            values.update(media_values)
        sql = f"UPDATE tasks SET {','.join(f'{key}=?' for key in values)} WHERE id=?"
        params = [*values.values(), task_id]
        if only_status:
            sql += f" AND status IN ({','.join('?' for _ in only_status)})"
            params.extend(only_status)
        if not conn.execute(sql, params).rowcount:
            return False
        conn.execute("DELETE FROM transcript_cues WHERE task_id=?", (task_id,))
        conn.executemany(
            "INSERT INTO transcript_cues(task_id,ordinal,start,end,text) VALUES(?,?,?,?,?)",
            [(task_id, index, cue["start"], cue["end"], cue["text"]) for index, cue in enumerate(cues)],
        )
        # User-authored cards remain independent. Generated cards carry a source hash.
        conn.execute(
            "DELETE FROM study_cards WHERE task_id=? AND source_hash<>'' AND source_hash<>?",
            (task_id, source_hash(cleaned)),
        )
    return True
