import hashlib
import io
import json
import zipfile

from app import db
from app.studio import package


def package_project(client, task, content=b"licensed media"):
    root = package.config.media_dir / task["id"]
    root.mkdir()
    (root / "source.mp4").write_bytes(content)
    db.update_task(task["id"], {"status": "completed", "file_path": f"{task['id']}/source.mp4", "title": "../客户/片段"})
    project = client.post("/api/studio/projects", json={"name": "安全交付"}).json()
    client.put(f"/api/studio/projects/{project['id']}/items", json={"task_ids": [task["id"]]})
    client.put(f"/api/studio/rights/{task['id']}", json={"license": "owned", "verified": True})
    return project["id"]


def test_delivery_zip_contains_manifest_rights_and_actual_safe_media(client, task):
    project_id = package_project(client, task)
    response = client.get(f"/api/studio/projects/{project_id}/package")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = archive.namelist()
        assert {"manifest.json", "README.md", "rights.csv"} <= set(names)
        media = next(name for name in names if name.startswith("media/"))
        assert ".." not in media and "\\" not in media
        assert archive.read(media) == b"licensed media"
        manifest = json.loads(archive.read("manifest.json"))
        assert manifest["checklist"]["ready"]
        assert manifest["files"] == [{"task_id": task["id"], "path": media, "size_bytes": len(b"licensed media"),
                                      "sha256": hashlib.sha256(b"licensed media").hexdigest()}]
        assert "file_path" not in archive.read("manifest.json").decode()
    # Slots and temporary files are released when the response finishes.
    assert client.get(f"/api/studio/projects/{project_id}/package").status_code == 200


def test_archive_rejects_unreviewed_and_outside_media_paths(client, task):
    project_id = package_project(client, task)
    endpoint = f"/api/studio/projects/{project_id}/package"
    client.put(f"/api/studio/rights/{task['id']}", json={"license": "owned"})
    assert client.get(endpoint).status_code == 409
    client.put(f"/api/studio/rights/{task['id']}", json={"license": "owned", "verified": True})
    db.update_task(task["id"], {"file_path": "../library.sqlite3"})
    assert client.get(endpoint).status_code == 409
    db.update_task(task["id"], {"file_path": str(package.config.db_path)})
    assert client.get(endpoint).status_code == 409


def test_archive_uses_actual_file_size_not_database_estimate(client, task, monkeypatch):
    project_id = package_project(client, task, b"x" * 40)
    monkeypatch.setattr(package, "MAX_PACKAGE_BYTES", 32)
    assert client.get(f"/api/studio/projects/{project_id}/package").status_code == 413
    monkeypatch.setattr(package, "MAX_PACKAGE_BYTES", 512 * 1024 * 1024)
    (package.config.media_dir / task["id"] / "source.mp4").write_bytes(b"")
    assert client.get(f"/api/studio/projects/{project_id}/package").status_code == 409


def test_archive_capacity_and_missing_project_release_slot(client):
    assert client.get("/api/studio/projects/missing/package").status_code == 404
    assert package.package_slots.acquire(blocking=False)
    assert package.package_slots.acquire(blocking=False)
    try:
        assert client.get("/api/studio/projects/missing/package").status_code == 429
    finally:
        package.package_slots.release()
        package.package_slots.release()


def test_archive_rejects_media_that_changes_during_copy(client, task, monkeypatch):
    project_id = package_project(client, task)
    original = package.os.fstat
    calls = 0

    def changed_stat(fd):
        nonlocal calls
        stat = original(fd)
        calls += 1
        if calls == 2:
            from types import SimpleNamespace

            return SimpleNamespace(st_size=stat.st_size, st_mtime_ns=stat.st_mtime_ns + 1)
        return stat

    monkeypatch.setattr(package.os, "fstat", changed_stat)
    assert client.get(f"/api/studio/projects/{project_id}/package").status_code == 409
    with db.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM studio_activity WHERE action='project.packaged'").fetchone()[0] == 0


def test_rights_revocation_during_copy_is_not_blocked_and_prevents_delivery(client, task, monkeypatch):
    from app.studio import storage
    from app.studio.models import RightsPatch

    project_id = package_project(client, task)
    original_digest = package.hashlib.sha256

    class RevokingDigest:
        def __init__(self):
            self.digest = original_digest()

        def update(self, chunk):
            storage.set_rights(task["id"], RightsPatch(license="unknown"))
            self.digest.update(chunk)

        def hexdigest(self):
            return self.digest.hexdigest()

    monkeypatch.setattr(package.hashlib, "sha256", RevokingDigest)
    assert client.get(f"/api/studio/projects/{project_id}/package").status_code == 409
    assert client.get(f"/api/studio/rights/{task['id']}").json()["license"] == "unknown"
    with db.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM studio_activity WHERE action='project.packaged'").fetchone()[0] == 0
