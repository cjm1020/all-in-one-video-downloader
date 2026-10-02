from dataclasses import replace

from app import main
from app.learning import clean_transcript


def test_vtt_import_and_summary_invalidated(client, task):
    path = f"/api/tasks/{task['id']}"
    text = "WEBVTT\n\n00:00:00.000 --> 00:00:02.000\n<b>先设计方案，再实现功能。</b>\n先设计方案，再实现功能。\n\n00:00:02.000 --> 00:00:04.000\n测试验证可以帮助我们检查下载流程。"
    response = client.post(path + "/transcript", json={"text": text})
    assert "-->" not in response.json()["transcript"] and "<b>" not in response.json()["transcript"]
    summarized = client.post(path + "/summary", json={"mode": "local"})
    assert "先设计方案" in summarized.json()["summary"] and summarized.json()["summary_mode"] == "local"
    assert client.post(path + "/transcript", json={"text": "这是替换之后的新字幕内容。"}).json()["summary"] == ""


def test_summary_requires_source(client, task):
    assert client.post(f"/api/tasks/{task['id']}/summary", json={"mode": "local"}).status_code == 409
    assert clean_transcript("WEBVTT\n\n1\n00:00:00.000 --> 00:00:02.000") == ""


def test_ai_requires_config(client, task):
    path = f"/api/tasks/{task['id']}"
    client.post(path + "/transcript", json={"text": "这是一份足够用于测试的字幕。"})
    assert client.post(path + "/summary", json={"mode": "ai"}).status_code == 503


def test_cookie_auth_same_origin_and_logout(client, monkeypatch):
    monkeypatch.setattr(main, "config", replace(main.config, access_token="test-secret"))
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/tasks").status_code == 401
    assert client.post("/api/session", json={"token": "wrong"}).status_code == 401
    response = client.post("/api/session", json={"token": "test-secret"})
    assert response.status_code == 200 and "HttpOnly" in response.headers["set-cookie"]
    assert client.get("/api/tasks").status_code == 200
    assert (
        client.post(
            "/api/tasks", json={"urls": ["https://example.com/x"]}, headers={"Origin": "https://attacker.example"}
        ).status_code
        == 403
    )
    assert client.delete("/api/session").status_code == 200
    assert client.get("/api/tasks").status_code == 401


def test_settings_health_and_limits(client):
    assert client.get("/api/health").json()["status"] == "ok"
    response = client.put("/api/settings", json={"default_preset": "audio", "rate_limit": 100, "storage_limit_gb": 2})
    assert response.status_code == 200
    assert client.get("/api/settings").json()["default_preset"] == "audio"
    assert client.put("/api/settings", json={"rate_limit": -1}).status_code == 422
    assert client.get("/api/status").json()["worker_online"] is False
