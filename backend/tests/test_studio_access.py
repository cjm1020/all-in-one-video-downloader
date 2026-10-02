from dataclasses import replace

from app import main
from app.studio import exports


def test_studio_endpoints_inherit_cookie_auth_and_same_origin_protection(client, monkeypatch):
    monkeypatch.setattr(main, "config", replace(main.config, access_token="studio-secret"))
    for path in (
        "/api/studio/projects",
        "/api/studio/workflows",
        "/api/studio/analytics",
        "/api/studio/projects/missing/export",
        "/api/studio/projects/missing/package",
        "/api/studio/rights/missing",
    ):
        assert client.get(path).status_code == 401
    assert client.post("/api/studio/projects", json={"name": "私有项目"}).status_code == 401
    assert client.post("/api/session", json={"token": "studio-secret"}).status_code == 200
    assert client.get("/api/studio/analytics").status_code == 200
    assert (
        client.post(
            "/api/studio/projects", json={"name": "项目"}, headers={"Origin": "https://attacker.example"}
        ).status_code
        == 403
    )
    assert client.get("/api/studio/projects").json() == []
    client.delete("/api/session")
    assert client.get("/api/studio/analytics").status_code == 401


def test_oversized_metadata_preview_fails_without_export_audit(client, monkeypatch):
    project = client.post("/api/studio/projects", json={"name": "资料限制"}).json()
    monkeypatch.setattr(exports, "MAX_METADATA_BYTES", 32)
    assert client.get(f"/api/studio/projects/{project['id']}/export").status_code == 413
    activity = client.get("/api/studio/analytics").json()["activity"]
    assert all(event["action"] != "project.exported" for event in activity)


def test_project_index_reports_counts_without_loading_item_documents(client, task, monkeypatch):
    from app import db
    from app.studio import storage

    project = client.post("/api/studio/projects", json={"name": "聚合项目"}).json()
    client.put(f"/api/studio/projects/{project['id']}/items", json={"task_ids": [task["id"]]})
    db.update_task(task["id"], {"status": "completed"})
    client.put(f"/api/studio/rights/{task['id']}", json={"license": "cc0", "verified": True})

    def fail_load(*args):
        raise AssertionError("index should aggregate without loading transcripts and notes")

    monkeypatch.setattr(storage, "project_items", fail_load)
    index = client.get("/api/studio/projects").json()[0]
    assert index["item_count"] == index["completed_count"] == index["licensed_count"] == 1
    assert index["ready"]
