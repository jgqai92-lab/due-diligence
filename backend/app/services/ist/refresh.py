"""IST refresh workflow: incremental update of completed screens."""

import json
import logging
from datetime import datetime, timezone

from app.database import SessionLocal
from app.models.ist import (
    ISTBottleneck,
    ISTCatalystCalendar,
    ISTClaim,
    ISTEquityCandidate,
    ISTMasterScreen,
    ISTReport,
    ISTRotationStrategy,
    ISTScreen,
    ISTStressTest,
)
from app.models.ist_refresh import ISTScreenRefresh
from app.services.ist.content_extraction import _run_content_extraction, _run_source_bias
from app.services.ist.dialectic import (
    _run_dialectic_optimist,
    _run_dialectic_pessimist,
    _run_dialectic_synthesis,
)
from app.services.ist.equity_identification import (
    _run_effects_analysis,
    _run_equity_scanning,
    _run_tier_classification,
)
from app.services.ist.final_synthesis import (
    _run_catalyst_calendar,
    _run_hfrt_handoff_generation,
    _run_master_screen,
    _run_report_generation,
    _run_rotation_strategy,
    _run_screen_certification,
    _run_stress_tests,
)
from app.services.ist.thematic_analysis import (
    _run_bottleneck_mapping,
    _run_demand_modeling,
    _run_external_validation,
)
from app.services.ist.claude_client import get_step_model_tier
from app.services.workflow_engine import register_step

logger = logging.getLogger(__name__)


IST_REFRESH_WORKFLOW_STEPS = [
    {"step_name": "delta_extraction", "phase": 1, "phase_name": "Delta Extraction", "step_order": 1, "depends_on": [], "model": "sonnet"},
    {"step_name": "delta_bias_assessment", "phase": 1, "phase_name": "Delta Extraction", "step_order": 2, "depends_on": ["delta_extraction"], "model": "sonnet"},
    {"step_name": "delta_sufficiency_gate", "phase": 1, "phase_name": "Delta Extraction", "step_order": 3, "depends_on": ["delta_bias_assessment"], "model": "none"},
    {"step_name": "impact_assessment", "phase": 2, "phase_name": "Re-Analysis", "step_order": 4, "depends_on": ["delta_sufficiency_gate"], "model": "opus"},
    {"step_name": "selective_reanalysis", "phase": 2, "phase_name": "Re-Analysis", "step_order": 5, "depends_on": ["impact_assessment"], "model": "opus"},
    {"step_name": "refresh_invariant_check", "phase": 2, "phase_name": "Re-Analysis", "step_order": 6, "depends_on": ["selective_reanalysis"], "model": "none"},
    {"step_name": "conditional_resynthesis", "phase": 3, "phase_name": "Re-Synthesis", "step_order": 7, "depends_on": ["refresh_invariant_check"], "model": "opus"},
    {"step_name": "refresh_certification", "phase": 3, "phase_name": "Re-Synthesis", "step_order": 8, "depends_on": ["conditional_resynthesis"], "model": "sonnet"},
]


def _load_json(value: str | None, fallback):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return fallback


def _merge_refresh_notes(refresh: ISTScreenRefresh, patch: dict) -> None:
    notes = _load_json(refresh.refresh_notes, {})
    if not isinstance(notes, dict):
        notes = {}
    notes.update(patch)
    refresh.refresh_notes = json.dumps(notes)


def _get_refresh_by_run(db, workflow_run_id: int) -> ISTScreenRefresh:
    refresh = (
        db.query(ISTScreenRefresh)
        .filter(ISTScreenRefresh.workflow_run_id == workflow_run_id)
        .first()
    )
    if not refresh:
        raise ValueError(f"No refresh found for workflow {workflow_run_id}")
    return refresh


def _get_refresh_screen(db, refresh: ISTScreenRefresh) -> ISTScreen:
    screen = db.query(ISTScreen).filter(ISTScreen.id == refresh.screen_id).first()
    if not screen:
        raise ValueError(f"No IST screen found for refresh {refresh.id}")
    return screen


def _mark_refresh_failed(
    db,
    refresh: ISTScreenRefresh,
    screen: ISTScreen | None,
    exc: Exception,
) -> None:
    logger.exception(
        "IST refresh failed",
        extra={
            "refresh_id": refresh.id if refresh else None,
            "screen_id": screen.id if screen else None,
            "error": str(exc),
        },
    )
    now = datetime.now(timezone.utc)
    refresh.status = "FAILED"
    refresh.error_message = str(exc)[:1000]
    refresh.completed_at = now
    if screen:
        # Keep canonical screen lifecycle stable even when refresh fails.
        screen.active_workflow_run_id = screen.workflow_run_id
        screen.status = "COMPLETED"
        screen.updated_at = now
    db.commit()


@register_step("IST_REFRESH", "delta_extraction")
async def handle_delta_extraction(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    refresh = None
    screen = None
    try:
        logger.info("Starting delta_extraction", extra={"workflow_run_id": workflow_run_id})
        refresh = _get_refresh_by_run(db, workflow_run_id)
        screen = _get_refresh_screen(db, refresh)

        refresh.status = "EXTRACTING"
        refresh.started_at = refresh.started_at or datetime.now(timezone.utc)
        db.commit()

        model = await get_step_model_tier(workflow_run_id, "delta_extraction")
        result = await _run_content_extraction(
            screen,
            db,
            workflow_run_id,
            raw_content=refresh.delta_content,
            claim_source_refresh_id=refresh.id,
            update_screen_status=False,
            replace_claims=False,
            model=model,
        )

        _merge_refresh_notes(
            refresh,
            {
                "deltaExtraction": result or {},
            },
        )

        delta_claims = (
            db.query(ISTClaim)
            .filter(
                ISTClaim.screen_id == screen.id,
                ISTClaim.source_refresh_id == refresh.id,
            )
            .order_by(ISTClaim.id)
            .all()
        )
        refresh.new_claims_count = len(delta_claims)
        refresh.new_claims = json.dumps(
            [
                {
                    "id": claim.id,
                    "claimText": claim.claim_text,
                    "sourceCitation": claim.source_citation,
                    "quantitativeAnchor": claim.quantitative_anchor,
                    "temporalMarker": claim.temporal_marker,
                    "confidence": claim.confidence,
                }
                for claim in delta_claims
            ]
        )
        db.commit()
        return result
    except Exception as exc:
        if refresh is not None:
            _mark_refresh_failed(db, refresh, screen, exc)
        raise
    finally:
        db.close()


@register_step("IST_REFRESH", "delta_bias_assessment")
async def handle_delta_bias_assessment(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    refresh = None
    screen = None
    try:
        logger.info("Starting delta_bias_assessment", extra={"workflow_run_id": workflow_run_id})
        refresh = _get_refresh_by_run(db, workflow_run_id)
        screen = _get_refresh_screen(db, refresh)

        refresh.status = "EXTRACTING"
        db.commit()

        model = await get_step_model_tier(workflow_run_id, "delta_bias_assessment")
        result = await _run_source_bias(
            screen,
            db,
            workflow_run_id,
            raw_content=refresh.delta_content,
            target_refresh=refresh,
            model=model,
        )
        _merge_refresh_notes(refresh, {"deltaBiasAssessment": result or {}})
        db.commit()
        return result
    except Exception as exc:
        if refresh is not None:
            _mark_refresh_failed(db, refresh, screen, exc)
        raise
    finally:
        db.close()


@register_step("IST_REFRESH", "delta_sufficiency_gate")
async def handle_delta_sufficiency_gate(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    refresh = None
    screen = None
    try:
        logger.info("Starting delta_sufficiency_gate", extra={"workflow_run_id": workflow_run_id})
        refresh = _get_refresh_by_run(db, workflow_run_id)
        screen = _get_refresh_screen(db, refresh)

        refresh.status = "ASSESSING"

        delta_claim_count = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id, ISTClaim.source_refresh_id == refresh.id)
            .count()
        )
        delta_quant_anchor_count = (
            db.query(ISTClaim)
            .filter(
                ISTClaim.screen_id == screen.id,
                ISTClaim.source_refresh_id == refresh.id,
                ISTClaim.quantitative_anchor.isnot(None),
            )
            .count()
        )

        if delta_claim_count < 1:
            raise ValueError("New content adds no investable claims.")
        if delta_quant_anchor_count < 1:
            raise ValueError("New content adds no investable claims with quantitative anchors.")

        db.commit()
        return {
            "gateResult": "PASSED",
            "deltaClaimCount": delta_claim_count,
            "deltaQuantAnchorCount": delta_quant_anchor_count,
        }
    except Exception as exc:
        if refresh is not None:
            _mark_refresh_failed(db, refresh, screen, exc)
        raise
    finally:
        db.close()


@register_step("IST_REFRESH", "impact_assessment")
async def handle_impact_assessment(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    refresh = None
    screen = None
    try:
        logger.info("Starting impact_assessment", extra={"workflow_run_id": workflow_run_id})
        refresh = _get_refresh_by_run(db, workflow_run_id)
        screen = _get_refresh_screen(db, refresh)

        refresh.status = "ASSESSING"

        delta_claim_count = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id, ISTClaim.source_refresh_id == refresh.id)
            .count()
        )

        if delta_claim_count < 1:
            raise ValueError("Refresh delta extraction produced no claims.")

        impact = {
            "bottleneck_mapping": {"needed": True, "reason": "Delta claims added"},
            "demand_modeling": {"needed": True, "reason": "Bottleneck updates require model recomputation"},
            "external_validation": {"needed": True, "reason": "New claims require validation coverage"},
            "equity_scanning": {"needed": True, "reason": "Delta claims may change candidate set"},
            "tier_classification": {"needed": True, "reason": "Candidate set changes require re-tiering"},
            "effects_analysis": {"needed": True, "reason": "Downstream effects depend on updated candidates"},
            "dialectic": {"needed": True, "reason": "Updated tiers require refreshed dialectic"},
            "final_synthesis": {"needed": True, "reason": "Master screen/report must reflect refreshed analysis"},
        }

        refresh.impact_assessment = json.dumps(impact)
        db.commit()
        return impact
    except Exception as exc:
        if refresh is not None:
            _mark_refresh_failed(db, refresh, screen, exc)
        raise
    finally:
        db.close()


@register_step("IST_REFRESH", "selective_reanalysis")
async def handle_selective_reanalysis(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    refresh = None
    screen = None
    try:
        logger.info("Starting selective_reanalysis", extra={"workflow_run_id": workflow_run_id})
        refresh = _get_refresh_by_run(db, workflow_run_id)
        screen = _get_refresh_screen(db, refresh)

        refresh.status = "RE_ANALYZING"
        db.commit()

        impact = _load_json(refresh.impact_assessment, {})
        if not isinstance(impact, dict):
            impact = {}

        def _needed(step_name: str) -> bool:
            step_data = impact.get(step_name)
            return bool(isinstance(step_data, dict) and step_data.get("needed"))

        steps_reexecuted: list[str] = []
        pre_candidates = (
            db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == screen.id)
            .order_by(ISTEquityCandidate.id)
            .all()
        )
        previous_tiers = {c.ticker: c.tier for c in pre_candidates}

        claims = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .order_by(ISTClaim.id)
            .all()
        )

        if _needed("bottleneck_mapping"):
            model = await get_step_model_tier(workflow_run_id, "selective_reanalysis")
            await _run_bottleneck_mapping(
                screen,
                claims,
                db,
                workflow_run_id,
                update_screen_status=False,
                replace_artifact=True,
                model=model,
            )
            steps_reexecuted.append("bottleneck_mapping")

        bottlenecks = (
            db.query(ISTBottleneck)
            .filter(ISTBottleneck.screen_id == screen.id)
            .order_by(ISTBottleneck.id)
            .all()
        )

        if _needed("demand_modeling"):
            await _run_demand_modeling(
                screen,
                bottlenecks,
                db,
                workflow_run_id,
                replace_artifact=True,
                model=model,
            )
            steps_reexecuted.append("demand_modeling")

        if _needed("external_validation"):
            await _run_external_validation(
                screen,
                claims,
                db,
                workflow_run_id,
                replace_artifact=True,
                model=model,
            )
            steps_reexecuted.append("external_validation")

        claims = (
            db.query(ISTClaim)
            .filter(ISTClaim.screen_id == screen.id)
            .order_by(ISTClaim.id)
            .all()
        )
        bottlenecks = (
            db.query(ISTBottleneck)
            .filter(ISTBottleneck.screen_id == screen.id)
            .order_by(ISTBottleneck.id)
            .all()
        )

        if _needed("equity_scanning"):
            await _run_equity_scanning(
                screen,
                bottlenecks,
                claims,
                db,
                workflow_run_id,
                update_screen_status=False,
                replace_artifact=True,
                model=model,
            )
            steps_reexecuted.append("equity_scanning")

        candidates = (
            db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == screen.id)
            .order_by(ISTEquityCandidate.id)
            .all()
        )

        if _needed("tier_classification"):
            await _run_tier_classification(
                screen,
                candidates,
                db,
                workflow_run_id,
            )
            steps_reexecuted.append("tier_classification")

        if _needed("effects_analysis"):
            await _run_effects_analysis(
                screen,
                bottlenecks,
                candidates,
                db,
                workflow_run_id,
                replace_artifact=True,
                model=model,
            )
            steps_reexecuted.append("effects_analysis")

        if _needed("dialectic"):
            await _run_dialectic_optimist(
                screen,
                db,
                workflow_run_id,
                update_screen_status=False,
                replace_artifact=True,
                model=model,
            )
            await _run_dialectic_pessimist(
                screen,
                db,
                workflow_run_id,
                replace_artifact=True,
                model=model,
            )
            await _run_dialectic_synthesis(
                screen,
                db,
                workflow_run_id,
                replace_artifact=True,
                model=model,
            )
            steps_reexecuted.extend(
                [
                    "dialectic_optimist",
                    "dialectic_pessimist",
                    "dialectic_synthesis",
                ]
            )

        post_candidates = (
            db.query(ISTEquityCandidate)
            .filter(ISTEquityCandidate.screen_id == screen.id)
            .order_by(ISTEquityCandidate.id)
            .all()
        )
        tier_changes = []
        for candidate in post_candidates:
            old_tier = previous_tiers.get(candidate.ticker)
            if old_tier is None or old_tier == candidate.tier:
                continue
            tier_changes.append(
                {
                    "ticker": candidate.ticker,
                    "oldTier": old_tier,
                    "newTier": candidate.tier,
                    "rationale": "Tier changed after selective reanalysis",
                }
            )

        refresh.tier_changes = json.dumps(tier_changes)
        refresh.tier_change_count = len(tier_changes)
        refresh.steps_reexecuted = json.dumps(steps_reexecuted)
        _merge_refresh_notes(
            refresh,
            {
                "tierChanges": tier_changes,
            },
        )
        db.commit()
        return {
            "stepsReexecuted": steps_reexecuted,
            "tierChangeCount": len(tier_changes),
        }
    except Exception as exc:
        if refresh is not None:
            _mark_refresh_failed(db, refresh, screen, exc)
        raise
    finally:
        db.close()


@register_step("IST_REFRESH", "refresh_invariant_check")
async def handle_refresh_invariant_check(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    refresh = None
    screen = None
    try:
        logger.info("Starting refresh_invariant_check", extra={"workflow_run_id": workflow_run_id})
        refresh = _get_refresh_by_run(db, workflow_run_id)
        screen = _get_refresh_screen(db, refresh)

        refresh.status = "RE_ANALYZING"

        claim_count = db.query(ISTClaim).filter(ISTClaim.screen_id == screen.id).count()
        bottleneck_count = db.query(ISTBottleneck).filter(ISTBottleneck.screen_id == screen.id).count()
        candidate_count = db.query(ISTEquityCandidate).filter(ISTEquityCandidate.screen_id == screen.id).count()

        deficiencies: list[str] = []
        if claim_count < 1:
            deficiencies.append("No claims available after refresh")
        if bottleneck_count < 1:
            deficiencies.append("No bottlenecks available after refresh")
        if candidate_count < 1:
            deficiencies.append("No candidates available after refresh")

        if deficiencies:
            raise ValueError("Refresh invariant check FAILED: " + "; ".join(deficiencies))

        db.commit()
        return {
            "gateResult": "PASSED",
            "claimCount": claim_count,
            "bottleneckCount": bottleneck_count,
            "candidateCount": candidate_count,
        }
    except Exception as exc:
        if refresh is not None:
            _mark_refresh_failed(db, refresh, screen, exc)
        raise
    finally:
        db.close()


@register_step("IST_REFRESH", "conditional_resynthesis")
async def handle_conditional_resynthesis(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    refresh = None
    screen = None
    try:
        logger.info("Starting conditional_resynthesis", extra={"workflow_run_id": workflow_run_id})
        refresh = _get_refresh_by_run(db, workflow_run_id)
        screen = _get_refresh_screen(db, refresh)

        refresh.status = "RE_SYNTHESIZING"
        db.commit()

        impact = _load_json(refresh.impact_assessment, {})
        if not isinstance(impact, dict):
            impact = {}

        needs_resynthesis = bool(
            impact.get("final_synthesis", {}).get("needed")
            or impact.get("tier_classification", {}).get("needed")
            or impact.get("equity_scanning", {}).get("needed")
        )

        if needs_resynthesis:
            # Replace Phase 5 owned artifacts.
            db.query(ISTReport).filter(ISTReport.screen_id == screen.id).delete()
            db.query(ISTStressTest).filter(ISTStressTest.screen_id == screen.id).delete()
            db.query(ISTCatalystCalendar).filter(ISTCatalystCalendar.screen_id == screen.id).delete()
            db.query(ISTRotationStrategy).filter(ISTRotationStrategy.screen_id == screen.id).delete()
            db.query(ISTMasterScreen).filter(ISTMasterScreen.screen_id == screen.id).delete()
            db.commit()

            model = await get_step_model_tier(workflow_run_id, "conditional_resynthesis")
            await _run_master_screen(
                db,
                screen,
                workflow_run_id,
                update_screen_status=False,
                model=model,
            )
            await _run_rotation_strategy(
                db,
                screen,
                workflow_run_id,
                update_screen_status=False,
                model=model,
            )
            await _run_catalyst_calendar(
                db,
                screen,
                workflow_run_id,
                update_screen_status=False,
                model=model,
            )
            await _run_stress_tests(
                db,
                screen,
                workflow_run_id,
                update_screen_status=False,
                model=model,
            )
            await _run_report_generation(
                db,
                screen,
                workflow_run_id,
                update_screen_status=False,
                model=model,
            )

            screen.updated_at = datetime.now(timezone.utc)
            _merge_refresh_notes(refresh, {"resynthesis": "full"})
            db.commit()
            return {"resynthesized": True}

        _merge_refresh_notes(refresh, {"resynthesis": "skipped"})
        db.commit()
        return {"resynthesized": False}
    except Exception as exc:
        if refresh is not None:
            _mark_refresh_failed(db, refresh, screen, exc)
        raise
    finally:
        db.close()


@register_step("IST_REFRESH", "refresh_certification")
async def handle_refresh_certification(workflow_run_id: int) -> dict | None:
    db = SessionLocal()
    refresh = None
    screen = None
    try:
        logger.info("Starting refresh_certification", extra={"workflow_run_id": workflow_run_id})
        refresh = _get_refresh_by_run(db, workflow_run_id)
        screen = _get_refresh_screen(db, refresh)

        refresh.status = "RE_SYNTHESIZING"
        db.commit()

        await _run_screen_certification(
            db,
            screen,
            workflow_run_id,
            update_screen_status=False,
        )
        await _run_hfrt_handoff_generation(
            db,
            screen,
            workflow_run_id,
            update_screen_status=False,
        )

        now = datetime.now(timezone.utc)
        screen.status = "COMPLETED"
        screen.active_workflow_run_id = screen.workflow_run_id
        screen.refresh_count = int(screen.refresh_count or 0) + 1
        screen.last_refreshed_at = now
        screen.updated_at = now

        refresh.status = "COMPLETED"
        refresh.error_message = None
        refresh.completed_at = now
        db.commit()

        return {
            "refreshId": refresh.id,
            "status": refresh.status,
            "refreshCount": screen.refresh_count,
            "completedAt": now.isoformat(),
        }
    except Exception as exc:
        if refresh is not None:
            _mark_refresh_failed(db, refresh, screen, exc)
        raise
    finally:
        db.close()
