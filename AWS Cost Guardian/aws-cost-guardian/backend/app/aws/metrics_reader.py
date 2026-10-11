"""CloudWatch summaries for inventoried resources. An empty series is missing evidence, not zero usage."""

from datetime import datetime, timedelta, timezone

from botocore.exceptions import ClientError

from app.core.logging import get_logger

logger = get_logger(__name__)

METRIC_LIMIT = 40
WINDOW_DAYS = 14


def collect_metrics(cloudwatch, resources: list[dict], *, now: datetime | None = None) -> tuple[list[dict], dict | None]:
    if cloudwatch is None:
        return [], {"service": "cloudwatch", "error": "CloudWatch client was not available."}
    end = now or datetime.now(timezone.utc)
    start = end - timedelta(days=WINDOW_DAYS)
    metrics: list[dict] = []
    collected = 0
    denied = False
    for resource in resources:
        spec = _spec(resource)
        if spec is None:
            continue
        if collected >= METRIC_LIMIT:
            return metrics, {
                "service": "cloudwatch",
                "error": f"Metrics were collected for the first {METRIC_LIMIT} eligible resources. The rest were not measured.",
            }
        collected += 1
        for namespace, metric_name, dimension in spec:
            try:
                payload = cloudwatch.get_metric_statistics(
                    Namespace=namespace,
                    MetricName=metric_name,
                    Dimensions=[dimension],
                    StartTime=start,
                    EndTime=end,
                    Period=86400,
                    Statistics=["Average", "Minimum", "Maximum", "SampleCount"],
                )
            except ClientError as exc:
                logger.exception("CloudWatch read failed")
                code = exc.response.get("Error", {}).get("Code", "")
                if code in {"AccessDenied", "AccessDeniedException"} and not denied:
                    denied = True
                    return metrics, {"service": "cloudwatch", "error": "Missing IAM permission. CloudWatch requires cloudwatch:GetMetricStatistics."}
                continue
            except Exception:
                logger.exception("CloudWatch read failed")
                continue
            points = payload.get("Datapoints") or []
            if not points:
                continue
            averages = [point["Average"] for point in points if point.get("Average") is not None]
            minimums = [point["Minimum"] for point in points if point.get("Minimum") is not None]
            maximums = [point["Maximum"] for point in points if point.get("Maximum") is not None]
            samples = [point.get("SampleCount") or 0 for point in points]
            if not averages:
                continue
            metrics.append(
                {
                    "resource_id": resource["resource_id"],
                    "metric_name": metric_name,
                    "timestamp": end.isoformat(),
                    "period": 86400,
                    "average": sum(averages) / len(averages),
                    "minimum": min(minimums) if minimums else None,
                    "maximum": max(maximums) if maximums else None,
                    "sample_count": int(sum(samples)),
                }
            )
    return metrics, None


def _spec(resource: dict) -> list[tuple[str, str, dict]] | None:
    resource_id = resource.get("resource_id")
    if not resource_id:
        return None
    if resource.get("service") == "EC2" and resource.get("resource_type") == "instance":
        dimension = {"Name": "InstanceId", "Value": resource_id}
        return [
            ("AWS/EC2", "CPUUtilization", dimension),
            ("AWS/EC2", "NetworkIn", dimension),
            ("AWS/EC2", "NetworkOut", dimension),
        ]
    if resource.get("service") == "RDS":
        dimension = {"Name": "DBInstanceIdentifier", "Value": resource_id}
        return [("AWS/RDS", "CPUUtilization", dimension), ("AWS/RDS", "DatabaseConnections", dimension)]
    if resource.get("resource_type") == "nat_gateway":
        dimension = {"Name": "NatGatewayId", "Value": resource_id}
        return [("AWS/NATGateway", "BytesOutToDestination", dimension)]
    if resource.get("service") == "Lambda":
        dimension = {"Name": "FunctionName", "Value": resource_id}
        return [("AWS/Lambda", "Invocations", dimension)]
    return None
