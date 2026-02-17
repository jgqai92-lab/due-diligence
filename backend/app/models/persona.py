"""Persona Overlay models -- persona_analyses table.

Stores individual and trio persona analysis results (Visser, Meldrum, Wissner-Gross).
"""

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    Integer,
    Text,
    DateTime,
    Index,
)

from app.models import Base


class PersonaAnalysis(Base):
    """Stores persona analysis results for Visser, Meldrum, Wissner-Gross, and trio summaries."""

    __tablename__ = "persona_analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    persona_name = Column(Text, nullable=False, index=True)  # "visser", "meldrum", "wissner_gross", "trio_summary"
    target_type = Column(Text, nullable=False)  # "ist_screen", "hfrt_project", "standalone"
    target_id = Column(Integer, nullable=True)  # FK to IST screen or HFRT project (null for standalone)
    input_context = Column(Text, nullable=False)  # JSON: the thesis/data sent to the persona
    analysis_result = Column(Text, nullable=True)  # JSON: structured persona output
    raw_response = Column(Text, nullable=True)  # Full Claude response markdown
    model_used = Column(Text, nullable=True)  # Claude model ID
    tokens_used = Column(Integer, nullable=True)  # Total tokens consumed
    created_at = Column(
        DateTime, nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    __table_args__ = (
        Index("ix_persona_target", "target_type", "target_id"),
        Index("ix_persona_name_created", "persona_name", "created_at"),
    )
