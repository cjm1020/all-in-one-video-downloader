"""Export an editorial handoff assembled only from saved source material."""

from .learning import local_summary


def editorial_brief(task: dict, markers: list[dict]) -> dict:
    return {
        "title": task["title"] or "未命名素材",
        "source_url": task["url"],
        "mode": "local-extraction",
        "source_available": bool(task["transcript"]),
        "source_points": local_summary(task["transcript"]) if task["transcript"] else "尚未导入字幕",
        "tags": task["tags"],
        "editor_notes": task["notes"],
        "moments": [{key: marker[key] for key in ("position", "label", "notes")} for marker in markers],
        "review_checks": ["核对原片和引用上下文", "确认素材授权和署名", "人工确认事实及发布文案"],
    }


def markdown_brief(brief: dict) -> str:
    moments = "\n".join(
        f"- {moment['position']:.1f}s · {moment['label']}\n  {moment['notes']}" for moment in brief["moments"]
    )
    checks = "\n".join(f"- [ ] {check}" for check in brief["review_checks"])
    return (
        f"# 内容制作简报 · {brief['title']}\n\n"
        f"来源：{brief['source_url']}\n\n"
        "生成方式：本地原句提取。以下内容需要编辑核对后再用于发布。\n\n"
        f"## 素材要点\n\n{brief['source_points']}\n\n"
        f"## 编辑笔记\n\n{brief['editor_notes'] or '尚未记录'}\n\n"
        f"## 标签\n\n{', '.join(brief['tags']) or '尚未添加'}\n\n"
        f"## 时间标记\n\n{moments or '尚未添加'}\n\n"
        f"## 发布前复核\n\n{checks}\n"
    )
