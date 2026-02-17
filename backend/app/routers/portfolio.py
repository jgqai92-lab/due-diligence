"""Portfolio management endpoints — CRUD + watchdog."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.holdings import Holding
from app.schemas.portfolio import (
    HoldingCreate,
    HoldingUpdate,
    HoldingResponse,
    PortfolioResponse,
    PortfolioSummary,
    WatchdogResult,
)
from app.services.alpaca_service import get_current_price
from app.utils.validators import validate_ticker

router = APIRouter(prefix="/api/portfolio", tags=["portfolio"])


def _enrich_holding(holding: Holding) -> HoldingResponse:
    """Add current price and P&L to a holding."""
    current_price = get_current_price(holding.ticker)
    market_value = None
    gain_loss = None
    gain_loss_pct = None

    if current_price:
        market_value = current_price * holding.shares
        cost_total = holding.cost_basis * holding.shares
        gain_loss = market_value - cost_total
        gain_loss_pct = (gain_loss / cost_total) * 100 if cost_total else None

    return HoldingResponse(
        id=holding.id,
        ticker=holding.ticker,
        shares=holding.shares,
        cost_basis=holding.cost_basis,
        purchase_date=holding.purchase_date,
        current_price=current_price,
        market_value=round(market_value, 2) if market_value else None,
        gain_loss=round(gain_loss, 2) if gain_loss else None,
        gain_loss_percent=round(gain_loss_pct, 2) if gain_loss_pct else None,
    )


@router.get("", response_model=PortfolioResponse)
def list_holdings(db: Session = Depends(get_db)):
    """Get all portfolio holdings with current valuations."""
    holdings = db.query(Holding).all()
    enriched = [_enrich_holding(h) for h in holdings]

    total_market = sum(h.market_value or 0 for h in enriched)
    total_cost = sum(h.cost_basis * h.shares for h in holdings)
    total_gl = total_market - total_cost if total_market else 0

    return PortfolioResponse(
        holdings=enriched,
        summary=PortfolioSummary(
            total_market_value=round(total_market, 2),
            total_cost_basis=round(total_cost, 2),
            total_gain_loss=round(total_gl, 2),
            holding_count=len(holdings),
        ),
    )


@router.post("", response_model=HoldingResponse, status_code=201)
def add_holding(data: HoldingCreate, db: Session = Depends(get_db)):
    """Add a new holding to the portfolio."""
    try:
        ticker = validate_ticker(data.ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "TICKER_INVALID", "message": str(e)}})

    holding = Holding(
        ticker=ticker,
        shares=data.shares,
        cost_basis=data.cost_basis,
        purchase_date=data.purchase_date,
    )
    db.add(holding)
    db.commit()
    db.refresh(holding)
    return _enrich_holding(holding)


@router.patch("/{holding_id}", response_model=HoldingResponse)
def update_holding(holding_id: int, data: HoldingUpdate, db: Session = Depends(get_db)):
    """Update an existing holding."""
    holding = db.query(Holding).filter(Holding.id == holding_id).first()
    if not holding:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Holding not found"}})

    if data.shares is not None:
        holding.shares = data.shares
    if data.cost_basis is not None:
        holding.cost_basis = data.cost_basis
    if data.purchase_date is not None:
        holding.purchase_date = data.purchase_date

    holding.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(holding)
    return _enrich_holding(holding)


@router.delete("/{holding_id}")
def delete_holding(holding_id: int, db: Session = Depends(get_db)):
    """Delete a holding from the portfolio."""
    holding = db.query(Holding).filter(Holding.id == holding_id).first()
    if not holding:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Holding not found"}})

    db.delete(holding)
    db.commit()
    return {"message": "Holding deleted", "id": holding_id}


@router.get("/watchdog", response_model=WatchdogResult)
def run_watchdog(db: Session = Depends(get_db)):
    """Run forensic scan on all portfolio holdings."""
    holdings = db.query(Holding).all()

    # Placeholder — full watchdog implementation would run forensic analysis
    # on each holding and compare against previous values
    return WatchdogResult(
        scanned_count=len(holdings),
        alert_count=0,
        alerts=[],
        last_scan_at=datetime.utcnow().isoformat() + "Z",
    )
