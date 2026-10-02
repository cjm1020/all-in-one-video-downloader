import sys

from yt_dlp import YoutubeDL

from .config import config
from .security import normalize_url, validate_public_url


class QuietLogger:
    def debug(self, message):
        pass

    def warning(self, message):
        print(message, file=sys.stderr)

    def error(self, message):
        print(message, file=sys.stderr)


class SafeYoutubeDL(YoutubeDL):
    def urlopen(self, req):
        url = req if isinstance(req, str) else (getattr(req, "url", None) or req.get_full_url())
        normalize_url(url)
        return super().urlopen(req)


def base_options() -> dict:
    options = {
        "quiet": True, "no_warnings": True, "logger": QuietLogger(),
        "noplaylist": True, "socket_timeout": 20, "retries": 2,
        "extractor_retries": 2, "cachedir": False, "proxy": "",
        "enable_file_urls": False, "hls_prefer_native": True,
        "external_downloader": {"default": "native"},
    }
    if config.cookie_file:
        options["cookiefile"] = config.cookie_file
    return options


def metadata(info: dict) -> dict:
    thumbnail = info.get("thumbnail") or ""
    if thumbnail:
        try:
            thumbnail = validate_public_url(thumbnail)
        except (ValueError, OSError):
            thumbnail = ""
    return {
        "title": info.get("title") or "未命名视频",
        "platform": info.get("extractor_key") or info.get("extractor") or "Direct",
        "duration": info.get("duration") or 0,
        "thumbnail": thumbnail,
    }


def inspect(url: str) -> dict:
    with SafeYoutubeDL(base_options()) as engine:
        info = engine.extract_info(validate_public_url(url), download=False)
        if not info or info.get("_type") in {"playlist", "multi_video"}:
            raise ValueError("请使用单个视频链接；批量下载可粘贴多行链接")
        formats = info.get("formats") or []
        return {**metadata(info), "uploader": info.get("uploader") or "",
                "heights": sorted({int(f["height"]) for f in formats if f.get("height")}),
                "has_subtitles": bool(info.get("subtitles") or info.get("automatic_captions")),
                "webpage_url": info.get("webpage_url") or url}

