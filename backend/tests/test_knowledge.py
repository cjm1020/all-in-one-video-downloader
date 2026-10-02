import json
from datetime import datetime, timezone

import pytest

from app import db
from app.captions import caption_text, for_clip, parse_captions
from app.knowledge_db import replace_transcript
from app.study import next_review

CAPTIONS = """WEBVTT

NOTE This note is not a subtitle.
Never index this secret note.

intro
00:00:01.000 --> 00:00:04.000 align:start
<b>SQLite transactions protect editorial data.</b>

00:00:04.000 --> 00:00:08.000
测试验证可以帮助我们检查下载和交付流程。
"""


def import_source(client, task, text=CAPTIONS):
    response = client.post(f"/api/tasks/{task['id']}/transcript", json={"text": text})
    assert response.status_code == 200
    return response.json()


def test_caption_search_returns_real_timestamps_and_literal_query(client, task):
    imported = import_source(client, task)
    assert "secret" not in imported["transcript"]
    response = client.get("/api/knowledge/search", params={"q": "sqlite"}).json()
    assert response["total"] == 1
    assert response["results"][0]["start"] == 1
    assert response["results"][0]["end"] == 4
    assert response["results"][0]["task_id"] == task["id"]
    assert client.get("/api/knowledge/search", params={"q": "%"}).json()["total"] == 0
    assert client.get("/api/knowledge/search", params={"q": "' OR 1=1 --"}).json()["total"] == 0
    assert client.get("/api/knowledge/search", params={"q": " "}).status_code == 422
    assert client.get("/api/knowledge/search", params={"q": "SQLite", "limit": 0}).status_code == 422


def test_legacy_transcript_search_and_replacement(client, task):
    db.update_task(task["id"], {"transcript": "旧库里的字幕也能找到需要的证据。"})
    result = client.get("/api/knowledge/search", params={"q": "证据"}).json()
    assert result["total"] == 1 and result["results"][0]["start"] is None
    import_source(client, task)
    assert client.get("/api/knowledge/search", params={"q": "证据"}).json()["total"] == 0


def test_marker_bounds_order_delete_and_task_cascade(client, task):
    db.update_task(task["id"], {"duration": 10})
    path = f"/api/knowledge/tasks/{task['id']}/markers"
    assert client.post(path, json={"position": 11, "label": "越界"}).status_code == 422
    assert client.post(path, json={"position": -1, "label": "越界"}).status_code == 422
    assert client.post(path, json={"position": 1, "label": " "}).status_code == 422
    first = client.post(path, json={"position": 8, "label": "结尾"}).json()
    second = client.post(path, json={"position": 2, "label": "开头", "notes": "引用时核对上下文"}).json()
    assert [row["id"] for row in client.get(path).json()] == [second["id"], first["id"]]
    assert client.delete(f"/api/knowledge/markers/{first['id']}").status_code == 200
    assert client.delete(f"/api/knowledge/markers/{first['id']}").status_code == 404
    assert client.delete(f"/api/tasks/{task['id']}").status_code == 200
    with db.connection() as conn:
        assert conn.execute("SELECT COUNT(*) FROM knowledge_markers").fetchone()[0] == 0


def test_cards_require_source_deduplicate_and_invalidate_only_generated(client, task):
    path = f"/api/knowledge/tasks/{task['id']}/cards"
    assert client.post(path + "/generate").status_code == 409
    manual = client.post(path, json={"question": "独立问题", "answer": "用户的判断"}).json()
    import_source(client, task)
    generated = client.post(path + "/generate").json()
    assert generated["mode"] == "local-extraction" and len(generated["added"]) == 2
    assert client.post(path + "/generate").json()["added"] == []
    assert client.post(path, json={"question": "独立问题", "answer": "用户的判断"}).status_code == 409
    for card in generated["added"]:
        assert "原句：" in card["answer"] and card["source_hash"]
    import_source(client, task, "这是替换后的全新字幕，应当撤下旧字幕的自动复习卡。")
    assert [card["id"] for card in client.get(path).json()] == [manual["id"]]


def test_reviews_due_guard_and_invalid_rating(client, task):
    card = client.post(f"/api/knowledge/tasks/{task['id']}/cards", json={"question": "Q", "answer": "A"}).json()
    path = f"/api/knowledge/cards/{card['id']}/review"
    assert card["id"] in [row["id"] for row in client.get("/api/knowledge/cards/due").json()]
    assert client.post(path, json={"rating": "bogus"}).status_code == 422
    reviewed = client.post(path, json={"rating": "good"}).json()
    assert reviewed["interval_days"] == 1 and reviewed["repetitions"] == 1
    assert client.get("/api/knowledge/cards/due").json() == []
    assert client.post(path, json={"rating": "easy"}).status_code == 409
    assert client.delete(f"/api/knowledge/cards/{card['id']}").status_code == 200


@pytest.mark.parametrize("rating,interval,minutes", [("again", 0, 10), ("good", 1, 1440), ("easy", 4, 5760)])
def test_schedule_is_deterministic(rating, interval, minutes):
    instant = datetime(2026, 10, 3, tzinfo=timezone.utc)
    value = next_review({"interval_days": 0, "repetitions": 2}, rating, instant)
    assert value["interval_days"] == interval
    assert (datetime.fromisoformat(value["due_at"]) - instant).total_seconds() == minutes * 60
    assert next_review({"interval_days": 300, "repetitions": 10}, "easy", instant)["interval_days"] == 365


def test_brief_exports_include_evidence_and_marker(client, task):
    import_source(client, task)
    client.post(f"/api/knowledge/tasks/{task['id']}/markers", json={"position": 1, "label": "事务重点"})
    path = f"/api/knowledge/tasks/{task['id']}/brief"
    body = json.loads(client.get(path, params={"format": "json"}).text)
    assert body["mode"] == "local-extraction"
    assert body["source_available"] and body["moments"][0]["label"] == "事务重点"
    markdown = client.get(path)
    assert "SQLite" in markdown.text and "授权" in markdown.text
    assert "attachment" in markdown.headers["content-disposition"]
    assert client.get(path, params={"format": "html"}).status_code == 400


def test_caption_clip_rebase_and_conditional_completion(client, task):
    cues = for_clip(parse_captions(CAPTIONS), 2, 5)
    assert [(cue["start"], cue["end"]) for cue in cues] == [(0, 2), (2, 3)]
    assert "SQLite" in caption_text(cues)
    assert for_clip(parse_captions("无时间戳的原文"), 2, 5) == []
    assert not replace_transcript(task["id"], caption_text(cues), cues, only_status=("downloading",))
    assert db.get_task(task["id"])["transcript"] == ""
    db.update_task(task["id"], {"status": "downloading"})
    assert replace_transcript(
        task["id"], caption_text(cues), cues, only_status=("downloading",),
        media_values={"status": "completed", "duration": 3},
    )
    assert client.get("/api/knowledge/search", params={"q": "SQLite"}).json()["results"][0]["start"] == 0
    assert db.get_task(task["id"])["duration"] == 3


def test_migration_is_idempotent_and_delete_cascades_cards(client, task):
    path = f"/api/knowledge/tasks/{task['id']}/cards"
    client.post(path, json={"question": "保存", "answer": "迁移后仍在"})
    db.initialize()
    db.initialize()
    assert len(client.get(path).json()) == 1
    client.delete(f"/api/tasks/{task['id']}")
    assert client.get("/api/knowledge/cards/due").json() == []
