"""Fetch trend context from Google Search through SerpAPI."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from twitter_bot.config import BotConfig


SERPAPI_ENDPOINT = "https://serpapi.com/search.json"
DEFAULT_JAPAN_TREND_QUERY = "日本 テック トレンド"
TITLE_SUFFIX_PATTERN = re.compile(r"\s*[|｜]\s*.+$")


@dataclass(frozen=True)
class SearchResult:
    title: str
    snippet: str
    link: str
    source: str | None = None


@dataclass(frozen=True)
class TrendBrief:
    query: str
    results: list[SearchResult]

    def as_topic(self, extra_intent: str | None = None) -> str:
        lines = [
            "Google Search via SerpAPIで見つけた日本の直近トレンド候補。",
            f"検索クエリ: {self.query}",
            "候補:",
        ]
        for index, result in enumerate(self.results, start=1):
            source = f" ({result.source})" if result.source else ""
            snippet = f" - {result.snippet}" if result.snippet else ""
            lines.append(f"{index}. {result.title}{source}{snippet}")
        if extra_intent:
            lines.extend(["追加の投稿意図:", extra_intent])
        return "\n".join(lines)


class JapanTrendFetcher:
    """Fetches likely viral Japan topics from Google Search through SerpAPI."""

    def __init__(self, config: BotConfig) -> None:
        if not config.serpapi_api_key:
            raise RuntimeError("SERPAPI_API_KEY is required for --japan-trend.")
        self._api_key = config.serpapi_api_key

    def fetch(
        self,
        query: str = DEFAULT_JAPAN_TREND_QUERY,
        limit: int = 5,
    ) -> TrendBrief:
        if limit < 1:
            raise ValueError("Trend result limit must be at least 1.")

        payload = self._request(
            {
                "engine": "google",
                "q": query,
                "api_key": self._api_key,
                "google_domain": "google.co.jp",
                "gl": "jp",
                "hl": "ja",
                "location": "Japan",
                "tbm": "nws",
                "tbs": "qdr:d",
                "num": 10,
                "safe": "active",
            }
        )
        results = self._extract_results(payload, limit=limit)
        if not results:
            raise RuntimeError("SerpAPI returned no usable Google News results.")
        return TrendBrief(query=query, results=results)

    def _request(self, params: dict[str, str | int]) -> dict[str, Any]:
        url = f"{SERPAPI_ENDPOINT}?{urlencode(params)}"
        try:
            with urlopen(url, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(
                f"SerpAPI request failed with HTTP {exc.code}: {detail}"
            ) from exc
        except URLError as exc:
            raise RuntimeError(f"SerpAPI request failed: {exc.reason}") from exc

    def _extract_results(self, payload: dict[str, Any], limit: int) -> list[SearchResult]:
        if "error" in payload:
            raise RuntimeError(f"SerpAPI error: {payload['error']}")

        results: list[SearchResult] = []
        seen_titles: set[str] = set()
        for item in payload.get("news_results", []):
            title = item.get("title")
            if not isinstance(title, str) or not title.strip():
                continue
            title = title.strip()
            title_key = self._title_key(title)
            if title_key in seen_titles:
                continue
            seen_titles.add(title_key)

            snippet = item.get("snippet") or item.get("description") or ""
            link = item.get("link") or ""
            source = item.get("source")
            results.append(
                SearchResult(
                    title=title,
                    snippet=snippet.strip() if isinstance(snippet, str) else "",
                    link=link.strip() if isinstance(link, str) else "",
                    source=source.strip() if isinstance(source, str) else None,
                )
            )
            if len(results) >= limit:
                break

        return results

    def _title_key(self, title: str) -> str:
        return TITLE_SUFFIX_PATTERN.sub("", title).casefold()
