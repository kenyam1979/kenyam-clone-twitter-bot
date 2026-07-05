"""Local JSONL memory for generated and posted tweets."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


DEFAULT_MEMORY_PATH = "data/post_history.jsonl"


@dataclass(frozen=True)
class TweetMemoryEntry:
    """One generated tweet memory record."""

    created_at: str
    text: str
    status: str
    topic: str
    tweet_id: str | None = None
    error: str | None = None


def build_memory_entry(
    *,
    text: str,
    status: str,
    topic: str,
    tweet_id: str | None = None,
    error: str | None = None,
) -> TweetMemoryEntry:
    return TweetMemoryEntry(
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
        text=text,
        status=status,
        topic=topic,
        tweet_id=tweet_id,
        error=error,
    )


def append_memory_entry(path: str, entry: TweetMemoryEntry) -> None:
    memory_path = Path(path)
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    with memory_path.open("a", encoding="utf-8") as file:
        file.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")


def load_recent_memory(path: str, limit: int) -> list[TweetMemoryEntry]:
    if limit < 1:
        return []

    memory_path = Path(path)
    if not memory_path.exists():
        return []

    entries: list[TweetMemoryEntry] = []
    for line in memory_path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
            entries.append(_entry_from_payload(payload))
        except (TypeError, ValueError, json.JSONDecodeError):
            continue
    return entries[-limit:]


def format_recent_memory(entries: list[TweetMemoryEntry]) -> str:
    if not entries:
        return "No recent generated tweets are recorded."

    lines = []
    for index, entry in enumerate(entries, start=1):
        status = f" [{entry.status}]" if entry.status else ""
        lines.append(f"{index}. {entry.created_at}{status}: {entry.text}")
    return "\n".join(lines)


def _entry_from_payload(payload: dict[str, Any]) -> TweetMemoryEntry:
    tweet_id = payload.get("tweet_id")
    error = payload.get("error")
    return TweetMemoryEntry(
        created_at=str(payload.get("created_at", "")),
        text=str(payload.get("text", "")),
        status=str(payload.get("status", "")),
        topic=str(payload.get("topic", "")),
        tweet_id=tweet_id if isinstance(tweet_id, str) else None,
        error=error if isinstance(error, str) else None,
    )
