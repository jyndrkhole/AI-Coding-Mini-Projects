"""Product comparison, trending, and price-history intelligence."""

from __future__ import annotations

import html
from datetime import datetime, timedelta
from typing import Any
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from src.config import ECOMMERCE_PLATFORMS, RECOMMENDATION_SITES
from src.groq_client import GroqService
from src.search import format_search_context, search_product_links
from src.urls import (
    format_money,
    match_recommendation_url,
    resolve_store_url,
    url_in_results,
)


COMPARE_SYSTEM = """You are an expert e-commerce product analyst for the Indian and global market.
Given a product query and optional live search snippets, produce a precise multi-store comparison.

Rules:
- Prefer INR prices when the product is commonly sold in India; otherwise use USD and note currency.
- Cover major platforms including Amazon, Flipkart, Croma, Reliance Digital, Vijay Sales, Tata CLiQ,
  Myntra, Ajio, Nykaa, Meesho, Snapdeal, Pepperfry when relevant.
- Also use editorial recommendation sources such as NDTV Shopping, Hindustan Times, Gadgets 360,
  91mobiles, Smartprix, Digit, and India Today Tech when snippets are available.
- Only include platforms where the product (or a close variant) is realistically sold.
- Be precise on specs, ratings, seller reputation, delivery, and value.
- Mark the single best buy clearly with reasoning.
- Always include list_price (MRP / original price) and sale price for each listing.
- CRITICAL: Never invent product page URLs or ASIN/SKU links. Only copy a URL if it appears
  exactly in the live search context. Otherwise set product_url to an empty string.
- Price history should be realistic monthly points for the last 12 months.
- If uncertain about an exact live price, give a realistic estimated range and set confidence accordingly.
"""


TRENDING_SYSTEM = """You are a retail trend analyst. Return currently trending products
across popular e-commerce categories with approximate best prices and why they are trending.
Focus on India + global bestsellers. Be concrete and useful for shoppers.
Do not invent product URLs. Leave product_url empty unless copied from live search context.
"""


def enrich_with_links(
    data: dict[str, Any],
    query: str,
    web: list[dict[str, Any]],
) -> dict[str, Any]:
    """Attach verified clickable store URLs (never keep hallucinated product pages)."""
    product_name = data.get("product_name") or query
    search_query = query or product_name

    best = data.get("best_buy") or {}
    best_platform = best.get("platform") or "Amazon"
    best["product_url"] = resolve_store_url(
        best_platform,
        web,
        search_query,
        candidate=best.get("product_url") or best.get("url") or best.get("url_hint"),
    )
    best.setdefault("list_price", best.get("mrp") or best.get("price"))
    best.setdefault("currency", "INR")
    data["best_buy"] = best

    listings = data.get("listings") or []
    for item in listings:
        platform = item.get("platform") or "Amazon"
        item["product_url"] = resolve_store_url(
            platform,
            web,
            search_query,
            candidate=item.get("product_url") or item.get("url"),
        )
        item.setdefault("list_price", item.get("mrp") or item.get("price"))
        item.setdefault("currency", "INR")
    data["listings"] = listings

    for alt in data.get("relevant_alternatives") or []:
        name = alt.get("name") or product_name
        platform = alt.get("platform") or "Amazon"
        alt["product_url"] = resolve_store_url(
            platform,
            web,
            name,
            candidate=alt.get("product_url"),
        )

    for trend in data.get("trending") or []:
        name = trend.get("name") or query
        platform = trend.get("best_platform") or "Amazon"
        trend["product_url"] = resolve_store_url(
            platform,
            web,
            name,
            candidate=trend.get("product_url"),
        )

    editorials = data.get("editorial_recommendations") or []
    for item in editorials:
        site = item.get("site") or "Hindustan Times"
        candidate = item.get("article_url") or item.get("url") or ""
        if candidate and str(candidate).startswith("http"):
            if url_in_results(str(candidate), web):
                item["article_url"] = str(candidate)
            else:
                item["article_url"] = match_recommendation_url(site, web, product_name)
        else:
            item["article_url"] = match_recommendation_url(site, web, product_name)
        item.setdefault("site", site)
    data["editorial_recommendations"] = editorials

    return data


def compare_product(query: str, groq: GroqService | None = None) -> dict[str, Any]:
    client = groq or GroqService()
    web = search_product_links(query)
    context = format_search_context(web)

    user_prompt = f"""
Product query: {query}

Live search context (use these URLs when they match a platform listing):
{context}

Return JSON with this exact shape:
{{
  "product_name": "canonical product name",
  "category": "category",
  "summary": "2-3 sentence overview",
  "key_specs": ["spec1", "spec2", "spec3", "spec4", "spec5"],
  "best_buy": {{
    "platform": "platform name",
    "price": 0,
    "list_price": 0,
    "currency": "INR",
    "product_url": "https://full-product-or-search-url",
    "reason": "why this is the best buy",
    "savings_note": "e.g. 12% below MRP"
  }},
  "listings": [
    {{
      "platform": "Amazon",
      "title": "listing title",
      "price": 0,
      "list_price": 0,
      "currency": "INR",
      "product_url": "https://full-product-or-search-url",
      "rating": 4.5,
      "reviews": 1200,
      "availability": "In Stock",
      "delivery": "2-3 days",
      "seller": "seller name",
      "pros": ["p1", "p2"],
      "cons": ["c1"],
      "score": 8.5
    }}
  ],
  "comparison_table": {{
    "dimensions": ["Price", "List Price", "Rating", "Delivery", "Warranty", "Return Policy", "Overall Value"],
    "rows": [
      {{
        "platform": "Amazon",
        "values": ["₹x", "₹y", "4.5", "2 days", "1 year", "7 days", "High"]
      }}
    ]
  }},
  "relevant_alternatives": [
    {{
      "name": "alternative product",
      "why_relevant": "reason",
      "approx_price": 0,
      "list_price": 0,
      "currency": "INR",
      "platform": "Amazon",
      "product_url": "https://...",
      "vs_main": "cheaper / premium / similar"
    }}
  ],
  "editorial_recommendations": [
    {{
      "site": "NDTV Shopping",
      "headline": "article or guide title",
      "verdict": "short recommendation verdict",
      "rating": "4.2/5 or Best Buy",
      "article_url": "https://..."
    }}
  ],
  "price_history": {{
    "currency": "INR",
    "points": [
      {{"month": "2025-08", "avg_price": 0, "low": 0, "high": 0}}
    ]
  }},
  "buying_advice": "short actionable advice",
  "confidence": "high|medium|low"
}}

Include 5-8 listings across relevant platforms from: {", ".join(ECOMMERCE_PLATFORMS)}.
Always try to include Croma and at least one of Reliance Digital / Vijay Sales / Tata CLiQ when the product is electronics.
Include 3-5 editorial_recommendations from: {", ".join(RECOMMENDATION_SITES)}.
Include exactly 12 monthly price_history points ending with the current month.
Every listing and best_buy MUST include product_url, price, and list_price.
"""
    data = client.chat_json(COMPARE_SYSTEM, user_prompt)
    if not isinstance(data, dict):
        raise ValueError("Unexpected comparison response shape")
    data = enrich_with_links(data, query, web)
    data["_web_results"] = web
    data["_queried_at"] = datetime.now().isoformat(timespec="seconds")
    return data


def get_trending(category: str = "All", groq: GroqService | None = None) -> dict[str, Any]:
    client = groq or GroqService()
    web = search_product_links(f"trending {category} products")
    context = format_search_context(web)

    user_prompt = f"""
Category focus: {category}
Live search context:
{context}

Return JSON:
{{
  "updated": "ISO date string",
  "category": "{category}",
  "trending": [
    {{
      "rank": 1,
      "name": "product name",
      "category": "subcategory",
      "best_price": 0,
      "list_price": 0,
      "currency": "INR",
      "best_platform": "Amazon",
      "product_url": "https://...",
      "trend_score": 92,
      "why_trending": "short reason",
      "change_7d": "+12%"
    }}
  ]
}}

Return 8 trending products with product_url for each.
"""
    data = client.chat_json(TRENDING_SYSTEM, user_prompt)
    if not isinstance(data, dict):
        raise ValueError("Unexpected trending response shape")
    data.setdefault("updated", datetime.now().date().isoformat())
    data = enrich_with_links(data, f"trending {category}", web)
    return data


def build_price_history_figure(comparison: dict[str, Any]) -> go.Figure:
    history = comparison.get("price_history") or {}
    points = history.get("points") or []
    currency = history.get("currency") or "INR"
    product = comparison.get("product_name") or "Product"

    if not points:
        today = datetime.now().replace(day=1)
        base = float((comparison.get("best_buy") or {}).get("price") or 10000)
        points = []
        for i in range(11, -1, -1):
            month = (today - timedelta(days=30 * i)).strftime("%Y-%m")
            drift = 1 + (0.04 * ((i % 5) - 2) / 10)
            avg = round(base * drift, 2)
            points.append(
                {
                    "month": month,
                    "avg_price": avg,
                    "low": round(avg * 0.92, 2),
                    "high": round(avg * 1.08, 2),
                }
            )

    df = pd.DataFrame(points)
    for col in ("avg_price", "low", "high"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    fig = make_subplots(specs=[[{"secondary_y": False}]])
    fig.add_trace(
        go.Scatter(
            x=df["month"],
            y=df["high"],
            mode="lines",
            line=dict(width=0),
            showlegend=False,
            hoverinfo="skip",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["month"],
            y=df["low"],
            mode="lines",
            fill="tonexty",
            fillcolor="rgba(14, 116, 144, 0.15)",
            line=dict(width=0),
            name="Price range",
        )
    )
    fig.add_trace(
        go.Scatter(
            x=df["month"],
            y=df["avg_price"],
            mode="lines+markers",
            name="Average price",
            line=dict(color="#0E7490", width=3),
            marker=dict(size=8, color="#164E63"),
        )
    )

    best = comparison.get("best_buy") or {}
    best_price = best.get("price")
    if best_price is not None:
        fig.add_hline(
            y=float(best_price),
            line_dash="dot",
            line_color="#B45309",
            annotation_text=f"Best buy now: {format_money(best_price, currency)}",
            annotation_position="top left",
        )

    fig.update_layout(
        title=f"Price history — {product}",
        xaxis_title="Month",
        yaxis_title=f"Price ({currency})",
        template="plotly_white",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(248,250,252,0.9)",
        font=dict(family="DM Sans, Segoe UI, sans-serif", color="#0F172A"),
        margin=dict(l=40, r=20, t=60, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        height=420,
    )
    return fig


def _savings_pct(price: object, list_price: object) -> str:
    try:
        p = float(price)  # type: ignore[arg-type]
        lp = float(list_price)  # type: ignore[arg-type]
        if lp > p > 0:
            return f"{round((lp - p) / lp * 100)}% off"
    except (TypeError, ValueError):
        pass
    return ""


def best_buy_markdown_link(comparison: dict[str, Any]) -> str:
    """Gradio-safe markdown link that always opens a working store page."""
    best = comparison.get("best_buy") or {}
    platform = best.get("platform") or "Store"
    url = best.get("product_url") or "#"
    price = format_money(best.get("price"), str(best.get("currency") or "INR"))
    list_price = format_money(
        best.get("list_price", best.get("price")),
        str(best.get("currency") or "INR"),
    )
    is_search = "/s?" in str(url) or "search" in str(url).lower()
    action = f"Search live deals on {platform}" if is_search else f"Open listing on {platform}"
    return (
        f"### Best buy link\n\n"
        f"**Deal {price}** · List {list_price}\n\n"
        f"**[{action} →]({url})**"
    )


def render_best_buy_html(comparison: dict[str, Any]) -> str:
    best = comparison.get("best_buy") or {}
    name = html.escape(str(comparison.get("product_name") or "Product"))
    platform = html.escape(str(best.get("platform") or "Store"))
    currency = str(best.get("currency") or "INR")
    price = best.get("price", "—")
    list_price = best.get("list_price", price)
    url = str(best.get("product_url") or "#")
    reason = html.escape(str(best.get("reason") or ""))
    savings = best.get("savings_note") or _savings_pct(price, list_price)
    confidence = html.escape(str(comparison.get("confidence") or "medium"))
    safe_url = html.escape(url, quote=True)
    price_txt = html.escape(format_money(price, currency))
    list_txt = html.escape(format_money(list_price, currency))
    savings_html = (
        f'<span class="pc-save">{html.escape(str(savings))}</span>' if savings else ""
    )
    is_search = "/s?" in url or "search" in url.lower()
    cta_label = f"Search on {platform} →" if is_search else f"Open on {platform} →"
    link_hint = (
        "Opens the live store search for this product"
        if is_search
        else "Opens the verified product listing"
    )

    return f"""
    <div class="pc-best-panel">
      <div class="pc-best-copy">
        <p class="pc-kicker">Recommended best buy</p>
        <h2>{name}</h2>
        <p class="pc-platform-line">Lowest strong value on <strong>{platform}</strong></p>
        <p class="pc-reason">{reason}</p>
        <span class="pc-badge">Confidence: {confidence}</span>
      </div>
      <div class="pc-best-pricebox">
        <p class="pc-kicker">Deal price</p>
        <p class="pc-price">{price_txt}</p>
        <p class="pc-list">List price <s>{list_txt}</s> {savings_html}</p>
        <a class="pc-cta"
           href="{safe_url}"
           target="_blank"
           rel="noopener noreferrer"
           onclick="window.open('{safe_url}', '_blank', 'noopener,noreferrer'); return false;">
          {cta_label}
        </a>
        <p class="pc-link-note">{html.escape(link_hint)} ·
          <a href="{safe_url}" target="_blank" rel="noopener noreferrer"
             onclick="window.open('{safe_url}', '_blank', 'noopener,noreferrer'); return false;">
             Open link
          </a>
        </p>
      </div>
    </div>
    """


def _link_attrs(url: str) -> str:
    safe = html.escape(url, quote=True)
    return (
        f'href="{safe}" target="_blank" rel="noopener noreferrer" '
        f"onclick=\"window.open('{safe}', '_blank', 'noopener,noreferrer'); return false;\""
    )


def render_listings_html(comparison: dict[str, Any]) -> str:
    listings = comparison.get("listings") or []
    best_platform = (comparison.get("best_buy") or {}).get("platform")
    if not listings:
        return "<div class='pc-empty'>No store listings yet.</div>"

    cards = []
    for item in listings:
        platform = html.escape(str(item.get("platform") or "Store"))
        title = html.escape(str(item.get("title") or ""))
        currency = str(item.get("currency") or "INR")
        price = item.get("price", "—")
        list_price = item.get("list_price", price)
        rating = html.escape(str(item.get("rating") or "—"))
        delivery = html.escape(str(item.get("delivery") or "—"))
        availability = html.escape(str(item.get("availability") or "—"))
        score = html.escape(str(item.get("score") or "—"))
        is_best = item.get("platform") == best_platform
        badge = '<span class="pc-pill best">Best buy</span>' if is_best else ""
        savings = _savings_pct(price, list_price)
        savings_html = (
            f'<span class="pc-save">{html.escape(savings)}</span>' if savings else ""
        )
        cards.append(
            f"""
            <article class="pc-card {'is-best' if is_best else ''}">
              <div class="pc-card-top">
                <div>
                  <p class="pc-store">{platform}</p>
                  <h3>{title}</h3>
                </div>
                {badge}
              </div>
              <div class="pc-card-prices">
                <span class="pc-deal">{html.escape(format_money(price, currency))}</span>
                <span class="pc-mrp">List <s>{html.escape(format_money(list_price, currency))}</s></span>
                {savings_html}
              </div>
              <div class="pc-meta">
                <span>★ {rating}</span>
                <span>{delivery}</span>
                <span>{availability}</span>
                <span>Score {score}</span>
              </div>
              <a class="pc-card-link" {_link_attrs(str(item.get("product_url") or "#"))}>
                View on {platform} →
              </a>
            </article>
            """
        )
    return f'<div class="pc-cards">{"".join(cards)}</div>'


def render_editorial_html(comparison: dict[str, Any]) -> str:
    items = comparison.get("editorial_recommendations") or []
    if not items:
        return "<div class='pc-empty'>No editorial recommendations found for this product.</div>"
    cards = []
    for item in items:
        site = html.escape(str(item.get("site") or "Editorial"))
        headline = html.escape(str(item.get("headline") or ""))
        verdict = html.escape(str(item.get("verdict") or ""))
        rating = html.escape(str(item.get("rating") or ""))
        rating = html.escape(str(item.get("rating") or ""))
        rating_html = f'<span class="pc-pill">{rating}</span>' if rating else ""
        cards.append(
            f"""
            <article class="pc-card pc-editorial">
              <div class="pc-card-top">
                <div>
                  <p class="pc-store">{site}</p>
                  <h3>{headline}</h3>
                </div>
                {rating_html}
              </div>
              <p class="pc-body-text">{verdict}</p>
              <a class="pc-card-link" {_link_attrs(str(item.get("article_url") or "#"))}>
                Read recommendation →
              </a>
            </article>
            """
        )
    return f'<div class="pc-cards">{"".join(cards)}</div>'


def render_summary_html(comparison: dict[str, Any]) -> str:
    name = html.escape(str(comparison.get("product_name") or "Product"))
    summary = html.escape(str(comparison.get("summary") or ""))
    specs = comparison.get("key_specs") or []
    advice = html.escape(str(comparison.get("buying_advice") or ""))
    specs_html = "".join(f"<li>{html.escape(str(s))}</li>" for s in specs)
    best_html = render_best_buy_html(comparison)
    listings_html = render_listings_html(comparison)
    editorial_html = render_editorial_html(comparison)

    return f"""
    <div class="pc-summary">
      {best_html}
      <div class="pc-overview">
        <div>
          <p class="pc-kicker">Product overview</p>
          <h2>{name}</h2>
          <p class="pc-lede">{summary}</p>
        </div>
        <div class="pc-grid">
          <div>
            <h3>Key specs</h3>
            <ul>{specs_html}</ul>
          </div>
          <div>
            <h3>Buying advice</h3>
            <p class="pc-body-text">{advice}</p>
          </div>
        </div>
      </div>
      <div class="pc-section">
        <p class="pc-kicker">Expert & media picks</p>
        <h2>Recommendations from review sites</h2>
        {editorial_html}
      </div>
      <div class="pc-section">
        <p class="pc-kicker">Compare across stores</p>
        <h2>All listings with prices & links</h2>
        {listings_html}
      </div>
    </div>
    """


def listings_to_dataframe(comparison: dict[str, Any]) -> pd.DataFrame:
    listings = comparison.get("listings") or []
    rows = []
    best_platform = (comparison.get("best_buy") or {}).get("platform")
    for item in listings:
        currency = item.get("currency", "INR")
        rows.append(
            {
                "Best": "★" if item.get("platform") == best_platform else "",
                "Platform": item.get("platform", ""),
                "Title": item.get("title", ""),
                "Deal price": format_money(item.get("price"), currency),
                "List price": format_money(item.get("list_price", item.get("price")), currency),
                "Rating": item.get("rating", ""),
                "Delivery": item.get("delivery", ""),
                "Product link": item.get("product_url", ""),
            }
        )
    return pd.DataFrame(rows)


def comparison_matrix(comparison: dict[str, Any]) -> pd.DataFrame:
    table = comparison.get("comparison_table") or {}
    dims = table.get("dimensions") or []
    rows = table.get("rows") or []
    if not dims or not rows:
        return pd.DataFrame()
    data = {"Dimension": dims}
    for row in rows:
        platform = row.get("platform", "Store")
        values = row.get("values") or []
        data[platform] = values + [""] * max(0, len(dims) - len(values))
        data[platform] = data[platform][: len(dims)]
    return pd.DataFrame(data)


def alternatives_dataframe(comparison: dict[str, Any]) -> pd.DataFrame:
    alts = comparison.get("relevant_alternatives") or []
    rows = []
    for a in alts:
        currency = a.get("currency", "INR")
        rows.append(
            {
                "Product": a.get("name", ""),
                "Deal price": format_money(a.get("approx_price"), currency),
                "List price": format_money(a.get("list_price", a.get("approx_price")), currency),
                "Vs searched": a.get("vs_main", ""),
                "Why relevant": a.get("why_relevant", ""),
                "Product link": a.get("product_url", ""),
            }
        )
    return pd.DataFrame(rows)


def trending_dataframe(payload: dict[str, Any]) -> pd.DataFrame:
    items = payload.get("trending") or []
    rows = []
    for t in items:
        currency = t.get("currency", "INR")
        rows.append(
            {
                "Rank": t.get("rank", ""),
                "Product": t.get("name", ""),
                "Category": t.get("category", ""),
                "Best price": format_money(t.get("best_price"), currency),
                "List price": format_money(t.get("list_price", t.get("best_price")), currency),
                "Platform": t.get("best_platform", ""),
                "Trend": t.get("trend_score", ""),
                "7d": t.get("change_7d", ""),
                "Why trending": t.get("why_trending", ""),
                "Product link": t.get("product_url", ""),
            }
        )
    return pd.DataFrame(rows)


def render_trending_html(payload: dict[str, Any]) -> str:
    items = payload.get("trending") or []
    if not items:
        return "<div class='pc-empty'>No trending products loaded yet.</div>"
    cards = []
    for t in items:
        name = html.escape(str(t.get("name") or ""))
        platform = html.escape(str(t.get("best_platform") or "Store"))
        currency = str(t.get("currency") or "INR")
        why = html.escape(str(t.get("why_trending") or ""))
        change = html.escape(str(t.get("change_7d") or ""))
        cards.append(
            f"""
            <article class="pc-card">
              <div class="pc-card-top">
                <div>
                  <p class="pc-store">#{html.escape(str(t.get('rank') or ''))} · {html.escape(str(t.get('category') or ''))}</p>
                  <h3>{name}</h3>
                </div>
                <span class="pc-pill">{change}</span>
              </div>
              <div class="pc-card-prices">
                <span class="pc-deal">{html.escape(format_money(t.get('best_price'), currency))}</span>
                <span class="pc-mrp">List <s>{html.escape(format_money(t.get('list_price', t.get('best_price')), currency))}</s></span>
              </div>
              <p class="pc-body-text">{why}</p>
              <a class="pc-card-link" {_link_attrs(str(t.get("product_url") or "#"))}>
                Buy on {platform} →
              </a>
            </article>
            """
        )
    return f'<div class="pc-cards">{"".join(cards)}</div>'


def render_alternatives_html(comparison: dict[str, Any]) -> str:
    alts = comparison.get("relevant_alternatives") or []
    if not alts:
        return "<div class='pc-empty'>No alternatives found.</div>"
    cards = []
    for a in alts:
        name = html.escape(str(a.get("name") or ""))
        currency = str(a.get("currency") or "INR")
        why = html.escape(str(a.get("why_relevant") or ""))
        vs = html.escape(str(a.get("vs_main") or ""))
        cards.append(
            f"""
            <article class="pc-card">
              <div class="pc-card-top">
                <div>
                  <p class="pc-store">{vs}</p>
                  <h3>{name}</h3>
                </div>
              </div>
              <div class="pc-card-prices">
                <span class="pc-deal">{html.escape(format_money(a.get('approx_price'), currency))}</span>
                <span class="pc-mrp">List <s>{html.escape(format_money(a.get('list_price', a.get('approx_price')), currency))}</s></span>
              </div>
              <p class="pc-body-text">{why}</p>
              <a class="pc-card-link" {_link_attrs(str(a.get("product_url") or "#"))}>
                View product →
              </a>
            </article>
            """
        )
    return f'<div class="pc-cards">{"".join(cards)}</div>'
