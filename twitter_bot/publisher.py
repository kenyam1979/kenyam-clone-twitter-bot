"""X publishing boundary."""

from __future__ import annotations

from twitter_bot.config import BotConfig


class XPublisher:
    """Posts tweets through Tweepy when credentials are configured."""

    def __init__(self, config: BotConfig) -> None:
        if not config.can_post_to_x:
            raise RuntimeError(
                "X posting credentials are incomplete. To publish, set "
                "X_CONSUMER_KEY, X_CONSUMER_SECRET, X_ACCESS_TOKEN, and "
                "X_ACCESS_TOKEN_SECRET. X_BEARER_TOKEN is app-only and is not "
                "enough to create posts."
            )

        import tweepy

        self._client = tweepy.Client(
            bearer_token=config.x_bearer_token,
            consumer_key=config.x_consumer_key,
            consumer_secret=config.x_consumer_secret,
            access_token=config.x_access_token,
            access_token_secret=config.x_access_token_secret,
        )

    def post(self, text: str) -> str:
        try:
            response = self._client.create_tweet(text=text)
        except Exception as exc:
            if exc.__class__.__name__ == "Forbidden":
                raise RuntimeError(
                    "X rejected the post with 403 Forbidden. In the X Developer "
                    "Console, set your app's OAuth 1.0a permissions to Read and "
                    "write, then regenerate X_ACCESS_TOKEN and "
                    "X_ACCESS_TOKEN_SECRET. Tokens created before the permission "
                    "change keep the old scope."
                ) from exc
            raise

        tweet_id = response.data["id"]
        return str(tweet_id)
