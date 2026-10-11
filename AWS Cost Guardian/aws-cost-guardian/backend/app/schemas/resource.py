from pydantic import BaseModel


class MetricResponse(BaseModel):
    metric_name: str
    timestamp: str | None
    period: int
    average: float | None
    minimum: float | None
    maximum: float | None
    sample_count: int | None


class ResourceResponse(BaseModel):
    id: int
    resource_id: str
    resource_type: str
    service: str
    region: str
    name: str | None
    state: str | None
    instance_type: str | None
    environment: str | None
    tags: dict
    metadata: dict
    metrics: list[MetricResponse] = []


class ResourceListResponse(BaseModel):
    resources: list[ResourceResponse]
