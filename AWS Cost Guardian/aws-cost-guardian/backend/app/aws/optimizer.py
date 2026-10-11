"""Normalize Compute Optimizer and Cost Optimization Hub. Savings stay zero when AWS does not return a figure."""

from decimal import Decimal

from botocore.exceptions import ClientError

from app.core.logging import get_logger
from app.core.money import as_decimal

logger = get_logger(__name__)


def collect_aws_recommendations(clients: dict) -> tuple[list[dict], list[dict]]:
    recommendations: list[dict] = []
    problems: list[dict] = []
    optimizer, problem = _optimizer(clients.get("compute_optimizer"))
    recommendations.extend(optimizer)
    if problem:
        problems.append(problem)
    hub, problem = _hub(clients.get("cost_optimization_hub"))
    recommendations.extend(hub)
    if problem:
        problems.append(problem)
    return recommendations, problems


def _denied_message(exc: ClientError, permission: str) -> str:
    code = exc.response.get("Error", {}).get("Code", "")
    if code in {"AccessDenied", "AccessDeniedException", "UnauthorizedOperation"}:
        return f"Missing IAM permission. {permission}"
    return "AWS recommendations unavailable."


def _optimizer(client) -> tuple[list[dict], dict | None]:
    if client is None or not hasattr(client, "get_ec2_instance_recommendations"):
        return [], {"service": "compute_optimizer", "error": "Compute Optimizer client was not available."}
    try:
        payload = client.get_ec2_instance_recommendations()
    except ClientError as exc:
        logger.exception("Compute Optimizer read failed")
        return [], {"service": "compute_optimizer", "error": _denied_message(exc, "Compute Optimizer requires compute-optimizer:GetEC2InstanceRecommendations.")}
    except Exception:
        logger.exception("Compute Optimizer read failed")
        return [], {"service": "compute_optimizer", "error": "Compute Optimizer unavailable."}
    rows = []
    for item in payload.get("instanceRecommendations") or []:
        options = item.get("recommendationOptions") or []
        option = options[0] if options else {}
        savings = _savings_value(option.get("savingsOpportunity") or item.get("savingsOpportunity"))
        current = item.get("currentInstanceType")
        recommended = option.get("instanceType")
        rows.append(
            _row(
                source="COMPUTE_OPTIMIZER",
                resource_id=item.get("instanceArn") or item.get("instanceName"),
                service="EC2",
                title=f"Compute Optimizer: {item.get('finding') or 'review instance'}",
                description=(
                    f"Compute Optimizer finding for {current or 'this instance'}"
                    + (f" suggests {recommended}." if recommended else ".")
                    + " Confirm memory, disk, and application behavior before a size change."
                ),
                savings=savings,
                risk="MEDIUM",
                action="REVIEW",
                evidence={
                    "summary": f"Compute Optimizer finding {item.get('finding') or 'unspecified'}.",
                    "facts": [f"Current type {current}" if current else "Current type was not returned"],
                    "assumptions": ["Estimated potential savings are taken only from the Compute Optimizer response."],
                    "pricing_available": savings > 0,
                },
            )
        )
    return rows, None


def _hub(client) -> tuple[list[dict], dict | None]:
    if client is None or not hasattr(client, "list_recommendations"):
        return [], {"service": "cost_optimization_hub", "error": "Cost Optimization Hub client was not available."}
    try:
        payload = client.list_recommendations(maxResults=100)
    except ClientError as exc:
        logger.exception("Cost Optimization Hub read failed")
        return [], {
            "service": "cost_optimization_hub",
            "error": _denied_message(exc, "Cost Optimization Hub requires cost-optimization-hub:ListRecommendations."),
        }
    except Exception:
        logger.exception("Cost Optimization Hub read failed")
        return [], {"service": "cost_optimization_hub", "error": "Cost Optimization Hub unavailable."}
    rows = []
    for item in payload.get("items") or []:
        savings = as_decimal((item.get("estimatedMonthlySavings") or 0))
        action = str(item.get("actionType") or "Review")
        rows.append(
            _row(
                source="COST_OPTIMIZATION_HUB",
                resource_id=item.get("resourceId") or item.get("recommendationId"),
                service=str(item.get("currentResourceType") or "AWS"),
                title=f"Cost Optimization Hub: {action}",
                description="Imported from Cost Optimization Hub. This application did not recalculate the estimate.",
                savings=savings,
                risk="MEDIUM",
                action="REVIEW",
                evidence={
                    "summary": item.get("recommendationId") or "Cost Optimization Hub recommendation",
                    "facts": [f"Action {action}"],
                    "assumptions": ["The monthly figure is the value returned by Cost Optimization Hub."],
                    "pricing_available": savings > 0,
                },
            )
        )
    return rows, None


def _savings_value(opportunity: dict | None) -> Decimal:
    if not isinstance(opportunity, dict):
        return Decimal("0.00")
    estimated = opportunity.get("estimatedMonthlySavings") or {}
    if isinstance(estimated, dict):
        return as_decimal(estimated.get("value"))
    return as_decimal(estimated)


def _row(source: str, resource_id: str | None, service: str, title: str, description: str, savings: Decimal, risk: str, action: str, evidence: dict) -> dict:
    monthly = as_decimal(savings)
    return {
        "resource_id": resource_id,
        "rule_id": source,
        "source": source,
        "service": service,
        "title": title,
        "description": description,
        "evidence": evidence,
        "current_monthly_cost": Decimal("0.00"),
        "estimated_monthly_savings": monthly,
        "estimated_annual_savings": (monthly * 12).quantize(Decimal("0.01")),
        "confidence": "MEDIUM",
        "data_quality": "AWS_RECOMMENDATION",
        "risk_level": risk,
        "action_type": action,
        "status": "OPEN",
    }
