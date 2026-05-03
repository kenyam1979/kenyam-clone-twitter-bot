"""LangChain pipeline for analyzing account writing style."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in ("", None):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from twitter_bot.config import BotConfig
from twitter_bot.samples import load_sample_tweets


STYLE_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You are a writing-style analyst. Infer reusable style traits from "
            "the supplied posts. Do not copy phrases, claims, private details, "
            "or named entities unless they are part of the requested topic.",
        ),
        (
            "human",
            "Analyze these posts and return a compact style guide with tone, "
            "sentence length, punctuation habits, emoji/hashtag use, and topics "
            "to avoid copying verbatim.\n\nPosts:\n{sample_tweets}",
        ),
    ]
)


class StyleGenerator:
    """Builds and runs the LangChain style-analysis chain."""

    def __init__(self, config: BotConfig, temperature: float = 0.2) -> None:
        llm = ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.openai_model,
            temperature=temperature,
        )
        self._style_chain = STYLE_PROMPT | llm | StrOutputParser()

    def generate(self, sample_tweets: list[str]) -> str:
        if not sample_tweets:
            raise ValueError("At least one sample tweet is required.")

        samples = "\n".join(f"- {tweet.strip()}" for tweet in sample_tweets if tweet.strip())
        if not samples:
            raise ValueError("At least one non-empty sample tweet is required.")

        return self._style_chain.invoke({"sample_tweets": samples}).strip()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a reusable style guide from sample tweets."
    )
    parser.add_argument(
        "--samples",
        required=True,
        help="Path to a newline-delimited file of your past tweets.",
    )
    parser.add_argument(
        "--out",
        help="Path to write the generated style guide. Prints to stdout when omitted.",
    )
    return parser


def main() -> None:
    load_dotenv()

    args = build_parser().parse_args()
    config = BotConfig.from_env()
    sample_tweets = load_sample_tweets(args.samples)
    style_guide = StyleGenerator(config).generate(sample_tweets)

    if args.out:
        Path(args.out).write_text(f"{style_guide}\n", encoding="utf-8")
        print(f"Wrote style guide to {args.out}")
    else:
        print(style_guide)


if __name__ == "__main__":
    main()
