"""Alert management endpoints."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.alerts import Alert
from app.schemas.alerts import AlertResponse, AlertsListResponse

router = APIRouter(prefix="/api/alerts", tags=["alerts"])


@router.get("", response_model=AlertsListResponse)
def list_alerts(
    severity: str | None = Query(None),
    dismissed: bool | None = Query(None),
    ticker: str | None = Query(None),
    db: Session = Depends(get_db),
):
    """List alerts with optional filters."""
    query = db.query(Alert)

    if severity:
        query = query.filter(Alert.severity == severity.lower())
    if dismissed is not None:
        query = query.filter(Alert.is_dismissed == (1 if dismissed else 0))
    if ticker:
        query = query.filter(Alert.ticker == ticker.upper())

    query = query.order_by(Alert.created_at.desc())
    alerts = query.all()

    undismissed = sum(1 for a in alerts if not a.is_dismissed)

    return AlertsListResponse(
        alerts=[
            AlertResponse(
                id=a.id,
                ticker=a.ticker,
                alert_type=a.alert_type,
                severity=a.severity,
                message=a.message,
                dismissed=bool(a.is_dismissed),
                created_at=a.created_at.isoformat() + "Z" if a.created_at else "",
                previous_value=a.previous_value,
                current_value=a.current_value,
            )
            for a in alerts
        ],
        count=len(alerts),
        undismissed_count=undismissed,
    )


@router.delete("/{alert_id}")
def dismiss_alert(alert_id: int, db: Session = Depends(get_db)):
    """Dismiss an alert."""
    alert = db.query(Alert).filter(Alert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail={"error": {"code": "NOT_FOUND", "message": "Alert not found"}})

    alert.is_dismissed = 1
    db.commit()
    return {"message": "Alert dismissed", "id": alert_id}
