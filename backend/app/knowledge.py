"""Local knowledge APIs for finding evidence and building review habits."""

import json
import uuid
import sqlite3

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response

from . import db
from .briefs import editorial_brief, markdown_brief
from .knowledge_db import source_hash
from .knowledge_models import CardCreate, MarkerCreate, ReviewInput
from .library import require_task
from .study import cloze_cards, next_review

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


@router.get("/tasks/{task_id}/cards")
def cards(task_id: str):
    require_task(task_id)
    with db.connection() as conn:
        return [dict(row) for row in conn.execute(
            "SELECT * FROM study_cards WHERE task_id=? ORDER BY due_at,id", (task_id,)
        )]


def insert_card(conn, task_id: str, data: dict, digest: str = "") -> dict | None:
    timestamp, card_id = db.now(), str(uuid.uuid4())
    try:
        conn.execute(
            """INSERT INTO study_cards(id,task_id,question,answer,source_hash,due_at,created_at,updated_at)
                VALUES(?,?,?,?,?,?,?,?)""",
            (card_id, task_id, data["question"], data["answer"], digest, timestamp, timestamp, timestamp),
        )
    except sqlite3.IntegrityError:
        # The parent existence is checked inside the same write transaction.
        return None
    return dict(conn.execute("SELECT * FROM study_cards WHERE id=?", (card_id,)).fetchone())


@router.post("/tasks/{task_id}/cards", status_code=201)
def add_card(task_id: str, data: CardCreate):
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT id FROM tasks WHERE id=?", (task_id,)).fetchone():
            raise HTTPException(404, "任务不存在")
        if conn.execute("SELECT COUNT(*) FROM study_cards WHERE task_id=?", (task_id,)).fetchone()[0] >= 200:
            raise HTTPException(409, "每个素材最多保存 200 张复习卡")
        card = insert_card(conn, task_id, data.model_dump())
        if card is None:
            raise HTTPException(409, "已经有相同的复习卡")
        return card


@router.post("/tasks/{task_id}/cards/generate")
def generate_cards(task_id: str):
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        task = conn.execute("SELECT transcript FROM tasks WHERE id=?", (task_id,)).fetchone()
        if not task:
            raise HTTPException(404, "任务不存在")
        if not task["transcript"]:
            raise HTTPException(409, "请先导入字幕，再提取原句复习卡")
        count = conn.execute("SELECT COUNT(*) FROM study_cards WHERE task_id=?", (task_id,)).fetchone()[0]
        added = []
        for data in cloze_cards(task["transcript"])[:max(0, 200 - count)]:
            card = insert_card(conn, task_id, data, source_hash(task["transcript"]))
            if card:
                added.append(card)
        return {"added": added, "mode": "local-extraction"}


@router.get("/cards/due")
def due_cards(limit: int = Query(default=50, ge=1, le=200)):
    with db.connection() as conn:
        return [dict(row) for row in conn.execute(
            """SELECT c.*,t.title FROM study_cards c JOIN tasks t ON t.id=c.task_id
                WHERE c.due_at<=? ORDER BY c.due_at,c.id LIMIT ?""", (db.now(), limit)
        )]


@router.post("/cards/{card_id}/review")
def review_card(card_id: str, data: ReviewInput):
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT * FROM study_cards WHERE id=?", (card_id,)).fetchone()
        if not row:
            raise HTTPException(404, "复习卡不存在")
        # Two concurrent clicks should not count as two reviews on the same day.
        if row["due_at"] > db.now():
            raise HTTPException(409, "这张卡已复习，下一次到期后可以继续")
        values = next_review(dict(row), data.rating)
        conn.execute(
            "UPDATE study_cards SET interval_days=?,repetitions=?,due_at=?,updated_at=? WHERE id=?",
            (values["interval_days"], values["repetitions"], values["due_at"], db.now(), card_id),
        )
        return dict(conn.execute("SELECT * FROM study_cards WHERE id=?", (card_id,)).fetchone())


@router.delete("/cards/{card_id}")
def delete_card(card_id: str):
    with db.connection() as conn:
        if not conn.execute("DELETE FROM study_cards WHERE id=?", (card_id,)).rowcount:
            raise HTTPException(404, "复习卡不存在")
    return {"ok": True}


@router.get("/tasks/{task_id}/brief")
def export_brief(task_id: str, format: str = "markdown"):
    brief = editorial_brief(require_task(task_id), markers(task_id))
    if format == "json":
        body, media_type, suffix = json.dumps(brief, ensure_ascii=False, indent=2), "application/json", "json"
    elif format == "markdown":
        body, media_type, suffix = markdown_brief(brief), "text/markdown", "md"
    else:
        raise HTTPException(400, "不支持的简报导出格式")
    return Response(body, media_type=media_type, headers={
        "Content-Disposition": f'attachment; filename="brief-{task_id[:8]}.{suffix}"',
    })
