from app import db


def make_project(client):
    return client.post("/api/studio/projects", json={"name": "素材交付"}).json()["id"]


def test_membership_replacement_is_atomic_and_deduplicated(client, task):
    project_id = make_project(client)
    endpoint = f"/api/studio/projects/{project_id}/items"
    response = client.put(endpoint, json={"task_ids": [task["id"], task["id"]]})
    assert response.status_code == 200
    assert [item["id"] for item in response.json()["items"]] == [task["id"]]
    assert client.put(endpoint, json={"task_ids": ["missing", task["id"]]}).status_code == 404
    assert client.get(f"/api/studio/projects/{project_id}").json()["checklist"]["total"] == 1
    assert client.put(endpoint, json={"task_ids": []}).json()["items"] == []
    assert db.get_task(task["id"])


def test_deleting_task_cascades_memberships_and_project_delete_keeps_media(client, task):
    first, second = make_project(client), make_project(client)
    for project_id in (first, second):
        assert (
            client.put(f"/api/studio/projects/{project_id}/items", json={"task_ids": [task["id"]]}).status_code == 200
        )
    assert client.delete(f"/api/studio/projects/{first}").status_code == 200
    assert db.get_task(task["id"])
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 200
    assert client.get(f"/api/studio/projects/{second}").json()["items"] == []


def test_membership_limits_and_missing_project(client, task):
    project_id = make_project(client)
    assert (
        client.put(f"/api/studio/projects/{project_id}/items", json={"task_ids": [task["id"]] * 501}).status_code == 422
    )
    assert client.put("/api/studio/projects/missing/items", json={"task_ids": []}).status_code == 404
