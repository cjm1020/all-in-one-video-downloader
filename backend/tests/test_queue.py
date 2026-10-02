from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

from app import db


def test_batch_dedup_and_presets(client):
    url = "https://example.com/video.mp4"
    added = client.post("/api/tasks", json={"urls": [url, url]}).json()
    assert len(added["added"]) == 1 and added["skipped"] == [url]
    assert len(client.post("/api/tasks", json={"urls": [url], "preset": "audio"}).json()["added"]) == 1
    assert len(client.get("/api/tasks").json()) == 2


def test_clips_have_distinct_identity(client):
    for start in [0, 10]:
        result = client.post(
            "/api/tasks", json={"urls": ["https://example.com/x"], "clip_start": start, "clip_end": start + 5}
        )
        assert len(result.json()["added"]) == 1


def test_task_controls_and_conflict(client, task):
    path = f"/api/tasks/{task['id']}/actions/"
    assert client.post(path + "pause").json()["status"] == "paused"
    assert db.claim_task() is None
    assert client.post(path + "pause").status_code == 409
    assert client.post(path + "resume").json()["status"] == "queued"
    assert client.post(path + "cancel").json()["status"] == "cancelled"
    assert client.post(path + "retry").json()["status"] == "queued"


def test_single_atomic_claim(client, task):
    with ThreadPoolExecutor(max_workers=6) as pool:
        claims = list(pool.map(lambda _: db.claim_task(), range(6)))
    assert sum(c is not None for c in claims) == 1
    assert db.get_task(task["id"])["status"] == "downloading"


def test_future_schedule_waits(client):
    future = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
    response = client.post("/api/tasks", json={"urls": ["https://example.com/x"], "scheduled_at": future})
    assert response.status_code == 201
    assert db.claim_task() is None


def test_expired_lease_recovers_but_paused_does_not(client, task):
    db.claim_task()
    expired = (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat()
    db.update_task(task["id"], {"lease_at": expired})
    db.recover_expired_tasks()
    assert db.get_task(task["id"])["status"] == "queued"
    db.update_task(task["id"], {"status": "paused", "lease_at": expired})
    db.recover_expired_tasks()
    assert db.get_task(task["id"])["status"] == "paused"


def test_initialize_keeps_queue_and_settings(client, task):
    db.set_settings({"rate_limit": 120})
    db.initialize()
    assert db.get_task(task["id"]) and db.get_settings()["rate_limit"] == 120


def test_completed_task_cannot_retry(client, task):
    db.update_task(task["id"], {"status": "completed"})
    assert client.post(f"/api/tasks/{task['id']}/actions/retry").status_code == 409


def test_stop_lease_blocks_resume_and_delete_until_worker_exits(client, task):
    db.claim_task()
    path = f"/api/tasks/{task['id']}"
    assert client.post(path + "/actions/pause").status_code == 200
    assert client.post(path + "/actions/resume").status_code == 409
    assert client.delete(path).status_code == 409
    db.update_task(task["id"], {"lease_at": None})
    assert client.post(path + "/actions/resume").status_code == 200


def test_invalid_request_is_not_queued(client):
    for data in [
        {"urls": ["http://127.0.0.1/x"]},
        {"urls": ["https://example.com/x"], "clip_start": 20, "clip_end": 10},
        {"urls": ["https://example.com/x"], "scheduled_at": "2026-10-02T20:00:00"},
        {"urls": []},
    ]:
        assert client.post("/api/tasks", json=data).status_code in [400, 422]
    assert client.get("/api/tasks").json() == []
