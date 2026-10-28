# AI Interview Readiness Bootcamp

Lecture code for the Scaler AI Interview Readiness Bootcamp. Each day is its own folder so later sessions can be added without moving Day 1.

```
AI Interview Readiness Bootcamp/
  .env           shared keys (not committed)
  Day 1/         LangChain labs, plus Strands agents on Bedrock and Groq
  Day 2/         Finance Analyser and NPS Analyst
  Day 3/         upcoming
  Day 4/         upcoming
  Day 5/         upcoming
  Day 6/         upcoming
  Day 7/         upcoming
  Day 8/         upcoming
```

## Day 1

- `section1` and `section2` — LangChain prompt templates, chains, and a first tool-using agent
- `section-01` through `section-07` — Strands agents, tools, memory, multi-agent patterns, MCP, deployment, and evals

The LangChain scripts call Groq. The Strands labs include Bedrock scripts and `_groq` twins. Copy `.env.example` to `.env` in this folder (next to `Day 1`) and add your keys. `.env` is gitignored. See `Day 1/README.md` for setup.

## Day 2

- `Finance Analyser` — fundamental health, DCF, and a rating for any public ticker. The numbers are calculated in Python. A model is optional commentary only.
- `NPS Analyst` — leadership brief for a bank survey: NPS, themes, revenue exposure, and callback recommendations. Scores are never rewritten by a model.

Each project has its own README for setup. Copy that project's `.env.example` to `.env` inside the project if you want optional model commentary. Neither app needs a key to compute its figures.
