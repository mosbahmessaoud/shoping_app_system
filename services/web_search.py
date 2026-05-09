# services/web_search.py
"""
Free web search backends for the AI agentic loop.

Fallback chain (auto mode):
  1. DuckDuckGo  — no key, completely free  (pip install duckduckgo-search)
  2. Tavily      — 1 000 free searches/month  (TAVILY_API_KEY in .env)
  3. Brave       — 2 000 free queries/month   (BRAVE_API_KEY in .env)
  4. Serper      — 2 500 one-time credits     (SERPER_API_KEY in .env)

Usage:
    from services.web_search import web_search
    result = web_search("dental supply prices Algeria 2025")

Returns:
    {
        "source":  "duckduckgo" | "tavily" | "brave" | "serper",
        "query":   "...",
        "results": [{"title": "...", "url": "...", "snippet": "..."}, ...]
    }
    On failure: {"error": "All search backends failed", "query": "..."}
"""

from __future__ import annotations

import logging
import os
from typing import Callable

import requests

logger = logging.getLogger(__name__)

MAX_RESULTS = 5
HTTP_TIMEOUT = 10    # seconds
DDG_TIMEOUT = 10     # seconds


# ── Backend 1: DuckDuckGo ──────────────────────────────────────────────────────

def _search_duckduckgo(query: str) -> dict:
    try:
        from duckduckgo_search import DDGS
        results = []
        with DDGS(timeout=DDG_TIMEOUT) as ddgs:
            for r in ddgs.text(query, max_results=MAX_RESULTS):
                results.append({
                    "title":   r.get("title", ""),
                    "url":     r.get("href", ""),
                    "snippet": r.get("body", ""),
                })
        if results:
            logger.info("DuckDuckGo: %d results for '%s'", len(results), query)
            return {"source": "duckduckgo", "query": query, "results": results}
        return {"error": "DuckDuckGo returned no results"}
    except ImportError:
        return {"error": "duckduckgo-search not installed"}
    except Exception as exc:
        logger.warning("DuckDuckGo failed: %s", exc)
        return {"error": str(exc)}


# ── Backend 2: Tavily ──────────────────────────────────────────────────────────

def _search_tavily(query: str) -> dict:
    api_key = os.getenv("TAVILY_API_KEY", "")
    if not api_key:
        return {"error": "TAVILY_API_KEY not configured"}
    try:
        resp = requests.post(
            "https://api.tavily.com/search",
            json={
                "api_key":        api_key,
                "query":          query,
                "max_results":    MAX_RESULTS,
                "search_depth":   "basic",
                "include_answer": False,
            },
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        results = [
            {"title": r.get("title", ""), "url": r.get(
                "url", ""), "snippet": r.get("content", "")}
            for r in resp.json().get("results", [])
        ]
        if results:
            return {"source": "tavily", "query": query, "results": results}
        return {"error": "Tavily returned no results"}
    except Exception as exc:
        logger.warning("Tavily failed: %s", exc)
        return {"error": str(exc)}


# ── Backend 3: Brave ───────────────────────────────────────────────────────────

def _search_brave(query: str) -> dict:
    api_key = os.getenv("BRAVE_API_KEY", "")
    if not api_key:
        return {"error": "BRAVE_API_KEY not configured"}
    try:
        resp = requests.get(
            "https://api.search.brave.com/res/v1/web/search",
            headers={
                "Accept": "application/json",
                "Accept-Encoding": "gzip",
                "X-Subscription-Token": api_key,
            },
            params={"q": query, "count": MAX_RESULTS},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        results = [
            {"title": r.get("title", ""), "url": r.get(
                "url", ""), "snippet": r.get("description", "")}
            for r in resp.json().get("web", {}).get("results", [])
        ]
        if results:
            return {"source": "brave", "query": query, "results": results}
        return {"error": "Brave returned no results"}
    except Exception as exc:
        logger.warning("Brave failed: %s", exc)
        return {"error": str(exc)}


# ── Backend 4: Serper ──────────────────────────────────────────────────────────

def _search_serper(query: str) -> dict:
    api_key = os.getenv("SERPER_API_KEY", "")
    if not api_key:
        return {"error": "SERPER_API_KEY not configured"}
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": api_key, "Content-Type": "application/json"},
            json={"q": query, "num": MAX_RESULTS},
            timeout=HTTP_TIMEOUT,
        )
        resp.raise_for_status()
        results = [
            {"title": r.get("title", ""), "url": r.get(
                "link", ""), "snippet": r.get("snippet", "")}
            for r in resp.json().get("organic", [])
        ]
        if results:
            return {"source": "serper", "query": query, "results": results}
        return {"error": "Serper returned no results"}
    except Exception as exc:
        logger.warning("Serper failed: %s", exc)
        return {"error": str(exc)}


# ── Public interface ───────────────────────────────────────────────────────────

_BACKENDS: dict[str, Callable[[str], dict]] = {
    "duckduckgo": _search_duckduckgo,
    "tavily":     _search_tavily,
    "brave":      _search_brave,
    "serper":     _search_serper,
}


def web_search(query: str, prefer: str = "auto") -> dict:
    """
    Search the web using the best available free backend.

    Args:
        query:  Search query string.
        prefer: Force a backend: "duckduckgo" | "tavily" | "brave" | "serper".
                Default "auto" tries each in order until one succeeds.

    Returns:
        {"source": "...", "query": "...", "results": [{title, url, snippet}, ...]}
        or {"error": "All search backends failed", "query": "..."}
    """
    if prefer != "auto" and prefer in _BACKENDS:
        result = _BACKENDS[prefer](query)
        if "error" not in result:
            return result
        logger.warning(
            "Preferred backend '%s' failed, falling through", prefer)

    for name, fn in _BACKENDS.items():
        result = fn(query)
        if "error" not in result:
            return result
        logger.debug("Backend '%s' failed: %s", name, result.get("error"))

    return {"error": "All search backends failed", "query": query}
