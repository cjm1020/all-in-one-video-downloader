from app import db


def ready_project(client, task):
    project = client.post("/api/studio/projects", json={"name": "可交付项目"}).json()
    client.put(f"/api/studio/projects/{project['id']}/items", json={"task_ids": [task["id"]]})
    db.update_task(task["id"], {"status": "completed"})
    client.put(f"/api/studio/rights/{task['id']}", json={"license": "owned", "verified": True})
    return project["id"]


def test_readiness_requires_nonempty_completed_and_verified(client, task):
    project = client.post("/api/studio/projects", json={"name": "严格验收"}).json()
    endpoint = f"/api/studio/projects/{project['id']}"
    assert client.patch(endpoint, json={"status": "delivered"}).status_code == 409
    client.put(endpoint + "/items", json={"task_ids": [task["id"]]})
    assert client.patch(endpoint, json={"status": "delivered"}).status_code == 409
    client.put(f"/api/studio/rights/{task['id']}", json={"license": "owned", "verified": True})
    assert not client.get(endpoint).json()["checklist"]["ready"]
    db.update_task(task["id"], {"status": "completed"})
    checks = client.get(endpoint).json()["checklist"]
    assert checks == {"total": 1, "completed": 1, "licensed": 1, "ready": True, "issues": []}
    assert client.patch(endpoint, json={"status": "delivered"}).json()["status"] == "delivered"
    assert client.get("/api/studio/projects").json()[0]["ready"]
    assert client.put(endpoint + "/items", json={"task_ids": []}).status_code == 409
    assert client.patch(endpoint, json={"status": "active"}).status_code == 200
    assert client.put(endpoint + "/items", json={"task_ids": []}).status_code == 200


def test_rights_downgrade_reopens_delivered_project(client, task):
    project_id = ready_project(client, task)
    endpoint = f"/api/studio/projects/{project_id}"
    client.patch(endpoint, json={"status": "delivered"})
    client.put(f"/api/studio/rights/{task['id']}", json={"license": "owned", "verified": False})
    assert client.get(endpoint).json()["project"]["status"] == "active"
    assert not client.get(endpoint).json()["checklist"]["ready"]


def test_task_removal_and_status_changes_reopen_delivered_project(client, task):
    project_id = ready_project(client, task)
    endpoint = f"/api/studio/projects/{project_id}"
    client.patch(endpoint, json={"status": "delivered"})
    db.update_task(task["id"], {"status": "failed"})
    assert client.get(endpoint).json()["project"]["status"] == "active"
    db.update_task(task["id"], {"status": "completed"})
    client.patch(endpoint, json={"status": "delivered"})
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 200
    assert client.get(endpoint).json()["project"]["status"] == "active"
    assert not client.get(endpoint).json()["checklist"]["ready"]
