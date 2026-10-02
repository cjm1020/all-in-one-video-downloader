import json
import uuid

from fastapi import HTTPException

from .. import db
from .media import availability


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
                project_id,
                data.name,
                data.client,
                data.budget_cents,
                data.due_at.isoformat() if data.due_at else None,
                data.notes,
                timestamp,
                timestamp,
            ),
        )
        record(conn, "project.created", project_id, {"name": data.name})
        return require_project(conn, project_id)


def list_projects() -> list[dict]:
    with db.connection() as conn:
        conn.execute("BEGIN")
        available = {}
        for row in conn.execute("""SELECT t.id,t.status,t.file_path,i.project_id FROM tasks t
            JOIN studio_project_items i ON i.task_id=t.id WHERE t.status='completed'"""):
            if availability(dict(row))[0]:
                available[row["project_id"]] = available.get(row["project_id"], 0) + 1
        result = []
        for row in conn.execute("""SELECT p.*,COUNT(t.id) AS item_count,
            COALESCE(SUM(t.status='completed'),0) AS completed_count,
            COALESCE(SUM(r.verified=1 AND r.license!='unknown'
                AND (r.license!='cc-by' OR trim(r.attribution)!='')
                AND (r.license!='permission' OR trim(r.evidence_url)!='')),0) AS licensed_count
            FROM studio_projects p LEFT JOIN studio_project_items i ON i.project_id=p.id
            LEFT JOIN tasks t ON t.id=i.task_id LEFT JOIN studio_rights r ON r.task_id=t.id
            GROUP BY p.id ORDER BY p.created_at DESC,p.id"""):
            project = dict(row)
            project["completed_count"] = available.get(project["id"], 0)
            project["ready"] = bool(
                project["item_count"]
                and project["completed_count"] == project["item_count"]
                and project["licensed_count"] == project["item_count"]
            )
            result.append(project)
        return result


def project_detail(project_id: str) -> dict:
    with db.connection() as conn:
        conn.execute("BEGIN")
        return project_snapshot(conn, project_id)


def rights_valid(rights: dict) -> bool:
    return bool(
        rights["verified"]
        and rights["license"] != "unknown"
        and (rights["license"] != "cc-by" or rights["attribution"].strip())
        and (rights["license"] != "permission" or rights["evidence_url"].strip())
    )


def checklist(items: list[dict]) -> dict:
    issues = []
    completed, licensed = 0, 0
    for item in items:
        if item["media_ready"]:
            completed += 1
        else:
            issues.append({"task_id": item["id"], "reason": item["media_issue"]})
        if rights_valid(item["rights"]):
            licensed += 1
        else:
            issues.append({"task_id": item["id"], "reason": "素材授权尚未审核或凭证不完整"})
    if not items:
        issues.append({"task_id": None, "reason": "请先添加项目素材"})
    return {
        "total": len(items),
        "completed": completed,
        "licensed": licensed,
        "ready": bool(items) and not issues,
        "issues": issues,
    }


def project_snapshot(conn, project_id: str) -> dict:
    project = require_project(conn, project_id)
    items = project_items(conn, project_id)
    return {"project": project, "items": items, "checklist": checklist(items)}


def project_items(conn, project_id: str) -> list[dict]:
    items = []
    for row in conn.execute(
        """SELECT t.*,r.license,r.attribution,r.evidence_url,r.verified,r.updated_at AS rights_updated_at
        FROM tasks t JOIN studio_project_items i ON i.task_id=t.id
        LEFT JOIN studio_rights r ON r.task_id=t.id WHERE i.project_id=? ORDER BY t.created_at, t.id""",
        (project_id,),
    ):
        item = db.serialize(row)
        item["media_ready"], item["media_issue"] = availability(dict(row))
        item["rights"] = {
            "task_id": item["id"],
            "license": item.pop("license") or "unknown",
            "attribution": item.pop("attribution") or "",
            "evidence_url": item.pop("evidence_url") or "",
            "verified": bool(item.pop("verified")),
            "updated_at": item.pop("rights_updated_at"),
        }
        items.append(item)
    return items


def require_task(conn, task_id: str):
    if not conn.execute("SELECT id FROM tasks WHERE id=?", (task_id,)).fetchone():
        raise HTTPException(404, "素材不存在")


def get_rights(conn, task_id: str) -> dict:
    require_task(conn, task_id)
    row = conn.execute("SELECT * FROM studio_rights WHERE task_id=?", (task_id,)).fetchone()
    result = (
        dict(row)
        if row
        else {
            "task_id": task_id,
            "license": "unknown",
            "attribution": "",
            "evidence_url": "",
            "verified": False,
            "updated_at": None,
        }
    )
    result["verified"] = bool(result["verified"])
    return result


def set_rights(task_id: str, data) -> dict:
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        require_task(conn, task_id)
        conn.execute(
            """INSERT INTO studio_rights VALUES (?,?,?,?,?,?) ON CONFLICT(task_id) DO UPDATE SET
            license=excluded.license, attribution=excluded.attribution, evidence_url=excluded.evidence_url,
            verified=excluded.verified, updated_at=excluded.updated_at""",
            (task_id, data.license, data.attribution, data.evidence_url, int(data.verified), db.now()),
        )
        record(conn, "rights.updated", task_id, {"license": data.license, "verified": data.verified})
        return get_rights(conn, task_id)


def replace_items(project_id: str, task_ids: list[str]) -> dict:
    task_ids = list(dict.fromkeys(task_ids))
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        project = require_project(conn, project_id)
        if project["status"] == "delivered":
            raise HTTPException(409, "请将项目重新设为进行中，再修改交付素材")
        if task_ids:
            placeholders = ",".join("?" for _ in task_ids)
            found = {row[0] for row in conn.execute(f"SELECT id FROM tasks WHERE id IN ({placeholders})", task_ids)}
            if len(found) != len(task_ids):
                raise HTTPException(404, "所选素材不存在，请刷新后重试")
        conn.execute("DELETE FROM studio_project_items WHERE project_id=?", (project_id,))
        conn.executemany("INSERT INTO studio_project_items VALUES (?,?)", ((project_id, value) for value in task_ids))
        conn.execute("UPDATE studio_projects SET updated_at=? WHERE id=?", (db.now(), project_id))
        record(conn, "project.items_updated", project_id, {"count": len(task_ids)})
    return project_detail(project_id)


def patch_project(project_id: str, data) -> dict:
    values = data.model_dump(exclude_unset=True)
    if any(value is None for key, value in values.items() if key != "due_at"):
        raise ValueError("项目字段不能为空")
    if values.get("name") == "":
        raise ValueError("项目名称不能为空")
    if values.get("due_at") is not None:
        values["due_at"] = values["due_at"].isoformat()
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        project = require_project(conn, project_id)
        if values.get("status") == "delivered" and not project_snapshot(conn, project_id)["checklist"]["ready"]:
            raise HTTPException(409, "请先完成素材下载和授权审核")
        if values:
            values["updated_at"] = db.now()
            assignments = ",".join(f"{key}=?" for key in values)
            conn.execute(f"UPDATE studio_projects SET {assignments} WHERE id=?", (*values.values(), project_id))
            action = "project.updated"
            if values.get("status") == "delivered" and project["status"] != "delivered":
                action = "project.delivered"
            elif project["status"] == "delivered" and values.get("status") in {"active", "draft"}:
                action = "project.reopened"
            record(conn, action, project_id, {"fields": list(values)})
        return require_project(conn, project_id)


def delete_project(project_id: str):
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        require_project(conn, project_id)
        conn.execute("DELETE FROM studio_projects WHERE id=?", (project_id,))
        record(conn, "project.deleted", project_id)
