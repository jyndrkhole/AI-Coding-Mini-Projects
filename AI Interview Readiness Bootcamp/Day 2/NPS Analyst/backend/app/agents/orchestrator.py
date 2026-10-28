"""Run the specialists in three phases, then refuse a report whose numbers do not match the tools."""

from __future__ import annotations

import asyncio
import time

from app.agents import action_planner, churn_risk, report_writer, score_analyst, voice_of_customer
from app.agents.tools import CTX, ToolContext
from app.analytics.fact_check import fact_check


async def _timed(trace: list, phase: str, name: str, factory) -> dict:
    started = time.perf_counter()
    try:
        output = await factory()
        if not isinstance(output, dict):
            output = {"available": False, "error": "Agent returned an unexpected result."}
        status = "completed" if output.get("available", True) else "unavailable"
        error = output.get("error")
    except Exception as exc:  # a specialist failure must not wipe the other results
        output = {"agent": name, "available": False, "error": exc.__class__.__name__}
        status = "failed"
        error = exc.__class__.__name__
    trace.append(
        {
            "phase": phase,
            "agent": name,
            "status": status,
            "duration_ms": int((time.perf_counter() - started) * 1000),
            "tools": output.get("tools_used", []),
            "error": error,
        }
    )
    return output


async def run_orchestrator(bundle: dict, runners: dict | None = None, narrative=None) -> dict:
    runners = runners or {
        "ScoreAnalystAgent": score_analyst.run,
        "VoiceOfCustomerAgent": voice_of_customer.run,
        "ChurnRiskAgent": churn_risk.run,
        "ActionPlannerAgent": action_planner.run,
        "ReportWriterAgent": report_writer.run,
    }
    token = CTX.set(ToolContext(bundle))
    trace: list[dict] = []
    try:
        score, voice, churn = await asyncio.gather(
            _timed(trace, "phase_1", "ScoreAnalystAgent", runners["ScoreAnalystAgent"]),
            _timed(trace, "phase_1", "VoiceOfCustomerAgent", runners["VoiceOfCustomerAgent"]),
            _timed(trace, "phase_1", "ChurnRiskAgent", runners["ChurnRiskAgent"]),
        )
        planner = await _timed(
            trace,
            "phase_2",
            "ActionPlannerAgent",
            lambda: runners["ActionPlannerAgent"](score, voice, churn),
        )
        report = await _timed(
            trace,
            "phase_3",
            "ReportWriterAgent",
            lambda: runners["ReportWriterAgent"](score, voice, churn, planner),
        )
        checked = fact_check(report, bundle)
        if not checked["passed"]:
            correction = checked["failures"]
            report = await _timed(
                trace,
                "phase_3_correction",
                "ReportWriterAgent",
                lambda: runners["ReportWriterAgent"](score, voice, churn, planner, correction),
            )
            checked = fact_check(report, bundle)
            if not checked["passed"]:
                report = await report_writer.run(score, voice, churn, planner, correction)
                report["status"] = "rejected"
                report["rejection_reason"] = "Fact checking failed twice. The brief below was rebuilt from the tools and the failed checks are attached."
                checked = fact_check(report, bundle)
                trace.append(
                    {
                        "phase": "fact_check",
                        "agent": "FactCheck",
                        "status": "failed" if not checked["passed"] else "completed",
                        "duration_ms": 0,
                        "tools": [],
                        "error": "correction_failed" if not checked["passed"] else None,
                    }
                )
        if narrative is not None and report.get("available"):
            report["ai_note"] = narrative.note(report.get("headline", ""))
            report["narrative_source"] = getattr(narrative, "name", "provider")
        else:
            report["narrative_source"] = "deterministic"
        unavailable = [row["agent"] for row in trace if row["status"] in {"failed", "unavailable"}]
        status = "completed_with_unavailable_sections" if unavailable else "completed"
        if report.get("status") == "rejected":
            status = "rejected"
        return {
            "status": status,
            "trace": trace,
            "tool_log": CTX.get().tool_calls,
            "specialists": {"score": score, "voice": voice, "churn": churn, "planner": planner},
            "report": report,
            "fact_check": checked,
        }
    finally:
        CTX.reset(token)
