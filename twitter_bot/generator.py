"""LangChain pipeline for drafting account-style tweets."""

from __future__ import annotations

from dataclasses import dataclass

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

from twitter_bot.config import BotConfig


TWEET_PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You draft posts for the account owner. Match the style guide, but "
            "write an original tweet in natural Japanese. Use Japanese even if "
            "the sample posts or topic are written in another language. Do not "
            "impersonate another person, do not invent personal experiences, "
            "and do not include unsafe or harassing content. Keep the tweet "
            "under {max_chars} characters.",
        ),
        (
            "human",
            "Style guide:\n{style_guide}\n\nTopic or intent:\n{topic}\n\n"
            "Return only the tweet text.",
        ),
    ]
)


@dataclass
class TweetDraft:
    text: str


class TweetGenerator:
    """Builds and runs the LangChain tweet-drafting chain."""

    def __init__(self, config: BotConfig, temperature: float = 0.8) -> None:
        llm = ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.openai_model,
            temperature=temperature,
        )
        self._tweet_chain = TWEET_PROMPT | llm | StrOutputParser()

    def draft(
        self,
        style_guide: str,
        topic: str,
        max_chars: int = 280,
    ) -> TweetDraft:
        if not style_guide.strip():
            raise ValueError("A style guide is required.")
        if not topic.strip():
            raise ValueError("A topic or intent is required.")
        if max_chars < 1:
            raise ValueError("Maximum tweet length must be at least 1.")

        text = self._tweet_chain.invoke(
            {
                "style_guide": style_guide.strip(),
                "topic": topic.strip(),
                "max_chars": max_chars,
            }
        ).strip()

        return TweetDraft(text=text[:max_chars])
