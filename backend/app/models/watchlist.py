from datetime import datetime
from sqlalchemy import Column, Integer, Text, DateTime
from app.models import Base


class Watchlist(Base):
    __tablename__ = "watchlist"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(Text, nullable=False, unique=True)
    added_at = Column(DateTime, nullable=False, default=datetime.utcnow)
