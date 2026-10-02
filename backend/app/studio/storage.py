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
