"""Deterministic cloze extraction and a deliberately simple review scheduler."""

import re
from datetime import datetime, timedelta, timezone


def cloze_cards(text: str) -> list[dict]:
    sentences = re.split(r"(?<=[。！？.!?])\s*|\n+", text)
    cards, seen = [], set()
    for raw in sentences:
        sentence = raw.strip()
        if len(sentence) < 12 or len(sentence) > 500:
            continue
        # Select a contiguous source token, never invent a conceptual answer.
        matches = re.findall(r"[a-zA-Z][a-zA-Z-]{3,}|[\u4e00-\u9fff]{2,8}", sentence)
        if not matches:
            continue
        token = max(matches, key=len)
        question = "补全字幕原句：" + sentence.replace(token, "［……］", 1)
        if question in seen:
            continue
        seen.add(question)
        cards.append({"question": question, "answer": token + "\n\n原句：" + sentence})
        if len(cards) == 8:
            break
    return cards


def next_review(card: dict, rating: str, instant: datetime | None = None) -> dict:
    timestamp = instant or datetime.now(timezone.utc)
    interval = card["interval_days"]
    repetitions = card["repetitions"]
    if rating == "again":
        return {"interval_days": 0, "repetitions": 0, "due_at": (timestamp + timedelta(minutes=10)).isoformat()}
    if rating not in {"good", "easy"}:
        raise ValueError("未知复习评级")
    interval = min(365, max(1 if rating == "good" else 4, interval * (2 if rating == "good" else 3)))
    return {
        "interval_days": interval, "repetitions": repetitions + 1,
        "due_at": (timestamp + timedelta(days=interval)).isoformat(),
    }
