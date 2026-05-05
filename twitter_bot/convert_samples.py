"""Convert X API or archive tweet JSON into newline-delimited sample tweets."""

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
X_ARCHIVE_PREFIX = "window.YTD.tweets.part0"


def normalize_tweet_text(text: str, keep_urls: bool = False) -> str:
    normalized = html.unescape(text)
    if not keep_urls:
        normalized = URL_PATTERN.sub("", normalized)
    return WHITESPACE_PATTERN.sub(" ", normalized).strip()


def load_payload(path: str) -> Any:
    raw_text = Path(path).read_text(encoding="utf-8").strip()
    try:
        return json.loads(raw_text)
    except json.JSONDecodeError:
        if not raw_text.startswith(X_ARCHIVE_PREFIX):
            raise

        _, separator, json_text = raw_text.partition("=")
        if not separator:
            raise ValueError(f"Expected X archive assignment in {path}")
        return json.loads(json_text.strip().removesuffix(";"))


def load_raw_tweets(path: str) -> list[dict[str, Any]]:
    payload = load_payload(path)

    if isinstance(payload, dict) and isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload, list):
        return payload

    raise ValueError(
        "Expected an X API response with a data list, an X archive tweets.js file, "
        "or a raw list of tweet objects."
    )


def extract_tweet_text(tweet: dict[str, Any]) -> str | None:
    archive_tweet = tweet.get("tweet")
    if isinstance(archive_tweet, dict):
        if archive_tweet.get("retweeted") is True:
            return None
        return extract_tweet_text(archive_tweet)

    text = tweet.get("text") or tweet.get("full_text")
    if not isinstance(text, str):
        return None
    if tweet.get("retweeted") is True or text.startswith("RT @"):
        return None
    return text


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
        text = extract_tweet_text(tweet)
        if text is None:
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
        description="Convert X API JSON or archive tweets.js into sample tweets."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Path to raw X API JSON or an X archive tweets.js file.",
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
