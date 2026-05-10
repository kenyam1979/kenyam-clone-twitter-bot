from __future__ import annotations

import argparse
from pathlib import Path

from dotenv import load_dotenv

from twitter_bot.config import BotConfig
from twitter_bot.trends import DEFAULT_JAPAN_TREND_QUERY


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
        help="Topic or intent for the new tweet.",
    )
    parser.add_argument(
        "--japan-trend",
        action="store_true",
        help="Fetch and screen likely viral Japan trends from Google News via SerpAPI.",
    )
    parser.add_argument(
        "--trend-query",
        default=DEFAULT_JAPAN_TREND_QUERY,
        help="Google query to use with --japan-trend.",
    )
    parser.add_argument(
        "--trend-results",
        type=int,
        default=5,
        help="Number of screened SerpAPI news results to summarize. Defaults to 5.",
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
    if not args.topic and not args.japan_trend:
        raise ValueError("Either --topic or --japan-trend is required.")

    style_guide = Path(args.style_guide).read_text(encoding="utf-8").strip()
    if not style_guide:
        raise ValueError(f"Style guide file is empty: {args.style_guide}")

    topic = args.topic
    if args.japan_trend:
        from twitter_bot.trends import JapanTrendFetcher

        trend = JapanTrendFetcher(config).fetch(
            query=args.trend_query,
            limit=args.trend_results,
        )
        topic = trend.as_topic(extra_intent=args.topic)
        print("Fetched screened Japan trend context from Google News via SerpAPI:")
        for result in trend.results:
            print(f"- {result.title}")

    from twitter_bot.generator import TweetGenerator

    generator = TweetGenerator(config)
    draft = generator.draft(
        style_guide=style_guide,
        topic=topic,
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
