from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
from starlette.background import BackgroundTask

from .. import db
from ..security import validate_public_url
from . import analytics, exports, package, storage, workflows
from .models import ItemReplace, ProjectCreate, ProjectPatch, RightsPatch, WorkflowCreate, WorkflowRun

router = APIRouter(prefix="/api/studio", tags=["studio"])


@router.get("/projects")
def projects():
    return storage.list_projects()


@router.get("/analytics")
def analytics_summary():
    return analytics.summary()


@router.post("/projects", status_code=201)
def create_project(data: ProjectCreate):
    return storage.create_project(data)


@router.get("/projects/{project_id}")
def project_detail(project_id: str):
    return storage.project_detail(project_id)


@router.patch("/projects/{project_id}")
def patch_project(project_id: str, data: ProjectPatch):
    return storage.patch_project(project_id, data)


@router.delete("/projects/{project_id}")
def delete_project(project_id: str):
    storage.delete_project(project_id)
    return {"ok": True}


@router.put("/projects/{project_id}/items")
def replace_items(project_id: str, data: ItemReplace):
    return storage.replace_items(project_id, data.task_ids)


@router.get("/rights/{task_id}")
def get_rights(task_id: str):
    with db.connection() as conn:
        return storage.get_rights(conn, task_id)


@router.put("/rights/{task_id}")
def set_rights(task_id: str, data: RightsPatch):
    return storage.set_rights(task_id, data)


@router.get("/workflows")
def list_workflows():
    return workflows.list_workflows()


@router.post("/workflows", status_code=201)
def create_workflow(data: WorkflowCreate):
    return workflows.create_workflow(data)


@router.delete("/workflows/{workflow_id}")
def delete_workflow(workflow_id: str):
    workflows.delete_workflow(workflow_id)
    return {"ok": True}


@router.post("/workflows/{workflow_id}/run")
def run_workflow(workflow_id: str, data: WorkflowRun):
    urls = [validate_public_url(url) for url in data.urls]
    return workflows.run_workflow(workflow_id, urls, data.project_id)


@router.get("/projects/{project_id}/export")
def export_project(project_id: str, format: str = "json"):
    body, media_type, suffix = exports.export_project(project_id, format)
    return Response(
        body,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="project-{project_id[:8]}.{suffix}"'},
    )


@router.get("/projects/{project_id}/package")
def delivery_package(project_id: str):
    if not package.package_slots.acquire(blocking=False):
        raise HTTPException(429, "当前交付包正在传输，请稍后重试")
    try:
        spool = package.build_package(project_id)
    except Exception:
        package.package_slots.release()
        raise
    closed = False

    def cleanup():
        nonlocal closed
        if not closed:
            closed = True
            spool.close()
            package.package_slots.release()

    def stream():
        try:
            while chunk := spool.read(package.CHUNK_BYTES):
                yield chunk
        finally:
            cleanup()

    return StreamingResponse(
        stream(),
        media_type="application/zip",
        background=BackgroundTask(cleanup),
        headers={"Content-Disposition": f'attachment; filename="project-{project_id[:8]}.zip"'},
    )
