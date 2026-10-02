from fastapi import APIRouter

from . import storage
from .models import ProjectCreate

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
