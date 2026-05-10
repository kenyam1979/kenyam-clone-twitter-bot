"""Fetch and screen trend context from Google News through SerpAPI."""

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
MARKET_NOISE_PATTERN = re.compile(
    r"株価|日経平均|為替|決算|上方修正|下方修正|配当|"
    r"ストップ高|ストップ安|急騰|急落|買い|売り|目標株価|"
    r"前場|後場|大引け|東証|NASDAQ|ナスダック|NYSE|ダウ"
)


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
            "Google News via SerpAPIで見つけた日本の直近トレンド候補。",
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
    """Fetches likely viral Japan topics from Google News through SerpAPI."""

    def __init__(self, config: BotConfig) -> None:
        if not config.serpapi_api_key:
            raise RuntimeError("SERPAPI_API_KEY is required for --japan-trend.")
        self._api_key = config.serpapi_api_key
        self._screener = TrendScreener(config)

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
        candidates = self._extract_results(payload, limit=10)
        results = self._screener.screen(candidates, limit=limit)
        if not results:
            raise RuntimeError(
                "SerpAPI returned no usable screened Google News results."
            )
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


class TrendScreener:
    """Screens Google News results for tweet-worthy trend context."""

    def __init__(self, config: BotConfig, temperature: float = 0.0) -> None:
        from langchain_core.output_parsers import StrOutputParser
        from langchain_core.prompts import ChatPromptTemplate
        from langchain_openai import ChatOpenAI

        llm = ChatOpenAI(
            api_key=config.openai_api_key,
            model=config.openai_model,
            temperature=temperature,
        )
        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "You screen Japanese Google News results before a Twitter bot "
                    "writes a short opinionated post. Keep items that are likely "
                    "to be socially discussable, culturally viral, technology "
                    "relevant, AI/software relevant, policy relevant, or useful "
                    "for structural commentary. Reject stock-price movement, "
                    "market summaries, earnings-only updates, analyst notes, "
                    "routine corporate PR, commodity price updates, sports score "
                    "recaps, celebrity gossip without broader social relevance, "
                    "and duplicate/syndicated variants. Return only JSON.",
                ),
                (
                    "human",
                    "Choose up to {limit} items to keep. Return JSON in this exact "
                    "shape: {{\"keep_indices\": [1, 2]}}\n\nResults:\n{results}",
                ),
            ]
        )
        self._chain = prompt | llm | StrOutputParser()

    def screen(self, results: list[SearchResult], limit: int) -> list[SearchResult]:
        if not results:
            return []

        prefiltered = [
            result for result in results if not self._is_obvious_noise(result)
        ]
        if not prefiltered:
            return []

        payload = "\n".join(
            self._format_result(index, result)
            for index, result in enumerate(prefiltered, start=1)
        )
        try:
            raw = self._chain.invoke({"limit": limit, "results": payload})
            keep_indices = self._parse_keep_indices(raw)
        except Exception:
            return prefiltered[:limit]

        screened: list[SearchResult] = []
        for index in keep_indices:
            if 1 <= index <= len(prefiltered):
                screened.append(prefiltered[index - 1])
            if len(screened) >= limit:
                break
        return screened

    def _is_obvious_noise(self, result: SearchResult) -> bool:
        text = f"{result.title} {result.snippet}"
        return bool(MARKET_NOISE_PATTERN.search(text))

    def _format_result(self, index: int, result: SearchResult) -> str:
        source = f" source={result.source}" if result.source else ""
        snippet = f" snippet={result.snippet}" if result.snippet else ""
        return f"{index}. title={result.title}{source}{snippet}"

    def _parse_keep_indices(self, raw: str) -> list[int]:
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.removeprefix("```json").removeprefix("```")
            cleaned = cleaned.removesuffix("```").strip()
        payload = json.loads(cleaned)
        keep_indices = payload.get("keep_indices", [])
        if not isinstance(keep_indices, list):
            return []
        return [index for index in keep_indices if isinstance(index, int)]
