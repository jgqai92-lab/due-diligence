from pydantic import BaseModel


class AlertResponse(BaseModel):
    id: int
    ticker: str
    alert_type: str
    severity: str
    message: str
    dismissed: bool = False
    created_at: str = ""
    previous_value: float | None = None
    current_value: float | None = None

    model_config = {"from_attributes": True}


class AlertsListResponse(BaseModel):
    alerts: list[AlertResponse]
    count: int
    undismissed_count: int
