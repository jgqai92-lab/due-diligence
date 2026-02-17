from pydantic import BaseModel, Field


class HoldingCreate(BaseModel):
    ticker: str
    shares: float = Field(gt=0)
    cost_basis: float = Field(gt=0, alias="costBasis")
    purchase_date: str = Field(alias="purchaseDate")

    model_config = {"populate_by_name": True}


class HoldingUpdate(BaseModel):
    shares: float | None = Field(default=None, gt=0)
    cost_basis: float | None = Field(default=None, gt=0, alias="costBasis")
    purchase_date: str | None = Field(default=None, alias="purchaseDate")

    model_config = {"populate_by_name": True}


class HoldingResponse(BaseModel):
    id: int
    ticker: str
    shares: float
    cost_basis: float
    purchase_date: str
    current_price: float | None = None
    market_value: float | None = None
    gain_loss: float | None = None
    gain_loss_percent: float | None = None

    model_config = {"from_attributes": True}


class PortfolioSummary(BaseModel):
    total_market_value: float = 0.0
    total_cost_basis: float = 0.0
    total_gain_loss: float = 0.0
    holding_count: int = 0


class PortfolioResponse(BaseModel):
    holdings: list[HoldingResponse]
    summary: PortfolioSummary


class WatchdogAlert(BaseModel):
    id: int
    ticker: str
    alert_type: str
    severity: str
    message: str
    previous_value: float | None = None
    current_value: float | None = None


class WatchdogResult(BaseModel):
    scanned_count: int = 0
    alert_count: int = 0
    alerts: list[WatchdogAlert] = []
    last_scan_at: str = ""
