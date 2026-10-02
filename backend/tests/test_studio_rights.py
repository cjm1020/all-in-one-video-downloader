import pytest

from app import db


def test_rights_default_unknown_and_explicit_review(client, task):
    endpoint = f"/api/studio/rights/{task['id']}"
    assert client.get(endpoint).json()["license"] == "unknown"
    assert not client.get(endpoint).json()["verified"]
    owned = client.put(endpoint, json={"license": "owned"}).json()
    assert not owned["verified"]
    verified = client.put(endpoint, json={"license": "owned", "verified": True}).json()
    assert verified["verified"] and verified["updated_at"]
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 200
    with db.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM studio_rights").fetchone()[0] == 0


@pytest.mark.parametrize(
    "data",
    [
        {"license": "unknown", "verified": True},
        {"license": "cc-by", "verified": True},
        {"license": "permission", "verified": True},
        {"license": "permission", "evidence_url": "https://localhost/proof"},
        {"license": "owned", "evidence_url": "file:///secret.txt"},
        {"license": "owned", "evidence_url": "https://user:password@example.com/proof"},
    ],
)
def test_rights_reject_incomplete_or_unsafe_evidence(client, task, data):
    endpoint = f"/api/studio/rights/{task['id']}"
    assert client.put(endpoint, json=data).status_code == 422
    assert client.get(endpoint).json()["license"] == "unknown"


def test_attribution_and_permission_evidence_are_persisted(client, task):
    endpoint = f"/api/studio/rights/{task['id']}"
    cc = client.put(endpoint, json={"license": "cc-by", "attribution": " Author · CC BY 4.0 ", "verified": True})
    assert cc.json()["attribution"] == "Author · CC BY 4.0"
    permission = client.put(endpoint, json={"license": "permission", "evidence_url": "https://example.com/proof#top"})
    assert permission.json()["evidence_url"] == "https://example.com/proof"
    assert not permission.json()["verified"]
    assert client.put("/api/studio/rights/missing", json={"license": "cc0"}).status_code == 404


def test_project_items_include_rights_records(client, task):
    project = client.post("/api/studio/projects", json={"name": "授权项目"}).json()
    endpoint = f"/api/studio/projects/{project['id']}/items"
    items = client.put(endpoint, json={"task_ids": [task["id"]]}).json()["items"]
    assert items[0]["rights"]["license"] == "unknown"
    assert "license" not in items[0]
    client.put(f"/api/studio/rights/{task['id']}", json={"license": "cc0", "verified": True})
    detail = client.get(f"/api/studio/projects/{project['id']}").json()
    assert detail["items"][0]["rights"]["verified"]
