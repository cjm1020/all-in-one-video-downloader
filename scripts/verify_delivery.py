"""Verify a real CC0 video download and byte-for-byte integrity of a delivery ZIP."""

import argparse
import hashlib
import http.cookiejar
import io
import json
import time
import uuid
import zipfile
from urllib.error import HTTPError
from urllib.request import HTTPCookieProcessor, Request, build_opener

SOURCE = "https://interactive-examples.mdn.mozilla.net/media/cc0-videos/flower.mp4"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://localhost:8090")
    parser.add_argument("--token", default="")
    args = parser.parse_args()
    opener = build_opener(HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(path, data=None, method=None, raw=False):
        request = Request(
            args.base_url.rstrip("/") + "/api" + path,
            data=json.dumps(data).encode("utf-8") if data is not None else None,
            headers={"Content-Type": "application/json"}, method=method or ("POST" if data is not None else "GET"),
        )
        try:
            response = opener.open(request, timeout=120)
        except HTTPError as exc:
            raise RuntimeError(f"{exc.code}: {exc.read().decode()}") from exc
        with response:
            body = response.read()
            return body if raw else json.loads(body)

    task_id, project_id = None, None
    try:
        if not call("/session")["authenticated"]:
            call("/session", {"token": args.token})
        assert call("/status")["worker_online"], "Worker must be running"
        # Unique fractional start avoids collision with existing user clips.
        start = 0.6 + (int(uuid.uuid4().hex[:4], 16) % 1000) / 10000
        outcome = call("/tasks", {"urls": [SOURCE], "preset": "commute", "clip_start": start, "clip_end": start + 1})
        assert outcome["added"], "Task unexpectedly duplicates an existing clip"
        task_id = outcome["added"][0]["id"]
        deadline = time.monotonic() + 150
        while time.monotonic() < deadline:
            task = call(f"/tasks/{task_id}")
            if task["status"] in {"completed", "failed", "cancelled"}:
                break
            time.sleep(1)
        assert task["status"] == "completed", task["error"] or task["status"]
        assert abs(task["duration"] - 1) < 0.001, task["duration"]
        original = call(f"/tasks/{task_id}/file", raw=True)
        assert original and len(original) == task["file_size"]
        project = call("/studio/projects", {"name": "CC0 真实交付验收", "notes": "验收结束自动清理。"})
        project_id = project["id"]
        call(f"/studio/projects/{project_id}/items", {"task_ids": [task_id]}, "PUT")
        call(f"/studio/rights/{task_id}", {"license": "cc0", "evidence_url": SOURCE, "verified": True}, "PUT")
        assert call(f"/studio/projects/{project_id}")["checklist"]["ready"]
        call(f"/studio/projects/{project_id}", {"status": "delivered"}, "PATCH")
        payload = call(f"/studio/projects/{project_id}/package", raw=True)
        with zipfile.ZipFile(io.BytesIO(payload)) as archive:
            manifest = json.loads(archive.read("manifest.json"))
            entry = manifest["files"][0]
            assert archive.read(entry["path"]) == original
            assert entry["sha256"] == hashlib.sha256(original).hexdigest()
            assert entry["size_bytes"] == len(original)
            assert manifest["checklist"]["ready"] and manifest["project"]["status"] == "delivered"
            assert {"README.md", "rights.csv", "manifest.json"} <= set(archive.namelist())
        print(json.dumps({
            "passed": True, "source": SOURCE, "clip_seconds": task["duration"],
            "media_bytes": len(original), "zip_bytes": len(payload), "sha256": entry["sha256"],
            "checks": ["real download", "FFmpeg clip", "file length", "rights gate", "delivery transition", "ZIP byte integrity", "manifest hash"],
        }, ensure_ascii=False))
    finally:
        if project_id:
            call(f"/studio/projects/{project_id}", method="DELETE")
        if task_id:
            current = call(f"/tasks/{task_id}")
            if current["status"] in {"downloading", "processing"}:
                call(f"/tasks/{task_id}/actions/cancel", {})
            deadline = time.monotonic() + 40
            while True:
                try:
                    call(f"/tasks/{task_id}", method="DELETE")
                    break
                except RuntimeError as exc:
                    if not str(exc).startswith("409:") or time.monotonic() >= deadline:
                        raise
                    time.sleep(1)


if __name__ == "__main__":
    main()
