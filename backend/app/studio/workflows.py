import json
import uuid

from fastapi import HTTPException

from .. import db
from .storage import record

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
