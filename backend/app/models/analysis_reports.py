from datetime import datetime
from sqlalchemy import Column, Integer, Text, String, DateTime
from app.models import Base


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(Text, nullable=False)
    company_name = Column(Text)
    sector = Column(Text)
    beneish_m_score = Column(Text)
    altman_z_score = Column(Text)
    altman_z_score_saas = Column(Text)
    rule_of_40 = Column(Text)
    magic_number = Column(Text)
    llm_report = Column(Text)
    bear_case = Column(Text)
    red_flags = Column(Text)
    data_sources = Column(Text)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    # New columns for comprehensive analysis (Wave 1)
    comprehensive_analysis = Column(Text)  # JSON blob of all metrics
    sector_category = Column(String)  # Detected sector category (e.g., SAAS, FINANCIAL)
