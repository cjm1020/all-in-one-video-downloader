import csv
import io
import json
import re

from fastapi import HTTPException

from .. import db
from .storage import project_snapshot, record

MAX_METADATA_BYTES = 8 * 1024 * 1024


def manifest(snapshot: dict) -> dict:
    fields = ("id", "title", "url", "preset", "platform", "status", "duration", "file_size", "tags",
              "notes", "summary", "rights")
    return {"schema_version": 1, "generated_at": db.now(), "project": snapshot["project"],
            "checklist": snapshot["checklist"],
            "items": [{key: item[key] for key in fields} for item in snapshot["items"]]}


def bounded_metadata(body: str) -> bytes:
    encoded = body.encode("utf-8")
    if len(encoded) > MAX_METADATA_BYTES:
        raise HTTPException(413, "项目资料过大，请减少素材数量或笔记内容")
    return encoded


def json_manifest(snapshot: dict) -> bytes:
    return bounded_metadata(json.dumps(manifest(snapshot), ensure_ascii=False, indent=2))


def markdown_label(value) -> str:
    return re.sub(r"([\\`*_{}\[\]<>#|])", r"\\\1", str(value).replace("\r", " ").replace("\n", " "))


def markdown_manifest(snapshot: dict) -> bytes:
    project, checks = snapshot["project"], snapshot["checklist"]
    body = [f"# {markdown_label(project['name'])}", "",
            f"客户：{markdown_label(project['client']) or '未填写'}",
            f"预算（分）：{project['budget_cents']}", f"截止日期：{project['due_at'] or '未设置'}",
            f"项目状态：{project['status']}", "",
            f"交付检查：{checks['completed']}/{checks['total']} 素材完成，"
            f"{checks['licensed']}/{checks['total']} 授权审核完成。",
            f"可以交付：{'是' if checks['ready'] else '否'}", "",
            "## 项目说明", "", project["notes"] or "暂无说明", "", "## 素材清单", ""]
    for index, item in enumerate(snapshot["items"], 1):
        rights = item["rights"]
        body.extend([f"### {index}. {markdown_label(item['title'] or item['id'])}", "",
                     f"来源：{item['url']}", f"状态：{item['status']}",
                     f"授权：{rights['license']}（{'已审核' if rights['verified'] else '待审核'}）",
                     f"署名：{markdown_label(rights['attribution']) or '无'}",
                     f"授权凭证：{rights['evidence_url'] or '无'}", "",
                     item["summary"] or "暂无摘要", "", item["notes"] or "暂无素材笔记", ""])
    if checks["issues"]:
        body.extend(["## 待处理项", ""])
        body.extend(f"- {issue['task_id'] or '项目'}：{issue['reason']}" for issue in checks["issues"])
    return bounded_metadata("\n".join(body))


def csv_cell(value) -> str:
    text = str(value)
    # Spreadsheet applications may interpret an imported value as a formula.
    if text.lstrip().startswith(("=", "+", "-", "@")) or text.startswith(("\t", "\r", "\n")):
        text = "'" + text
    return text


def csv_manifest(snapshot: dict) -> bytes:
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer)
    writer.writerow(["task_id", "title", "url", "status", "license", "verified", "attribution", "evidence_url",
                     "duration_seconds", "file_size_bytes", "tags"])
    for item in snapshot["items"]:
        rights = item["rights"]
        writer.writerow([csv_cell(value) for value in (
            item["id"], item["title"], item["url"], item["status"], rights["license"], rights["verified"],
            rights["attribution"], rights["evidence_url"], item["duration"], item["file_size"], ", ".join(item["tags"]),
        )])
    return bounded_metadata("\ufeff" + buffer.getvalue())


def export_project(project_id: str, format: str) -> tuple[bytes, str, str]:
    formats = {"json": (json_manifest, "application/json", "json"),
               "markdown": (markdown_manifest, "text/markdown", "md"),
               "csv": (csv_manifest, "text/csv", "csv")}
    if format not in formats:
        raise HTTPException(400, "不支持的项目导出格式")
    exporter, media_type, suffix = formats[format]
    with db.connection() as conn:
        conn.execute("BEGIN IMMEDIATE")
        snapshot = project_snapshot(conn, project_id)
        body = exporter(snapshot)
        record(conn, "project.exported", project_id, {"format": format, "ready": snapshot["checklist"]["ready"]})
    return body, media_type, suffix
