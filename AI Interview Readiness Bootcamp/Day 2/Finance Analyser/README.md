# Fundamental Analyser

A research desk for one question: given a public ticker, what is its financial health, intrinsic value, risk, and news context relative to the current price?

The rating is a documented score. A language model may comment on the finished numbers. It does not invent figures and it does not choose the rating.

## How the agents run

```text
Phase 1   Market data and headlines, together
Phase 2   FinancialDataAgent, NewsAndSentimentAgent, RiskAgent, together
Phase 3   ValuationAgent, after the statements exist (it does not wait for news)
Phase 4   ReportWriterAgent, after valuation, news, and risk have all finished
```

Risk reads the statements directly, in parallel with the financial agent. Valuation-specific flags are added after the DCF, because they depend on it. The published risk label includes both passes.

Shared Yahoo requests sit in a short-lived memory cache, so a second agent does not download the same statements again.

## What is calculated, and what is commentary

| Piece | Who decides |
| --- | --- |
| Ratios, margins, growth | Formula module. Missing inputs stay blank. |
| Financial health | Pass rate against thresholds in `backend/app/finance/thresholds.py`. A general heuristic, not an industry standard. Banks skip the current-ratio test. |
| DCF | Enterprise FCFF discounted at WACC when revenue, margin, tax, depreciation, capex, working capital, and the capital structure are all present. Otherwise a labeled equity DCF on positive free cash flow, discounted at the cost of equity. Levered free cash flow is never discounted with WACC. |
| Peers | A narrow configured universe, or the tickers you type. The peer median is not treated as fair value. |
| Risk | Count of explicit flags. |
| Rating | Weighted score. Missing health or valuation yields `INSUFFICIENT_DATA` rather than a neutral 3. News is 10% and cannot override a missing valuation. |
| Prose | Templates from those results. Optional model commentary is stored separately. |

Upside is `(intrinsic value per share / price − 1) × 100`.

Valuation bands: above 30% significantly undervalued, above 10% slightly undervalued, from −10% to 10% fairly valued, to −30% slightly overvalued, below that significantly overvalued.

Rating bands on the 1–5 score: 4.25 strong buy, 3.50 buy, 2.75 hold, 2.00 sell, otherwise strong sell.

## Run it

Python 3.11 or newer, and Node.

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pytest
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open `http://127.0.0.1:5173`. Try `AAPL`, `MSFT`, `NVDA`, `RELIANCE.NS`, or `TCS.NS`.

## Language model

Copy `.env.example` to `.env` in this folder. Set one provider. The app will not switch providers on its own.

```text
LLM_PROVIDER=groq
GROQ_API_KEY=
GROQ_MODEL=llama-3.3-70b-versatile
```

or:

```text
LLM_PROVIDER=openai
OPENAI_API_KEY=
OPENAI_MODEL=gpt-4.1-mini
```

A Cursor subscription is not an API key this service can call. Without a provider, the ratios, DCF, risk flags, and rating still run, and the brief says the commentary is rule-based.

Keys are read from the environment only. They are not returned by the API or written into the report.

## Data

Yahoo Finance via `yfinance` for prices and statements. When `Ticker.news` is empty, headlines come from Yahoo's search feed for that ticker. Nothing is scraped from arbitrary websites, and no figure is filled in to complete a section.

History is a SQLite file at `backend/data/analyses.db`. The repository ignores it.

## Tests

`backend/tests` covers the formulas, negative equity, zero prices, valuation bands, the rating when news and valuation disagree, peer selection, statement signs, and the orchestrator timing: the three specialists overlap, valuation starts before a slow news agent finishes, and the writer starts only after all of them.
