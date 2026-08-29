"""Bonus Interviewer agent — not graded, given fully worked.

Class 6 only introduced the *vocabulary* of an orchestrator coordinating
specialized agents. This file is a small, complete example of that idea:

    The Interviewer's only job is to look at how the candidate has done so
    far and pick the *category* of the next question. It does not evaluate
    answers. Evaluation stays entirely in InterviewAgent (Asks 1–3), which
    this file does not modify.

Run it via:  python run_multi_agent.py
"""

from __future__ import annotations

import json
import os
from collections import defaultdict

from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv(Path(__file__).resolve().parent / ".env")

DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")

CATEGORIES = ("behavioral", "technical", "system_design")

SYSTEM_PROMPT = """You pick the next mock-interview question category.

You will be given:
- which categories exist
- which categories still have unused questions
- a scorecard of answers so far (category + relevance score)

Choose ONE category from the unused list using this policy:
1. If nothing has been answered yet, start with behavioral.
2. If a category has a relevance score under 50 and still has unused questions,
   stay there so the candidate can try again in the weak area.
3. Otherwise rotate toward a category they have practiced less.
4. Never pick a category with zero unused questions.

Reply with JSON only, no markdown:
{"category": "<one of the unused categories>", "reason": "<one sentence>"}
"""


class InterviewerAgent:
    """Specialized agent: next-category picker. No evaluation, no memory of answers
    beyond the scorecard the orchestrator hands it."""

    def __init__(self, model: str | None = None):
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key or api_key == "your_groq_api_key_here":
            raise RuntimeError("GROQ_API_KEY is missing. See .env.example.")
        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.groq.com/openai/v1",
        )
        self.model = model or DEFAULT_MODEL

    def choose_next_category(
        self,
        history: list[dict],
        remaining_by_category: dict[str, int],
    ) -> tuple[str, str]:
        """Return (category, reason). Falls back to a deterministic pick if the
        model returns something unusable."""
        unused = [c for c, n in remaining_by_category.items() if n > 0]
        if not unused:
            return "", "No questions left in the bank."

        fallback = self._heuristic(history, unused)
        payload = {
            "available_categories": list(CATEGORIES),
            "unused_categories": unused,
            "remaining_by_category": remaining_by_category,
            "scorecard": [
                {
                    "category": turn.get("category"),
                    "relevance_score": turn.get("relevance_score"),
                    "question": turn.get("question"),
                }
                for turn in history
            ],
        }

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(payload, indent=2)},
                ],
                temperature=0.2,
                max_tokens=200,
            )
            raw = (response.choices[0].message.content or "").strip()
            data = _parse_json(raw)
            category = str(data.get("category", "")).strip().lower()
            reason = str(data.get("reason", "")).strip()
            if category in unused:
                return category, reason or fallback[1]
        except Exception:
            pass

        return fallback

    def _heuristic(
        self, history: list[dict], unused: list[str]
    ) -> tuple[str, str]:
        if not history:
            pick = "behavioral" if "behavioral" in unused else unused[0]
            return pick, "Opening with a behavioral question to warm up."

        weak = [
            t
            for t in history
            if t.get("relevance_score", 100) < 50
            and t.get("category") in unused
        ]
        if weak:
            cat = weak[-1]["category"]
            return cat, f"Staying on {cat} because the last attempt scored under 50."

        counts: dict[str, int] = defaultdict(int)
        for turn in history:
            cat = turn.get("category")
            if cat:
                counts[cat] += 1
        pick = min(unused, key=lambda c: counts[c])
        return pick, f"Rotating to {pick}, which has been practiced least."


def _parse_json(raw: str) -> dict:
    start = raw.find("{")
    end = raw.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        data = json.loads(raw[start : end + 1])
        return data if isinstance(data, dict) else {}
    except json.JSONDecodeError:
        return {}
