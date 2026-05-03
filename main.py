from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from twitter_bot.config import BotConfig


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Draft or publish a tweet in the style of your own account."
    )
    parser.add_argument(
        "--style-guide",
        required=True,
        help="Path to a saved style guide. Skips style generation when provided.",
    )
    parser.add_argument(
        "--topic",
        required=True,
        help="Topic or intent for the new tweet.",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=280,
        help="Maximum tweet length. Defaults to 280.",
    )
    parser.add_argument(
        "--post",
        action="store_true",
        help="Publish to Twitter/X. Without this flag the program only prints a draft.",
    )
    return parser


def main() -> None:
    load_dotenv()

    args = build_parser().parse_args()
    config = BotConfig.from_env()
    style_guide = Path(args.style_guide).read_text(encoding="utf-8").strip()
    if not style_guide:
        raise ValueError(f"Style guide file is empty: {args.style_guide}")

    from twitter_bot.generator import TweetGenerator

    generator = TweetGenerator(config)
    draft = generator.draft(
        style_guide=style_guide,
        topic=args.topic,
        max_chars=args.max_chars,
    )

    if args.post:
        from twitter_bot.publisher import XPublisher

        tweet_id = XPublisher(config).post(draft.text)
        print(f"Published tweet id: {tweet_id}")
    else:
        print(draft.text)


if __name__ == "__main__":
    main()
