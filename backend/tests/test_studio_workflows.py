def test_builtin_recipes_and_custom_workflow_persistence(client):
    builtins = client.get("/api/studio/workflows").json()
    assert len(builtins) == 4
    assert all(recipe["builtin"] for recipe in builtins)
    created = client.post("/api/studio/workflows", json={
        "name": "  采访参考  ", "description": "采访准备", "preset": "audio",
        "tags": [" 采访 ", "采访", ""], "rate_limit": 512,
    })
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
