def project(api, **values):
    response = api.post("/api/studio/projects", json={"name": "产品宣传片", **values})
    assert response.status_code == 201
    return response.json()


def test_project_creation_persists_client_budget_and_deadline(client):
    created = project(client, client="创意团队", budget_cents=120000, due_at="2026-12-01T18:00:00+08:00")
    assert created["status"] == "draft"
    assert created["budget_cents"] == 120000
    assert created["due_at"] == "2026-12-01T10:00:00+00:00"
    assert client.get("/api/studio/projects").json()[0]["id"] == created["id"]
    detail = client.get(f"/api/studio/projects/{created['id']}").json()
    assert detail["project"]["client"] == "创意团队"
    assert not detail["checklist"]["ready"]


def test_project_input_bounds_and_missing_project(client):
    for values in (
        {"name": "  "},
        {"budget_cents": -1},
        {"budget_cents": 1_000_000_000_001},
        {"due_at": "2026-12-01T18:00:00"},
        {"name": "a" * 121},
        {"status": "delivered"},
    ):
        assert client.post("/api/studio/projects", json={"name": "项目", **values}).status_code == 422
    assert client.get("/api/studio/projects/missing").status_code == 404


def test_project_patch_clears_deadline_and_preserves_other_fields(client):
    created = project(client, budget_cents=30000, due_at="2026-12-01T18:00:00Z")
    endpoint = f"/api/studio/projects/{created['id']}"
    edited = client.patch(endpoint, json={"name": " 新名称 ", "due_at": None, "status": "active"})
    assert edited.status_code == 200
    assert edited.json()["name"] == "新名称"
    assert edited.json()["due_at"] is None
    assert edited.json()["budget_cents"] == 30000
    assert client.patch(endpoint, json={"budget_cents": None}).status_code == 400
    assert client.patch(endpoint, json={"name": "  "}).status_code == 400
    assert client.patch(endpoint, json={"status": "delivered"}).status_code == 409


def test_project_deletion_preserves_tasks_and_other_projects(client, task):
    first, second = project(client), project(client, name="另一项目")
    assert client.delete(f"/api/studio/projects/{first['id']}").status_code == 200
    assert client.get(f"/api/studio/projects/{first['id']}").status_code == 404
    assert client.get(f"/api/studio/projects/{second['id']}").status_code == 200
    assert client.get(f"/api/tasks/{task['id']}").status_code == 200
    assert client.delete("/api/studio/projects/missing").status_code == 404
