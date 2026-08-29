"""Rule-based evaluation tools. Each function returns a structured dict.

These are ordinary Python functions. The agent decides when to call them;
they do not talk to an LLM themselves.
"""

from __future__ import annotations

import re
from collections import Counter

# Word-level fillers. Multi-word phrases are matched separately so "you know"
# is counted as one filler, not two leftover words.
FILLER_WORDS = {
    "um",
    "uh",
    "umm",
    "uhh",
    "er",
    "ah",
    "like",
    "basically",
    "literally",
    "actually",
    "kinda",
    "gonna",
    "wanna",
    "yeah",
    "right",
}
FILLER_PHRASES = ("you know", "i mean", "sort of", "kind of")

# Cue phrases that suggest a STAR component is present. Matching is
# case-insensitive and looks for the phrase as a substring of the answer.
STAR_CUES = {
    "situation": [
        "situation",
        "context",
        "background",
        "at the time",
        "our team",
        "the project",
        "the company",
        "we were",
        "when i",
        "while working",
        "in my role",
        "previously",
    ],
    "task": [
        "task",
        "responsible",
        "my job",
        "i needed",
        "had to",
        "goal was",
        "objective",
        "assigned",
        "expected to",
        "the challenge",
        "problem was",
        "requirement",
    ],
    "action": [
        "i implemented",
        "i built",
        "i created",
        "i led",
        "i decided",
        "i worked",
        "i reached out",
        "i organized",
        "i stepped",
        "i proposed",
        "i changed",
        "steps i took",
        "what i did",
        "i took",
        "action i",
    ],
    "result": [
        "result",
        "outcome",
        "impact",
        "as a result",
        "ended up",
        "we shipped",
        "increased",
        "decreased",
        "reduced",
        "improved",
        "learned",
        "percent",
        "%",
        "successfully",
        "the effect",
    ],
}


def _tokenize(text: str) -> list[str]:
    """Lowercase word tokens, keeping apostrophes inside words (I'm, don't)."""
    return re.findall(r"[a-z]+(?:'[a-z]+)?", text.lower())


def detect_filler_words(answer: str) -> dict:
    """Flag common filler words and phrases in `answer`.

    Returns:
        filler_count  – total occurrences
        fillers_found – {word: count} for everything that matched
        density       – fillers per 100 words (0 if the answer is empty)
        comment       – a short human-readable note
    """
    if not answer or not answer.strip():
        return {
            "filler_count": 0,
            "fillers_found": {},
            "density": 0.0,
            "comment": "Empty answer — nothing to scan.",
        }

    lowered = " " + answer.lower() + " "
    found: Counter[str] = Counter()

    for phrase in FILLER_PHRASES:
        # Count non-overlapping occurrences of the whole phrase.
        count = len(re.findall(rf"\b{re.escape(phrase)}\b", lowered))
        if count:
            found[phrase] += count
            # Blank out matched phrases so leftover words aren't double-counted.
            lowered = re.sub(rf"\b{re.escape(phrase)}\b", " ", lowered)

    tokens = _tokenize(lowered)
    for token in tokens:
        if token in FILLER_WORDS:
            found[token] += 1

    total_words = max(len(_tokenize(answer)), 1)
    filler_count = int(sum(found.values()))
    density = round(100.0 * filler_count / total_words, 1)

    if filler_count == 0:
        comment = "No common filler words detected. Clean delivery."
    elif density < 5:
        comment = "A few fillers — easy to tighten with a pause instead of a hedge."
    else:
        comment = "Quite a few fillers. Slow down and replace them with a short pause."

    return {
        "filler_count": filler_count,
        "fillers_found": dict(found),
        "density": density,
        "comment": comment,
    }


def check_star_structure(answer: str) -> dict:
    """Check whether a behavioral answer covers Situation, Task, Action, Result.

    Returns:
        present       – components that look covered
        missing       – components with no cue phrases
        coverage      – fraction of the four components found (0.0–1.0)
        matched_cues  – which cue phrases fired, for debugging / feedback
        is_complete   – True only when all four are present
    """
    if not answer or not answer.strip():
        return {
            "present": [],
            "missing": ["situation", "task", "action", "result"],
            "coverage": 0.0,
            "matched_cues": {},
            "is_complete": False,
        }

    text = answer.lower()
    present: list[str] = []
    missing: list[str] = []
    matched_cues: dict[str, list[str]] = {}

    for component, cues in STAR_CUES.items():
        hits = [cue for cue in cues if cue in text]
        # First-person action is a strong Action signal even without a canned phrase.
        if component == "action" and re.search(r"\bi\s+\w+", text):
            hits.append("first-person action (I + verb)")
        if hits:
            present.append(component)
            matched_cues[component] = hits
        else:
            missing.append(component)

    coverage = round(len(present) / 4.0, 2)
    return {
        "present": present,
        "missing": missing,
        "coverage": coverage,
        "matched_cues": matched_cues,
        "is_complete": len(missing) == 0,
    }


def score_relevance(answer: str, expected_keywords: list[str] | None = None) -> dict:
    """Score (0–100) how many expected keywords/concepts appear in the answer.

    Matching is case-insensitive. A keyword matches if it appears as a whole
    word or as a substring of a token (so "scale" matches "scalable").

    Returns:
        score             – 0–100
        matched_keywords  – keywords found
        missing_keywords  – keywords not found
        total_expected    – how many we looked for
    """
    keywords = [k.strip() for k in (expected_keywords or []) if k and k.strip()]
    if not keywords:
        return {
            "score": 0,
            "matched_keywords": [],
            "missing_keywords": [],
            "total_expected": 0,
        }

    text = (answer or "").lower()
    tokens = set(_tokenize(text))
    matched: list[str] = []
    missing: list[str] = []

    for raw in keywords:
        key = raw.lower()
        whole_word = bool(re.search(rf"\b{re.escape(key)}\b", text))
        prefix = any(token.startswith(key) or key in token for token in tokens)
        if whole_word or prefix:
            matched.append(raw)
        else:
            missing.append(raw)

    score = int(round(100.0 * len(matched) / len(keywords)))
    return {
        "score": score,
        "matched_keywords": matched,
        "missing_keywords": missing,
        "total_expected": len(keywords),
    }


# OpenAI-style tool menu the agent sends to the model. Keep this next to the
# functions so the names/schemas cannot drift apart.
TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "detect_filler_words",
            "description": (
                "Count filler words (um, like, basically, you know, …) in the "
                "candidate's answer. Use this on every spoken/written answer."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "The candidate's full answer text.",
                    }
                },
                "required": ["answer"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_star_structure",
            "description": (
                "Check whether a behavioral answer covers Situation, Task, "
                "Action, and Result. Prefer this for behavioral / storytelling "
                "questions; skip it for purely technical design questions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "The candidate's full answer text.",
                    }
                },
                "required": ["answer"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "score_relevance",
            "description": (
                "Score 0–100 how many expected keywords/concepts for this "
                "question appear in the answer. Always call this so the "
                "scorecard and weakest-area report have a number to use."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "The candidate's full answer text.",
                    },
                    "expected_keywords": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Keywords/concepts the answer should cover.",
                    },
                },
                "required": ["answer", "expected_keywords"],
            },
        },
    },
]


def run_tool(name: str, arguments: dict) -> dict:
    """Dispatch a tool call by name. Used by the agent loop."""
    if name == "detect_filler_words":
        return detect_filler_words(arguments.get("answer", ""))
    if name == "check_star_structure":
        return check_star_structure(arguments.get("answer", ""))
    if name == "score_relevance":
        return score_relevance(
            arguments.get("answer", ""),
            arguments.get("expected_keywords") or [],
        )
    return {"error": f"Unknown tool: {name}"}


if __name__ == "__main__":
    sample = (
        "Um, so like, basically when I was on the payments team the situation "
        "was a failing nightly job. I needed to keep checkout working. I built "
        "a retry queue and as a result latency dropped 40 percent."
    )
    print("detect_filler_words:", detect_filler_words(sample))
    print("check_star_structure:", check_star_structure(sample))
    print(
        "score_relevance:",
        score_relevance(sample, ["team", "queue", "latency", "cache", "database"]),
    )
