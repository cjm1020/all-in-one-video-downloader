import json
import subprocess
import sys
import time

from . import db
from .captions import caption_text, for_clip, parse_captions
from .config import config
from .extractor import SafeYoutubeDL, base_options, metadata
from .knowledge_db import replace_transcript
from .security import install_network_guard, validate_public_url

PRESETS = {
    "everyday": "bv*[height<=720]+ba/b[height<=720]/b",
    "archive": "bv*[height<=1080]+ba/b[height<=1080]/b",
    "commute": "bv*[height<=480]+ba/b[height<=480]/b",
    "audio": "ba/b",
}
MEDIA_EXTENSIONS = {".mp4", ".webm", ".mkv", ".mov", ".mp3", ".m4a", ".ogg", ".opus", ".wav", ".flac"}


def run_download(task_id: str):
    task = db.get_task(task_id, raw=True)
    if not task or task["status"] != "downloading":
        return
    directory = config.media_dir / task_id
    directory.mkdir(parents=True, exist_ok=True)
    last_update = 0.0

    def progress(event):
        nonlocal last_update
        if event["status"] == "downloading" and time.monotonic() - last_update > 0.4:
            total = event.get("total_bytes") or event.get("total_bytes_estimate") or 0
            percent = min(95, event.get("downloaded_bytes", 0) / total * 95) if total else 0
            db.update_task(
                task_id,
                {"progress": percent, "speed": event.get("speed") or 0, "eta": event.get("eta") or 0},
                ("downloading",),
            )
            last_update = time.monotonic()

    def processing(event):
        if event["status"] == "started":
            db.update_task(task_id, {"status": "processing", "progress": 96, "speed": 0}, ("downloading", "processing"))

    options = {
        **base_options(),
        "format": PRESETS[task["preset"]],
        "outtmpl": str(directory / "source.%(ext)s"),
        "merge_output_format": "mp4",
        "continuedl": True,
        "overwrites": False,
        "progress_hooks": [progress],
        "postprocessor_hooks": [processing],
        "writesubtitles": True,
        "writeautomaticsub": True,
        "subtitleslangs": ["en", "zh-Hans", "zh-Hant", "zh", "en-orig"],
        "subtitlesformat": "vtt/best",
        "max_filesize": int(db.get_settings()["storage_limit_gb"] * 1024**3),
    }
    if task["rate_limit"]:
        options["ratelimit"] = task["rate_limit"] * 1024
    if task["preset"] == "audio":
        options["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]
    with SafeYoutubeDL(options) as engine:
        info = engine.extract_info(validate_public_url(task["url"]), download=False)
        if not info or info.get("_type") in {"playlist", "multi_video"}:
            raise ValueError("请使用单个视频链接；多个视频请按行批量添加")
        if info.get("is_live"):
            raise ValueError("首版暂不下载直播，请在直播结束后使用回放链接")
        if task["clip_end"] and info.get("duration") and task["clip_end"] > info["duration"]:
            raise ValueError("片段结束时间超出了视频时长")
        selected = info.get("requested_formats") or [info]
        for fmt in selected:
            if fmt.get("protocol") not in {"http", "https", "m3u8_native", "http_dash_segments"}:
                raise ValueError("当前流协议暂不支持安全下载")
        db.update_task(task_id, metadata(info), ("downloading",))
        engine.process_info(info)
    files = [p for p in directory.iterdir() if p.suffix.lower() in MEDIA_EXTENSIONS and p.stem != "clip"]
    if not files:
        raise ValueError("下载未生成可播放的文件；请检查来源和存储空间")
    output = max(files, key=lambda p: p.stat().st_size)
    probe = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(output),
        ],
        check=True,
        capture_output=True,
        timeout=30,
    )
    source_duration = float(json.loads(probe.stdout).get("format", {}).get("duration") or 0)
    if task["clip_end"] and source_duration and task["clip_end"] > source_duration + 0.05:
        raise ValueError("片段结束时间超出了实际视频时长")
    if task["clip_end"] is not None:
        db.update_task(task_id, {"status": "processing", "progress": 97, "speed": 0}, ("downloading", "processing"))
        audio = task["preset"] == "audio"
        clipped = directory / ("clip.mp3" if audio else "clip.mp4")
        command = [
            "ffmpeg",
            "-nostdin",
            "-y",
            "-v",
            "error",
            "-protocol_whitelist",
            "file,pipe",
            "-ss",
            str(task["clip_start"]),
            "-i",
            str(output),
            "-t",
            str(task["clip_end"] - task["clip_start"]),
        ]
        command += (
            ["-vn", "-c:a", "libmp3lame"]
            if audio
            else ["-c:v", "libx264", "-preset", "fast", "-c:a", "aac", "-movflags", "+faststart"]
        )
        command += [str(clipped)]
        subprocess.run(command, check=True, capture_output=True, timeout=600)
        output.unlink()
        output = clipped
    thumbnail = info.get("thumbnail") or ""
    if task["preset"] != "audio":
        poster = directory / "poster.jpg"
        generated = subprocess.run(
            [
                "ffmpeg",
                "-nostdin",
                "-y",
                "-v",
                "error",
                "-protocol_whitelist",
                "file,pipe",
                "-i",
                str(output),
                "-frames:v",
                "1",
                "-vf",
                "scale=640:-2",
                str(poster),
            ],
            capture_output=True,
            timeout=30,
            check=False,
        )
        if generated.returncode == 0 and poster.is_file():
            thumbnail = f"/api/tasks/{task_id}/poster"
    captions = list(directory.glob("*.vtt")) + list(directory.glob("*.srt"))
    cues = []
    if captions:
        cues = for_clip(
            parse_captions(captions[0].read_text(encoding="utf-8", errors="replace")[:250000]),
            task["clip_start"], task["clip_end"],
        )
    replace_transcript(
        task_id,
        caption_text(cues), cues,
        only_status=("downloading", "processing"),
        media_values={
            "status": "completed",
            "progress": 100,
            "speed": 0,
            "eta": 0,
            "file_path": str(output.relative_to(config.media_dir)),
            "file_size": output.stat().st_size,
            "duration": (
                task["clip_end"] - task["clip_start"] if task["clip_end"] is not None
                else source_duration or info.get("duration") or 0
            ),
            "thumbnail": thumbnail,
            "error": "",
        },
    )


if __name__ == "__main__":
    try:
        install_network_guard()
        run_download(sys.argv[1])
    except Exception as exc:
        db.update_task(
            sys.argv[1],
            {"status": "failed", "error": str(exc)[-1200:], "speed": 0, "eta": 0},
            ("downloading", "processing"),
        )
        print(str(exc), file=sys.stderr)
        sys.exit(1)
