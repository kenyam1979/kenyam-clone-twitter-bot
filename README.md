# Twitter Bot

A LangChain-powered bot that drafts tweets in the style of your own Twitter/X
account using sample posts that you provide. Drafts are written in Japanese.

## Architecture

- `main.py`: tweet drafting and publishing CLI entry point.
- `twitter_bot/config.py`: environment-backed settings.
- `twitter_bot/convert_samples.py`: converts X API JSON into sample tweet text.
- `twitter_bot/samples.py`: loads newline-delimited examples from your account.
- `twitter_bot/style.py`: LangChain style-analysis chain.
- `twitter_bot/trends.py`: fetches Japan trend context from Google News via SerpAPI.
- `twitter_bot/generator.py`: LangChain tweet-drafting chain.
- `twitter_bot/publisher.py`: optional X publishing boundary via Tweepy.

The default flow is safe by design: the bot prints a draft. It only posts when
you pass `--post` and configure Twitter/X credentials.

## Setup

```bash
cp .env.example .env
uv sync
```

Then edit `.env` and set `OPENAI_API_KEY`.

Optional SerpAPI key for Google News trend lookup:

```bash
SERPAPI_API_KEY=...
```

Optional model override:

```bash
OPENAI_MODEL=gpt-4o-mini
```

Optional LangSmith tracing:

```bash
LANGSMITH_TRACING=true
LANGSMITH_API_KEY=...
LANGSMITH_PROJECT=twitter-bot
```

When enabled, LangChain will send chain runs, prompts, model calls, latency, and
errors to the configured LangSmith project.
Set `LANGSMITH_TRACING=false` if you want local runs without tracing.
The app loads these values from `.env` at startup.
If you prefer shell exports instead, those work too:

```bash
export OPENAI_API_KEY="..."
export LANGSMITH_TRACING=true
export LANGSMITH_API_KEY="..."
export LANGSMITH_PROJECT="twitter-bot"
```

Optional Twitter/X credentials for publishing:

```bash
X_CONSUMER_KEY=...
X_CONSUMER_SECRET=...
X_BEARER_TOKEN=...
X_ACCESS_TOKEN=...
X_ACCESS_TOKEN_SECRET=...
```

`X_BEARER_TOKEN` is app-only authentication. It is useful for read-only X API
calls, but X still requires user-context credentials to create posts. For
`--post`, set `X_ACCESS_TOKEN` and `X_ACCESS_TOKEN_SECRET` too.

## Usage

Start from either a newline-delimited sample file:

```text
First example tweet
Second example tweet
Third example tweet
```

Or convert an X API JSON response like `tweet_raw.txt`:

```bash
uv run python -m twitter_bot.convert_samples --input tweet_raw.txt --out sample_tweets.txt
```

You can also convert an X archive export like `data/tweets.js`:

```bash
uv run python -m twitter_bot.convert_samples --input data/tweets.js --out data/sample_tweets.txt
```

Generate a reusable style guide:

```bash
uv run python -m twitter_bot.style --samples sample_tweets.txt --out style_guide.txt
```

The topic can be written in English or Japanese. The generated tweet will be
written in Japanese.

Draft without posting from a saved style guide:

```bash
uv run python main.py --style-guide style_guide.txt --topic "launching a weekend side project"
```

Publish from a saved style guide:

```bash
uv run python main.py --style-guide style_guide.txt --topic "launching a weekend side project" --post
```

Draft from a likely viral Japan trend found through Google News via SerpAPI:

```bash
uv run python main.py --style-guide style_guide.txt --japan-trend
```

Publish a tweet from that trend context:

```bash
uv run python main.py --style-guide style_guide.txt --japan-trend --post
```

Use a custom Google query:

```bash
uv run python main.py --style-guide style_guide.txt --japan-trend --trend-query "日本 AI 今日 話題"
```

## Notes

Use posts from your own account or posts you have permission to emulate. The
prompt asks the model to learn broad style traits and avoid copying exact
phrases, private details, or claims from the examples.
