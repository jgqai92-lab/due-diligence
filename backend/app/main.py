"""FastAPI application entry point for The Skeptical Analyst."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.config import settings
from app.database import engine
from app.models import Base
from app.routers import (
    alerts,
    analyze,
    bridge,
    frameworks,
    hfrt,
    ist,
    ist_synthesis,
    personas,
    portfolio,
    search,
    watchlist,
    workflows,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)


def _run_schema_migrations():
    """Alembic-free column migrations for additive changes.

    Each migration checks for the column's existence and adds it if missing.
    Safe to run on every startup — no-op if columns already exist.
    """
    try:
        from sqlalchemy import text, inspect
        with engine.connect() as conn:
            inspector = inspect(engine)

            # Gap 1: Add external_validation_results to hfrt_projects
            existing_cols = {c["name"] for c in inspector.get_columns("hfrt_projects")}
            if "external_validation_results" not in existing_cols:
                conn.execute(
                    text("ALTER TABLE hfrt_projects ADD COLUMN external_validation_results TEXT")
                )
                conn.commit()
                logger.info("Migration: added external_validation_results to hfrt_projects")
    except Exception as exc:
        # Non-fatal: log and continue. Table may not exist yet on fresh DBs.
        logger.warning("Schema migration warning (non-fatal): %s", exc)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create tables on startup if they don't exist, then run additive migrations."""
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables verified.")
    _run_schema_migrations()
    yield


app = FastAPI(
    title="The Skeptical Analyst",
    description="Forensic Due Diligence & Portfolio Engine",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(analyze.router)
app.include_router(search.router)
app.include_router(portfolio.router)
app.include_router(alerts.router)
app.include_router(workflows.router)
app.include_router(ist.router)
app.include_router(ist_synthesis.router)
app.include_router(hfrt.router)
app.include_router(frameworks.router)
app.include_router(personas.router)
app.include_router(bridge.router)
app.include_router(watchlist.router)

# Register IST step handlers by importing the service modules
from app.services.ist import content_extraction as _ist_content_extraction  # noqa: F401
from app.services.ist import thematic_analysis as _ist_thematic_analysis  # noqa: F401
from app.services.ist import equity_identification as _ist_equity_identification  # noqa: F401
from app.services.ist import dialectic as _ist_dialectic  # noqa: F401
from app.services.ist import final_synthesis as _ist_final_synthesis  # noqa: F401
from app.services.ist import refresh as _ist_refresh  # noqa: F401
from app.services.ist import synthesis as _ist_synthesis  # noqa: F401

# Register HFRT step handlers by importing the service modules
from app.services.hfrt import idea_screener as _hfrt_idea_screener  # noqa: F401
from app.services.hfrt import fundamental_analyst as _hfrt_fundamental  # noqa: F401
from app.services.hfrt import industry_analyst as _hfrt_industry  # noqa: F401
from app.services.hfrt import quantitative_analyst as _hfrt_quantitative  # noqa: F401
from app.services.hfrt import due_diligence as _hfrt_due_diligence  # noqa: F401
from app.services.hfrt import dialectic as _hfrt_dialectic  # noqa: F401
from app.services.hfrt import thesis_synthesizer as _hfrt_thesis  # noqa: F401


@app.get("/api/health")
def health_check():
    return {"status": "ok", "service": "skeptical-analyst"}
