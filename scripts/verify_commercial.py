"""Exercise commercial APIs against a running instance without downloading media.

Creates explicitly scheduled test data and removes its tasks, projects, and recipes.
Audit events remain to preserve the truthful operation history.
This proves workflow contracts and guards, not real video download or copyright ownership.
"""

import argparse
import http.cookiejar
import json
import uuid
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8090")
    parser.add_argument("--token", default="", help="Access token, if the instance requires one")
    args = parser.parse_args()
    opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))
    checks = []

    def call(method, path, data=None, expected=200, raw=False):
        request = Request(
            args.base_url.rstrip("/") + "/api" + path,
            data=json.dumps(data).encode("utf-8") if data is not None else None,
            headers={"Content-Type": "application/json"}, method=method,
        )
        try:
            response = opener.open(request, timeout=30)
        except HTTPError as exc:
            response = exc
        with response:
            body = response.read().decode("utf-8")
            if response.status != expected:
                raise RuntimeError(f"{method} {path}: expected {expected}, received {response.status}: {body[:300]}")
            return body if raw else json.loads(body)

    def checked(label):
        checks.append(label)
        print("PASS " + label)

    task_id, project_id, workflow_id = None, None, None
    try:
        session = call("GET", "/session")
        if not session["authenticated"]:
            call("POST", "/session", {"token": args.token})
        url = f"https://example.com/commercial-acceptance/{uuid.uuid4()}"
        scheduled = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
        task = call("POST", "/tasks", {"urls": [url], "scheduled_at": scheduled}, expected=201)["added"][0]
        task_id = task["id"]
        project = call("POST", "/studio/projects", {
            "name": "自动验收临时项目", "client": "API 验收", "budget_cents": 12300,
        }, expected=201)
        project_id = project["id"]
        call("PUT", f"/studio/projects/{project_id}/items", {"task_ids": [task_id]})
        detail = call("GET", f"/studio/projects/{project_id}")
        assert detail["checklist"]["total"] == 1 and not detail["checklist"]["ready"]
        call("PATCH", f"/studio/projects/{project_id}", {"status": "delivered"}, expected=409)
        checked("queued and unverified media cannot be delivered")

        call("PUT", f"/studio/rights/{task_id}", {"license": "unknown", "verified": True}, expected=422)
        call("PUT", f"/studio/rights/{task_id}", {"license": "unknown", "verified": False})
        checked("unknown rights cannot be recorded as verified")

        call("POST", f"/tasks/{task_id}/transcript", {
            "text": "WEBVTT\n\n00:00:01.000 --> 00:00:03.000\n字幕证据应保留时间戳，自动复习卡需要追溯原文。",
        })
        found = call("GET", "/knowledge/search?q=%E5%AD%97%E5%B9%95%E8%AF%81%E6%8D%AE")
        assert any(row["task_id"] == task_id and row["start"] == 1 for row in found["results"])
        checked("subtitle search returns original timestamp evidence")

        call("POST", f"/knowledge/tasks/{task_id}/markers", {"position": 1, "label": "证据起点"}, expected=201)
        generated = call("POST", f"/knowledge/tasks/{task_id}/cards/generate")["added"]
        assert generated
        assert call("POST", f"/knowledge/tasks/{task_id}/cards/generate")["added"] == []
        reviewed = call("POST", f"/knowledge/cards/{generated[0]['id']}/review", {"rating": "good"})
        assert reviewed["interval_days"] == 1
        call("POST", f"/knowledge/cards/{generated[0]['id']}/review", {"rating": "good"}, expected=409)
        brief = call("GET", f"/knowledge/tasks/{task_id}/brief", raw=True)
        assert "证据起点" in brief and "本地原句" in brief
        checked("source cards deduplicate and reject premature repeat reviews")

        recipe = call("POST", "/studio/workflows", {
            "name": "自动验收临时配方", "description": "仅验证重复执行，不执行网络下载",
            "preset": "everyday", "collection_id": "inbox", "tags": ["验收"], "rate_limit": 0,
        }, expected=201)
        workflow_id = recipe["id"]
        outcome = call("POST", f"/studio/workflows/{workflow_id}/run", {"urls": [url], "project_id": project_id})
        assert outcome["added"] == [] and outcome["skipped"] == [url]
        checked("reusable recipe execution does not create duplicate downloads")

        export = call("GET", f"/studio/projects/{project_id}/export?format=json", raw=True)
        assert task_id in export
        analytics = call("GET", "/studio/analytics")
        assert analytics["projects"] >= 1 and analytics["activity"]
        checked("delivery manifests and activity analytics use saved data")
    finally:
        # Remove the project first, including after a partially successful run.
        cleanup_errors = []
        for path in [
            f"/studio/projects/{project_id}" if project_id else None,
            f"/studio/workflows/{workflow_id}" if workflow_id else None,
            f"/tasks/{task_id}" if task_id else None,
        ]:
            if path:
                try:
                    call("DELETE", path)
                except (OSError, RuntimeError, ValueError) as exc:
                    cleanup_errors.append(str(exc))
        if cleanup_errors:
            raise RuntimeError("Acceptance cleanup failed: " + "; ".join(cleanup_errors))
    print(json.dumps({"passed": len(checks), "checks": checks, "fixture": "scheduled synthetic API records"}, ensure_ascii=False))


if __name__ == "__main__":
    main()
