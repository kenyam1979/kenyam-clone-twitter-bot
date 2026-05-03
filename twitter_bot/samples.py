"""Utilities for loading account sample tweets."""

from __future__ import annotations

from pathlib import Path


def load_sample_tweets(path: str) -> list[str]:
    sample_path = Path(path)
    if not sample_path.exists():
        raise FileNotFoundError(f"Sample tweet file not found: {path}")

    tweets = [
        line.strip()
        for line in sample_path.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if not tweets:
        raise ValueError(f"No sample tweets found in {path}")
    return tweets
