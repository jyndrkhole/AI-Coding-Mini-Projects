"""Check a leadership report against the deterministic bundle. A failed check is kept visible."""

from __future__ import annotations


def _close(left, right) -> bool:
    if left is None or right is None:
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) < 1e-6
    return left == right


def _lookup(bundle: dict, metric: str, scope: str):
    overview = bundle["overview"]
    if scope == "overall" and metric in overview:
        return overview[metric]
    if scope == "overall" and metric == "revenue_exposed_inr":
        return bundle["revenue"]["revenue_exposed_inr"]
    if scope == "overall" and metric == "estimated_expected_revenue_at_risk_inr":
        return bundle["revenue"]["estimated_expected_revenue_at_risk_inr"]
    if scope == "overall" and metric == "missing_revenue_count":
        return bundle["revenue"]["missing_revenue_count"]
    months = {row["month"]: row for row in bundle["months"]}
    if scope in months and metric in months[scope]:
        return months[scope][metric]
    if scope.startswith("theme:"):
        theme_name = scope.split(":", 1)[1]
        for theme in bundle["themes"]:
            if theme["theme"] == theme_name and metric in theme:
                return theme[metric]
        return None
    for segment_type, rows in bundle["segments"].items():
        prefix = f"{segment_type}:"
        if scope.startswith(prefix):
            label = scope[len(prefix) :]
            for row in rows:
                if row["segment"] == label and metric in row:
                    return row[metric]
            return None
    return None


def fact_check(report: dict, bundle: dict) -> dict:
    checks = []
    failures = []
    warnings = []
    comments_by_id = {row.response_id: row.comment for row in bundle["responses"]}
    theme_names = {theme["theme"] for theme in bundle["themes"]}
    response_ids = set(comments_by_id)

    for claim in report.get("claims", []):
        actual = _lookup(bundle, claim["metric"], claim["scope"])
        ok = _close(actual, claim["value"])
        entry = {
            "metric": claim["metric"],
            "scope": claim["scope"],
            "reported": claim["value"],
            "actual": actual,
            "passed": ok,
        }
        checks.append(entry)
        if not ok:
            failures.append(
                {
                    "check": "numeric_claim",
                    "detail": f"{claim['metric']} for {claim['scope']} is {claim['value']}, calculated value is {actual}.",
                }
            )

    for quote in report.get("quotes", []):
        actual_comment = comments_by_id.get(quote.get("response_id"))
        if actual_comment is None or actual_comment != quote.get("comment"):
            failures.append(
                {
                    "check": "quoted_comment",
                    "detail": f"Comment for {quote.get('response_id')} is not an exact survey comment.",
                }
            )
        else:
            checks.append({"check": "quoted_comment", "response_id": quote["response_id"], "passed": True})

    for theme in report.get("named_themes", []):
        if theme not in theme_names:
            failures.append({"check": "theme", "detail": f"{theme} is not in the theme results."})
        else:
            checks.append({"check": "theme", "theme": theme, "passed": True})

    for response_id in report.get("callback_ids", []):
        if response_id not in response_ids:
            failures.append({"check": "callback", "detail": f"{response_id} is not a survey response."})
        else:
            checks.append({"check": "callback", "response_id": response_id, "passed": True})

    low_samples = [
        f"{row['segment_type']}:{row['segment']}"
        for rows in bundle["segments"].values()
        for row in rows
        if row.get("low_sample")
    ]
    if low_samples and not report.get("small_samples_disclosed"):
        warnings.append({"check": "small_sample_caveat", "detail": "At least one segment is below the minimum sample and the report does not say so."})
    if not report.get("assumptions_disclosed"):
        warnings.append({"check": "assumptions", "detail": "Churn assumptions are not disclosed."})
    missing_revenue = bundle["revenue"]["missing_revenue_count"]
    missing_comments = bundle["quality"]["missing_comment_count"]
    if (missing_revenue or missing_comments) and not report.get("missing_data_disclosed"):
        warnings.append({"check": "missing_data", "detail": "Missing revenue or comments are not disclosed."})
    if missing_revenue and report.get("missing_revenue_treated_as_zero"):
        failures.append({"check": "missing_revenue_as_zero", "detail": "Missing revenue was treated as zero."})

    return {"passed": not failures, "checks": checks, "failures": failures, "warnings": warnings}
