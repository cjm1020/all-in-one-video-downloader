from pathlib import Path

from fastapi import HTTPException

from ..config import config


def safe_path(task: dict) -> Path:
    """Require a completed, nonempty media file inside its own task directory."""
    if task["status"] != "completed":
        raise HTTPException(409, "素材下载尚未完成")
    media_root = config.media_dir.resolve()
    identifier = task["id"]
    if Path(identifier).name != identifier or identifier in {".", ".."}:
        raise HTTPException(409, "素材标识无效")
    root = (media_root / identifier).resolve()
    path_value = task["file_path"]
    if not path_value or Path(path_value).is_absolute():
        raise HTTPException(409, "素材文件尚未准备好")
    try:
        target = (media_root / path_value).resolve()
        if root.parent != media_root or not target.is_relative_to(root) or not target.is_file():
            raise HTTPException(409, "素材文件已丢失或路径无效，请重新下载")
        if target.stat().st_size <= 0:
            raise HTTPException(409, "素材文件为空，请重新下载")
    except (OSError, ValueError) as exc:
        raise HTTPException(409, "素材文件无法访问，请检查文件状态并重新下载") from exc
    return target


def availability(task: dict) -> tuple[bool, str]:
    try:
        safe_path(task)
    except HTTPException as exc:
        return False, exc.detail
    return True, ""
