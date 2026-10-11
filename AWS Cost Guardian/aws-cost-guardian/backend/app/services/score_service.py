"""Deterministic optimization score from stored inventory and recommendations."""


def calculate_optimization_score(resources: list[dict], recommendations: list[dict]) -> dict:
    penalties = 0
    strengths: list[str] = []
    opportunities: list[str] = []

    unattached = [row for row in resources if row.get("resource_type") == "volume" and row.get("state") == "available"]
    if unattached:
        penalties += min(20, 5 * len(unattached))
        opportunities.append(f"{len(unattached)} unattached volume(s) are stored.")
    else:
        strengths.append("No unattached EBS volumes are stored.")

    always_on = [
        row
        for row in resources
        if row.get("resource_type") == "instance"
        and str(row.get("environment") or "").lower() in {"dev", "development"}
        and row.get("state") == "running"
        and (row.get("metadata") or {}).get("schedule") in (None, "", "none")
    ]
    if always_on:
        penalties += min(15, 5 * len(always_on))
        opportunities.append(f"{len(always_on)} development instance(s) are running without a schedule.")
    else:
        strengths.append("No always-on development instance is stored.")

    if resources:
        covered = sum(1 for row in resources if (row.get("tags") or {}).get("Environment") or (row.get("tags") or {}).get("environment") or row.get("environment"))
        percent = round(covered / len(resources) * 100)
        if percent < 80:
            penalties += 10
            opportunities.append(f"Environment tag coverage is {percent}%.")
        else:
            strengths.append(f"Environment tag coverage is {percent}%.")

    architecture = [row for row in recommendations if row.get("action_type") == "ARCHITECTURE" or row.get("category") == "architecture"]
    if architecture:
        penalties += min(15, 5 * len(architecture))
        opportunities.append(f"{len(architecture)} architecture review(s) are open.")
    else:
        strengths.append("No open architecture review is stored.")

    ranked = sorted(recommendations, key=lambda row: row.get("priority") or 999)
    top = [row.get("title") for row in ranked if row.get("title")][:3]
    return {
        "score": max(0, min(100, 100 - penalties)),
        "maximum": 100,
        "source": "stored_evidence",
        "label": "Cost optimization score",
        "strengths": strengths,
        "opportunities": opportunities,
        "top_improvements": top,
    }
