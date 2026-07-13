"""E-commerce product and search URL helpers."""

from __future__ import annotations

from urllib.parse import quote_plus, urlparse

PLATFORM_DOMAINS: dict[str, tuple[str, ...]] = {
    "Amazon": ("amazon.in", "amazon.com", "amzn.to", "amazon."),
    "Flipkart": ("flipkart.com",),
    "Croma": ("croma.com",),
    "Reliance Digital": ("reliancedigital.in",),
    "Vijay Sales": ("vijaysales.com",),
    "Tata CLiQ": ("tatacliq.com",),
    "Myntra": ("myntra.com",),
    "Ajio": ("ajio.com",),
    "Nykaa": ("nykaa.com",),
    "Meesho": ("meesho.com",),
    "Snapdeal": ("snapdeal.com",),
    "Pepperfry": ("pepperfry.com",),
}

PLATFORM_SEARCH_TEMPLATES: dict[str, str] = {
    "Amazon": "https://www.amazon.in/s?k={q}",
    "Flipkart": "https://www.flipkart.com/search?q={q}",
    "Croma": "https://www.croma.com/search/?q={q}",
    "Reliance Digital": "https://www.reliancedigital.in/search?q={q}",
    "Vijay Sales": "https://www.vijaysales.com/search/{q}",
    "Tata CLiQ": "https://www.tatacliq.com/search/?searchCategory=all&text={q}",
    "Myntra": "https://www.myntra.com/{q}?rawQuery={q}",
    "Ajio": "https://www.ajio.com/search/?text={q}",
    "Nykaa": "https://www.nykaa.com/search/result/?q={q}",
    "Meesho": "https://www.meesho.com/search?q={q}",
    "Snapdeal": "https://www.snapdeal.com/search?keyword={q}",
    "Pepperfry": "https://www.pepperfry.com/site_product/search?q={q}",
}

PLATFORM_HOME: dict[str, str] = {
    "Amazon": "https://www.amazon.in/",
    "Flipkart": "https://www.flipkart.com/",
    "Croma": "https://www.croma.com/",
    "Reliance Digital": "https://www.reliancedigital.in/",
    "Vijay Sales": "https://www.vijaysales.com/",
    "Tata CLiQ": "https://www.tatacliq.com/",
    "Myntra": "https://www.myntra.com/",
    "Ajio": "https://www.ajio.com/",
    "Nykaa": "https://www.nykaa.com/",
    "Meesho": "https://www.meesho.com/",
    "Snapdeal": "https://www.snapdeal.com/",
    "Pepperfry": "https://www.pepperfry.com/",
}

RECOMMENDATION_DOMAINS: dict[str, tuple[str, ...]] = {
    "NDTV Shopping": ("shopping.ndtv.com", "ndtv.com"),
    "Hindustan Times": ("hindustantimes.com",),
    "Gadgets 360": ("gadgets360.com", "gadgets.ndtv.com"),
    "91mobiles": ("91mobiles.com",),
    "Smartprix": ("smartprix.com",),
    "Digit": ("digit.in",),
    "India Today Tech": ("indiatoday.in",),
}

RECOMMENDATION_SEARCH_TEMPLATES: dict[str, str] = {
    "NDTV Shopping": "https://www.google.com/search?q=site:shopping.ndtv.com+{q}",
    "Hindustan Times": "https://www.hindustantimes.com/search?q={q}",
    "Gadgets 360": "https://www.gadgets360.com/search?q={q}",
    "91mobiles": "https://www.91mobiles.com/search.php?q={q}",
    "Smartprix": "https://www.smartprix.com/products/?q={q}",
    "Digit": "https://www.digit.in/?s={q}",
    "India Today Tech": "https://www.indiatoday.in/topic/{q}",
}

_PRODUCT_PATH_HINTS = (
    "/dp/",
    "/gp/product/",
    "/p/",
    "/product/",
    "/pd/",
    "/item/",
    "/buy-",
)


def platform_search_url(platform: str, query: str) -> str:
    """Always-working store search page for the query."""
    template = PLATFORM_SEARCH_TEMPLATES.get(platform)
    q = quote_plus((query or "").strip() or "product")
    if not template:
        return f"https://www.google.com/search?q={quote_plus(f'{query} {platform} buy')}"
    return template.format(q=q)


def recommendation_search_url(site: str, query: str) -> str:
    template = RECOMMENDATION_SEARCH_TEMPLATES.get(site)
    q = quote_plus((query or "").strip() or "product")
    if not template:
        return f"https://www.google.com/search?q={quote_plus(f'{query} {site} review')}"
    return template.format(q=q)


def _looks_like_product_page(url: str) -> bool:
    lower = url.lower()
    return any(hint in lower for hint in _PRODUCT_PATH_HINTS)


def _domain_matches(url: str, domains: tuple[str, ...]) -> bool:
    try:
        host = urlparse(url).netloc.lower()
    except Exception:
        return False
    return any(domain in host for domain in domains)


def url_in_results(url: str, web_results: list[dict]) -> bool:
    target = (url or "").strip().rstrip("/")
    if not target:
        return False
    for item in web_results:
        found = (item.get("url") or "").strip().rstrip("/")
        if found and (found == target or target in found or found in target):
            return True
    return False


def resolve_store_url(
    platform: str,
    web_results: list[dict],
    query: str,
    candidate: str | None = None,
) -> str:
    """
    Resolve a clickable store URL that actually works.

    Never trust LLM-invented product pages. Prefer live search hits,
    otherwise fall back to the platform search page for the query.
    """
    domains = PLATFORM_DOMAINS.get(platform, ())
    search_fallback = platform_search_url(platform, query)

    # Only keep a candidate if it came from live web results for this platform.
    if candidate and str(candidate).startswith("http") and domains:
        if url_in_results(str(candidate), web_results) and _domain_matches(
            str(candidate), domains
        ):
            return str(candidate)

    product_hits: list[str] = []
    other_hits: list[str] = []
    for item in web_results:
        url = (item.get("url") or "").strip()
        if not url.startswith("http") or not domains:
            continue
        if not _domain_matches(url, domains):
            continue
        if _looks_like_product_page(url):
            product_hits.append(url)
        else:
            other_hits.append(url)

    if product_hits:
        return product_hits[0]
    if other_hits:
        return other_hits[0]
    return search_fallback


def match_platform_url(platform: str, web_results: list[dict], query: str) -> str:
    return resolve_store_url(platform, web_results, query)


def match_recommendation_url(site: str, web_results: list[dict], query: str) -> str:
    domains = RECOMMENDATION_DOMAINS.get(site, ())
    for item in web_results:
        url = (item.get("url") or "").strip()
        if url.startswith("http") and domains and _domain_matches(url, domains):
            return url
    return recommendation_search_url(site, query)


def format_money(amount: object, currency: str = "INR") -> str:
    try:
        value = float(amount)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return f"{currency} {amount}"
    if currency.upper() == "INR":
        return f"₹{value:,.0f}" if value == int(value) else f"₹{value:,.2f}"
    return f"{currency} {value:,.2f}"
