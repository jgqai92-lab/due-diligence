from datetime import datetime
from sqlalchemy import Column, Integer, Float, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from app.models import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    holding_id = Column(Integer, ForeignKey("holdings.id", ondelete="SET NULL"), nullable=True)
    ticker = Column(Text, nullable=False)
    alert_type = Column(Text, nullable=False)
    severity = Column(Text, nullable=False)
    message = Column(Text, nullable=False)
    previous_value = Column(Float)
    current_value = Column(Float)
    details = Column(Text)
    is_dismissed = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    holding = relationship("Holding", back_populates="alerts")
