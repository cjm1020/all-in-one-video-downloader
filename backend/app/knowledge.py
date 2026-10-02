"""Local knowledge APIs for finding evidence and building review habits."""

import uuid

from fastapi import APIRouter, HTTPException, Query

from . import db
from .knowledge_models import MarkerCreate
from .library import require_task

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/search")
def search(q: str = Query(min_length=1, max_length=100), limit: int = Query(default=20, ge=1, le=100)):
    query = q.strip().lower()
    if not query:
        raise HTTPException(422, "请输入要检索的字幕关键词")
    with db.connection() as conn:
        # instr treats wildcard and SQL punctuation as literal query characters.
        sql = """SELECT c.task_id,t.title,c.text,c.start,c.end,t.updated_at,c.ordinal
            FROM transcript_cues c JOIN tasks t ON t.id=c.task_id
            WHERE instr(lower(c.text),?)>0
            UNION ALL
            SELECT t.id,t.title,t.transcript,NULL,NULL,t.updated_at,0 FROM tasks t
            WHERE t.transcript<>'' AND instr(lower(t.transcript),?)>0
            AND NOT EXISTS(SELECT 1 FROM transcript_cues c WHERE c.task_id=t.id)"""
        total = conn.execute(f"SELECT COUNT(*) FROM ({sql})", (query, query)).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM ({sql}) ORDER BY updated_at DESC,task_id,ordinal LIMIT ?", (query, query, limit)
        ).fetchall()
        results = []
        for row in rows:
            text = row["text"]
            position = text.lower().find(query)
            offset = max(0, position - 100)
            snippet = text[offset:offset + 500]
            results.append({
                "task_id": row["task_id"], "title": row["title"],
                "text": ("…" if offset else "") + snippet + ("…" if offset + 500 < len(text) else ""),
                "start": row["start"], "end": row["end"],
            })
    return {"results": results, "total": total}


@router.get("/tasks/{task_id}/markers")
def markers(task_id: str):
    require_task(task_id)
    with db.connection() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM knowledge_markers WHERE task_id=? ORDER BY position,created_at", (task_id,)
        )]


@router.post("/tasks/{task_id}/markers", status_code=201)
def add_marker(task_id: str, data: MarkerCreate):
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        task = conn.execute("SELECT duration FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not task:
            raise HTTPException(404, "任务不存在")
        if task["duration"] and data.position > task["duration"]:
            raise HTTPException(422, "时间标记超过了媒体时长")
        if conn.execute("SELECT COUNT(*) FROM knowledge_markers WHERE task_id=?", (task_id,)).fetchone()[0] >= 200:
            raise HTTPException(409, "每个素材最多保存 200 个时间标记")
        marker_id = str(uuid.uuid4())
        conn.execute(
            "INSERT INTO knowledge_markers(id,task_id,position,label,notes,color,created_at) VALUES(?,?,?,?,?,?,?)",
            (marker_id, task_id, data.position, data.label, data.notes, data.color, db.now()),
        )
        return dict(conn.execute("SELECT * FROM knowledge_markers WHERE id=?", (marker_id,)).fetchone())


@router.delete("/markers/{marker_id}")
def delete_marker(marker_id: str):
    with db.connection() as conn:
        if not conn.execute("DELETE FROM knowledge_markers WHERE id=?", (marker_id,)).rowcount:
            raise HTTPException(404, "时间标记不存在")
    return {"ok": True}
