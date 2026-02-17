from pydantic import BaseModel


class Citation(BaseModel):
    line_item: str = ""
    filing_type: str = ""
    period: str = ""
    raw_value: float | None = None
    source: str = ""
    formula: str = ""  # Mathematical formula for the metric (e.g., "DSRI = (Receivables_t / Revenue_t) / (Receivables_t-1 / Revenue_t-1)")
    description: str = ""  # Plain-English explanation of what the metric measures


class MetricComponent(BaseModel):
    value: float | None = None
    citation: Citation = Citation()


class BeneishMScoreComponents(BaseModel):
    dsri: MetricComponent = MetricComponent()
    gmi: MetricComponent = MetricComponent()
    aqi: MetricComponent = MetricComponent()
    sgi: MetricComponent = MetricComponent()
    depi: MetricComponent = MetricComponent()
    sgai: MetricComponent = MetricComponent()
    lvgi: MetricComponent = MetricComponent()
    tata: MetricComponent = MetricComponent()


class BeneishThresholds(BaseModel):
    likely_manipulator: float = -1.78
    grey_zone: list[float] = [-2.22, -1.78]


class BeneishMScore(BaseModel):
    composite: float | None = None
    interpretation: str | None = None
    components: BeneishMScoreComponents = BeneishMScoreComponents()
    thresholds: BeneishThresholds = BeneishThresholds()


class AltmanZScoreVariant(BaseModel):
    score: float | None = None
    zone: str | None = None
    components: dict[str, MetricComponent] = {}
    disclaimer: str | None = None


class AltmanZScore(BaseModel):
    standard: AltmanZScoreVariant = AltmanZScoreVariant()
    saas_modified: AltmanZScoreVariant = AltmanZScoreVariant()


class RuleOf40(BaseModel):
    score: float | None = None
    revenue_growth_percent: float | None = None
    fcf_margin_percent: float | None = None
    interpretation: str | None = None
    citations: dict[str, Citation] = {}


class MagicNumber(BaseModel):
    score: float | None = None
    net_new_arr: float | None = None
    sales_and_marketing_spend: float | None = None
    interpretation: str | None = None
    citations: dict[str, Citation] = {}


class ForensicMetrics(BaseModel):
    beneish_m_score: BeneishMScore = BeneishMScore()
    altman_z_score: AltmanZScore = AltmanZScore()
    rule_of_40: RuleOf40 = RuleOf40()
    magic_number: MagicNumber = MagicNumber()


# ─── New General Metric Models ─────────────────────────────────────


class ProfitabilityMetrics(BaseModel):
    gross_margin: MetricComponent = MetricComponent()
    operating_margin: MetricComponent = MetricComponent()
    net_margin: MetricComponent = MetricComponent()
    roe: MetricComponent = MetricComponent()
    roa: MetricComponent = MetricComponent()
    roic: MetricComponent = MetricComponent()


class LeverageMetrics(BaseModel):
    debt_to_equity: MetricComponent = MetricComponent()
    interest_coverage: MetricComponent = MetricComponent()
    current_ratio: MetricComponent = MetricComponent()
    quick_ratio: MetricComponent = MetricComponent()
    net_debt_to_ebitda: MetricComponent = MetricComponent()


class CashFlowMetrics(BaseModel):
    fcf_yield: MetricComponent = MetricComponent()
    ocf_to_net_income: MetricComponent = MetricComponent()
    fcf_margin: MetricComponent = MetricComponent()
    capex_to_revenue: MetricComponent = MetricComponent()


class GrowthMetrics(BaseModel):
    revenue_growth_yoy: MetricComponent = MetricComponent()
    earnings_growth_yoy: MetricComponent = MetricComponent()
    fcf_growth_yoy: MetricComponent = MetricComponent()
    revenue_cagr_3y: MetricComponent = MetricComponent()


class ValuationMetrics(BaseModel):
    pe_trailing: MetricComponent = MetricComponent()
    pe_forward: MetricComponent = MetricComponent()
    ev_to_ebitda: MetricComponent = MetricComponent()
    price_to_fcf: MetricComponent = MetricComponent()
    price_to_sales: MetricComponent = MetricComponent()
    peg_ratio: MetricComponent = MetricComponent()


class ShareholderMetrics(BaseModel):
    dividend_yield: MetricComponent = MetricComponent()
    payout_ratio: MetricComponent = MetricComponent()


class SentimentMetrics(BaseModel):
    analyst_rating: MetricComponent = MetricComponent()
    analyst_count: int | None = None
    analyst_recommendation: str | None = None
    short_ratio: MetricComponent = MetricComponent()
    short_percent_float: MetricComponent = MetricComponent()
    institutional_pct: MetricComponent = MetricComponent()
    insider_pct: MetricComponent = MetricComponent()


class SectorSpecificMetrics(BaseModel):
    sector_category: str = "GENERAL"
    label: str = ""
    metrics: dict[str, MetricComponent] = {}
    interpretations: dict[str, str | None] = {}


class ComprehensiveAnalysis(BaseModel):
    """Top-level model containing forensic scores plus all general metrics."""
    # Forensic (existing, unchanged)
    beneish_m_score: BeneishMScore = BeneishMScore()
    altman_z_score: AltmanZScore = AltmanZScore()
    # General financial health (new)
    profitability: ProfitabilityMetrics = ProfitabilityMetrics()
    leverage: LeverageMetrics = LeverageMetrics()
    cash_flow: CashFlowMetrics = CashFlowMetrics()
    growth: GrowthMetrics = GrowthMetrics()
    valuation: ValuationMetrics = ValuationMetrics()
    shareholder_returns: ShareholderMetrics = ShareholderMetrics()
    sentiment: SentimentMetrics = SentimentMetrics()
    # Sector-specific (conditional)
    sector_category: str = "GENERAL"
    sector_specific: SectorSpecificMetrics | None = None


# ─── Existing Models (unchanged) ──────────────────────────────────


class CompanyProfile(BaseModel):
    name: str = ""
    sector: str = ""
    industry: str = ""
    market_cap: float | None = None
    full_time_employees: int | None = None


class ForensicReport(BaseModel):
    markdown: str = ""
    generated_at: str = ""
    model: str = ""


class DataSources(BaseModel):
    provider: str = "yfinance"
    periods: list[str] = []
    fetched_at: str = ""
    cache_hit: bool = False


# ─── Financial Statement Models ────────────────────────────────────


class FinancialStatementLineItem(BaseModel):
    label: str
    values: list[float | None]


class FinancialStatement(BaseModel):
    periods: list[str] = []
    line_items: list[FinancialStatementLineItem] = []


class FinancialStatements(BaseModel):
    income_statement: FinancialStatement = FinancialStatement()
    balance_sheet: FinancialStatement = FinancialStatement()
    cash_flow: FinancialStatement = FinancialStatement()


class AnalysisResponse(BaseModel):
    ticker: str
    company_profile: CompanyProfile = CompanyProfile()
    forensic_metrics: ForensicMetrics = ForensicMetrics()
    comprehensive_analysis: ComprehensiveAnalysis = ComprehensiveAnalysis()
    report: ForensicReport = ForensicReport()
    data_sources: DataSources = DataSources()
    financial_statements: FinancialStatements = FinancialStatements()

    model_config = {"populate_by_name": True}
