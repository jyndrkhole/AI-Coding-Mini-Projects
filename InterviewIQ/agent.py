"""Tool-calling evaluator agent with session memory.

The agent:
  1. Reads a candidate answer.
  2. Lets the LLM pick which evaluation tools to call.
  3. Turns tool results into short, encouraging feedback.
  4. Remembers every turn so it can answer "how am I doing?" mid-session
     and produce a report that names the weakest area — not a flat recap.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv
from openai import APIError, BadRequestError, OpenAI

from tools import (
    TOOL_DEFINITIONS,
    check_star_structure,
    detect_filler_words,
    run_tool,
    score_relevance,
)
from interview_bank import QUESTIONS

load_dotenv(Path(__file__).resolve().parent / ".env")

# Groq retired llama-3.1-8b-instant / llama-3.3-70b-versatile on 2026-08-16.
# gpt-oss-20b is the documented free-tier replacement and supports tool calling.
DEFAULT_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
MAX_TOOL_ROUNDS = 4

SYSTEM_PROMPT = """You are InterviewIQ, a supportive mock-interview coach.

You have three evaluation tools. For every candidate answer:
- Always call score_relevance (pass the expected_keywords you were given).
- Always call detect_filler_words.
- Call check_star_structure for behavioral / storytelling questions.
  Skip STAR for purely technical or system-design questions.

After the tools return, write short, encouraging feedback (about 4–8 sentences):
- First line: name the interview question you just scored (quote it).
- Lead with what worked.
- Mention the relevance score and any missing concepts.
- If STAR was used, say which parts were present or missing.
- If fillers showed up, mention them gently.
- End with one concrete thing to try next time.

Do not invent scores — only use numbers the tools returned.
Do not mix this question up with a previous one.

When calling a tool, keep arguments tiny, valid JSON. Pass "answer" as
the short string "from_user_message" — never paste the candidate's full
answer into tool arguments (the runtime already has it).
"""

META_SYSTEM_PROMPT = """You are InterviewIQ answering a question about the candidate's
session so far. You are given a factual session summary that already includes
the average relevance score and the named weakest area.

Rules:
- Base your answer only on that summary. Do not invent scores or questions.
- If they ask for the weakest area, name the exact question from the summary.
- If they ask how accurate / how they did on "my answer", name the most
  recently scored question in full and talk about that one — never a question
  they have not answered yet.
- Be concise and encouraging. 3–6 sentences is enough.
"""


def _message_to_dict(message) -> dict:
    """Turn a ChatCompletion message into a plain dict the next request accepts."""
    payload: dict = {"role": message.role, "content": message.content}
    if message.tool_calls:
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments or "{}",
                },
            }
            for call in message.tool_calls
        ]
    return payload


def _client() -> OpenAI:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key or api_key == "your_groq_api_key_here":
        raise RuntimeError(
            "GROQ_API_KEY is missing. Copy .env.example to .env and paste a "
            "key from https://console.groq.com"
        )
    return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")


def ping_llm(prompt: str = "Reply with exactly: InterviewIQ is ready.") -> str:
    """One plain completion with no tools — use this to verify the API key."""
    response = _client().chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=64,
    )
    return (response.choices[0].message.content or "").strip()


def _bank_meta(
    question: str,
    question_number: int | None = None,
    question_id: str | None = None,
) -> tuple[int | None, str | None]:
    """Map a prompt to its 1-based bank number (Q1…Q6) and id."""
    if question_number is not None and question_id:
        return int(question_number), question_id
    for i, item in enumerate(QUESTIONS, start=1):
        if item["question"] == question:
            return i, item["id"]
    return None, None


class InterviewAgent:
    """Evaluator agent: tool calling + session memory + aggregation."""

    def __init__(self, model: str | None = None):
        self.model = model or DEFAULT_MODEL
        self.client = _client()
        # Every evaluated turn lands here. ask_agent / generate_final_report
        # read this list — never just the last message.
        self.history: list[dict] = []
        self._current_answer = ""
        self._current_keywords: list[str] = []

    # ------------------------------------------------------------------
    # Public API used by main.py, memory_check.py, and app.py
    # ------------------------------------------------------------------

    def evaluate_answer(
        self,
        question: str,
        answer: str,
        expected_keywords: list[str] | None = None,
        category: str | None = None,
        question_number: int | None = None,
        question_id: str | None = None,
    ) -> str:
        """Run tools on one answer, store the turn, return coach feedback."""
        keywords = list(expected_keywords or [])
        self._current_answer = answer
        self._current_keywords = keywords

        user_blob = (
            f"Interview question: {question}\n"
            f"Question category: {category or 'unspecified'}\n"
            f"Expected keywords: {json.dumps(keywords)}\n\n"
            f"Candidate's answer:\n{answer}"
        )
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_blob},
        ]

        tool_results: dict[str, dict] = {}
        feedback = ""

        # Long pasted answers often make the model emit invalid tool JSON
        # (Groq then returns 400 tool_use_failed). Score those locally.
        use_local_tools = len(answer) > 1500
        if not use_local_tools:
            try:
                for _ in range(MAX_TOOL_ROUNDS):
                    response = self.client.chat.completions.create(
                        model=self.model,
                        messages=messages,
                        tools=TOOL_DEFINITIONS,
                        tool_choice="auto",
                        temperature=0.3,
                    )
                    message = response.choices[0].message
                    messages.append(_message_to_dict(message))

                    if not message.tool_calls:
                        feedback = (message.content or "").strip()
                        break

                    for call in message.tool_calls:
                        result = self._run_named_tool(
                            call.function.name, call.function.arguments
                        )
                        tool_results[call.function.name] = result
                        messages.append(
                            {
                                "role": "tool",
                                "tool_call_id": call.id,
                                "name": call.function.name,
                                "content": json.dumps(result),
                            }
                        )
            except (BadRequestError, APIError):
                use_local_tools = True
                tool_results = {}
                feedback = ""

        if use_local_tools or "score_relevance" not in tool_results:
            tool_results.update(
                self._run_required_tools(answer, keywords, category)
            )
        if use_local_tools and not feedback:
            feedback = self._write_feedback(question, category, tool_results)

        # Guarantee we always have a relevance number in memory, even if the
        # model skipped the tool — otherwise weakest-area aggregation breaks.
        if "score_relevance" not in tool_results:
            tool_results["score_relevance"] = score_relevance(answer, keywords)

        relevance = int(tool_results["score_relevance"].get("score", 0))
        qnum, qid = _bank_meta(question, question_number, question_id)
        self.history.append(
            {
                "question": question,
                "answer": answer,
                "category": category,
                "keywords": keywords,
                "tool_results": tool_results,
                "relevance_score": relevance,
                "feedback": feedback,
                "question_number": qnum,
                "question_id": qid,
            }
        )
        return feedback or self._fallback_feedback(tool_results)

    def ask_agent(self, user_question: str) -> str:
        """Answer a meta-question using the *whole* session, not just last turn."""
        summary = self._session_summary()
        if not self.history:
            return (
                "You haven't answered any questions yet, so there's nothing "
                "for me to review. Submit an answer first, then ask again."
            )

        messages = [
            {"role": "system", "content": META_SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Session summary (facts — treat as ground truth):\n{summary}\n\n"
                    f"Candidate's question: {user_question}"
                ),
            },
        ]
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=400,
            )
            reply = (response.choices[0].message.content or "").strip()
        except (BadRequestError, APIError, OSError):
            return summary
        # If the model wanders, still surface the weakest-area fact.
        weakest = self._weakest_turn()
        if weakest and weakest["question"].lower() not in reply.lower():
            if any(
                word in user_question.lower()
                for word in ("weak", "worst", "lowest", "struggling")
            ):
                reply = (
                    f"Your weakest area so far is: {weakest['question']} "
                    f"(relevance {weakest['relevance_score']}/100).\n\n{reply}"
                )
        return reply or summary

    @staticmethod
    def _format_fillers(turn: dict) -> str:
        """Human-readable filler list, e.g. 'like×2, um×1' or 'none'."""
        result = turn.get("tool_results", {}).get("detect_filler_words") or {}
        found = result.get("fillers_found") or {}
        if not found:
            return "none"
        parts = [f"{word}×{count}" if count != 1 else word for word, count in found.items()]
        total = result.get("filler_count", sum(found.values()))
        return f"{total} ({', '.join(parts)})"

    def generate_final_report(self) -> str:
        """Aggregate the session: average relevance + named weakest area."""
        if not self.history:
            return "No answers recorded yet. Complete at least one question first."

        scores = [turn["relevance_score"] for turn in self.history]
        avg = mean(scores)
        weakest = self._weakest_turn()
        strongest = max(self.history, key=lambda t: t["relevance_score"])

        unique = len({self._question_key(t) for t in self.history})
        lines = [
            "=== InterviewIQ — Final Report ===",
            (
                f"Unique questions: {unique}  ·  "
                f"Evaluations: {len(self.history)}"
            ),
            f"Average relevance score: {avg:.1f}/100",
            (
                f"Weakest area: {weakest['question']} "
                f"(relevance {weakest['relevance_score']}/100)"
            ),
            (
                f"Strongest answer: {strongest['question']} "
                f"(relevance {strongest['relevance_score']}/100)"
            ),
            "",
            "Per-question scores:",
        ]
        for i, turn in enumerate(self.history):
            fillers = self._format_fillers(turn)
            star = turn["tool_results"].get("check_star_structure")
            star_note = (
                f"STAR {star.get('coverage', 0):.0%}" if star else "STAR n/a"
            )
            lines.append(
                f"  {self._turn_code(i)}  [{turn['relevance_score']}/100] {star_note}, "
                f"fillers={fillers} — {turn['question']}"
            )

        lines.extend(
            [
                "",
                "Coaching note: spend your next practice round on the weakest "
                "area above. Cover the missing keywords and, if it was a "
                "behavioral question, hit Situation / Task / Action / Result "
                "explicitly.",
            ]
        )
        return "\n".join(lines)

    def scorecard_rows(self) -> list[list[str]]:
        """Rows for the live scorecard table in the Gradio UI."""
        rows = []
        for i, turn in enumerate(self.history):
            star = turn["tool_results"].get("check_star_structure")
            if star:
                missing = star.get("missing") or []
                star_cell = (
                    "Complete" if not missing else "Missing: " + ", ".join(missing)
                )
            else:
                star_cell = "n/a"
            rows.append(
                [
                    self._turn_code(i),
                    turn["question"],
                    str(turn["relevance_score"]),
                    star_cell,
                    self._format_fillers(turn),
                ]
            )
        return rows

    def scorecard_markdown(self) -> str:
        """Full scorecard as markdown so every row is visible without expanding."""
        if not self.history:
            return "_No questions scored yet._"
        lines = [
            "| ID | Question | Relevance | STAR | Fillers |",
            "| --- | --- | ---: | --- | --- |",
        ]
        for row in self.scorecard_rows():
            cells = [str(c).replace("|", "/").replace("\n", " ") for c in row]
            lines.append("| " + " | ".join(cells) + " |")
        return "\n".join(lines)

    def previous_answers_text(self) -> str:
        """Full question + answer text for every stored turn (for the UI)."""
        if not self.history:
            return "No answers stored yet. Submit a question to start the session log."
        blocks = []
        for i, turn in enumerate(self.history):
            blocks.append(
                f"{self._turn_code(i)}  ·  {turn['relevance_score']}/100\n"
                f"Question: {turn['question']}\n"
                f"Fillers: {self._format_fillers(turn)}\n\n"
                f"Your answer:\n{turn['answer']}"
            )
        return "\n\n----------\n\n".join(blocks)

    def reset(self) -> None:
        self.history.clear()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    @staticmethod
    def _question_key(turn: dict) -> str:
        return str(turn.get("question_id") or turn["question"])

    def _turn_code(self, index: int) -> str:
        """Stable bank id, with .2 / .3 for extra submits of the same question."""
        turn = self.history[index]
        key = self._question_key(turn)
        attempt = sum(
            1 for t in self.history[: index + 1] if self._question_key(t) == key
        )
        n = turn.get("question_number")
        if n is None:
            return f"#{index + 1}" if attempt == 1 else f"#{index + 1}.{attempt}"
        if attempt == 1:
            return f"Q{n}"
        return f"Q{n}.{attempt}"

    def _run_named_tool(self, name: str, raw_arguments: str | dict) -> dict:
        if isinstance(raw_arguments, dict):
            arguments = dict(raw_arguments)
        else:
            try:
                arguments = json.loads(raw_arguments or "{}")
            except json.JSONDecodeError:
                arguments = {}
        # Don't trust the model to pass the answer/keywords correctly.
        arguments.setdefault("answer", self._current_answer)
        if name == "score_relevance" and not arguments.get("expected_keywords"):
            arguments["expected_keywords"] = self._current_keywords
        # Model sometimes dumps the whole essay into arguments; always use ours.
        if arguments.get("answer") in {"", "from_user_message"} or (
            isinstance(arguments.get("answer"), str)
            and len(arguments.get("answer", "")) > len(self._current_answer)
        ):
            arguments["answer"] = self._current_answer
        return run_tool(name, arguments)

    def _run_required_tools(
        self,
        answer: str,
        keywords: list[str],
        category: str | None,
    ) -> dict:
        """Run the rule-based tools without asking the model to emit JSON."""
        results = {
            "detect_filler_words": detect_filler_words(answer),
            "score_relevance": score_relevance(answer, keywords),
        }
        cat = (category or "").strip().lower()
        if cat in {"", "behavioral", "unspecified"}:
            results["check_star_structure"] = check_star_structure(answer)
        return results

    def _write_feedback(
        self,
        question: str,
        category: str | None,
        tool_results: dict,
    ) -> str:
        """Ask the model for coach copy from tool JSON — no tool calling."""
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "Write short encouraging interview feedback (4–8 sentences). "
                            "Quote the question in the first line. Use only the tool "
                            "results below — do not invent scores."
                        ),
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "question": question,
                                "category": category,
                                "tool_results": tool_results,
                            }
                        ),
                    },
                ],
                temperature=0.3,
                max_tokens=500,
            )
            text = (response.choices[0].message.content or "").strip()
            if text:
                return text
        except (BadRequestError, APIError, OSError):
            pass
        return self._fallback_feedback(tool_results)

    def _weakest_turn(self) -> dict | None:
        if not self.history:
            return None
        return min(self.history, key=lambda t: t["relevance_score"])

    def _session_summary(self) -> str:
        if not self.history:
            return "No answers yet."
        scores = [t["relevance_score"] for t in self.history]
        weakest = self._weakest_turn()
        unique = len({self._question_key(t) for t in self.history})
        lines = [
            f"Unique questions: {unique}  ·  Evaluations: {len(self.history)}",
            f"Average relevance score: {mean(scores):.1f}/100",
            (
                f"Weakest area: {weakest['question']} "
                f"(relevance {weakest['relevance_score']}/100)"
            ),
            "",
            "Turns in chronological order:",
        ]
        for i, turn in enumerate(self.history):
            tools = ", ".join(turn["tool_results"].keys()) or "none"
            lines.append(
                f"{self._turn_code(i)} score={turn['relevance_score']} tools=[{tools}] "
                f"Q: {turn['question']}"
            )
            matched = (
                turn["tool_results"]
                .get("score_relevance", {})
                .get("matched_keywords", [])
            )
            missing = (
                turn["tool_results"]
                .get("score_relevance", {})
                .get("missing_keywords", [])
            )
            lines.append(f"   matched={matched} missing={missing}")
        return "\n".join(lines)

    def _fallback_feedback(self, tool_results: dict) -> str:
        rel = tool_results.get("score_relevance", {})
        score = rel.get("score", 0)
        missing = rel.get("missing_keywords") or []
        fillers = tool_results.get("detect_filler_words", {})
        star = tool_results.get("check_star_structure")
        parts = [f"Relevance score: {score}/100."]
        if missing:
            parts.append("Concepts still to cover: " + ", ".join(missing) + ".")
        else:
            parts.append("You hit the expected concepts — nice.")
        if fillers:
            parts.append(fillers.get("comment", ""))
        if star:
            if star.get("is_complete"):
                parts.append("STAR structure looks complete.")
            else:
                parts.append(
                    "STAR pieces still missing: " + ", ".join(star.get("missing") or []) + "."
                )
        parts.append("Try one more pass focusing on the gaps above — you've got this.")
        return " ".join(p for p in parts if p)
