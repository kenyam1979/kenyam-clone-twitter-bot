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
            "あなたは日本語の投稿文体を分析する編集者です。渡された投稿から、"
            "再利用できる文体の特徴だけを抽出してください。表現、主張、私的な"
            "情報、固有名詞をそのままコピーしてはいけません。出力は必ず日本語"
            "にしてください。",
        ),
        (
            "human",
            "以下の投稿を分析し、今後のツイート作成に使える簡潔な日本語の"
            "スタイルガイドを作成してください。\n\n"
            "含める内容:\n"
            "- 口調と距離感\n"
            "- 文の長さと改行の癖\n"
            "- 句読点、記号、絵文字、ハッシュタグの使い方\n"
            "- よく扱う話題の方向性\n"
            "- そのまま真似してはいけない要素\n"
            "- 新しい投稿を書くときの注意点\n\n"
            "投稿:\n{sample_tweets}",
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
