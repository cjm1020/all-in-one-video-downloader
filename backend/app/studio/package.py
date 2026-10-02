import os
import re
import tempfile
import threading
import zipfile
from contextlib import ExitStack
from pathlib import Path

from fastapi import HTTPException

from .. import db
from ..config import config
from .exports import csv_manifest, json_manifest, markdown_manifest
from .storage import project_snapshot, record

MAX_PACKAGE_BYTES = 512 * 1024 * 1024
MAX_PACKAGE_ITEMS = 100
CHUNK_BYTES = 1024 * 1024
package_slots = threading.BoundedSemaphore(2)


def safe_path(task: dict) -> Path:
    media_root = config.media_dir.resolve()
    identifier = task["id"]
    if Path(identifier).name != identifier or identifier in {".", ".."}:
        raise HTTPException(409, "素材标识无效")
    root = (media_root / identifier).resolve()
    path_value = task["file_path"]
    if not path_value or Path(path_value).is_absolute():
        raise HTTPException(409, "素材文件尚未准备好")
    target = (media_root / path_value).resolve()
    if root.parent != media_root or not target.is_relative_to(root) or not target.is_file():
        raise HTTPException(409, "素材文件已丢失或路径无效，请重新下载")
    return target


def archive_filename(index: int, task: dict, path: Path) -> str:
    label = re.sub(r"[^\w\-. ]", "_", task["title"] or "media", flags=re.UNICODE).strip(" .")[:70] or "media"
    suffix = re.sub(r"[^a-zA-Z0-9.]", "", path.suffix)[:12]
    return f"media/{index:03d}-{label}-{task['id'][:8]}{suffix}"


def build_package(project_id: str):
    """Spool a bounded archive; caller owns the returned file and slot cleanup."""
    spool = tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b")
    try:
        with db.connection() as conn, ExitStack() as opened:
            conn.execute("BEGIN IMMEDIATE")
            snapshot = project_snapshot(conn, project_id)
            if not snapshot["checklist"]["ready"]:
                raise HTTPException(409, "请先完成全部素材下载和授权审核，再生成交付包")
            if len(snapshot["items"]) > MAX_PACKAGE_ITEMS:
                raise HTTPException(413, f"一次交付最多包含 {MAX_PACKAGE_ITEMS} 个素材")
            sources, expected_bytes = [], 0
            for index, item in enumerate(snapshot["items"], 1):
                task = dict(conn.execute("SELECT * FROM tasks WHERE id=?", (item["id"],)).fetchone())
                path = safe_path(task)
                source = opened.enter_context(path.open("rb"))
                # Resolve again after opening to reject a replaced directory or symlink.
                if safe_path(task) != path:
                    raise HTTPException(409, "素材文件在打包期间发生变化，请重试")
                size = os.fstat(source.fileno()).st_size
                if size <= 0:
                    raise HTTPException(409, "素材文件为空，请重新下载")
                expected_bytes += size
                if expected_bytes > MAX_PACKAGE_BYTES:
                    raise HTTPException(413, "交付包素材总量不能超过 512 MiB，请拆分项目")
                sources.append((source, archive_filename(index, task, path)))
            documents = {"manifest.json": json_manifest(snapshot), "README.md": markdown_manifest(snapshot),
                         "rights.csv": csv_manifest(snapshot)}
            if expected_bytes + sum(len(value) for value in documents.values()) > MAX_PACKAGE_BYTES:
                raise HTTPException(413, "素材与资料总量超过交付包限制，请拆分项目")
            copied_bytes = 0
            with zipfile.ZipFile(spool, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
                for filename, body in documents.items():
                    archive.writestr(filename, body)
                for source, filename in sources:
                    with archive.open(filename, "w", force_zip64=True) as destination:
                        while chunk := source.read(CHUNK_BYTES):
                            copied_bytes += len(chunk)
                            if copied_bytes > expected_bytes:
                                raise HTTPException(409, "素材文件在打包期间变大，请重试")
                            destination.write(chunk)
                if copied_bytes != expected_bytes:
                    raise HTTPException(409, "素材文件在打包期间变化，请重试")
            record(conn, "project.packaged", project_id, {"items": len(sources), "media_bytes": copied_bytes})
        spool.seek(0)
        return spool
    except HTTPException:
        spool.close()
        raise
    except OSError as exc:
        spool.close()
        raise HTTPException(409, "无法读取交付素材或写入临时文件，请检查磁盘空间和文件状态") from exc
    except Exception:
        spool.close()
        raise
