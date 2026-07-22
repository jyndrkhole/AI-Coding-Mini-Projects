"""Web search helpers for live product signals and editorial recommendations."""

from __future__ import annotations

from typing import Any

from src.config import ECOMMERCE_PLATFORMS, RECOMMENDATION_SITES
from src.urls import PLATFORM_DOMAINS, RECOMMENDATION_DOMAINS


def search_web(query: str, max_results: int = 8) -> list[dict[str, Any]]:
    """Search the web for product listings and price signals."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        try:
            from ddgs import DDGS  # type: ignore
        except ImportError:
            return []

    results: list[dict[str, Any]] = []
    try:
        with DDGS() as ddgs:
            for item in ddgs.text(query, max_results=max_results):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("href") or item.get("link") or "",
                        "snippet": item.get("body", ""),
                        "source": "web",
                    }
                )
    except Exception:
        return results
    return results


def _append_unique(
    results: list[dict[str, Any]],
    seen: set[str],
    items: list[dict[str, Any]],
    *,
    source: str,
) -> None:
    for item in items:
        url = item.get("url", "")
        if not url or url in seen:
            continue
        seen.add(url)
        enriched = dict(item)
        enriched["source"] = source
        results.append(enriched)


def search_product_links(query: str) -> list[dict[str, Any]]:
    """Collect store listings plus editorial recommendation pages."""
    seen: set[str] = set()
    results: list[dict[str, Any]] = []

    _append_unique(
        results,
        seen,
        search_web(
            f"{query} buy price Amazon Flipkart Croma Reliance Digital",
            8,
        ),
        source="commerce",
    )

    # Priority stores including Croma and other electronics retailers
    priority_stores = [
        "Amazon",
        "Flipkart",
        "Croma",
        "Reliance Digital",
        "Vijay Sales",
        "Tata CLiQ",
        "Myntra",
    ]
    for platform in priority_stores:
        domains = PLATFORM_DOMAINS.get(platform, ())
        if not domains:
            continue
        _append_unique(
            results,
            seen,
            search_web(f"{query} site:{domains[0]}", 3),
            source="commerce",
        )

    for platform in ECOMMERCE_PLATFORMS:
        if platform in priority_stores:
            continue
        domains = PLATFORM_DOMAINS.get(platform, ())
        if not domains:
            continue
        _append_unique(
            results,
            seen,
            search_web(f"{query} site:{domains[0]}", 2),
            source="commerce",
        )

    # Editorial / recommendation sites
    editorial_queries = [
        f"{query} review recommendation site:shopping.ndtv.com OR site:gadgets360.com",
        f"{query} best buy review site:hindustantimes.com OR site:91mobiles.com OR site:smartprix.com",
        f"{query} review site:digit.in OR site:indiatoday.in",
    ]
    for q in editorial_queries:
        _append_unique(results, seen, search_web(q, 5), source="editorial")

    for site in RECOMMENDATION_SITES:
        domains = RECOMMENDATION_DOMAINS.get(site, ())
        if not domains:
            continue
        _append_unique(
            results,
            seen,
            search_web(f"{query} review OR recommendation site:{domains[0]}", 2),
            source="editorial",
        )

    return results[:28]


def format_search_context(results: list[dict[str, Any]]) -> str:
    if not results:
        return "No live web results available. Use widely known market pricing."
    lines = []
    for i, r in enumerate(results, 1):
        lines.append(
            f"{i}. [{r.get('source', 'web')}] {r.get('title', '')}\n"
            f"   URL: {r.get('url', '')}\n"
            f"   Snippet: {r.get('snippet', '')}"
        )
    return "\n".join(lines)
