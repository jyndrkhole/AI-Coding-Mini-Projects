"""In-memory Daily Triage Log and real aggregation for the day's exceptions."""

from collections import defaultdict

_log: list[dict] = []


def clear_log() -> None:
    _log.clear()


def record_exception(result: dict) -> dict:
    """Store one processed exception and return it unchanged."""
    _log.append(result)
    return result


def get_log() -> list[dict]:
    return list(_log)


def generate_daily_summary() -> str:
    """Aggregate the session: totals, escalation rate, and the costliest category.

    Costliest category is the one with the highest *sum* of compensation, so
    many small payouts can beat a single large one.
    """
    if not _log:
        return "Daily Triage Summary\n\nNo exceptions processed yet today."

    total_comp = sum(float(item.get("compensation_amount", 0) or 0) for item in _log)
    escalated_count = sum(1 for item in _log if item.get("escalated"))
    rate = escalated_count / len(_log)

    by_category: dict[str, float] = defaultdict(float)
    for item in _log:
        category = item.get("category") or "unknown"
        by_category[category] += float(item.get("compensation_amount", 0) or 0)

    costliest_category = max(by_category, key=by_category.get)
    costliest_total = by_category[costliest_category]

    lines = [
        "Daily Triage Summary",
        "",
        f"Exceptions processed: {len(_log)}",
        f"Total compensation paid: ${total_comp:.2f}",
        f"Escalation rate: {rate:.0%} ({escalated_count}/{len(_log)})",
        (
            f"Costliest category: {costliest_category} "
            f"(${costliest_total:.2f} total compensation)"
        ),
        "",
        "Compensation by category:",
    ]
    for category, total in sorted(by_category.items(), key=lambda kv: kv[1], reverse=True):
        lines.append(f"- {category}: ${total:.2f}")
    return "\n".join(lines)
