from pydantic import BaseModel


class ScanStep(BaseModel):
    service: str
    status: str
    error: str | None = None
    detail: str | None = None
    timestamp: str


class ScanResponse(BaseModel):
    status: str
    steps: list[ScanStep]
