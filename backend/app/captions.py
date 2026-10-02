"""Small SRT/VTT reader that preserves time evidence for search and review."""

import html
import re

TIMING = re.compile(
    r"(?P<start>(?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3})\s*-->\s*"
    r"(?P<end>(?:\d{1,2}:)?\d{2}:\d{2}[.,]\d{3})"
)


def seconds(value: str) -> float:
    parts = value.replace(",", ".").split(":")
    if any(float(part) >= 60 for part in parts[-2:]):
        raise ValueError("无效字幕时间")
    return sum(float(part) * (60 ** index) for index, part in enumerate(reversed(parts)))


def parse_captions(text: str) -> list[dict]:
    cues, lines = [], []
    start, end, skipping = None, None, False

    def flush():
        if lines:
            cues.append({"start": start, "end": end, "text": "\n".join(lines)})
            lines.clear()

    source_lines = text.replace("\r", "").lstrip("\ufeff").splitlines()
    for index, raw in enumerate(source_lines):
        line = raw.strip()
        if not line:
            flush()
            start, end, skipping = None, None, False
            continue
        if line.startswith(("NOTE", "STYLE", "REGION")):
            flush()
            skipping = True
        if skipping:
            continue
        if line.startswith(("WEBVTT", "Kind:", "Language:", "X-TIMESTAMP-MAP")) or line.isdigit():
            continue
        match = TIMING.search(line)
        if match:
            flush()
            try:
                start, end = seconds(match["start"]), seconds(match["end"])
                if start >= end or end > 86400:
                    start, end = None, None
            except ValueError:
                start, end = None, None
            continue
        if "-->" in line:
            flush()
            start, end = None, None
            continue
        # VTT identifiers can be arbitrary strings immediately before a time row.
        if index + 1 < len(source_lines) and TIMING.search(source_lines[index + 1]) and not lines:
            continue
        cleaned = html.unescape(re.sub(r"<[^>]+>", "", line)).strip()
        if cleaned and (not lines or cleaned != lines[-1]):
            lines.append(cleaned)
        # Bound plain-text snippets as well as subtitle blocks for useful search output.
        if sum(map(len, lines)) >= 1000:
            flush()
    flush()
    return cues


def caption_text(cues: list[dict]) -> str:
    lines, previous = [], ""
    for cue in cues:
        for line in cue["text"].splitlines():
            if line != previous:
                lines.append(line)
                previous = line
    return "\n".join(lines)


def for_clip(cues: list[dict], start: float | None, end: float | None) -> list[dict]:
    if start is None or end is None:
        return cues
    result = []
    for cue in cues:
        if cue["start"] is None:
            continue  # Untimed text cannot be attributed to a specific clip.
        if cue["end"] > start and cue["start"] < end:
            result.append({**cue, "start": max(0, cue["start"] - start), "end": min(end, cue["end"]) - start})
    return result
