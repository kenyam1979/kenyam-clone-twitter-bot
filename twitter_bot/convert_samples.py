"""Convert X API tweet JSON into newline-delimited sample tweets."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

if __package__ in ("", None):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


URL_PATTERN = re.compile(r"https?://\S+")
WHITESPACE_PATTERN = re.compile(r"\s+")


def normalize_tweet_text(text: str, keep_urls: bool = False) -> str:
    normalized = html.unescape(text)
    if not keep_urls:
        normalized = URL_PATTERN.sub("", normalized)
    return WHITESPACE_PATTERN.sub(" ", normalized).strip()


def load_raw_tweets(path: str) -> list[dict[str, Any]]:
    raw_path = Path(path)
    payload = json.loads(raw_path.read_text(encoding="utf-8"))

    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload

    raise ValueError(
        "Expected an X API response with a data list, or a raw list of tweet objects."
    )


def convert_tweets(
    input_path: str,
    output_path: str,
    keep_urls: bool = False,
    oldest_first: bool = False,
    limit: int | None = None,
) -> int:
    if limit is not None and limit < 1:
        raise ValueError("Limit must be at least 1.")

    tweets = load_raw_tweets(input_path)
    if oldest_first:
        tweets = list(reversed(tweets))

    samples: list[str] = []
    seen: set[str] = set()
    for tweet in tweets:
        text = tweet.get("text")
        if not isinstance(text, str):
            continue

        sample = normalize_tweet_text(text, keep_urls=keep_urls)
        if not sample or sample in seen:
            continue

        samples.append(sample)
        seen.add(sample)
        if limit is not None and len(samples) >= limit:
            break

    if not samples:
        raise ValueError(f"No tweet text found in {input_path}")

    Path(output_path).write_text("\n".join(samples) + "\n", encoding="utf-8")
    return len(samples)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert X API tweet JSON into sample tweets for style generation."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to raw X API JSON, such as tweet_raw.txt.",
    )
    parser.add_argument(
        "--out",
        required=True,
        help="Path to write newline-delimited sample tweets.",
    )
    parser.add_argument(
        "--keep-urls",
        action="store_true",
        help="Keep URLs in sample tweets. By default URLs are removed.",
    )
    parser.add_argument(
        "--oldest-first",
        action="store_true",
        help="Reverse the input order before writing samples.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="Maximum number of sample tweets to write.",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    count = convert_tweets(
        input_path=args.input,
        output_path=args.out,
        keep_urls=args.keep_urls,
        oldest_first=args.oldest_first,
        limit=args.limit,
    )
    print(f"Wrote {count} sample tweets to {args.out}")


if __name__ == "__main__":
    main()
