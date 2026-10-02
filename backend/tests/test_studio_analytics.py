from app import db


def test_analytics_distinguishes_planned_budget_completed_media_and_rights(client, task):
    empty = client.get("/api/studio/analytics").json()
    assert empty["projects"] == 0 and empty["completed_media"] == 0
    first = client.post("/api/studio/projects", json={"name": "客户 A", "budget_cents": 90000}).json()
    client.post("/api/studio/projects", json={"name": "客户 B", "budget_cents": 10000})
    client.patch(f"/api/studio/projects/{first['id']}", json={"status": "active"})
    client.put(f"/api/studio/projects/{first['id']}/items", json={"task_ids": [task["id"]]})
    root = db.config.media_dir / task["id"]
    root.mkdir()
    (root / "source.mp4").write_bytes(b"x" * 300)
    db.update_task(
        task["id"],
        {
            "status": "completed",
            "duration": 180,
            "file_size": 300,
            "platform": "Example",
            "file_path": f"{task['id']}/source.mp4",
        },
    )
    client.put(f"/api/studio/rights/{task['id']}", json={"license": "owned", "verified": True})
    client.patch(f"/api/studio/projects/{first['id']}", json={"status": "delivered"})
    client.post("/api/studio/workflows/team-learning/run", json={"urls": ["https://example.com/queued"]})
    summary = client.get("/api/studio/analytics").json()
    assert summary["projects"] == 2 and summary["delivered_projects"] == 1
    assert summary["active_projects"] == 0
    assert summary["budget_cents"] == 100000
    assert summary["completed_media"] == summary["licensed_media"] == 1
    assert summary["storage_bytes"] == 300 and summary["download_minutes"] == 3
    assert summary["platforms"] == [{"name": "Example", "count": 1}]
    actions = {event["action"] for event in summary["activity"]}
    assert {"project.created", "project.delivered", "rights.updated", "workflow.run"} <= actions
    assert all(isinstance(event["details"], dict) for event in summary["activity"])


def test_analytics_activity_is_bounded_and_includes_export_events(client, task):
    project = client.post("/api/studio/projects", json={"name": "审计"}).json()
    endpoint = f"/api/studio/projects/{project['id']}"
    for index in range(32):
        client.patch(endpoint, json={"notes": f"更新 {index}"})
    assert client.get(endpoint + "/export").status_code == 200
    summary = client.get("/api/studio/analytics").json()
    assert len(summary["activity"]) == 30
    assert summary["activity"][0]["action"] == "project.exported"
    assert summary["licensed_media"] == 0
