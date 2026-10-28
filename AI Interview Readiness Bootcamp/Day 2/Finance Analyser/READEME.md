# Project: AI-Powered Multi-Agent Fundamental Stock Analysis System

## 1. Your Role

Act as a senior Python engineer, AI-agent architect, financial data engineer, and quantitative equity research analyst.

Build a complete, runnable, modular application that performs **fundamental analysis of publicly traded stocks using a coordinated multi-agent AI system**.

The application should allow a user to enter a stock ticker, such as `AAPL`, `MSFT`, `NVDA`, `RELIANCE.NS`, or `TCS.NS`, and receive a detailed, evidence-based fundamental analysis report.

Use the following reference materials to guide the design and educational explanations:

1. Reference website: [https://shrijankumar1-maker.github.io/finance-section-1/](https://shrijankumar1-maker.github.io/finance-section-1/)
2. The architecture, workflow, and UI screenshots supplied with this task.
3. The functional requirements, agent responsibilities, financial definitions, and implementation constraints specified in this prompt.

Treat the reference website and screenshots as design and conceptual references, not as sources of live financial data.

Do not simply create a mockup, static dashboard, or single LLM prompt that generates an investment opinion. Implement the complete data retrieval, financial calculation, agent orchestration, analysis, validation, and reporting pipeline.

Before writing code:

- Inspect the existing workspace and repository.
- Identify any existing framework, files, dependencies, and conventions.
- Reuse suitable existing components rather than replacing them unnecessarily.
- Create an implementation plan and then implement the solution.
- Do not stop after presenting the plan.

---

# 2. Primary Objective

Given a publicly traded stock, the system should answer:

**"What is the fundamental financial health, intrinsic value, risk profile, and investment outlook of this stock relative to its current market price?"**

The system must evaluate the company from multiple perspectives:

1. Financial health and historical performance.
2. Profitability, liquidity, leverage, and operating efficiency.
3. Cash generation and free cash flow.
4. Intrinsic valuation using discounted cash flow.
5. Relative valuation against comparable companies.
6. Business risks and financial vulnerabilities.
7. Recent company news and market sentiment.
8. Bull, base, and bear scenarios.
9. An overall investment assessment derived from explicit, explainable rules.
10. Data quality, confidence, and limitations.

The final report must clearly distinguish:

- Reported financial facts.
- Calculated financial metrics.
- Forecast assumptions.
- External news and commentary.
- LLM-generated interpretations.
- Model-derived valuation estimates.
- Final assessment and supporting evidence.

Never invent financial figures to complete a report.

If data is unavailable, show that it is unavailable and explain how this affects the analysis.

This is an educational research and decision-support application, not an autonomous trading system or a guarantee of investment returns.

---

# 3. Technology Stack

Prefer the following stack unless the existing repository has a strong reason to use something else.

## Backend

- Python 3.11 or later.
- FastAPI for REST APIs.
- Pydantic for request and response validation.
- Pandas and NumPy for data processing.
- yfinance for market prices and financial statement data where available.
- Requests or an appropriate HTTP client for external APIs.
- A configurable LLM provider abstraction.
- pytest for unit and integration tests.

## Frontend

Inspect the repository before choosing the frontend.

If there is no existing frontend, use:

- React.
- TypeScript.
- Vite.
- A clean, responsive dashboard design.
- Recharts or an equivalent charting library.
- A suitable icon library.

If the repository already contains a suitable frontend, extend it instead of unnecessarily introducing a second frontend framework.

## Storage

For the initial implementation:

- SQLite for analysis history and persistent report metadata.
- JSON for validated agent outputs and report snapshots where appropriate.
- In-memory caching for repeated financial-data requests.

Keep persistence modular so SQLite can later be replaced with PostgreSQL.

## Financial data

Use yfinance as the initial data provider.

Design a provider interface so additional sources can be introduced later without rewriting the agents.

Possible future sources include:

- SEC EDGAR company filings for US-listed companies.
- Company annual reports.
- Official investor-relations websites.
- Additional licensed market-data providers.

Do not scrape websites indiscriminately or assume that every provider exposes the same fields.

---

# 4. LLM Provider Configuration

The application must support two LLM configuration options:

## Option A: Groq API

Use Groq when the user configures a Groq API key.

Configuration:

`GROQ_API_KEY`

`GROQ_MODEL`

Use an available model compatible with the required tool-calling or structured-output functionality.

Do not hardcode an assumed model name as permanently available. Make the model configurable and document how to select a supported model.

Use the official Groq API or a compatible SDK.

## Option B: Cursor IDE / OpenAI API key

Investigate what credentials and endpoints are actually available in the development environment.

Important distinction:

- Cursor IDE's built-in AI subscription is not automatically equivalent to an application API key.
- Do not assume that a Cursor subscription can be called directly by a deployed Python application.
- Do not attempt to extract credentials from Cursor's internal storage or bypass its authentication mechanisms.

If the user supplies a valid OpenAI API key, support it through the official API and a configurable model.

Configuration:

`OPENAI_API_KEY`

`OPENAI_MODEL`

If the user specifically wants to use Cursor's built-in models, explain any limitations and keep the LLM interface provider-agnostic so a supported integration can be added later.

## Provider selection

Implement a configuration option:

`LLM_PROVIDER=groq`

or:

`LLM_PROVIDER=openai`

The application should:

- Validate configuration during startup or before analysis.
- Provide a clear error if the selected provider is not configured.
- Avoid silently switching providers without telling the user.
- Never expose API keys in the frontend, logs, API responses, or generated reports.
- Load secrets from environment variables.
- Include `.env.example` with placeholder values only.
- Include `.env` in `.gitignore`.

If LLM access is unavailable, allow the deterministic financial calculations to run independently wherever possible. Clearly label any omitted LLM-generated analysis.

---

# 5. Multi-Agent Architecture

Use a **supervisor-worker architecture with explicit dependency management**, optionally implemented as a directed graph.

Recommended architecture:

- Supervisor / Orchestrator Agent.
- Financial Data Agent.
- Valuation Agent.
- Risk Agent.
- News and Sentiment Agent.
- Report Writer Agent.

The design should follow the architecture illustrated in the supplied screenshots: specialist agents perform independent work, dependent agents receive validated results, and the report writer synthesizes the completed analyses.

Do not force all agents to run sequentially if they do not depend on one another.

## Recommended execution graph

Phase 1: Data preparation.

Retrieve market prices, company information, financial statements, historical financial data, and relevant news.

Validate and normalize the retrieved data.

Phase 2: Parallel specialist analysis.

Run the following agents in parallel where dependencies permit:

1. FinancialDataAgent.
2. NewsAndSentimentAgent.
3. RiskAgent, after receiving the minimum financial and company context it requires.

Phase 3: Valuation.

Run ValuationAgent after the required financial data and relevant peer data are available.

Phase 4: Synthesis and validation.

Run ReportWriterAgent after the specialist analyses are complete.

Validate the report against the original data and calculated metrics.

Return the final report to the user.

Represent these dependencies explicitly in the orchestration layer.

Use asynchronous execution where appropriate.

Implement timeouts, bounded retries, structured errors, and cancellation handling.

Do not assume that agents have run concurrently merely because their code uses asynchronous syntax. Verify parallel execution with tests or instrumentation.

## Architecture selection

Do not introduce a heavyweight agent framework solely for the sake of using one.

Choose one of these approaches after inspecting the repository:

- A lightweight supervisor-worker implementation using Python async functions and structured LLM calls.
- A graph-based orchestration framework if explicit state, conditional routing, retries, and execution tracing justify the dependency.

If using LangGraph, keep graph state typed and node responsibilities explicit.

If using the OpenAI Agents SDK, verify that the chosen SDK supports the configured provider and required integrations before adopting it.

If using a simple Python orchestration layer, implement the same dependency graph and validation responsibilities directly.

The architecture should be easy to understand, test, extend, and debug.

---

# 6. Agent Responsibilities

## Agent 1: FinancialDataAgent

Purpose:

Retrieve and interpret the company's financial statements, financial ratios, and historical financial performance.

### Data retrieval

Use yfinance where the required fields are available:

- Company name.
- Ticker.
- Exchange.
- Sector.
- Industry.
- Currency.
- Current or latest available market price.
- Market capitalization.
- Enterprise value, where available.
- Shares outstanding.
- Revenue.
- Gross profit.
- Operating income.
- Net income.
- Cash and cash equivalents.
- Total assets.
- Current assets.
- Total liabilities.
- Current liabilities.
- Total debt.
- Shareholders' equity.
- Operating cash flow.
- Capital expenditure.
- Free cash flow.
- Earnings per share.
- Dividends, where applicable.

Retrieve several years of historical financial data when available.

Prefer up to five years of annual financial statements, along with quarterly data where available and useful.

Do not assume all tickers have complete historical data.

Capture the actual reporting periods and dates associated with the retrieved figures.

### Financial statements

Analyze the three core financial statements.

**Income statement**

- Revenue growth.
- Gross profit and gross margin.
- Operating income and operating margin.
- Net income and net profit margin.
- EPS growth, where available.

**Balance sheet**

- Cash and cash equivalents.
- Total debt.
- Net debt, when calculable.
- Current assets and current liabilities.
- Total assets and total liabilities.
- Shareholders' equity.
- Working capital, when calculable.

**Cash flow statement**

- Operating cash flow.
- Capital expenditure.
- Free cash flow.
- Operating cash flow relative to net income.
- Free cash flow trend.
- Dividend coverage by cash flow, when relevant.

### Ratio calculations

Implement deterministic financial functions for:

- Revenue growth.
- Gross margin.
- Operating margin.
- Net profit margin.
- Return on equity.
- Return on assets.
- Current ratio.
- Quick ratio, when the required data is available.
- Debt-to-equity ratio.
- Net debt.
- Interest coverage, when the required fields are available.
- Operating cash flow to net income.
- Free cash flow margin.
- Free cash flow growth, when meaningful.
- Dividend payout ratio, when relevant.

Use appropriate average balances for ratios such as ROE and ROA when the required historical balance-sheet data is available.

Document the precise formula used for each metric.

Handle zero denominators, missing values, negative earnings, and unusual financial structures safely.

For example, a negative debt-to-equity ratio caused by negative equity must not be interpreted as low debt risk.

### Financial health classification

Classify financial health using explicit rules rather than allowing the LLM to invent a rating.

Possible output values:

- STRONG.
- SOLID.
- MIXED.
- WEAK.
- INSUFFICIENT_DATA.

Define the thresholds and scoring methodology in a dedicated configuration or module.

Avoid universal thresholds that incorrectly penalize industries with different financial structures.

Where industry-aware thresholds are unavailable, label the classification as a general heuristic.

Return:

- Financial metrics.
- Historical trends.
- Strengths.
- Weaknesses.
- Missing data.
- Data quality.
- Financial health classification.
- Evidence supporting the classification.

The LLM may interpret these results but must not fabricate or independently recalculate reported figures.

---

## Agent 2: ValuationAgent

Purpose:

Estimate intrinsic value and compare it with the current market price.

Use two principal valuation approaches:

1. Discounted Cash Flow (DCF).
2. Comparable-company valuation.

The two approaches should be calculated by deterministic Python functions, with the LLM used to explain the assumptions and results.

### A. Discounted Cash Flow

Implement a DCF model using a clearly documented methodology.

For a standard enterprise-value DCF:

1. Establish the latest relevant historical cash flow.
2. Determine whether the available cash flow is suitable for forecasting.
3. Define forecast assumptions for the next five years by default.
4. Forecast free cash flow to the firm.
5. Calculate the weighted average cost of capital (WACC).
6. Estimate terminal value.
7. Discount forecast cash flows and terminal value to present value.
8. Calculate enterprise value.
9. Convert enterprise value to equity value using the appropriate debt, cash, and other relevant adjustments when data is available.
10. Divide by an appropriate share count to estimate intrinsic value per share.

Use the formula:

FCFF = EBIT × (1 − tax rate) + depreciation and amortization − capital expenditure − change in net working capital.

Only use this formula when the required inputs are available and meaningful.

If the required inputs are missing, do not silently substitute arbitrary figures.

A simplified cash-flow-based DCF may be offered only when its methodology is explicitly defined and the available data supports it.

Do not mix levered free cash flow with WACC-based enterprise valuation.

### Forecast assumptions

Support:

- Revenue growth.
- Operating margin.
- Tax rate.
- Capital expenditure.
- Working-capital assumptions.
- Discount rate.
- Terminal growth rate.
- Forecast period.

Use historical data as an input to assumption generation, not as a guarantee of future performance.

Where the system proposes an assumption, record:

- Its value.
- Its source.
- Its rationale.
- Whether it was derived from historical data, analyst input, or a model-generated estimate.

Do not represent LLM-generated assumptions as management guidance or verified analyst consensus.

Allow the user to inspect and modify assumptions before rerunning valuation.

### DCF validation

Validate the following:

- Discount rate is greater than the terminal growth rate.
- Terminal growth assumptions are reasonable relative to the selected currency and market.
- Required inputs are present.
- Units are consistent.
- Forecasts are finite.
- The terminal value is not silently treated as a guaranteed outcome.
- Negative or unstable cash flows are handled transparently.
- Share count and enterprise-to-equity adjustments are appropriate.

When the company has persistently negative or highly volatile free cash flow, clearly explain why a DCF estimate may be unreliable.

### DCF outputs

Return:

- Base-case intrinsic value per share.
- Current market price.
- Absolute difference between intrinsic value and market price.
- Upside/downside percentage.
- Enterprise value.
- Equity value, when calculable.
- WACC.
- Terminal growth rate.
- Forecast cash flows.
- Terminal value.
- Terminal value as a percentage of enterprise value.
- Key assumptions.
- Sensitivity analysis.

Calculate upside/downside using:

`(Intrinsic Value per Share / Current Market Price - 1) * 100`

Guard against invalid or zero market prices.

### Sensitivity analysis

Generate a two-dimensional valuation sensitivity table varying:

- Discount rate.
- Terminal growth rate.

Also support sensitivity to operating assumptions where practical.

Display the resulting values in a table or heatmap.

Do not allow invalid combinations in which the terminal growth rate equals or exceeds the discount rate.

### B. Comparable-company valuation

Select comparable companies based on:

- Industry.
- Business model.
- Company size.
- Geography where relevant.
- Available financial data.

Do not compare companies solely because they belong to the same broad sector.

Allow the user to override the selected peers.

Calculate available valuation multiples, including:

- Price-to-earnings.
- Price-to-sales.
- Price-to-book.
- EV/EBITDA.
- EV/revenue.

Use only ratios for which the required data is available and the calculation is meaningful.

Handle negative earnings and EBITDA appropriately.

For peer valuation:

- Show the target company's multiple.
- Show each peer's multiple.
- Show median and mean peer multiples.
- Explain the selected peer group.
- Identify excluded peers and reasons where practical.

Do not treat the peer median as inherently fair value.

If data is insufficient to establish a meaningful peer group, return an explicit limitation rather than manufacturing comparables.

### Valuation classification

Produce one of these labels:

- SIGNIFICANTLY UNDERVALUED.
- SLIGHTLY UNDERVALUED.
- FAIRLY VALUED.
- SLIGHTLY OVERVALUED.
- SIGNIFICANTLY OVERVALUED.
- INSUFFICIENT_DATA.

Define the thresholds centrally and make them configurable.

A reasonable initial configurable default is:

- More than 30% estimated upside: SIGNIFICANTLY UNDERVALUED.
- More than 10%, up to 30% upside: SLIGHTLY UNDERVALUED.
- Between -10% and +10%: FAIRLY VALUED.
- More than 10%, up to 30% downside: SLIGHTLY OVERVALUED.
- More than 30% downside: SIGNIFICANTLY OVERVALUED.

These are application heuristics, not universal financial standards.

The valuation agent must explain the result using calculated metrics and explicit assumptions.

It must not issue a valuation classification if the underlying valuation is invalid or insufficiently supported.

---

## Agent 3: RiskAgent

Purpose:

Identify financial, business, valuation, and information-quality risks.

Use financial metrics and available news as evidence.

### Risk categories

**Financial risk**

- Excessive debt.
- Weak interest coverage.
- Deteriorating liquidity.
- Negative or declining operating cash flow.
- Persistent negative free cash flow.
- Earnings that are poorly supported by cash generation.
- Deteriorating margins.
- Declining revenue.
- Weak or negative equity.

**Valuation risk**

- High valuation multiples relative to peers.
- Large dependence on terminal value.
- High sensitivity to discount-rate assumptions.
- Intrinsic-value estimates with wide uncertainty.
- A large premium to calculated intrinsic value.

**Business risk**

- Sector concentration.
- Cyclicality.
- Competitive pressure.
- Customer or supplier concentration, when supported by data.
- Regulatory exposure, when supported by credible sources.

**News and event risk**

- Earnings surprises.
- Management changes.
- Legal or regulatory developments.
- Product or operational disruptions.
- Material company announcements.

Do not assert that a company has a specific exposure unless the data supports it.

### Stress testing

Where the data permits, test scenarios such as:

- Revenue decline.
- Margin compression.
- Increased borrowing costs.
- Reduced free cash flow.
- Lower terminal growth.

Show how the scenarios affect valuation and financial resilience.

### Risk classification

Use:

- LOW.
- MODERATE.
- ELEVATED.
- HIGH.
- INSUFFICIENT_DATA.

Define explicit rules and thresholds.

Return:

- Overall risk level.
- Individual risk flags.
- Severity.
- Evidence.
- Relevant financial metrics.
- Potential financial impact.
- Assumptions and limitations.

The final risk classification must be derived from a documented methodology rather than an unconstrained LLM opinion.

---

## Agent 4: NewsAndSentimentAgent

Purpose:

Analyze recent company-related news and identify the overall news and sentiment context.

Use a configurable lookback period, such as the previous 30 days, and allow the user to change it.

Use yfinance news where available.

Design a provider abstraction so a dedicated news API can be added later.

### News retrieval

For every article, capture available information:

- Title.
- Publisher.
- Publication date.
- Original article URL.
- Source ticker or company.
- Short factual summary.
- Relevant category.
- Sentiment classification.

Avoid duplicates and irrelevant stories.

Prefer company-specific news over generic market commentary.

Distinguish:

- Company announcements.
- Earnings and financial performance.
- Analyst opinions.
- Industry developments.
- Macroeconomic news.
- Market commentary.

### Sentiment analysis

Classify sentiment as:

- STRONGLY BULLISH.
- BULLISH.
- NEUTRAL.
- BEARISH.
- STRONGLY BEARISH.
- INSUFFICIENT_DATA.

Return the reasoning and supporting article references for each material classification.

Do not assume that a positive headline necessarily implies improved fundamentals.

Distinguish reported facts from opinion.

If news access fails, disclose the failure and do not invent recent headlines.

Do not claim that the sentiment analysis predicts future stock performance.

### Outputs

Return:

- Overall news sentiment.
- Recent material developments.
- Positive catalysts.
- Negative catalysts.
- Relevant dates.
- Source links.
- Potential impact on the company's fundamentals.
- Confidence and limitations.

The report must distinguish news sentiment from the financial valuation.

For example, a stock can have bullish news sentiment while being significantly overvalued.

---

## Agent 5: ReportWriterAgent

Purpose:

Produce the final investment research report from the validated outputs of the specialist agents.

This agent should focus on synthesis and communication.

It must not:

- Invent missing metrics.
- Override calculated valuations without explanation.
- Change the risk classification without an explicit, validated rule.
- Treat sentiment as a substitute for financial performance.
- Present forecasts as reported financial results.
- Convert an insufficient-data outcome into a confident recommendation.

### Report structure

Generate the report using the following sections.

1. Executive Summary.
2. Company Overview.
3. Current Market Snapshot.
4. Financial Health.
5. Historical Financial Performance.
6. Income Statement Analysis.
7. Balance Sheet Analysis.
8. Cash Flow Analysis.
9. Key Financial Ratios.
10. DCF Valuation.
11. Comparable-Company Valuation.
12. Bull, Base, and Bear Scenarios.
13. Risk Assessment.
14. Recent News and Sentiment.
15. Key Strengths.
16. Key Weaknesses.
17. Catalysts to Monitor.
18. Overall Investment Assessment.
19. Data Quality and Confidence.
20. Sources and Methodology.

### Final assessment labels

Use the following labels:

- STRONG BUY.
- BUY.
- HOLD.
- SELL.
- STRONG SELL.
- INSUFFICIENT_DATA.

These labels must be based on a transparent, configurable rating methodology.

Do not let the LLM independently decide the rating based only on narrative reasoning.

Implement a deterministic rating engine that considers:

- Financial health.
- DCF valuation.
- Peer valuation.
- Risk.
- Data quality.

News sentiment may be included as a supplementary factor, but it should not dominate the assessment.

Keep the component scores, weights, thresholds, and missing-data rules in configuration.

Use a reasonable initial weighting scheme, for example:

- Financial health: 30%.
- Valuation: 35%.
- Risk: 25%.
- News and sentiment: 10%.

Treat these as configurable starting assumptions, not proven investment rules.

If a critical component is unavailable, do not automatically assign it a neutral score.

Instead:

- Renormalize weights only where appropriate and document the adjustment.
- Reduce the confidence rating.
- Require minimum data coverage.
- Return INSUFFICIENT_DATA when essential evidence is missing or invalid.

The report must show how the overall rating was calculated and why it may be unreliable.

### Explain the disagreement between agents

One of the most important requirements is to preserve disagreement between specialist analyses.

For example:

- ValuationAgent: SIGNIFICANTLY OVERVALUED.
- RiskAgent: ELEVATED RISK.
- NewsAndSentimentAgent: BULLISH.

The report must not force these outputs into artificial agreement