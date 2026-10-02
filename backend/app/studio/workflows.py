import json
import uuid

from fastapi import HTTPException

from .. import db
from .models import MAX_PROJECT_ITEMS
from .storage import record, require_project

BUILTINS = (
    {"id": "creator-research", "name": "创作者灵感采集", "description": "收集参考视频，统一标记灵感素材，供脚本研究使用。",
     "preset": "everyday", "tags": ["灵感", "参考"], "rate_limit": 0},
    {"id": "client-archive", "name": "客户高清素材归档", "description": "使用归档质量保存授权素材，准备项目交付。",
     "preset": "archive", "tags": ["客户素材", "待审核"], "rate_limit": 0},
    {"id": "podcast-research", "name": "播客音频研究", "description": "保存音频参考，结合字幕导入和研究笔记准备选题。",
     "preset": "audio", "tags": ["播客", "研究"], "rate_limit": 0},
    {"id": "team-learning", "name": "团队轻量学习", "description": "使用节省空间的预设整理内部学习材料，限制下载速率。",
     "preset": "commute", "tags": ["团队学习"], "rate_limit": 2048},
)


def serialize(row) -> dict:
    value = dict(row)
    value["tags"] = json.loads(value["tags"])
    value["collection_id"] = value["collection_id"] or "inbox"
    value["builtin"] = False
    return value


def get_workflow(conn, workflow_id: str) -> dict:
    for builtin in BUILTINS:
        if builtin["id"] == workflow_id:
            return {**builtin, "tags": list(builtin["tags"]), "collection_id": "inbox", "builtin": True}
    row = conn.execute("SELECT * FROM studio_workflows WHERE id=?", (workflow_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "工作流不存在")
    return serialize(row)


def list_workflows() -> list[dict]:
    with db.connection() as conn:
        return [get_workflow(conn, recipe["id"]) for recipe in BUILTINS] + [
            serialize(row) for row in conn.execute("SELECT * FROM studio_workflows ORDER BY created_at DESC, id")
        ]


def create_workflow(data) -> dict:
    workflow_id, timestamp = str(uuid.uuid4()), db.now()
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        if not conn.execute("SELECT id FROM collections WHERE id=?", (data.collection_id,)).fetchone():
            raise HTTPException(404, "工作流目标合集不存在")
        conn.execute(
            "INSERT INTO studio_workflows VALUES (?,?,?,?,?,?,?,?,?)",
            (workflow_id, data.name, data.description, data.preset, data.collection_id,
             json.dumps(data.tags, ensure_ascii=False), data.rate_limit, timestamp, timestamp),
        )
        record(conn, "workflow.created", workflow_id, {"name": data.name})
        return get_workflow(conn, workflow_id)


def delete_workflow(workflow_id: str):
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        workflow = get_workflow(conn, workflow_id)
        if workflow["builtin"]:
            raise HTTPException(409, "内置工作流不能删除")
        conn.execute("DELETE FROM studio_workflows WHERE id=?", (workflow_id,))
        record(conn, "workflow.deleted", workflow_id)


def run_workflow(workflow_id: str, urls: list[str], project_id: str | None) -> dict:
    added, skipped = [], []
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        workflow = get_workflow(conn, workflow_id)
        if project_id is not None:
            project = require_project(conn, project_id)
            if project["status"] == "delivered":
                raise HTTPException(409, "请重新打开项目后再运行工作流")
            item_count = conn.execute(
                "SELECT COUNT(*) FROM studio_project_items WHERE project_id=?", (project_id,)
            ).fetchone()[0]
        for url in urls:
            if conn.execute(
                """SELECT id FROM tasks WHERE url=? AND preset=? AND clip_start IS NULL AND clip_end IS NULL
                AND status NOT IN ('failed','cancelled') LIMIT 1""", (url, workflow["preset"]),
            ).fetchone():
                skipped.append(url)
                continue
            task_id, timestamp = str(uuid.uuid4()), db.now()
            if project_id is not None and item_count + len(added) >= MAX_PROJECT_ITEMS:
                raise HTTPException(413, f"一个项目最多包含 {MAX_PROJECT_ITEMS} 个素材，请拆分项目")
            conn.execute(
                """INSERT INTO tasks
                (id,url,preset,collection_id,tags,rate_limit,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)""",
                (task_id, url, workflow["preset"], workflow["collection_id"],
                 json.dumps(workflow["tags"], ensure_ascii=False), workflow["rate_limit"], timestamp, timestamp),
            )
            if project_id is not None:
                conn.execute("INSERT INTO studio_project_items VALUES (?,?)", (project_id, task_id))
            added.append(db.serialize(conn.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()))
        if project_id is not None and added:
            conn.execute("UPDATE studio_projects SET updated_at=? WHERE id=?", (db.now(), project_id))
        record(conn, "workflow.run", workflow_id,
               {"added": len(added), "skipped": len(skipped), "project_id": project_id})
    return {"added": added, "skipped": skipped}
