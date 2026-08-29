# InterviewIQ -- Starter Kit

## Setup
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env            # then paste your GROQ_API_KEY inside
```
Get a free Groq key at https://console.groq.com

## What to do
Read `Problem_Statement_and_Milestones.md` for the full problem statement and the asks.

```bash
# 1. Confirm the three tools work with no API key
python tools.py

# 2. CLI walkthrough (needs GROQ_API_KEY)
python main.py

# 3. Memory / aggregation check — must name the weak question, not the last turn
python memory_check.py

# 4. Browser UI (the demo)
python app.py

# 5. Optional, ungraded two-agent loop
python run_multi_agent.py
```

## Files
| File | What it is |
|---|---|
| `interview_bank.py` | Sample interview questions + expected keywords. Add your own if you like. |
| `tools.py` | Three rule-based evaluators: fillers, STAR, relevance. Each returns a dict. |
| `agent.py` | Tool-calling evaluator, session memory, weakest-area report, `ask_agent`. |
| `app.py` | Gradio UI — required demo surface. |
| `main.py` | CLI runner for terminal testing. |
| `memory_check.py` | Scripted mini-session that fails if memory is last-turn-only. |
| `requirements.txt` | `openai`, `python-dotenv`, `gradio`. |
| `.env.example` | Copy to `.env` and add your API key. Never commit the real `.env`. |
| `.gitignore` | Keeps your venv, `.env`, and cache files out of git. |
| `interviewer_agent.py`, `run_multi_agent.py` | Optional bonus (ungraded) — Interviewer picks the next category; Evaluator from Asks 1–3 is unchanged. |
