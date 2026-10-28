"""Markdown and HTML exports. Comments are escaped in HTML."""

from __future__ import annotations

import html
import json

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.db import repositories


def load_report(session: Session, run_id: str) -> dict:
    row = repositories.report_for_run(session, run_id)
    if row is None:
        raise NotFoundError(f"Report for {run_id} was not found.")
    return {"alert_level": row.alert_level, "report": json.loads(row.report_json), "fact_check": json.loads(row.fact_check_json)}


def to_markdown(document: dict) -> str:
    report = document["report"]
    lines = [
        f"# Leadership brief — {report['alert_level']}",
        "",
        report["headline"],
        "",
        "## NPS performance",
        "",
    ]
    overall = report["nps_performance"]["overall"]
    nps_text = "unavailable" if overall["nps"] is None else f"{overall['nps']:.1f}"
    lines.append(
        f"Full period NPS **{nps_text}** from {overall['total_responses']} responses "
        f"({overall['promoters']} promoters, {overall['passives']} passives, {overall['detractors']} detractors)."
    )
    lines.append("")
    for month in report["nps_performance"]["months"]:
        change = "n/a" if month["nps_change"] is None else f"{month['nps_change']:.1f}"
        month_nps = "unavailable" if month["nps"] is None else f"{month['nps']:.1f}"
        lines.append(f"- {month['label']}: NPS {month_nps} (change {change}), n={month['total_responses']}")
    why = report["why_it_moved"]
    lines.extend(["", "## Why it moved", ""])
    if why.get("status") != "available":
        lines.append(why.get("detail", "Voice of customer is unavailable."))
    else:
        lines.append(why["association"]["statement"])
        lines.append("")
        lines.append("Comments below are copied from the survey.")
        for quote in report["quotes"]:
            lines.append(f"> {quote['comment']}")
            lines.append(f"> — {quote['response_id']}")
            lines.append("")
    financial = report["financial_exposure"]
    lines.extend(["", "## Financial exposure", ""])
    if financial.get("status") != "available":
        lines.append(financial.get("detail", "Revenue analysis is unavailable."))
    else:
        lines.append(financial["statement"])
        lines.append("")
        lines.append(f"- Revenue exposed: ₹{financial['revenue_exposed_inr']:,.0f}")
        lines.append(f"- Expected revenue at risk: ₹{financial['estimated_expected_revenue_at_risk_inr']:,.0f}")
        lines.append(f"- Missing revenue rows: {financial['missing_revenue_count']}")
        lines.append(f"- Coverage: {financial['coverage_percentage']:.1f}%")
        assumptions = financial["assumptions"]
        lines.append(
            "- Assumptions: "
            f"promoter {assumptions['promoter_churn_probability']:.0%}, "
            f"passive {assumptions['passive_churn_probability']:.0%}, "
            f"detractor {assumptions['detractor_churn_probability']:.0%}."
        )
    lines.extend(["", "## Actions", ""])
    for action in report.get("actions", []):
        lines.append(f"{action['priority']}. **{action['title']}** ({action['timeframe']}, {action['suggested_owner']})")
        lines.append(f"   {action['evidence']}")
        lines.append(f"   Success metric: {action['success_metric']}")
    lines.extend(["", "## Callbacks this week", ""])
    if not report.get("callbacks"):
        lines.append("No callback recommendations.")
    for row in report.get("callbacks", []):
        lines.append(
            f"- {row['timeframe']} {row['response_id']} score {row['score']} {row['theme']} "
            f"revenue {row['annual_revenue_inr']}. {row['suggested_action']}"
        )
    lines.extend(["", "## Caveats", ""])
    for note in report["caveats"]["notes"]:
        lines.append(f"- {note}")
    checks = document["fact_check"]
    lines.extend(["", "## Fact check", "", f"Passed: {checks['passed']}. Failures: {len(checks['failures'])}. Warnings: {len(checks['warnings'])}."])
    return "\n".join(lines) + "\n"


def to_html(document: dict) -> str:
    body = html.escape(to_markdown(document)).replace("\n", "<br>\n")
    return (
        "<!DOCTYPE html><html><head><meta charset=\"utf-8\"><title>NPS leadership brief</title></head>"
        f"<body style=\"font-family: Georgia, serif; max-width: 46rem; margin: 2rem auto;\">{body}</body></html>"
    )
