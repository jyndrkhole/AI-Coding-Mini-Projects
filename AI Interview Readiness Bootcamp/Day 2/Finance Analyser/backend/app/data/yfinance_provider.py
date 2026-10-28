"""Yahoo Finance adapter. A later provider can implement the same two methods."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import httpx
import pandas as pd

from app.data.cache import TTLCache
from app.data.errors import ProviderError, TickerNotFound
from app.data.normalize import frames_to_periods
from app.domain.models import CompanySnapshot, MarketSnapshot, NewsArticle
from app.finance.mathutil import clean_number

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None


def canonical_ticker(ticker: str) -> str:
    text = ticker.strip().upper()
    if not text or len(text) > 24 or any(char.isspace() for char in text):
        raise TickerNotFound(f"'{ticker}' is not a usable ticker.")
    return text


class YFinanceProvider:
    def __init__(self, ttl_seconds: int = 900) -> None:
        self.cache = TTLCache(ttl_seconds)

    async def get_snapshot(self, ticker: str) -> CompanySnapshot:
        symbol = canonical_ticker(ticker)
        return await self.cache.get_or_set(f"snapshot:{symbol}", lambda: self._snapshot(symbol))

    async def get_news(self, ticker: str, lookback_days: int) -> list[NewsArticle]:
        symbol = canonical_ticker(ticker)
        articles = await self.cache.get_or_set(f"news:{symbol}", lambda: self._news(symbol))
        return _filter_lookback(articles, lookback_days)

    async def _snapshot(self, symbol: str) -> CompanySnapshot:
        try:
            return await asyncio.wait_for(asyncio.to_thread(self._snapshot_sync, symbol), timeout=40)
        except TickerNotFound:
            raise
        except asyncio.TimeoutError as exc:
            raise ProviderError(f"Timed out while loading {symbol} from Yahoo Finance.") from exc
        except Exception as exc:
            raise ProviderError(f"Yahoo Finance failed for {symbol}: {exc}") from exc

    async def _news(self, symbol: str) -> list[NewsArticle]:
        try:
            return await asyncio.wait_for(asyncio.to_thread(self._news_sync, symbol), timeout=30)
        except Exception:
            return []

    def _snapshot_sync(self, symbol: str) -> CompanySnapshot:
        if yf is None:
            raise ProviderError("yfinance is not installed.")
        ticker = yf.Ticker(symbol)
        info = _info(ticker)
        annual = frames_to_periods(
            _frame(ticker, "financials"),
            _frame(ticker, "balance_sheet"),
            _frame(ticker, "cashflow"),
            "annual",
            5,
        )
        quarterly = frames_to_periods(
            _frame(ticker, "quarterly_financials"),
            _frame(ticker, "quarterly_balance_sheet"),
            _frame(ticker, "quarterly_cashflow"),
            "quarter",
            8,
        )
        price = _first(info, "currentPrice", "regularMarketPrice", "previousClose")
        if price is None:
            price = _last_close(ticker)
        name = info.get("longName") or info.get("shortName")
        if not name and price is None and not annual:
            raise TickerNotFound(f"No Yahoo Finance listing was found for {symbol}.")
        market_cap = clean_number(info.get("marketCap"))
        shares = clean_number(info.get("sharesOutstanding"))
        shares_source = "sharesOutstanding" if shares else None
        if market_cap and price and price > 0:
            shares = market_cap / price
            shares_source = "market cap / price, so the per-share value uses the same share count as the quoted price"
        debt = annual[-1].total_debt if annual else clean_number(info.get("totalDebt"))
        cash = annual[-1].cash if annual else clean_number(info.get("totalCash"))
        enterprise = clean_number(info.get("enterpriseValue"))
        enterprise_source = "Yahoo Finance enterpriseValue" if enterprise is not None else None
        if enterprise is None and market_cap is not None and debt is not None and cash is not None:
            enterprise = market_cap + debt - cash
            enterprise_source = "Calculated as market cap + total debt − cash"
        as_of = info.get("regularMarketTime")
        if isinstance(as_of, (int, float)):
            as_of = datetime.fromtimestamp(as_of, timezone.utc).isoformat()
        elif as_of is not None:
            as_of = str(as_of)
        limitations = []
        if annual and annual[-1].cash_definition and "Short Term" in annual[-1].cash_definition:
            limitations.append("Cash includes short-term investments because cash and cash equivalents alone was not reported.")
        if shares_source and market_cap and price and abs((market_cap / price) - (clean_number(info.get("sharesOutstanding")) or market_cap / price)) > 0:
            reported = clean_number(info.get("sharesOutstanding"))
            implied = market_cap / price
            if reported and abs(implied - reported) / reported > 0.15:
                limitations.append("Market cap divided by price differs from reported shares outstanding by more than 15%. The implied share count is used.")
        return CompanySnapshot(
            market=MarketSnapshot(
                ticker=symbol,
                company_name=name or symbol,
                exchange=info.get("exchange") or info.get("fullExchangeName"),
                sector=info.get("sector"),
                industry=info.get("industry"),
                currency=info.get("currency") or info.get("financialCurrency"),
                price=price,
                previous_close=clean_number(info.get("previousClose")),
                price_as_of=as_of,
                market_cap=market_cap,
                enterprise_value=enterprise,
                enterprise_value_source=enterprise_source,
                shares=shares,
                shares_source=shares_source,
                beta=clean_number(info.get("beta")),
                trailing_pe=clean_number(info.get("trailingPE")),
                dividend_yield=clean_number(info.get("dividendYield")),
            ),
            annual=annual,
            quarterly=quarterly,
            limitations=limitations,
        )

    def _news_sync(self, symbol: str) -> list[NewsArticle]:
        articles: list[NewsArticle] = []
        if yf is not None:
            raw = getattr(yf.Ticker(symbol), "news", None) or []
            articles = _articles_from_items(raw)
        if not articles:
            articles = _search_news(symbol)
        return articles


def _info(ticker) -> dict:
    for method in ("get_info", "info"):
        try:
            value = getattr(ticker, method)
            info = value() if callable(value) else value
            if isinstance(info, dict):
                return info
        except Exception:
            continue
    return {}


def _frame(ticker, name: str):
    try:
        frame = getattr(ticker, name)
        if isinstance(frame, pd.DataFrame):
            return frame
    except Exception:
        return None
    return None


def _first(info: dict, *keys: str) -> float | None:
    for key in keys:
        number = clean_number(info.get(key))
        if number is not None:
            return number
    return None


def _last_close(ticker) -> float | None:
    try:
        history = ticker.history(period="5d")
        if history is None or history.empty or "Close" not in history:
            return None
        return clean_number(history["Close"].iloc[-1])
    except Exception:
        return None


def _articles_from_items(raw) -> list[NewsArticle]:
    articles: list[NewsArticle] = []
    seen: set[str] = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            continue
        parsed = _parse_article(item, index)
        if parsed is None:
            continue
        key = parsed.url or parsed.title
        if key in seen:
            continue
        seen.add(key)
        articles.append(parsed)
    return articles


def _search_news(symbol: str) -> list[NewsArticle]:
    """Yahoo's search feed. Used when Ticker.news is empty; it is the same vendor, not a scraped article body."""
    try:
        with httpx.Client(timeout=20, headers={"User-Agent": "Mozilla/5.0"}, follow_redirects=True) as client:
            response = client.get(
                "https://query1.finance.yahoo.com/v1/finance/search",
                params={"q": symbol, "newsCount": 12},
            )
        if response.status_code != 200:
            return []
        root = symbol.split(".")[0]
        related_items = []
        for item in response.json().get("news") or []:
            related = {str(ticker).upper() for ticker in item.get("relatedTickers") or []}
            if symbol in related or root in related:
                related_items.append(item)
        return _articles_from_items(related_items)
    except Exception:
        return []


def _parse_article(item: dict, index: int) -> NewsArticle | None:
    content = item.get("content") if isinstance(item.get("content"), dict) else {}
    title = content.get("title") or item.get("title") or ""
    title = str(title).strip()
    if not title:
        return None
    provider = None
    if isinstance(content.get("provider"), dict):
        provider = content["provider"].get("displayName")
    provider = provider or item.get("publisher")
    url = None
    for candidate in (
        (content.get("canonicalUrl") or {}).get("url") if isinstance(content.get("canonicalUrl"), dict) else None,
        (content.get("clickThroughUrl") or {}).get("url") if isinstance(content.get("clickThroughUrl"), dict) else None,
        item.get("link"),
        item.get("url"),
    ):
        if candidate:
            url = str(candidate)
            break
    published = content.get("pubDate") or item.get("providerPublishTime")
    if isinstance(published, (int, float)):
        published = datetime.fromtimestamp(published, timezone.utc).isoformat()
    elif published is not None:
        published = str(published)
    summary = content.get("summary") or content.get("description") or item.get("summary")
    return NewsArticle(
        id=str(content.get("id") or item.get("uuid") or f"news-{index}"),
        title=title,
        publisher=str(provider) if provider else None,
        published_at=published,
        url=url,
        summary=str(summary) if summary else None,
    )


def _filter_lookback(articles: list[NewsArticle], lookback_days: int) -> list[NewsArticle]:
    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    kept: list[NewsArticle] = []
    for article in articles:
        if not article.published_at:
            kept.append(article)
            continue
        parsed = _parse_time(article.published_at)
        if parsed is None or parsed >= cutoff:
            kept.append(article)
    return kept


def _parse_time(value: str) -> datetime | None:
    text = value.replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed
