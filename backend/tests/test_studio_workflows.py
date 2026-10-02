def test_builtin_recipes_and_custom_workflow_persistence(client):
    builtins = client.get("/api/studio/workflows").json()
    assert len(builtins) == 4
    assert all(recipe["builtin"] for recipe in builtins)
    created = client.post(
        "/api/studio/workflows",
        json={
            "name": "  采访参考  ",
            "description": "采访准备",
            "preset": "audio",
            "tags": [" 采访 ", "采访", ""],
            "rate_limit": 512,
        },
    )
    assert created.status_code == 201
    workflow = created.json()
    assert workflow["name"] == "采访参考" and workflow["tags"] == ["采访"]
    assert not workflow["builtin"] and workflow["collection_id"] == "inbox"
    assert len(client.get("/api/studio/workflows").json()) == 5
    assert client.delete(f"/api/studio/workflows/{workflow['id']}").status_code == 200
    assert len(client.get("/api/studio/workflows").json()) == 4
    assert client.delete(f"/api/studio/workflows/{builtins[0]['id']}").status_code == 409


def test_recipe_validation_and_deleted_collection_fallback(client):
    collection = client.post("/api/collections", json={"name": "客户资料"}).json()
    workflow = client.post("/api/studio/workflows", json={"name": "客户归档", "collection_id": collection["id"]}).json()
    assert client.delete(f"/api/collections/{collection['id']}").status_code == 200
    recipes = client.get("/api/studio/workflows").json()
    assert next(recipe for recipe in recipes if recipe["id"] == workflow["id"])["collection_id"] == "inbox"
    assert client.post("/api/studio/workflows", json={"name": "  "}).status_code == 422
    assert client.post("/api/studio/workflows", json={"name": "测试", "collection_id": "missing"}).status_code == 404
    assert client.post("/api/studio/workflows", json={"name": "测试", "rate_limit": -1}).status_code == 422
    assert client.delete("/api/studio/workflows/missing").status_code == 404


def test_workflow_run_applies_recipe_and_project_membership_atomically(client):
    project = client.post("/api/studio/projects", json={"name": "播客项目"}).json()
    endpoint = "/api/studio/workflows/podcast-research/run"
    response = client.post(endpoint, json={"urls": ["https://example.com/episode"], "project_id": project["id"]})
    assert response.status_code == 200
    added = response.json()["added"]
    assert len(added) == 1 and added[0]["preset"] == "audio"
    assert added[0]["tags"] == ["播客", "研究"]
    detail = client.get(f"/api/studio/projects/{project['id']}").json()
    assert detail["items"][0]["id"] == added[0]["id"]
    assert detail["items"][0]["rights"]["license"] == "unknown"
    duplicate = client.post(endpoint, json={"urls": ["https://example.com/episode"]}).json()
    assert duplicate == {"added": [], "skipped": ["https://example.com/episode"]}


def test_invalid_batch_or_missing_project_creates_no_partial_tasks(client):
    endpoint = "/api/studio/workflows/client-archive/run"
    assert client.post(endpoint, json={"urls": ["https://example.com/a", "https://127.0.0.1/b"]}).status_code == 400
    assert client.get("/api/tasks").json() == []
    assert client.post(endpoint, json={"urls": ["https://example.com/a"], "project_id": "missing"}).status_code == 404
    assert client.get("/api/tasks").json() == []
    assert client.post(endpoint, json={"urls": ["https://example.com/" + "a" * 2048]}).status_code == 422
    assert client.post("/api/studio/workflows/missing/run", json={"urls": ["https://example.com/a"]}).status_code == 404


def test_custom_recipe_runs_after_destination_collection_deleted(client):
    collection = client.post("/api/collections", json={"name": "旧合集"}).json()
    recipe = client.post(
        "/api/studio/workflows",
        json={
            "name": "可迁移工作流",
            "preset": "commute",
            "rate_limit": 256,
            "collection_id": collection["id"],
        },
    ).json()
    client.delete(f"/api/collections/{collection['id']}")
    response = client.post(f"/api/studio/workflows/{recipe['id']}/run", json={"urls": ["https://example.com/new"]})
    assert response.status_code == 200
    task = response.json()["added"][0]
    assert task["collection_id"] == "inbox" and task["rate_limit"] == 256
