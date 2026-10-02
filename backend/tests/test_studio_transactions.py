from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest

from app import db
from app.studio import storage, workflows
from app.studio.models import ProjectPatch, RightsPatch


def test_concurrent_workflow_runs_create_one_deduplicated_task(client):
    barrier = Barrier(2)

    def run():
        barrier.wait(timeout=5)
        return workflows.run_workflow("creator-research", ["https://example.com/concurrent"], None)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: run(), range(2)))
    assert sum(len(result["added"]) for result in results) == 1
    assert sum(len(result["skipped"]) for result in results) == 1
    assert len(db.list_tasks()) == 1


def test_workflow_rolls_back_tasks_membership_and_audit_together(client, monkeypatch):
    project = client.post("/api/studio/projects", json={"name": "事务测试"}).json()

    def fail_audit(*args, **kwargs):
        raise RuntimeError("simulated persistence failure")

    monkeypatch.setattr(workflows, "record", fail_audit)
    with pytest.raises(RuntimeError, match="persistence"):
        workflows.run_workflow("client-archive", ["https://example.com/rollback"], project["id"])
    assert db.list_tasks() == []
    assert storage.project_detail(project["id"])["items"] == []
    with db.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM studio_activity WHERE action='workflow.run'").fetchone()[0] == 0


def test_project_limit_failure_rolls_back_whole_workflow_batch(client, monkeypatch):
    project = client.post("/api/studio/projects", json={"name": "容量测试"}).json()
    monkeypatch.setattr(workflows, "MAX_PROJECT_ITEMS", 1)
    response = client.post(
        "/api/studio/workflows/creator-research/run",
        json={
            "urls": ["https://example.com/first", "https://example.com/second"],
            "project_id": project["id"],
        },
    )
    assert response.status_code == 413
    assert db.list_tasks() == [] and storage.project_detail(project["id"])["items"] == []


def test_concurrent_rights_revocation_never_leaves_delivered_project(client, task):
    project = client.post("/api/studio/projects", json={"name": "并发验收"}).json()
    storage.replace_items(project["id"], [task["id"]])
    root = db.config.media_dir / task["id"]
    root.mkdir()
    (root / "source.mp4").write_bytes(b"completed media")
    db.update_task(task["id"], {"status": "completed", "file_path": f"{task['id']}/source.mp4"})
    storage.set_rights(task["id"], RightsPatch(license="owned", verified=True))
    barrier = Barrier(2)

    def deliver():
        from fastapi import HTTPException

        barrier.wait(timeout=5)
        try:
            storage.patch_project(project["id"], ProjectPatch(status="delivered"))
        except HTTPException as exc:
            assert exc.status_code == 409

    def revoke():
        barrier.wait(timeout=5)
        storage.set_rights(task["id"], RightsPatch(license="unknown"))

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = [pool.submit(deliver), pool.submit(revoke)]
        for result in results:
            result.result(timeout=10)
    detail = storage.project_detail(project["id"])
    assert detail["project"]["status"] != "delivered"
    assert not detail["checklist"]["ready"]
