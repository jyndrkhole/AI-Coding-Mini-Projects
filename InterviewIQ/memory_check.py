"""Scripted mini-session that checks memory + aggregation actually work.

Flow:
  1. Score a strong behavioral answer.
  2. Score a deliberately weak technical answer (URL shortener).
  3. Score another strong answer *after* the weak one.

Then we ask "what's my weakest area?" and generate the final report.

If the agent only looked at the last turn, it would name the most recent
(strong) question. Passing means it names the URL-shortener question instead.
"""

from __future__ import annotations

import sys

from agent import InterviewAgent
from interview_bank import QUESTIONS

# Distinctive phrases we look for in the agent's reply / report.
WEAK_QUESTION = QUESTIONS[1]  # URL shortener
STRONG_FIRST = QUESTIONS[0]  # teammate conflict
STRONG_LAST = QUESTIONS[5]  # tight deadline

WEAK_MARKERS = ("url shortener", "bit.ly", "bitly")
LAST_TURN_MARKERS = ("tight deadline", "deadline")

STRONG_CONFLICT = (
    "When I was on the payments team, a teammate and I had a conflict over a hotfix. "
    "I made a point to listen, kept communication calm, and we reached a compromise. "
    "The resolution was to split the work. I asked for feedback afterwards, and the "
    "outcome was we shipped the same day with the team aligned."
)

WEAK_SHORTENER = (
    "Um, like, yeah, basically I dunno. Websites I guess. Whatever. You know."
)

STRONG_DEADLINE = (
    "We had a tight deadline to ship onboarding. I sat with the stakeholder, "
    "cut scope, prioritized the must-haves, made a plan with the team, accepted "
    "a tradeoff on polish, and we delivered on Friday."
)


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def main() -> int:
    print("InterviewIQ memory check")
    print("-" * 60)

    try:
        agent = InterviewAgent()
    except Exception as exc:
        print("FAIL: could not create the agent:", exc)
        return 1

    print("1/3  Strong answer — teammate conflict")
    agent.evaluate_answer(
        STRONG_FIRST["question"],
        STRONG_CONFLICT,
        expected_keywords=STRONG_FIRST["keywords"],
        category=STRONG_FIRST["category"],
    )
    print(f"      stored score: {agent.history[-1]['relevance_score']}")

    print("2/3  Weak answer   — URL shortener (deliberately bad)")
    agent.evaluate_answer(
        WEAK_QUESTION["question"],
        WEAK_SHORTENER,
        expected_keywords=WEAK_QUESTION["keywords"],
        category=WEAK_QUESTION["category"],
    )
    print(f"      stored score: {agent.history[-1]['relevance_score']}")

    print("3/3  Strong answer — tight deadline (this is the LAST turn)")
    agent.evaluate_answer(
        STRONG_LAST["question"],
        STRONG_DEADLINE,
        expected_keywords=STRONG_LAST["keywords"],
        category=STRONG_LAST["category"],
    )
    print(f"      stored score: {agent.history[-1]['relevance_score']}")

    scores = [t["relevance_score"] for t in agent.history]
    print(f"\nStored scores in order: {scores}")
    if not (scores[1] < scores[0] and scores[1] < scores[2]):
        print(
            "FAIL: the weak answer did not receive the lowest relevance score. "
            "Check score_relevance — it should be near 0 for an answer with no keywords."
        )
        return 1

    print('\nAsking: "What\'s my weakest area so far?"')
    reply = agent.ask_agent("What's my weakest area so far?")
    print("\n--- ask_agent reply ---")
    print(reply)
    print("-----------------------\n")

    report = agent.generate_final_report()
    print("--- generate_final_report ---")
    print(report)
    print("-----------------------------\n")

    combined = reply + "\n" + report
    named_weak = _contains_any(combined, WEAK_MARKERS)
    named_last = _contains_any(reply, LAST_TURN_MARKERS) and not named_weak

    if named_last:
        print(
            "FAIL: the agent named the most recent (strong) question as the "
            "weakest area. Memory is only looking at the last turn."
        )
        return 1

    if not named_weak:
        print(
            "FAIL: neither ask_agent nor the final report named the URL "
            "shortener question as the weakest area."
        )
        return 1

    # The report itself must do real aggregation, not just a recap.
    report_l = report.lower()
    if "average" not in report_l or "weakest" not in report_l:
        print(
            "FAIL: generate_final_report must include an average relevance "
            "score and a named weakest area."
        )
        return 1

    print(
        "PASS: weakest area is the URL-shortener question, not the last turn. "
        "Session memory and aggregation are working."
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
