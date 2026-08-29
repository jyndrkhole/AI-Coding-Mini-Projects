"""Bonus orchestrator — Interviewer + Evaluator, not graded.

Loop:
    Interviewer picks a category
        → we pull the next unused question in that category
        → you answer
        → Evaluator (InterviewAgent, unchanged) scores it
        → Interviewer sees the updated scorecard and picks again

Nothing here is required for Asks 1–3. The Evaluator is imported as-is.
"""

from __future__ import annotations

from collections import defaultdict

from agent import InterviewAgent, ping_llm
from interview_bank import QUESTIONS
from interviewer_agent import InterviewerAgent


def _remaining(used_ids: set[str]) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for item in QUESTIONS:
        if item["id"] not in used_ids:
            counts[item["category"]] += 1
    return dict(counts)


def _next_in_category(category: str, used_ids: set[str]) -> dict | None:
    for item in QUESTIONS:
        if item["category"] == category and item["id"] not in used_ids:
            return item
    return None


def main() -> None:
    print("InterviewIQ — multi-agent (bonus, ungraded)")
    print("Interviewer picks the category; Evaluator scores the answer.\n")

    try:
        print("LLM check:", ping_llm())
    except Exception as exc:
        print("Could not reach Groq:", exc)
        return

    interviewer = InterviewerAgent()
    evaluator = InterviewAgent()
    used: set[str] = set()

    while len(used) < len(QUESTIONS):
        remaining = _remaining(used)
        category, reason = interviewer.choose_next_category(
            evaluator.history, remaining
        )
        item = _next_in_category(category, used) if category else None
        if item is None:
            print("No unused question in the chosen category — stopping.")
            break

        print("=" * 72)
        print(f"Interviewer chose [{category}] — {reason}")
        print(item["question"])
        print()
        answer = input("Your answer (or 'quit'): ").strip()
        if answer.lower() in {"quit", "exit", "q"}:
            break
        if not answer:
            print("Empty answer, skipping this pick.\n")
            continue

        print("\nEvaluator is scoring...\n")
        feedback = evaluator.evaluate_answer(
            question=item["question"],
            answer=answer,
            expected_keywords=item["keywords"],
            category=item["category"],
        )
        used.add(item["id"])
        print(feedback)
        print(f"\n(Relevance stored: {evaluator.history[-1]['relevance_score']}/100)\n")

    print("\n" + evaluator.generate_final_report())


if __name__ == "__main__":
    main()
