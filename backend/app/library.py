import json
import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse, Response

from . import db
from .config import config
from .models import CollectionCreate, TaskPatch

router = APIRouter(prefix="/api")


def require_task(task_id: str, raw: bool = False):
    task = db.get_task(task_id, raw)
    if not task:
        raise HTTPException(404, "任务不存在")
    return task


def safe_media_path(task: dict) -> Path:
    if task["status"] != "completed" or not task["file_path"]:
        raise HTTPException(409, "文件尚未准备好")
    target = (config.media_dir / task["file_path"]).resolve()
    root = (config.media_dir / task["id"]).resolve()
    if not target.is_relative_to(root) or not target.is_file():
        raise HTTPException(404, "文件不存在或路径无效")
    return target


@router.get("/collections")
def collections():
    with db.connection() as conn:
        return [dict(r) for r in conn.execute("""SELECT c.*, COUNT(t.id) AS count FROM collections c
            LEFT JOIN tasks t ON t.collection_id=c.id GROUP BY c.id ORDER BY c.created_at""")]


@router.post("/collections", status_code=201)
def create_collection(data: CollectionCreate):
    import sqlite3
    collection_id = str(uuid.uuid4())
    name = data.name.strip()
    if not name:
        raise ValueError("合集名称不能为空")
    with db.connection() as conn:
        try:
            conn.execute("INSERT INTO collections VALUES (?,?,?,?)", (collection_id, name, data.color, db.now()))
        except sqlite3.IntegrityError:
            raise HTTPException(409, "已经有同名合集")
    return {"id": collection_id, "name": name, "color": data.color, "count": 0}


@router.delete("/collections/{collection_id}")
def delete_collection(collection_id: str):
    if collection_id == "inbox":
        raise HTTPException(400, "默认合集不能删除")
    with db.connection() as conn:
        conn.execute("UPDATE tasks SET collection_id='inbox',updated_at=? WHERE collection_id=?",
                     (db.now(), collection_id))
        if not conn.execute("DELETE FROM collections WHERE id=?", (collection_id,)).rowcount:
            raise HTTPException(404, "合集不存在")
    return {"ok": True}


@router.patch("/tasks/{task_id}")
def edit_task(task_id: str, data: TaskPatch):
    require_task(task_id)
    values = data.model_dump(exclude_none=True)
    if "collection_id" in values:
        with db.connection() as conn:
            if not conn.execute("SELECT id FROM collections WHERE id=?", (values["collection_id"],)).fetchone():
                raise HTTPException(404, "合集不存在")
    if values:
        db.update_task(task_id, values)
    return require_task(task_id)


@router.delete("/tasks/{task_id}")
def delete_task(task_id: str):
    require_task(task_id)
    with db.connection() as conn:
        deleted = conn.execute("DELETE FROM tasks WHERE id=? AND status NOT IN ('downloading','processing')",
                               (task_id,)).rowcount
        if not deleted:
            raise HTTPException(409, "请先暂停或取消正在执行的任务，稍后再删除")
    directory = (config.media_dir / task_id).resolve()
    if directory.parent == config.media_dir.resolve() and directory.is_dir():
        shutil.rmtree(directory)
    return {"ok": True}


@router.get("/tasks/{task_id}/file")
def media_file(task_id: str, download: bool = False):
    task = require_task(task_id, raw=True)
    path = safe_media_path(task)
    filename = (task["title"] or "video").replace('/', '_').replace('\\', '_')[:100] + path.suffix
    return FileResponse(path, filename=filename, content_disposition_type="attachment" if download else "inline")


@router.get("/tasks/{task_id}/export")
def export_task(task_id: str, format: str = "markdown"):
    task = require_task(task_id)
    if format == "json":
        body, media_type, suffix = json.dumps(task, ensure_ascii=False, indent=2), "application/json", "json"
    elif format == "transcript":
        if not task["transcript"]:
            raise HTTPException(409, "还没有字幕，请先导入")
        body, media_type, suffix = task["transcript"], "text/plain", "txt"
    elif format == "markdown":
        body = (f"# {task['title'] or '视频资料卡'}\n\n"
                f"来源：{task['url']}\n\n标签：{', '.join(task['tags']) or '无'}\n\n"
                f"## 摘要\n\n{task['summary'] or '尚未生成'}\n\n"
                f"## 我的笔记\n\n{task['notes'] or '尚未记录'}\n\n"
                f"## 字幕\n\n{task['transcript'] or '尚未导入'}\n")
        media_type, suffix = "text/markdown", "md"
    else:
        raise HTTPException(400, "不支持的导出格式")
    return Response(body, media_type=media_type, headers={
        "Content-Disposition": f'attachment; filename="video-{task_id[:8]}.{suffix}"'})
