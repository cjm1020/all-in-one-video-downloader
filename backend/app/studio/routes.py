from fastapi import APIRouter

from .. import db
from . import storage, workflows
from .models import ItemReplace, ProjectCreate, ProjectPatch, RightsPatch, WorkflowCreate

router = APIRouter(prefix="/api/studio", tags=["studio"])


@router.get("/projects")
def projects():
    return storage.list_projects()


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
