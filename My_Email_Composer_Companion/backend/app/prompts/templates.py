"""Built-in prompt templates and system prompts for email generation."""

from typing import Optional

REPLY_STYLES = [
    "Formal",
    "Friendly",
    "Executive",
    "Technical",
    "Sales",
    "Architecture Review",
    "Escalation",
    "Proposal",
    "Follow-up",
]

REWRITE_MODES = {
    "make_professional": "Rewrite to be more professional and polished.",
    "make_executive": "Rewrite for an executive audience: concise, strategic, outcome-focused.",
    "improve_grammar": "Fix grammar, spelling, and punctuation while preserving meaning.",
    "make_more_technical": "Add appropriate technical depth and precise terminology.",
    "simplify": "Simplify language for clarity without losing key points.",
    "shorten": "Make significantly shorter while keeping essential information.",
    "expand": "Expand with more detail, context, and supporting explanation.",
    "add_business_justification": "Add clear business justification and value framing.",
    "add_technical_details": "Add relevant technical details and architecture context.",
    "improve_persuasiveness": "Strengthen persuasiveness while remaining professional.",
    "make_client_friendly": "Make more client-friendly, collaborative, and clear.",
    "remove_ai_tone": "Remove generic AI tone; make it sound natural and human-written.",
}

BUILTIN_PROMPTS = [
    {
        "name": "Client Proposal",
        "category": "proposal",
        "description": "Draft a client proposal email outlining scope, approach, and next steps.",
        "template": (
            "Draft a client proposal email based on the following notes.\n"
            "Include: context, proposed approach, key benefits, timeline (if available), "
            "and clear next steps.\n\nNotes:\n{{input}}"
        ),
        "variables": ["input"],
    },
    {
        "name": "Technical Clarification",
        "category": "technical",
        "description": "Clarify a technical point for a client or partner.",
        "template": (
            "Write a clear technical clarification email based on these points.\n"
            "Be precise, avoid jargon overload, and confirm understanding.\n\nPoints:\n{{input}}"
        ),
        "variables": ["input"],
    },
    {
        "name": "RCA",
        "category": "incident",
        "description": "Root cause analysis communication.",
        "template": (
            "Draft an RCA (Root Cause Analysis) email covering: incident summary, impact, "
            "root cause, corrective actions, preventive measures, and timeline.\n\nDetails:\n{{input}}"
        ),
        "variables": ["input"],
    },
    {
        "name": "Delay Explanation",
        "category": "status",
        "description": "Professionally explain a delay and recovery plan.",
        "template": (
            "Write a professional delay explanation email. Acknowledge impact, explain cause "
            "without excuses, provide revised timeline, and mitigation steps.\n\nDetails:\n{{input}}"
        ),
        "variables": ["input"],
    },
    {
        "name": "Architecture Recommendation",
        "category": "architecture",
        "description": "Recommend an architecture approach.",
        "template": (
            "Draft an architecture recommendation email. Cover current state, recommended approach, "
            "trade-offs, risks, and rationale.\n\nContext:\n{{input}}"
        ),
        "variables": ["input"],
    },
    {
        "name": "Cost Estimation",
        "category": "commercial",
        "description": "Communicate cost estimation context.",
        "template": (
            "Write a cost estimation email that frames assumptions, scope boundaries, "
            "estimate ranges if available, and next steps for refinement.\n\nDetails:\n{{input}}"
        ),
        "variables": ["input"],
    },
    {
        "name": "Escalation Response",
        "category": "escalation",
        "description": "Respond to an escalation calmly and decisively.",
        "template": (
            "Draft an escalation response. Acknowledge concern, summarize status, "
            "ownership, immediate actions, and communication cadence.\n\nContext:\n{{input}}"
        ),
        "variables": ["input"],
    },
    {
        "name": "Project Update",
        "category": "status",
        "description": "Structured project status update.",
        "template": (
            "Write a project update email with: progress, completed items, upcoming work, "
            "risks/blockers, and asks.\n\nUpdate notes:\n{{input}}"
        ),
        "variables": ["input"],
    },
    {
        "name": "Release Communication",
        "category": "release",
        "description": "Announce or communicate a release.",
        "template": (
            "Draft a release communication covering what's shipping, who is impacted, "
            "rollout notes, known issues, and support contacts.\n\nRelease info:\n{{input}}"
        ),
        "variables": ["input"],
    },
    {
        "name": "Change Request",
        "category": "change",
        "description": "Communicate a change request.",
        "template": (
            "Write a change request email describing the change, business reason, impact, "
            "effort/timeline implications, and approval ask.\n\nDetails:\n{{input}}"
        ),
        "variables": ["input"],
    },
    {
        "name": "Requirement Clarification",
        "category": "requirements",
        "description": "Ask clarifying questions on requirements.",
        "template": (
            "Draft a requirement clarification email. Restate understanding, list open questions, "
            "and propose assumptions if answers are delayed.\n\nContext:\n{{input}}"
        ),
        "variables": ["input"],
    },
]


CTO_SYSTEM_PROMPT = """You are an expert email writing assistant for a CTO and Solution Architect.
Your writing must be:
- Professional, concise, and client-ready
- Technically accurate with appropriate depth
- Business-friendly and confident without arrogance
- Free of generic AI filler phrases
- Structured with clear paragraphs and actionable next steps when relevant

Match the user's personal writing style when style examples are provided.
Prefer precise technical language over marketing fluff.
Never invent facts not present in the input or retrieved context.
If context is incomplete, write carefully and note assumptions briefly when needed."""


def build_compose_prompt(
    rough_notes: str,
    context: str = "",
    style_examples: str = "",
    subject: Optional[str] = None,
    extra_instructions: Optional[str] = None,
) -> str:
    parts = [
        "Convert the following rough notes into a polished professional email.",
        "Output ONLY the email body (and subject line if helpful as 'Subject: ...').",
    ]
    if subject:
        parts.append(f"Suggested subject: {subject}")
    if style_examples:
        parts.append(f"## Writing Style Examples\n{style_examples}")
    if context:
        parts.append(f"## Relevant Knowledge Base Context\n{context}")
    if extra_instructions:
        parts.append(f"## Additional Instructions\n{extra_instructions}")
    parts.append(f"## Rough Notes\n{rough_notes}")
    return "\n\n".join(parts)


def build_reply_prompt(
    thread: str,
    style: str = "Formal",
    context: str = "",
    style_examples: str = "",
    extra_instructions: Optional[str] = None,
) -> str:
    parts = [
        f"Draft a reply to the following email thread in a {style} style.",
        "Address unanswered questions and action items. Preserve conversation context.",
        "Output ONLY the reply email body.",
    ]
    if style_examples:
        parts.append(f"## Writing Style Examples\n{style_examples}")
    if context:
        parts.append(f"## Relevant Knowledge Base Context\n{context}")
    if extra_instructions:
        parts.append(f"## Additional Instructions\n{extra_instructions}")
    parts.append(f"## Email Thread\n{thread}")
    return "\n\n".join(parts)


def build_thread_analysis_prompt(thread: str) -> str:
    return f"""Analyze the following email thread and return a JSON object with these keys:
- summary: string
- key_decisions: string[]
- pending_questions: string[]
- blockers: string[]
- commitments: string[]
- risks: string[]
- next_actions: string[]
- stakeholders: string[]

Return ONLY valid JSON.

## Email Thread
{thread}"""


def build_rewrite_prompt(text: str, mode: str) -> str:
    instruction = REWRITE_MODES.get(mode, mode)
    return f"""{instruction}

Output ONLY the rewritten email text.

## Original Text
{text}"""


def build_suggestions_prompt(email_text: str) -> str:
    return f"""Review this draft email and return a JSON object with:
- client_concerns: string[] (possible concerns the recipient may have)
- missing_technical_points: string[]
- ambiguous_statements: string[]
- risk_analysis: string[]
- confidence_score: number (0-100)
- alternative_wording: string[] (2-3 alternative phrasings for key sentences)

Return ONLY valid JSON.

## Draft Email
{email_text}"""


def build_chat_prompt(message: str, context: str = "", history: str = "") -> str:
    parts = [
        "You are a CTO email and knowledge assistant. Answer helpfully using the context when available."
    ]
    if history:
        parts.append(f"## Recent Conversation\n{history}")
    if context:
        parts.append(f"## Retrieved Context\n{context}")
    parts.append(f"## User Message\n{message}")
    return "\n\n".join(parts)
