import json
import uuid

from fastapi import HTTPException

from .. import db


def record(conn, action: str, entity_id: str, details: dict | None = None):
    conn.execute(
        "INSERT INTO studio_activity VALUES (?,?,?,?,?)",
        (str(uuid.uuid4()), action, entity_id, json.dumps(details or {}, ensure_ascii=False), db.now()),
    )


def require_project(conn, project_id: str) -> dict:
    row = conn.execute("SELECT * FROM studio_projects WHERE id=?", (project_id,)).fetchone()
    if row is None:
        raise HTTPException(404, "项目不存在")
    return dict(row)


def create_project(data) -> dict:
    project_id, timestamp = str(uuid.uuid4()), db.now()
    with db.connection() as conn:
        conn.execute(
            """INSERT INTO studio_projects
            (id,name,client,budget_cents,due_at,notes,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?)""",
            (
                project_id, data.name, data.client, data.budget_cents,
                data.due_at.isoformat() if data.due_at else None, data.notes, timestamp, timestamp,
            ),
        )
        record(conn, "project.created", project_id, {"name": data.name})
        return require_project(conn, project_id)


def list_projects() -> list[dict]:
    with db.connection() as conn:
        return [dict(row) for row in conn.execute("SELECT * FROM studio_projects ORDER BY created_at DESC, id")]


def project_detail(project_id: str) -> dict:
    with db.connection() as conn:
        project = require_project(conn, project_id)
        return {"project": project, "items": [], "checklist": {"total": 0, "completed": 0, "licensed": 0,
                "ready": False, "issues": [{"task_id": None, "reason": "请先添加项目素材"}]}}


def patch_project(project_id: str, data) -> dict:
    values = data.model_dump(exclude_unset=True)
    if any(value is None for key, value in values.items() if key != "due_at"):
        raise ValueError("项目字段不能为空")
    if values.get("name") == "":
        raise ValueError("项目名称不能为空")
    if values.get("status") == "delivered":
        raise HTTPException(409, "请先完成素材下载和授权审核")
    if values.get("due_at") is not None:
        values["due_at"] = values["due_at"].isoformat()
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        require_project(conn, project_id)
        if values:
            values["updated_at"] = db.now()
            assignments = ",".join(f"{key}=?" for key in values)
            conn.execute(f"UPDATE studio_projects SET {assignments} WHERE id=?", (*values.values(), project_id))
            record(conn, "project.updated", project_id, {"fields": list(values)})
        return require_project(conn, project_id)


def delete_project(project_id: str):
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        require_project(conn, project_id)
        conn.execute("DELETE FROM studio_projects WHERE id=?", (project_id,))
        record(conn, "project.deleted", project_id)
