"""HFRT startup readiness verification (Gap B1).

Checks that all required services and data are available before
starting an HFRT research project. Caches result until app restart.

Called once when the first HFRT project is created in a session.
"""

import logging
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Module-level cache — reset on app restart
_cached_result: Optional["StartupResult"] = None


class StartupResult(BaseModel):
    ready: bool
    issues: list[str] = Field(default_factory=list)
    checks: dict[str, bool] = Field(default_factory=dict)


def verify_hfrt_readiness(force: bool = False) -> StartupResult:
    """Check that all HFRT prerequisites are met.

    Checks:
      1. Database is writable (via SessionLocal)
      2. Claude API key is configured
      3. SEC EDGAR user agent is configured
      4. Framework files are present in data/frameworks/hfrt/

    Args:
        force: If True, bypass cache and re-check.

    Returns:
        StartupResult with ready flag and any issues found.
    """
    global _cached_result
    if _cached_result is not None and not force:
        return _cached_result

    issues: list[str] = []
    checks: dict[str, bool] = {}

    # 1. Database writable
    try:
        from app.database import SessionLocal
        db = SessionLocal()
        try:
            db.execute("SELECT 1")
            checks["database"] = True
        except Exception as e:
            checks["database"] = False
            issues.append(f"Database not writable: {e}")
        finally:
            db.close()
    except Exception as e:
        checks["database"] = False
        issues.append(f"Cannot create database session: {e}")

    # 2. Claude API key configured
    try:
        from app.config import settings
        has_key = bool(getattr(settings, "anthropic_api_key", None))
        checks["claude_api_key"] = has_key
        if not has_key:
            issues.append("ANTHROPIC_API_KEY not configured")
    except Exception as e:
        checks["claude_api_key"] = False
        issues.append(f"Cannot read config: {e}")

    # 3. SEC EDGAR user agent configured
    try:
        from app.config import settings
        has_agent = bool(getattr(settings, "sec_user_agent", None))
        checks["sec_user_agent"] = has_agent
        if not has_agent:
            issues.append("SEC_USER_AGENT not configured — SEC EDGAR requests will fail")
    except Exception:
        checks["sec_user_agent"] = False
        issues.append("Cannot check SEC user agent config")

    # 4. Framework files present
    framework_dir = Path(__file__).resolve().parent.parent / "data" / "frameworks" / "hfrt"
    if framework_dir.exists():
        md_files = list(framework_dir.glob("*.md"))
        checks["framework_files"] = len(md_files) >= 10
        if len(md_files) < 10:
            issues.append(
                f"Only {len(md_files)} HFRT framework files found in {framework_dir} "
                f"(expected >= 10)"
            )
    else:
        checks["framework_files"] = False
        issues.append(f"HFRT framework directory not found: {framework_dir}")

    ready = len(issues) == 0
    result = StartupResult(ready=ready, issues=issues, checks=checks)
    _cached_result = result

    if not ready:
        logger.warning("HFRT readiness check failed: %s", issues)
    else:
        logger.info("HFRT readiness check passed")

    return result


def clear_cache() -> None:
    """Clear the cached readiness result (for testing)."""
    global _cached_result
    _cached_result = None
