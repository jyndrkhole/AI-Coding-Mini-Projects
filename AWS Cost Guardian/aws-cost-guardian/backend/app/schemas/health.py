from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
    mock_aws: bool
    database: str
