from app import db, library


def test_collection_delete_preserves_content(client, task):
    collection = client.post("/api/collections", json={"name": "编程灵感", "color": "lavender"}).json()
    assert client.patch(f"/api/tasks/{task['id']}", json={"collection_id": collection["id"]}).status_code == 200
    assert client.delete(f"/api/collections/{collection['id']}").status_code == 200
    assert db.get_task(task["id"])["collection_id"] == "inbox"
    assert client.delete("/api/collections/inbox").status_code == 400


def test_notes_tags_favorites_and_exports(client, task):
    path = f"/api/tasks/{task['id']}"
    edit = client.patch(path, json={"notes": "有趣的讲解", "favorite": True, "tags": ["教程", "教程", " 灵感 "]})
    assert edit.json()["tags"] == ["教程", "灵感"] and edit.json()["favorite"]
    exported = client.get(path + "/export")
    assert "有趣的讲解" in exported.text
    assert exported.headers["content-disposition"].endswith('.md"')
    assert client.get(path + "/export?format=json").json()["notes"] == "有趣的讲解"


def test_range_delivery_and_safe_file(client, task):
    root = library.config.media_dir / task["id"]
    root.mkdir()
    (root / "source.mp4").write_bytes(b"0123456789")
    db.update_task(task["id"], {"status": "completed", "file_path": f"{task['id']}/source.mp4", "file_size": 10})
    response = client.get(f"/api/tasks/{task['id']}/file", headers={"Range": "bytes=2-5"})
    assert response.status_code == 206 and response.content == b"2345"
    assert (
        client.get(f"/api/tasks/{task['id']}/file?download=true")
        .headers["content-disposition"]
        .startswith("attachment")
    )
    db.update_task(task["id"], {"file_path": "../library.sqlite3"})
    assert client.get(f"/api/tasks/{task['id']}/file").status_code == 404


def test_delete_active_rejected_and_cleanup(client, task):
    db.claim_task()
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 409
    db.update_task(task["id"], {"status": "paused"})
    root = library.config.media_dir / task["id"]
    root.mkdir()
    (root / "source.part").write_text("partial")
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 200
    assert not root.exists() and db.get_task(task["id"]) is None


def test_unknown_collection_rejected(client, task):
    assert client.patch(f"/api/tasks/{task['id']}", json={"collection_id": "missing"}).status_code == 404
    assert (
        client.post("/api/tasks", json={"urls": ["https://example.com/y"], "collection_id": "missing"}).status_code
        == 400
    )
