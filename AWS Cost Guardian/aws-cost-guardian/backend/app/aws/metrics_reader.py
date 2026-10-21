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
    measurable = [(resource, spec) for resource in resources if (spec := _spec(resource)) is not None]
    measurable.sort(key=lambda item: 0 if _measured_first(item[0]) else 1)
    for resource, spec in measurable:
        if not _measured_first(resource) and collected >= METRIC_LIMIT:
            return metrics, {
                "service": "cloudwatch",
                "error": f"Metrics were collected for the first {METRIC_LIMIT} other resources. Load balancers and databases were still measured.",
            }
        if not _measured_first(resource):
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
                    Statistics=["Average", "Sum", "Minimum", "Maximum", "SampleCount"],
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
            if not averages:
                averages = [point["Sum"] for point in points if point.get("Sum") is not None]
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


def _measured_first(resource: dict) -> bool:
    return resource.get("service") == "RDS" or resource.get("resource_type") == "load_balancer"


def _balancer_dimension(resource_id: str) -> str | None:
    marker = ":loadbalancer/"
    if marker not in resource_id:
        return None
    value = resource_id.split(marker, 1)[1]
    return value or None


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
    if resource.get("resource_type") == "load_balancer":
        dimension_value = _balancer_dimension(str(resource_id))
        if dimension_value is None:
            return None
        kind = dimension_value.split("/", 1)[0]
        if kind == "app":
            namespace, metric_name = "AWS/ApplicationELB", "RequestCount"
        elif kind == "net":
            namespace, metric_name = "AWS/NetworkELB", "ActiveFlowCount"
        elif kind == "gwy":
            namespace, metric_name = "AWS/GatewayELB", "ActiveFlowCount"
        else:
            return None
        return [(namespace, metric_name, {"Name": "LoadBalancer", "Value": dimension_value})]
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
