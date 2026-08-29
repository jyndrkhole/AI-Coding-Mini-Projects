"""Sample interview questions plus the keywords each answer is expected to cover.

Add, remove, or edit entries — the rest of the project reads this list as-is.
Each item:
    question  – the prompt shown to the candidate
    category  – used by the optional Interviewer agent (behavioral / technical / system_design)
    keywords  – concepts `score_relevance` looks for in the answer
"""

QUESTIONS = [
    {
        "id": "q1",
        "category": "behavioral",
        "question": "Tell me about a time you had a conflict with a teammate. How did you handle it?",
        "keywords": [
            "conflict",
            "team",
            "listen",
            "communication",
            "compromise",
            "resolution",
            "feedback",
            "outcome",
        ],
    },
    {
        "id": "q2",
        "category": "technical",
        "question": "How would you design a URL shortener like bit.ly?",
        "keywords": [
            "hash",
            "database",
            "redirect",
            "unique",
            "scale",
            "cache",
            "api",
            "collision",
        ],
    },
    {
        "id": "q3",
        "category": "behavioral",
        "question": "Describe a time you failed. What did you learn from it?",
        "keywords": [
            "failure",
            "mistake",
            "learned",
            "improve",
            "responsibility",
            "action",
            "result",
            "change",
        ],
    },
    {
        "id": "q4",
        "category": "technical",
        "question": "Walk me through how you would debug a slow API endpoint in production.",
        "keywords": [
            "logs",
            "latency",
            "profiling",
            "database",
            "query",
            "cache",
            "metrics",
            "bottleneck",
        ],
    },
    {
        "id": "q5",
        "category": "system_design",
        "question": "How would you design a real-time chat system for millions of users?",
        "keywords": [
            "websocket",
            "message",
            "queue",
            "scale",
            "fanout",
            "presence",
            "database",
            "delivery",
        ],
    },
    {
        "id": "q6",
        "category": "behavioral",
        "question": "Tell me about a project you led under a tight deadline. What did you do to ship on time?",
        "keywords": [
            "deadline",
            "prioritize",
            "scope",
            "team",
            "plan",
            "tradeoff",
            "delivered",
            "stakeholder",
        ],
    },
]


def get_question(index: int) -> dict:
    """Return the question dict at `index`, wrapping around the bank."""
    return QUESTIONS[index % len(QUESTIONS)]


def questions_by_category(category: str) -> list[dict]:
    """Return every question whose category matches (case-insensitive)."""
    wanted = category.strip().lower()
    return [q for q in QUESTIONS if q["category"].lower() == wanted]
