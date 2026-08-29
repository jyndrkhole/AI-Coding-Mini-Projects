"""CLI runner — handy for testing the agent in the terminal before the UI.

Walks through every question in interview_bank.py. After each answer you can
ask a meta-question (or press Enter to skip). Type `quit` to stop early.
"""

from interview_bank import QUESTIONS
from agent import InterviewAgent, ping_llm


def main() -> None:
    print("InterviewIQ — CLI")
    print("Checking the LLM connection (no tools yet)...")
    try:
        print(" ", ping_llm())
    except Exception as exc:
        print("Could not reach Groq:", exc)
        print("Copy .env.example to .env and add your GROQ_API_KEY.")
        return

    agent = InterviewAgent()
    print(f"\n{len(QUESTIONS)} questions. Type 'quit' to stop.\n")

    for i, item in enumerate(QUESTIONS, start=1):
        print("=" * 72)
        print(f"Q{i}/{len(QUESTIONS)}  [{item['category']}]")
        print(item["question"])
        print()
        answer = input("Your answer: ").strip()
        if answer.lower() in {"quit", "exit", "q"}:
            break
        if not answer:
            print("(skipped — empty answer)\n")
            continue

        print("\nEvaluating...\n")
        feedback = agent.evaluate_answer(
            question=item["question"],
            answer=answer,
            expected_keywords=item["keywords"],
            category=item["category"],
            question_number=i,
            question_id=item["id"],
        )
        print(feedback)
        print()
        meta = input("Ask the coach anything (or Enter to continue): ").strip()
        if meta:
            print("\n" + agent.ask_agent(meta) + "\n")

    print("\n" + agent.generate_final_report())


if __name__ == "__main__":
    main()
