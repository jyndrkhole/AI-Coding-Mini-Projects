"""InterviewIQ Gradio UI — the interface you demo.

Layout is the required surface: current question, answer box, feedback,
live scorecard, meta-question box, and a final-report button. The handlers
call InterviewAgent from agent.py.
"""

from __future__ import annotations

import gradio as gr

from agent import InterviewAgent
from interview_bank import QUESTIONS

MOON = "🌙"

THEME_CSS = """
#theme-toggle {
    min-width: 44px !important;
    max-width: 56px !important;
    margin-left: auto;
}
#scorecard table {
    width: 100%;
    font-size: 0.95rem;
}
"""

THEME_HEAD = """
<script>
(function () {
    const saved = localStorage.getItem("interviewiq-theme");
    const dark = saved ? saved === "dark"
        : window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.classList.toggle("dark", dark);
    document.addEventListener("DOMContentLoaded", () => {
        document.body.classList.toggle("dark", dark);
    });
})();
</script>
"""

TOGGLE_THEME_JS = """
() => {
    const dark = !document.body.classList.contains("dark");
    document.documentElement.classList.toggle("dark", dark);
    document.body.classList.toggle("dark", dark);
    localStorage.setItem("interviewiq-theme", dark ? "dark" : "light");
    const btn = document.querySelector("#theme-toggle button");
    if (btn) btn.title = dark ? "Switch to light mode" : "Switch to dark mode";
    return dark ? "☀️" : "🌙";
}
"""

RESTORE_THEME_JS = """
() => {
    const saved = localStorage.getItem("interviewiq-theme");
    const dark = saved ? saved === "dark"
        : window.matchMedia("(prefers-color-scheme: dark)").matches;
    document.documentElement.classList.toggle("dark", dark);
    document.body.classList.toggle("dark", dark);
    const btn = document.querySelector("#theme-toggle button");
    if (btn) btn.title = dark ? "Switch to light mode" : "Switch to dark mode";
    return dark ? "☀️" : "🌙";
}
"""

QUESTION_CHOICES = [
    f"Q{i} — {item['question']}" for i, item in enumerate(QUESTIONS, start=1)
]

_agent: InterviewAgent | None = None


def get_agent() -> InterviewAgent:
    global _agent
    if _agent is None:
        _agent = InterviewAgent()
    return _agent


def current_question_text(index: int) -> str:
    item = QUESTIONS[index % len(QUESTIONS)]
    n = (index % len(QUESTIONS)) + 1
    return (
        f"Question {n} of {len(QUESTIONS)}  ·  {item['category']}\n\n"
        f"{item['question']}"
    )


def _nav_buttons(index: int):
    last = len(QUESTIONS) - 1
    return (
        gr.update(interactive=index > 0),
        gr.update(interactive=index < last),
    )


def _last_answer_for(index: int) -> str:
    item = QUESTIONS[index % len(QUESTIONS)]
    for turn in reversed(get_agent().history):
        if turn.get("question_id") == item["id"] or turn.get("question") == item["question"]:
            return turn.get("answer") or ""
    return ""


def _labeled_feedback(item: dict, index: int, feedback: str) -> str:
    n = (index % len(QUESTIONS)) + 1
    return (
        f"Feedback for question {n} of {len(QUESTIONS)} · {item['category']}\n"
        f"{item['question']}\n\n"
        f"{feedback}"
    )


def submit_answer(answer: str, index: int):
    agent = get_agent()
    item = QUESTIONS[index % len(QUESTIONS)]
    if not (answer or "").strip():
        return (
            "Please write an answer before submitting.",
            agent.scorecard_markdown(),
            agent.previous_answers_text(),
            index,
            current_question_text(index),
            "",
            QUESTION_CHOICES[index % len(QUESTIONS)],
            *_nav_buttons(index),
        )

    n = (index % len(QUESTIONS)) + 1
    try:
        feedback = agent.evaluate_answer(
            question=item["question"],
            answer=answer.strip(),
            expected_keywords=item["keywords"],
            category=item["category"],
            question_number=n,
            question_id=item["id"],
        )
    except Exception:
        return (
            "Could not score that answer — the model sent an invalid tool call. "
            "The tools can still run if you submit again; if it keeps failing, "
            "try a slightly shorter answer.",
            agent.scorecard_markdown(),
            agent.previous_answers_text(),
            index,
            current_question_text(index),
            answer.strip(),
            QUESTION_CHOICES[index % len(QUESTIONS)],
            *_nav_buttons(index),
        )
    # Stay on this question so feedback is not shown against the next prompt.
    return (
        _labeled_feedback(item, index, feedback),
        agent.scorecard_markdown(),
        agent.previous_answers_text(),
        index,
        current_question_text(index),
        answer.strip(),
        QUESTION_CHOICES[index % len(QUESTIONS)],
        *_nav_buttons(index),
    )


def go_to_question(index: int):
    """Move to a bank question. Session history is left intact."""
    index = max(0, min(int(index), len(QUESTIONS) - 1))
    last = _last_answer_for(index)
    note = ""
    if last:
        note = (
            "This question is already in your session. "
            "Edit and submit again to add another attempt (e.g. Q1.2). "
            "Earlier scores stay on the scorecard."
        )
    return (
        current_question_text(index),
        last,
        index,
        note,
        QUESTION_CHOICES[index],
        *_nav_buttons(index),
    )


def previous_question(index: int):
    return go_to_question(index - 1)


def next_question(index: int):
    return go_to_question(index + 1)


def jump_question(choice: str):
    if not choice:
        return go_to_question(0)
    # "Q3 — Describe a time..."
    token = choice.split("—", 1)[0].strip()  # Q3
    n = int(token[1:])
    return go_to_question(n - 1)


def ask_coach(meta_question: str):
    agent = get_agent()
    if not (meta_question or "").strip():
        return "Type a question for the coach — e.g. “how am I doing so far?”"
    return agent.ask_agent(meta_question.strip())


def pull_report() -> str:
    return get_agent().generate_final_report()


def restart():
    get_agent().reset()
    return (
        "",
        "_No questions scored yet._",
        "No answers stored yet. Submit a question to start the session log.",
        0,
        current_question_text(0),
        "",
        "",
        "",
        QUESTION_CHOICES[0],
        *_nav_buttons(0),
    )


def build_ui() -> gr.Blocks:
    with gr.Blocks(title="InterviewIQ") as demo:
        with gr.Row(equal_height=True):
            gr.Markdown(
                """
# InterviewIQ
A mock-interview coach. Answer in the box, get tool-backed feedback, and ask
how you're doing at any point — the coach remembers the whole session.
                """
            )
            theme_btn = gr.Button(
                MOON,
                elem_id="theme-toggle",
                size="sm",
                min_width=44,
            )
        q_index = gr.State(0)

        question_box = gr.Textbox(
            label="Current question",
            value=current_question_text(0),
            lines=5,
            interactive=False,
        )
        answer_box = gr.Textbox(
            label="Your answer",
            placeholder="Speak the way you would in a real interview…",
            lines=8,
        )
        with gr.Row():
            jump_dd = gr.Dropdown(
                choices=QUESTION_CHOICES,
                value=QUESTION_CHOICES[0],
                label="Jump to any question (session scores are kept)",
                scale=4,
            )
            jump_btn = gr.Button("Go to question", scale=1)
        with gr.Row():
            prev_btn = gr.Button("Previous question", interactive=False)
            submit_btn = gr.Button("Submit answer", variant="primary")
            next_btn = gr.Button("Next question")

        feedback_box = gr.Textbox(
            label="Coach feedback",
            lines=10,
            interactive=False,
        )
        gr.Markdown("### Live scorecard — every question answered so far")
        scorecard = gr.Markdown(
            value="_No questions scored yet._",
            elem_id="scorecard",
        )
        history_box = gr.Textbox(
            label="Previous answers — full text from this session",
            value="No answers stored yet. Submit a question to start the session log.",
            lines=10,
            interactive=False,
        )

        gr.Markdown("### Ask the coach")
        with gr.Row():
            meta_box = gr.Textbox(
                label="Meta-question",
                placeholder="How am I doing so far?  What's my weakest area?",
                lines=2,
                scale=4,
            )
            meta_btn = gr.Button("Ask coach", scale=1)
        meta_reply = gr.Textbox(label="Coach's reply", lines=6, interactive=False)

        with gr.Row():
            report_btn = gr.Button("Final report", variant="secondary")
            restart_btn = gr.Button("Restart session")
        report_box = gr.Textbox(label="Final report", lines=14, interactive=False)

        nav_outputs = [
            question_box,
            answer_box,
            q_index,
            feedback_box,
            jump_dd,
            prev_btn,
            next_btn,
        ]
        submit_btn.click(
            submit_answer,
            inputs=[answer_box, q_index],
            outputs=[
                feedback_box,
                scorecard,
                history_box,
                q_index,
                question_box,
                answer_box,
                jump_dd,
                prev_btn,
                next_btn,
            ],
        )
        prev_btn.click(previous_question, inputs=[q_index], outputs=nav_outputs)
        next_btn.click(next_question, inputs=[q_index], outputs=nav_outputs)
        jump_btn.click(jump_question, inputs=[jump_dd], outputs=nav_outputs)
        meta_btn.click(ask_coach, inputs=[meta_box], outputs=[meta_reply])
        report_btn.click(pull_report, outputs=[report_box])
        restart_btn.click(
            restart,
            outputs=[
                feedback_box,
                scorecard,
                history_box,
                q_index,
                question_box,
                answer_box,
                meta_reply,
                report_box,
                jump_dd,
                prev_btn,
                next_btn,
            ],
        )
        theme_btn.click(
            None,
            js=TOGGLE_THEME_JS,
            outputs=[theme_btn],
        )
        demo.load(
            None,
            js=RESTORE_THEME_JS,
            outputs=[theme_btn],
        )

    return demo


if __name__ == "__main__":
    build_ui().launch(css=THEME_CSS, head=THEME_HEAD)
