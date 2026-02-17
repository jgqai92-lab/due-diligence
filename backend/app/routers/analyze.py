"""Analysis endpoints — comprehensive due diligence engine."""

import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

from app.database import get_db
from app.schemas.analysis import AnalysisResponse, CompanyProfile, DataSources, ForensicReport, FinancialStatements, FinancialStatement
from app.models.analysis_reports import AnalysisReport
from app.services.yfinance_service import fetch_financial_data, clear_cache, transform_statement
from app.services.forensic_engine import run_forensic_analysis, run_comprehensive_analysis
from app.services.citation_service import validate_citations
from app.services.claude_service import generate_report
from app.services.alert_service import generate_comprehensive_alerts
from app.utils.validators import validate_ticker

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/analyze", tags=["analysis"])


def _build_response(ticker: str, data: dict, force_refresh: bool = False, db: Session = None) -> AnalysisResponse:
    """Run the full analysis pipeline and return comprehensive response."""
    info = data.get("info", {})

    # Company profile
    profile = CompanyProfile(
        name=info.get("longName", info.get("shortName", ticker)),
        sector=info.get("sector", ""),
        industry=info.get("industry", ""),
        market_cap=info.get("marketCap"),
        full_time_employees=info.get("fullTimeEmployees"),
    )

    # Run forensic calculations (backward compatibility)
    forensic_metrics = run_forensic_analysis(data)

    # Run comprehensive analysis (new — includes forensic + general metrics)
    comprehensive = run_comprehensive_analysis(data)

    # Validate forensic citations
    issues = validate_citations(forensic_metrics)
    if issues:
        logger.warning("Citation issues for %s: %s", ticker, issues)

    # Build expanded raw summary for Claude (includes balance sheet + cash flow)
    raw_summary = _extract_expanded_summary(data, info)

    # Generate Claude report using comprehensive analysis
    report = generate_report(ticker, profile.name, comprehensive, raw_summary)

    # Data sources
    sources = DataSources(
        provider="yfinance",
        periods=data.get("periods", []),
        fetched_at=data.get("fetched_at", ""),
        cache_hit=data.get("cache_hit", False),
    )

    # Store report in DB
    if db:
        _store_report(db, ticker, profile, forensic_metrics, comprehensive, report, sources)

    # Generate alerts from comprehensive analysis metrics
    if db:
        try:
            generated_alerts = generate_comprehensive_alerts(comprehensive, ticker, db=db)
            if generated_alerts:
                logger.info("Generated %d alerts for %s", len(generated_alerts), ticker)
        except Exception as e:
            logger.error("Alert generation failed for %s: %s", ticker, e)

    # Build financial statements from raw cached data
    financial_statements = FinancialStatements(
        income_statement=FinancialStatement(**transform_statement(data.get("financials", {}))),
        balance_sheet=FinancialStatement(**transform_statement(data.get("balance_sheet", {}))),
        cash_flow=FinancialStatement(**transform_statement(data.get("cashflow", {}))),
    )

    return AnalysisResponse(
        ticker=ticker,
        company_profile=profile,
        forensic_metrics=forensic_metrics,
        comprehensive_analysis=comprehensive,
        report=report,
        data_sources=sources,
        financial_statements=financial_statements,
    )


def _extract_key_financials(financials: dict) -> dict:
    """Extract a summary of key financial data for Claude's context."""
    if not financials:
        return {}
    summary = {}
    for period, values in list(financials.items())[:3]:
        if isinstance(values, dict):
            summary[period[:10]] = {
                k: v for k, v in values.items()
                if k in ["Total Revenue", "Gross Profit", "Net Income", "EBIT", "Operating Revenue"]
            }
    return summary


def _extract_balance_sheet_summary(balance_sheet: dict) -> dict:
    """Extract a summary of key balance sheet data for Claude's context."""
    if not balance_sheet:
        return {}
    summary = {}
    key_fields = [
        "Total Assets", "Total Liabilities Net Minority Interest",
        "Stockholders Equity", "Total Debt", "Current Assets",
        "Current Liabilities", "Cash And Cash Equivalents",
        "Net Receivables", "Retained Earnings",
    ]
    for period, values in list(balance_sheet.items())[:2]:
        if isinstance(values, dict):
            summary[period[:10]] = {
                k: v for k, v in values.items()
                if k in key_fields
            }
    return summary


def _extract_cashflow_summary(cashflow: dict) -> dict:
    """Extract a summary of key cash flow data for Claude's context."""
    if not cashflow:
        return {}
    summary = {}
    key_fields = [
        "Operating Cash Flow", "Capital Expenditure",
        "Free Cash Flow", "Repurchase Of Capital Stock",
        "Issuance Of Debt", "Repayment Of Debt",
        "Common Stock Dividend Paid",
    ]
    for period, values in list(cashflow.items())[:2]:
        if isinstance(values, dict):
            summary[period[:10]] = {
                k: v for k, v in values.items()
                if k in key_fields
            }
    return summary


def _extract_expanded_summary(data: dict, info: dict) -> dict:
    """Build expanded raw data summary for Claude context (financials + balance sheet + cashflow)."""
    return {
        "revenue": _extract_key_financials(data.get("financials", {})),
        "balance_sheet": _extract_balance_sheet_summary(data.get("balance_sheet", {})),
        "cash_flow": _extract_cashflow_summary(data.get("cashflow", {})),
        "market_cap": info.get("marketCap"),
        "enterprise_value": info.get("enterpriseValue"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "employees": info.get("fullTimeEmployees"),
        "beta": info.get("beta"),
        "52w_high": info.get("fiftyTwoWeekHigh"),
        "52w_low": info.get("fiftyTwoWeekLow"),
    }


def _store_report(db: Session, ticker: str, profile: CompanyProfile, forensic_metrics, comprehensive, report, sources):
    """Persist analysis report to SQLite."""
    try:
        db_report = AnalysisReport(
            ticker=ticker,
            company_name=profile.name,
            sector=profile.sector,
            # Legacy forensic columns (backward compatibility)
            beneish_m_score=forensic_metrics.beneish_m_score.model_dump_json(),
            altman_z_score=forensic_metrics.altman_z_score.standard.model_dump_json(),
            altman_z_score_saas=forensic_metrics.altman_z_score.saas_modified.model_dump_json(),
            rule_of_40=forensic_metrics.rule_of_40.model_dump_json(),
            magic_number=forensic_metrics.magic_number.model_dump_json(),
            llm_report=report.markdown,
            bear_case=_extract_bear_case(report.markdown),
            red_flags=json.dumps([]),
            data_sources=sources.model_dump_json(),
            # New comprehensive analysis columns
            comprehensive_analysis=comprehensive.model_dump_json(),
            sector_category=comprehensive.sector_category,
        )
        db.add(db_report)
        db.commit()
    except Exception as e:
        logger.error("Failed to store report for %s: %s", ticker, e)
        db.rollback()


def _extract_bear_case(markdown: str) -> str:
    """Extract the Bear Case section from the markdown report."""
    lines = markdown.split("\n")
    in_bear = False
    bear_lines = []
    for line in lines:
        if "bear case" in line.lower() and line.strip().startswith("#"):
            in_bear = True
            continue
        if in_bear and line.strip().startswith("#"):
            break
        if in_bear:
            bear_lines.append(line)
    return "\n".join(bear_lines).strip()


@router.get("/{ticker}", response_model=AnalysisResponse)
@limiter.limit("10/hour")
def analyze_ticker(request: Request, ticker: str, db: Session = Depends(get_db)):
    """Run comprehensive analysis (uses cache if data < 24h old)."""
    try:
        ticker = validate_ticker(ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "TICKER_INVALID", "message": str(e)}})

    try:
        data = fetch_financial_data(db, ticker, force_refresh=False)
    except Exception as e:
        raise HTTPException(status_code=502, detail={"error": {"code": "YFINANCE_ERROR", "message": str(e)}})

    info = data.get("info", {})
    if not info or not info.get("symbol"):
        raise HTTPException(status_code=404, detail={"error": {"code": "TICKER_NOT_FOUND", "message": f"No data found for {ticker}"}})

    financials = data.get("financials", {})
    if len(financials) < 1:
        raise HTTPException(status_code=422, detail={"error": {"code": "INSUFFICIENT_DATA", "message": f"No financial data available for {ticker}"}})

    return _build_response(ticker, data, db=db)


@router.get("/{ticker}/refresh", response_model=AnalysisResponse)
@limiter.limit("3/hour")
def refresh_analysis(request: Request, ticker: str, db: Session = Depends(get_db)):
    """Force refresh — bypass cache, re-fetch from yfinance."""
    try:
        ticker = validate_ticker(ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "TICKER_INVALID", "message": str(e)}})

    try:
        data = fetch_financial_data(db, ticker, force_refresh=True)
    except Exception as e:
        raise HTTPException(status_code=502, detail={"error": {"code": "YFINANCE_ERROR", "message": str(e)}})

    info = data.get("info", {})
    if not info or not info.get("symbol"):
        raise HTTPException(status_code=404, detail={"error": {"code": "TICKER_NOT_FOUND", "message": f"No data found for {ticker}"}})

    return _build_response(ticker, data, force_refresh=True, db=db)


@router.delete("/{ticker}/cache")
def clear_ticker_cache(ticker: str, db: Session = Depends(get_db)):
    """Clear cached data for a ticker (useful for fixing stale cache issues)."""
    try:
        ticker = validate_ticker(ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "TICKER_INVALID", "message": str(e)}})

    deleted = clear_cache(db, ticker)
    return {
        "ticker": ticker,
        "message": f"Cleared {deleted} cache entries",
        "deleted_count": deleted,
    }


@router.get("/{ticker}/report")
def get_report(ticker: str, db: Session = Depends(get_db)):
    """Retrieve the latest Claude-generated report for a ticker."""
    try:
        ticker = validate_ticker(ticker)
    except ValueError as e:
        raise HTTPException(status_code=400, detail={"error": {"code": "TICKER_INVALID", "message": str(e)}})

    report = (
        db.query(AnalysisReport)
        .filter(AnalysisReport.ticker == ticker)
        .order_by(AnalysisReport.created_at.desc())
        .first()
    )

    if not report:
        raise HTTPException(status_code=404, detail={"error": {"code": "TICKER_NOT_FOUND", "message": f"No report found for {ticker}"}})

    return {
        "ticker": ticker,
        "report": {
            "markdown": report.llm_report or "",
            "generatedAt": report.created_at.isoformat() + "Z" if report.created_at else "",
            "model": "claude-sonnet",
        },
    }
