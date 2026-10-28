"""Deterministic analytics, fact checking, and agent ordering."""

import asyncio
import time

from app.agents.orchestrator import run_orchestrator
from app.analytics.fact_check import fact_check
from app.analytics.nps import calculate_nps
from app.analytics.simulation import simulate_fix
from app.analytics.themes import accept_model_theme, classify_comment, sentiment_of
from app.core.config import Settings
from app.data.loader import load_survey_csv
from app.data.normalizer import NormalizedResponse, normalize
from app.data.validator import validate_frame
from app.services.bundle import build_bundle
from app.core.config import survey_path


def response(response_id, score, comment, revenue, month="2026-07", product="Savings Account", channel="Branch", tenure="1-3 yrs"):
    return NormalizedResponse(
        response_id=response_id,
        date=f"{month}-15",
        month=month,
        analysis_month=month,
        product=product,
        tenure=tenure,
        channel=channel,
        score=score,
        comment=comment,
        annual_revenue_inr=revenue,
    )


def test_sentiment_and_known_themes():
    otp = classify_comment("OTP never arrives since the last app update. Could not login for two days.")
    assert otp["primary_theme"] == "OTP_AND_LOGIN"
    assert otp["sentiment"] == "NEGATIVE"
    assert otp["secondary_theme"] == "MOBILE_APP"
    praise = classify_comment("Excellent service, love it!")
    assert praise["sentiment"] == "POSITIVE"
    recharge = classify_comment("Mobile recharge and bill payments are super quick.")
    assert recharge["primary_theme"] == "UPI_AND_PAYMENTS"
    assert recharge["sentiment"] == "POSITIVE"
    assert classify_comment("I was charged an annual fee on my credit card even after reaching the spend target.")["primary_theme"] == "FEES_AND_CHARGES"
    assert sentiment_of("Not happy with the service lately.") == "NEGATIVE"
    assert classify_comment(None)["primary_theme"] == "UNCLEAR"
    assert classify_comment("Average experience.")["primary_theme"] == "UNCLEAR"
    assert accept_model_theme("NOT_A_REAL_THEME") == "UNCLEAR"
    assert accept_model_theme("FEES_AND_CHARGES") == "FEES_AND_CHARGES"


def test_contradiction_does_not_change_the_score():
    rows = [response("R1", 0, "Excellent service, very happy with my bank!", 1000)]
    bundle = build_bundle(rows, [], Settings(bootstrap_samples=20, min_sample=30))
    assert rows[0].score == 0
    assert bundle["quality"]["contradiction_count"] == 1
    assert bundle["overview"]["nps"] == -100


def test_revenue_skips_missing_values_and_uses_assumptions():
    settings = Settings(churn_promoter=0.03, churn_passive=0.10, churn_detractor=0.25, bootstrap_samples=20)
    rows = [
        response("P", 10, "Great cashback on the credit card every month.", 100),
        response("S", 8, "Average experience.", 100),
        response("D", 1, "OTP never arrives since the last app update.", 100),
        response("M", 2, "The fee structure is confusing and nobody could explain it to me.", None),
    ]
    bundle = build_bundle(rows, [], settings)
    revenue = bundle["revenue"]
    assert revenue["missing_revenue_count"] == 1
    assert revenue["revenue_exposed_inr"] == 300
    assert revenue["estimated_expected_revenue_at_risk_inr"] == 100 * 0.03 + 100 * 0.10 + 100 * 0.25
    groups = {row["label"]: row for row in revenue["by_group"]}
    assert groups["detractor"]["revenue_exposed_inr"] == 100
    assert groups["detractor"]["missing_revenue_count"] == 1


def test_confidence_is_reproducible_and_flags_small_samples():
    rows = [response(f"R{i}", score, "App crashes when I open the statements page.", 10) for i, score in enumerate([0, 10, 7, 6, 9])]
    settings = Settings(bootstrap_samples=40, bootstrap_seed=7, min_sample=30)
    first = build_bundle(rows, [], settings)["confidence"]["overall"]
    second = build_bundle(rows, [], settings)["confidence"]["overall"]
    assert first["confidence_low"] == second["confidence_low"]
    assert first["confidence_high"] == second["confidence_high"]
    assert first["caution"] == "LOW SAMPLE — INTERPRET WITH CAUTION"
    certain = build_bundle([response("A", 10, "Seamless experience, everything works on the app.", 10), response("B", 9, "Good bank, no complaints.", 10)], [], Settings(bootstrap_samples=20, min_sample=30))
    assert certain["confidence"]["overall"]["confidence_low"] == 100
    assert certain["confidence"]["overall"]["confidence_high"] == 100


def test_simulation_changes_a_copy_only():
    rows = [response("D", 0, "OTP never arrives since the last app update.", 10), response("P", 10, "Good bank, no complaints.", 10)]
    result = simulate_fix(rows, {"D": "OTP_AND_LOGIN", "P": "SERVICE_QUALITY"}, "OTP_AND_LOGIN", "A")
    assert rows[0].score == 0
    assert result["current_nps"] == 0
    assert result["simulated_nps"] == 50
    assert result["affected_response_count"] == 1
    assert "hypothetical" in " ".join(result["caveats"]).lower() or "Hypothetical" in result["caveats"][0]


def test_fact_check_rejects_bad_numbers_wrong_month_and_fake_quotes():
    rows = [
        response("J", 10, "Good bank, no complaints.", 50, "2026-07"),
        response("S", 0, "OTP never arrives since the last app update.", 50, "2026-09"),
    ]
    bundle = build_bundle(rows, [], Settings(bootstrap_samples=10, min_sample=30))
    good = asyncio.run(run_orchestrator(bundle))
    assert good["fact_check"]["passed"] is True
    assert good["report"]["alert_level"] in {"RED", "AMBER", "GREEN"}
    bad = dict(good["report"])
    bad["claims"] = [{"metric": "nps", "scope": "overall", "value": 99}]
    failed = fact_check(bad, bundle)
    assert failed["passed"] is False
    wrong_month = dict(good["report"])
    wrong_month["claims"] = [{"metric": "nps", "scope": "2026-09", "value": bundle["months"][0]["nps"]}]
    assert fact_check(wrong_month, bundle)["passed"] is False
    fake_quote = dict(good["report"])
    fake_quote["quotes"] = [{"response_id": "J", "comment": "This sentence was not in the survey."}]
    assert fact_check(fake_quote, bundle)["passed"] is False
    wrong_revenue = dict(good["report"])
    wrong_revenue["claims"] = [{"metric": "revenue_exposed_inr", "scope": "overall", "value": 1}]
    assert fact_check(wrong_revenue, bundle)["passed"] is False
    quiet = dict(good["report"])
    quiet["assumptions_disclosed"] = False
    quiet["small_samples_disclosed"] = False
    quiet["missing_data_disclosed"] = False
    warned = fact_check(quiet, bundle)
    assert warned["warnings"]


def test_agents_run_phase_one_together_and_planner_after():
    rows = [response("A", 10, "Good bank, no complaints.", 20), response("B", 0, "IVR goes in circles, never reached a human. Complaint still open.", 80)]
    bundle = build_bundle(rows, [], Settings(bootstrap_samples=10, min_sample=30))
    order = []

    def make(name, delay):
        async def _run():
            order.append(("start", name, time.monotonic()))
            await asyncio.sleep(delay)
            order.append(("end", name, time.monotonic()))
            return {"available": True, "tools_used": ["stub"], "low_samples": [], "quotes": [], "negative_themes": [], "positive_themes": [], "association": {"statement": "stub"}, "volume_leader": None, "revenue_leader": None, "volume_and_revenue_same_theme": False, "statement": "stub"}

        return _run

    result = asyncio.run(
        run_orchestrator(
            bundle,
            runners={
                "ScoreAnalystAgent": make("score", 0.05),
                "VoiceOfCustomerAgent": make("voice", 0.05),
                "ChurnRiskAgent": make("churn", 0.05),
                "ActionPlannerAgent": __import__("app.agents.action_planner", fromlist=["run"]).run,
                "ReportWriterAgent": __import__("app.agents.report_writer", fromlist=["run"]).run,
            },
        )
    )
    starts = [stamp for kind, name, stamp in order if kind == "start"]
    ends = [stamp for kind, name, stamp in order if kind == "end"]
    assert max(starts) < min(ends)
    phase1 = [row for row in result["trace"] if row["phase"] == "phase_1"]
    phase2 = next(row for row in result["trace"] if row["agent"] == "ActionPlannerAgent")
    assert phase2["phase"] == "phase_2"
    assert {row["agent"] for row in phase1} == {"ScoreAnalystAgent", "VoiceOfCustomerAgent", "ChurnRiskAgent"}
    assert result["fact_check"]["passed"] is True


def test_a_failed_specialist_does_not_erase_the_others():
    rows = [response("A", 9, "Good bank, no complaints.", 20)]
    bundle = build_bundle(rows, [], Settings(bootstrap_samples=10, min_sample=30))

    async def boom():
        raise RuntimeError("voice failed")

    result = asyncio.run(
        run_orchestrator(
            bundle,
            runners={
                "ScoreAnalystAgent": __import__("app.agents.score_analyst", fromlist=["run"]).run,
                "VoiceOfCustomerAgent": boom,
                "ChurnRiskAgent": __import__("app.agents.churn_risk", fromlist=["run"]).run,
                "ActionPlannerAgent": __import__("app.agents.action_planner", fromlist=["run"]).run,
                "ReportWriterAgent": __import__("app.agents.report_writer", fromlist=["run"]).run,
            },
        )
    )
    voice = next(row for row in result["trace"] if row["agent"] == "VoiceOfCustomerAgent")
    assert voice["status"] == "failed"
    assert result["specialists"]["score"]["available"] is True
    assert result["report"]["why_it_moved"]["status"] == "unavailable"
    assert result["fact_check"]["passed"] is True


def test_supplied_survey_matches_the_calculated_months():
    frame = load_survey_csv(survey_path())
    validation = validate_frame(frame)
    rows = normalize(frame, validation)
    bundle = build_bundle(rows, validation.issues, Settings(bootstrap_samples=50, min_sample=30))
    by_month = {row["month"]: row["nps"] for row in bundle["months"]}
    assert bundle["overview"]["total_responses"] == 600
    assert by_month["2026-07"] == 32
    assert by_month["2026-09"] == -6.5
    assert calculate_nps(rows)["nps"] == 18.5
    assert all(item["status"] == "match" for item in bundle["reference_claims"])
    assert bundle["alert"]["level"] == "RED"
    assert bundle["quality"]["contradiction_count"] > 0
    assert rows[2].score == 0
    themes = {row["theme"]: row for row in bundle["themes"]}
    assert themes["OTP_AND_LOGIN"]["detractor_change"] > 0
    assert bundle["association"]["theme"] == "OTP_AND_LOGIN"
    assert bundle["priorities"]["same_theme"] is False
