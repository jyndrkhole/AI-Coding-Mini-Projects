"""Gradio interface for the Shipment Exception Desk. Required, not optional."""

import gradio as gr

from pipeline import process_exception
from session import generate_daily_summary, get_log, record_exception


def _format_outcome(result: dict) -> str:
    badge = "ESCALATED" if result["escalated"] else "AUTO-RESOLVED"
    return (
        f"**{badge}**\n\n"
        f"- Category: `{result['category']}`\n"
        f"- Customer tier: `{result['customer_tier']}`\n"
        f"- Shipment value: `${result['shipment_value']:.2f}`\n"
        f"- Compensation: `${result['compensation_amount']:.2f}`\n"
        f"- Policy: {result['compensation']['policy']}"
    )


def _format_steps(result: dict) -> str:
    return "\n".join(f"{i}. {step}" for i, step in enumerate(result["steps"], start=1))


def _log_rows() -> list[list]:
    rows = []
    for item in get_log():
        rows.append(
            [
                item["category"],
                item["customer_tier"],
                f"${item['shipment_value']:.2f}",
                f"${item['compensation_amount']:.2f}",
                item["outcome"],
            ]
        )
    return rows


def submit_report(report: str, shipment_value: float, customer_tier: str):
    if not (report or "").strip():
        raise gr.Error("Paste an exception report before submitting.")
    if shipment_value is None or float(shipment_value) < 0:
        raise gr.Error("Shipment value must be zero or greater.")

    result = process_exception(report.strip(), float(shipment_value), customer_tier)
    record_exception(result)
    return (
        _format_outcome(result),
        _format_steps(result),
        result["message"],
        _log_rows(),
    )


def show_summary() -> str:
    return generate_daily_summary()


LOG_HEADERS = ["Category", "Tier", "Value", "Compensation", "Outcome"]

# Moon = switch to dark; sun = switch to light. CSS mask so the icon follows currentColor.
_MOON_ICON = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M21.752 15.002A9.72 9.72 0 0 1 "
    "18 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 "
    "0 0 0 3 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 0 0 9.002-5.998z'/%3E"
    "%3C/svg%3E\")"
)
_SUN_ICON = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "viewBox='0 0 24 24'%3E%3Cpath fill='black' d='M12 2.25a.75.75 0 0 1 .75.75v2.25a.75.75 "
    "0 0 1-1.5 0V3a.75.75 0 0 1 .75-.75zM7.5 12a4.5 4.5 0 1 1 9 0 4.5 4.5 0 0 1-9 0zm11.394"
    "-5.834a.75.75 0 1 0-1.06-1.06l-1.591 1.59a.75.75 0 0 0 1.06 1.061l1.591-1.59zM21.75 "
    "12a.75.75 0 0 1-.75.75h-2.25a.75.75 0 0 1 0-1.5H21a.75.75 0 0 1 .75.75zm-3.916 "
    "6.894a.75.75 0 0 0 1.06-1.06l-1.59-1.591a.75.75 0 1 0-1.061 1.06l1.59 1.591zM12 "
    "18a.75.75 0 0 1 .75.75V21a.75.75 0 0 1-1.5 0v-2.25A.75.75 0 0 1 12 18zm-4.242-.697a.75.75 "
    "0 0 0-1.061-1.06l-1.591 1.59a.75.75 0 1 0 1.06 1.061l1.591-1.59zM6 12a.75.75 0 0 1-.75.75H3"
    "a.75.75 0 0 1 0-1.5h2.25A.75.75 0 0 1 6 12zM6.697 7.757a.75.75 0 0 0 1.06-1.06l-1.59-1.591"
    "a.75.75 0 0 0-1.061 1.06l1.59 1.591z'/%3E%3C/svg%3E\")"
)

HEADER_CSS = f"""
#app-header {{ align-items: center; }}
#theme-toggle {{ max-width: 11rem; min-width: 10rem; }}
#theme-toggle button {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 0.45rem;
}}
#theme-toggle button::before {{
    content: "";
    width: 1.1rem;
    height: 1.1rem;
    background: currentColor;
    -webkit-mask: {_MOON_ICON} center / contain no-repeat;
    mask: {_MOON_ICON} center / contain no-repeat;
}}
body.dark #theme-toggle button::before {{
    -webkit-mask: {_SUN_ICON} center / contain no-repeat;
    mask: {_SUN_ICON} center / contain no-repeat;
}}
"""

TOGGLE_THEME_JS = """
() => {
    const isDark = document.body.classList.toggle('dark');
    localStorage.setItem('nw-theme', isDark ? 'dark' : 'light');
    return isDark ? 'Light mode' : 'Dark mode';
}
"""

APPLY_SAVED_THEME_JS = """
() => {
    const saved = localStorage.getItem('nw-theme');
    const preferDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const dark = saved ? saved === 'dark' : preferDark;
    document.body.classList.toggle('dark', dark);
    return dark ? 'Light mode' : 'Dark mode';
}
"""

PAGE_JS = """
function applyNorthwindTheme() {
    const saved = localStorage.getItem('nw-theme');
    const preferDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
    const dark = saved ? saved === 'dark' : preferDark;
    document.body.classList.toggle('dark', dark);
}
applyNorthwindTheme();
"""

with gr.Blocks(title="Northwind Shipment Exception Desk") as demo:
    with gr.Row(elem_id="app-header"):
        gr.Markdown("# Northwind Logistics — Shipment Exception Desk")
        theme_btn = gr.Button("Dark mode", size="sm", elem_id="theme-toggle")
    gr.Markdown(
        "Submit an exception report. The desk classifies it, applies compensation "
        "policy, and either drafts a customer email or escalates to a manager."
    )

    with gr.Row():
        with gr.Column():
            report = gr.Textbox(
                label="Exception report",
                lines=8,
                placeholder="What went wrong with the shipment?",
            )
            with gr.Row():
                shipment_value = gr.Number(label="Shipment value ($)", value=80, minimum=0)
                customer_tier = gr.Dropdown(
                    label="Customer tier",
                    choices=["standard", "premium"],
                    value="standard",
                )
            submit = gr.Button("Submit exception", variant="primary")
            gr.Examples(
                examples=[
                    [
                        "Order NW-1842 arrived two days late. Boxes are unopened and goods look fine.",
                        80,
                        "standard",
                    ],
                    [
                        "Tracking went dark a week ago. Carrier confirms the pallet is lost.",
                        400,
                        "standard",
                    ],
                    [
                        "One corner of the box was crushed and two mugs arrived chipped.",
                        60,
                        "standard",
                    ],
                    [
                        "asdf qwerty ??? purple Tuesday invoice banana /////// 42%%%",
                        25,
                        "premium",
                    ],
                ],
                inputs=[report, shipment_value, customer_tier],
            )

        with gr.Column():
            outcome = gr.Markdown(label="Outcome")
            steps = gr.Markdown(label="Steps")
            message = gr.Textbox(label="Drafted message", lines=10)

    gr.Markdown("## Daily Triage Log")
    log_table = gr.Dataframe(headers=LOG_HEADERS, interactive=False, wrap=True)
    summary_btn = gr.Button("Daily Summary")
    summary = gr.Textbox(label="Daily Triage Summary", lines=10)

    submit.click(
        submit_report,
        inputs=[report, shipment_value, customer_tier],
        outputs=[outcome, steps, message, log_table],
    )
    summary_btn.click(show_summary, outputs=summary)
    theme_btn.click(None, None, theme_btn, js=TOGGLE_THEME_JS)
    demo.load(None, None, theme_btn, js=APPLY_SAVED_THEME_JS)

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft(), css=HEADER_CSS, js=PAGE_JS)
