from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime, UniqueConstraint, Index
from app.models import Base


class CachedFinancial(Base):
    __tablename__ = "cached_financials"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(Text, nullable=False)
    data_type = Column(Text, nullable=False)
    raw_json = Column(Text, nullable=False)
    fetched_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=False)

    __table_args__ = (
        UniqueConstraint("ticker", "data_type", name="uq_cache_ticker_type"),
        Index("idx_cache_lookup", "ticker", "data_type", "expires_at"),
        Index("idx_cache_expiry", "expires_at"),
    )
