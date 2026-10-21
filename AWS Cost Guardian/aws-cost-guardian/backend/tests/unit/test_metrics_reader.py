from app.aws.metrics_reader import collect_metrics


class _CloudWatch:
    def __init__(self) -> None:
        self.calls = []

    def get_metric_statistics(self, **kwargs):
        self.calls.append(kwargs)
        return {"Datapoints": [{"Sum": 0, "SampleCount": 14}]}


def test_load_balancer_request_count_is_measured_from_the_daily_sum() -> None:
    cloudwatch = _CloudWatch()
    metrics, problem = collect_metrics(
        cloudwatch,
        [
            {
                "resource_id": "arn:aws:elasticloadbalancing:us-east-1:1:loadbalancer/app/old/abc",
                "resource_type": "load_balancer",
                "service": "ELB",
            }
        ],
    )
    assert problem is None
    assert metrics[0]["metric_name"] == "RequestCount"
    assert metrics[0]["average"] == 0
    assert cloudwatch.calls[0]["Namespace"] == "AWS/ApplicationELB"
    assert cloudwatch.calls[0]["Dimensions"] == [{"Name": "LoadBalancer", "Value": "app/old/abc"}]
