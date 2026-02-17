from datetime import datetime
from sqlalchemy import Column, Integer, Float, DateTime, CheckConstraint
from app.models import Base


class AlertSettings(Base):
    __tablename__ = "alert_settings"

    id = Column(Integer, primary_key=True)
    # Existing forensic alert toggles
    enable_z_score_alerts = Column(Integer, nullable=False, default=1)
    enable_m_score_alerts = Column(Integer, nullable=False, default=1)
    enable_rule_of_40_alerts = Column(Integer, nullable=False, default=1)
    enable_magic_number_alerts = Column(Integer, nullable=False, default=1)
    z_score_threshold = Column(Float, nullable=False, default=2.99)
    m_score_threshold = Column(Float, nullable=False, default=-1.78)
    # New comprehensive analysis alert toggles (Wave 5)
    enable_profitability_alerts = Column(Integer, nullable=False, default=1)
    enable_leverage_alerts = Column(Integer, nullable=False, default=1)
    enable_cash_flow_alerts = Column(Integer, nullable=False, default=1)
    enable_valuation_alerts = Column(Integer, nullable=False, default=1)
    enable_short_interest_alerts = Column(Integer, nullable=False, default=1)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        CheckConstraint("id = 1", name="ck_alert_settings_single_row"),
    )
