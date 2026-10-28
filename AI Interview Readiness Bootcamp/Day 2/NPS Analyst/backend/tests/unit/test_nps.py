"""NPS classification and empty-input behaviour."""

from app.analytics.nps import calculate_nps, classify_score, nps_by_month
from app.data.normalizer import NormalizedResponse


def row(score: int, month: str = "2026-07", response_id: str = "R1") -> NormalizedResponse:
    return NormalizedResponse(
        response_id=response_id,
        date=f"{month}-15",
        month=month,
        analysis_month=month,
        product="Savings Account",
        tenure="1-3 yrs",
        channel="Branch",
        score=score,
        comment=None,
        annual_revenue_inr=1000,
    )


def test_classification_boundaries():
    assert classify_score(9) == "promoter"
    assert classify_score(10) == "promoter"
    assert classify_score(8) == "passive"
    assert classify_score(7) == "passive"
    assert classify_score(6) == "detractor"
    assert classify_score(0) == "detractor"


def test_all_promoters_all_passives_all_detractors():
    assert calculate_nps([row(10), row(9)])["nps"] == 100
    assert calculate_nps([row(7), row(8)])["nps"] == 0
    assert calculate_nps([row(0), row(6)])["nps"] == -100


def test_mixed_population_uses_all_valid_responses():
    result = calculate_nps([row(10), row(8), row(0), row(6)])
    assert result["total_responses"] == 4
    assert result["promoters"] == 1
    assert result["passives"] == 1
    assert result["detractors"] == 2
    assert result["nps"] == 25 - 50


def test_empty_dataset_does_not_invent_an_nps():
    result = calculate_nps([])
    assert result["total_responses"] == 0
    assert result["nps"] is None


def test_monthly_groups_do_not_invent_missing_months():
    months = nps_by_month([row(10, "2026-07", "A"), row(0, "2026-09", "B")])
    assert [item["month"] for item in months] == ["2026-07", "2026-09"]
    assert months[0]["nps"] == 100
    assert months[1]["nps"] == -100
