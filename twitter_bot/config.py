"""Runtime configuration for the tweet bot."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class BotConfig:
    """Environment-backed application settings."""

    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    x_consumer_key: str | None = None
    x_consumer_secret: str | None = None
    x_bearer_token: str | None = None
    x_access_token: str | None = None
    x_access_token_secret: str | None = None
    serpapi_api_key: str | None = None

    @classmethod
    def from_env(cls) -> "BotConfig":
        openai_api_key = os.getenv("OPENAI_API_KEY")
        if not openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required.")

        return cls(
            openai_api_key=openai_api_key,
            openai_model=os.getenv("OPENAI_MODEL", cls.openai_model),
            x_consumer_key=os.getenv("X_CONSUMER_KEY") or os.getenv("TWITTER_API_KEY"),
            x_consumer_secret=os.getenv("X_CONSUMER_SECRET")
            or os.getenv("TWITTER_API_SECRET"),
            x_bearer_token=os.getenv("X_BEARER_TOKEN") or os.getenv("TWITTER_BEARER_TOKEN"),
            x_access_token=os.getenv("X_ACCESS_TOKEN") or os.getenv("TWITTER_ACCESS_TOKEN"),
            x_access_token_secret=os.getenv("X_ACCESS_TOKEN_SECRET")
            or os.getenv("TWITTER_ACCESS_TOKEN_SECRET"),
            serpapi_api_key=os.getenv("SERPAPI_API_KEY"),
        )

    @property
    def can_post_to_x(self) -> bool:
        return all(
            [
                self.x_consumer_key,
                self.x_consumer_secret,
                self.x_access_token,
                self.x_access_token_secret,
            ]
        )
