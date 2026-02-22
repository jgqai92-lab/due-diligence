"""Integration tests for IST refresh + synthesis extension endpoints."""

import json
from datetime import datetime, timezone

import pytest
from sqlalchemy.orm import sessionmaker

from app.models.ist import ISTBottleneck, ISTClaim, ISTEquityCandidate, ISTScreen
from app.models.ist_refresh import ISTScreenRefresh
from app.models.ist_synthesis import ISTSynthesisSource
from app.models.workflow import WorkflowRun, WorkflowStep
from app.services.ist.refresh import IST_REFRESH_WORKFLOW_STEPS
from app.services.ist.synthesis import IST_SYNTHESIS_WORKFLOW_STEPS
from app.services.ist import synthesis as synthesis_service


VALID_CONTENT = (
    "This is a test content discussing AI infrastructure demand and supply bottlenecks. "
    "Data center power constraints are worsening and cooling systems remain capacity-limited. "
    "Investment demand is increasing across transmission, backup power, and liquid cooling systems. "
) * 4


def _create_screen(client, name: str, hypothesis: str | None = None):
    payload = {
        "name": name,
        "content": VALID_CONTENT,
        "contentType": "text",
    }
    if hypothesis:
        payload["hypothesis"] = hypothesis
    return client.post("/api/ist/screens", json=payload)


def _mark_completed_certified(db, screen_id: int):
    screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
    assert screen is not None
    run = db.query(WorkflowRun).filter(WorkflowRun.id == screen.workflow_run_id).first()
    assert run is not None

    now = datetime.now(timezone.utc)
    screen.status = "COMPLETED"
    screen.is_certified = 1
    screen.certified_at = now
    run.status = "COMPLETED"
    run.current_phase = 5
    db.commit()


def _extract_json_tag(user_prompt: str, tag: str):
    start = user_prompt.find(f"<{tag}>")
    end = user_prompt.find(f"</{tag}>")
    if start == -1 or end == -1 or end <= start:
        return None
    raw = user_prompt[start + len(tag) + 2 : end].strip()
    if not raw:
        return None
    return json.loads(raw)


class TestISTRefreshEndpoints:
    def test_create_refresh_requires_completed_and_certified(self, client):
        create_resp = _create_screen(client, "Refresh Guardrails")
        assert create_resp.status_code == 201
        screen_id = create_resp.json()["id"]

        resp = client.post(
            f"/api/ist/screens/{screen_id}/refresh",
            json={"content": VALID_CONTENT, "contentType": "text"},
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"]["code"] == "INVALID_STATE"

    def test_create_refresh_success_creates_workflow_and_steps(self, client, db):
        create_resp = _create_screen(client, "Refresh Ready")
        assert create_resp.status_code == 201
        screen_id = create_resp.json()["id"]
        _mark_completed_certified(db, screen_id)

        resp = client.post(
            f"/api/ist/screens/{screen_id}/refresh",
            json={"content": VALID_CONTENT, "contentType": "article"},
        )
        assert resp.status_code == 201
        data = resp.json()
        refresh_id = data["id"]
        refresh_run_id = data["workflowRunId"]
        assert data["status"] == "PENDING"
        assert data["refreshNumber"] == 1

        refresh = db.query(ISTScreenRefresh).filter(ISTScreenRefresh.id == refresh_id).first()
        assert refresh is not None
        assert refresh.workflow_run_id == refresh_run_id
        assert refresh.content_type == "article"

        run = db.query(WorkflowRun).filter(WorkflowRun.id == refresh_run_id).first()
        assert run is not None
        assert run.workflow_type == "IST_REFRESH"

        steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == refresh_run_id)
            .order_by(WorkflowStep.step_order)
            .all()
        )
        assert len(steps) == len(IST_REFRESH_WORKFLOW_STEPS)
        assert [s.step_name for s in steps] == [s["step_name"] for s in IST_REFRESH_WORKFLOW_STEPS]

        screen = db.query(ISTScreen).filter(ISTScreen.id == screen_id).first()
        assert screen is not None
        assert screen.active_workflow_run_id == refresh_run_id

    def test_create_refresh_idempotency_returns_existing(self, client, db):
        create_resp = _create_screen(client, "Refresh Idempotency")
        assert create_resp.status_code == 201
        screen_id = create_resp.json()["id"]
        _mark_completed_certified(db, screen_id)

        payload = {
            "content": VALID_CONTENT,
            "contentType": "text",
            "idempotencyKey": "refresh-key-001",
        }
        first = client.post(f"/api/ist/screens/{screen_id}/refresh", json=payload)
        assert first.status_code == 201
        first_id = first.json()["id"]

        second = client.post(f"/api/ist/screens/{screen_id}/refresh", json=payload)
        assert second.status_code == 201
        second_data = second.json()
        assert second_data["id"] == first_id
        assert second_data["idempotent"] is True

        refresh_count = (
            db.query(ISTScreenRefresh)
            .filter(ISTScreenRefresh.screen_id == screen_id)
            .count()
        )
        assert refresh_count == 1

    def test_refresh_list_detail_and_delta_claims(self, client, db):
        create_resp = _create_screen(client, "Refresh Detail")
        assert create_resp.status_code == 201
        screen_id = create_resp.json()["id"]
        _mark_completed_certified(db, screen_id)

        create_refresh = client.post(
            f"/api/ist/screens/{screen_id}/refresh",
            json={"content": VALID_CONTENT, "contentType": "research_note"},
        )
        assert create_refresh.status_code == 201
        refresh_id = create_refresh.json()["id"]

        db.add(
            ISTClaim(
                screen_id=screen_id,
                source_refresh_id=refresh_id,
                claim_text="Delta claim for refresh list/detail test",
                source_citation="Refresh source section",
                quantitative_anchor="15% CAGR",
                temporal_marker="2027",
                confidence=0.82,
            )
        )
        db.commit()

        list_resp = client.get(f"/api/ist/screens/{screen_id}/refreshes")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] == 1
        assert list_data["refreshes"][0]["id"] == refresh_id
        assert list_data["refreshes"][0]["deltaClaimCount"] == 1

        detail_resp = client.get(f"/api/ist/screens/{screen_id}/refreshes/{refresh_id}")
        assert detail_resp.status_code == 200
        detail_data = detail_resp.json()
        assert detail_data["id"] == refresh_id
        assert detail_data["deltaClaimCount"] == 1
        assert detail_data["contentType"] == "research_note"

        claims_resp = client.get(f"/api/ist/screens/{screen_id}/refreshes/{refresh_id}/claims")
        assert claims_resp.status_code == 200
        claims_data = claims_resp.json()
        assert claims_data["refreshId"] == refresh_id
        assert claims_data["totalCount"] == 1
        assert claims_data["claims"][0]["claimText"] == "Delta claim for refresh list/detail test"


class TestISTSynthesisEndpoints:
    def test_create_synthesis_requires_completed_certified_screens(self, client):
        s1 = _create_screen(client, "Synthesis Guardrail 1")
        s2 = _create_screen(client, "Synthesis Guardrail 2")
        assert s1.status_code == 201
        assert s2.status_code == 201

        resp = client.post(
            "/api/ist/syntheses",
            json={
                "name": "Invalid Synthesis",
                "screenIds": [s1.json()["id"], s2.json()["id"]],
            },
        )
        assert resp.status_code == 409
        assert resp.json()["detail"]["error"]["code"] == "SCREENS_NOT_COMPLETED"

    def test_create_synthesis_success_and_sources(self, client, db):
        s1 = _create_screen(client, "Energy Bottlenecks", hypothesis="Energy scarcity from AI scaling")
        s2 = _create_screen(client, "Agent Adoption", hypothesis="AI agent adoption accelerates demand")
        assert s1.status_code == 201
        assert s2.status_code == 201
        sid1 = s1.json()["id"]
        sid2 = s2.json()["id"]
        _mark_completed_certified(db, sid1)
        _mark_completed_certified(db, sid2)

        db.add_all(
            [
                ISTEquityCandidate(
                    screen_id=sid1,
                    ticker="VRT",
                    company_name="Vertiv Holdings Co",
                    bottleneck_id=None,
                    scarcity_score=json.dumps({"overall": 3.8}),
                    tier=2,
                    conviction="MEDIUM",
                ),
                ISTEquityCandidate(
                    screen_id=sid2,
                    ticker="VRT",
                    company_name="Vertiv Holdings Co",
                    bottleneck_id=None,
                    scarcity_score=json.dumps({"overall": 3.4}),
                    tier=3,
                    conviction="LOW",
                ),
                ISTEquityCandidate(
                    screen_id=sid2,
                    ticker="NVDA",
                    company_name="NVIDIA Corp",
                    bottleneck_id=None,
                    scarcity_score=json.dumps({"overall": 4.2}),
                    tier=1,
                    conviction="HIGH",
                ),
            ]
        )
        db.commit()

        create_resp = client.post(
            "/api/ist/syntheses",
            json={
                "name": "Energy + Agents Synthesis",
                "screenIds": [sid1, sid2],
                "autoAdvance": False,
            },
        )
        assert create_resp.status_code == 201
        create_data = create_resp.json()
        synthesis_id = create_data["id"]
        run_id = create_data["workflowRunId"]
        assert create_data["status"] == "PENDING"

        run = db.query(WorkflowRun).filter(WorkflowRun.id == run_id).first()
        assert run is not None
        assert run.workflow_type == "IST_SYNTHESIS"

        steps = (
            db.query(WorkflowStep)
            .filter(WorkflowStep.workflow_run_id == run_id)
            .order_by(WorkflowStep.step_order)
            .all()
        )
        assert len(steps) == len(IST_SYNTHESIS_WORKFLOW_STEPS)
        assert [s.step_name for s in steps] == [s["step_name"] for s in IST_SYNTHESIS_WORKFLOW_STEPS]

        source_rows = (
            db.query(ISTSynthesisSource)
            .filter(ISTSynthesisSource.synthesis_id == synthesis_id)
            .all()
        )
        assert len(source_rows) == 2

        list_resp = client.get("/api/ist/syntheses")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert list_data["total"] == 1
        assert list_data["syntheses"][0]["id"] == synthesis_id
        assert list_data["syntheses"][0]["sourceScreenCount"] == 2

        sources_resp = client.get(f"/api/ist/syntheses/{synthesis_id}/sources")
        assert sources_resp.status_code == 200
        sources_data = sources_resp.json()
        assert len(sources_data["sources"]) == 2

    @pytest.mark.asyncio
    async def test_synthesis_workflow_outputs_and_endpoints(self, client, db, monkeypatch):
        s1 = _create_screen(client, "Power Constraints", hypothesis="Grid bottlenecks constrain AI growth")
        s2 = _create_screen(client, "Cooling Demand", hypothesis="Cooling demand accelerates capacity spend")
        assert s1.status_code == 201
        assert s2.status_code == 201
        sid1 = s1.json()["id"]
        sid2 = s2.json()["id"]
        _mark_completed_certified(db, sid1)
        _mark_completed_certified(db, sid2)

        db.add_all(
            [
                ISTBottleneck(
                    screen_id=sid1,
                    name="Grid Interconnect Delays",
                    phase=1,
                    phase_label="Constrained Supply",
                    description="Utilities cannot connect new capacity quickly enough.",
                ),
                ISTBottleneck(
                    screen_id=sid2,
                    name="Cooling Retrofits",
                    phase=2,
                    phase_label="Capacity Retrofit",
                    description="Liquid cooling retrofits lag compute deployments.",
                ),
                ISTEquityCandidate(
                    screen_id=sid1,
                    ticker="VRT",
                    company_name="Vertiv Holdings Co",
                    bottleneck_id=None,
                    scarcity_score=json.dumps({"overall": 4.0}),
                    tier=2,
                    conviction="MEDIUM",
                ),
                ISTEquityCandidate(
                    screen_id=sid2,
                    ticker="VRT",
                    company_name="Vertiv Holdings Co",
                    bottleneck_id=None,
                    scarcity_score=json.dumps({"overall": 3.8}),
                    tier=2,
                    conviction="MEDIUM",
                ),
                ISTEquityCandidate(
                    screen_id=sid2,
                    ticker="ETN",
                    company_name="Eaton Corp",
                    bottleneck_id=None,
                    scarcity_score=json.dumps({"overall": 3.5}),
                    tier=3,
                    conviction="LOW",
                ),
            ]
        )
        db.commit()

        create_resp = client.post(
            "/api/ist/syntheses",
            json={
                "name": "Power + Cooling Synthesis",
                "screenIds": [sid1, sid2],
                "autoAdvance": False,
            },
        )
        assert create_resp.status_code == 201
        synthesis_id = create_resp.json()["id"]
        workflow_run_id = create_resp.json()["workflowRunId"]

        test_session_local = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=db.get_bind(),
        )
        monkeypatch.setattr(synthesis_service, "SessionLocal", test_session_local)

        async def fake_call_claude(system_prompt, user_prompt, response_model, **kwargs):
            model_name = response_model.__name__
            if model_name == "ThesisInteractionResult":
                return response_model(
                    classification="reinforcing",
                    rationale="Both screens reinforce infrastructure capacity demand.",
                    impact="Shared beneficiaries likely see stronger conviction.",
                )
            if model_name == "CombinedBottleneckResult":
                return response_model(
                    unified_cascade=[
                        {"phase": 1, "name": "Grid Interconnect Delays"},
                        {"phase": 2, "name": "Cooling Retrofits"},
                    ],
                    emergent_bottlenecks=["Transformer lead-time bottleneck"],
                    temporal_sequence="Interconnect delays precede cooling retrofit demand spikes.",
                    summary="Combined bottlenecks create a multi-quarter deployment lag.",
                )
            if model_name == "CrossScreenEffectsResult":
                return response_model(
                    effects_chains=[
                        {
                            "source": "Grid delays",
                            "propagation": "Delayed compute deployments",
                            "target": "Cooling retrofit timing",
                        }
                    ],
                    feedback_loops=["Power delay -> retrofit delay -> backlog expansion"],
                    summary="Cross-screen effects amplify cycle timing risk.",
                )
            if model_name == "TierReassessmentBatch":
                baseline = _extract_json_tag(user_prompt, "equity_baseline") or []
                assessments = []
                for idx, row in enumerate(baseline):
                    original_tier = int(row.get("originalTier", 3))
                    new_tier = 1 if idx == 0 else original_tier
                    ticker = row.get("ticker", "")
                    assessments.append(
                        {
                            "ticker": ticker,
                            "original_tier": original_tier,
                            "new_tier": new_tier,
                            "rationale": f"{ticker} benefits from cross-screen demand reinforcement.",
                            "conviction": "HIGH" if new_tier == 1 else "MEDIUM",
                            "combined_thesis": f"{ticker} sits at the intersection of both screen themes.",
                        }
                    )
                return response_model(assessments=assessments)
            if model_name == "_DialecticPayload":
                prompt_lower = system_prompt.lower()
                if "optimistic" in prompt_lower:
                    return response_model(
                        narrative="Optimist case: reinforcement across power and cooling supports upside.",
                        key_points=["Demand reinforcement", "Improved conviction"],
                    )
                if "skeptical" in prompt_lower:
                    return response_model(
                        narrative="Pessimist case: sequencing and policy delays may cap upside.",
                        key_points=["Timing risk", "Execution fragility"],
                    )
                return response_model(
                    narrative="Balanced synthesis: upside exists, but sequencing risk must be monitored.",
                    key_points=["Balanced risk/reward", "Monitor milestones"],
                )
            raise AssertionError(f"Unexpected response model: {model_name}")

        async def fake_call_claude_raw(system_prompt, user_prompt, **kwargs):
            return (
                "# Combined Investment Thesis\n\n"
                "## Executive Summary\n\n"
                "Reinforcing cross-screen dynamics support a focused shortlist.\n\n"
                "## Recommended Actions\n\n"
                "- Prioritize Tier 1 names for HFRT handoff."
            )

        monkeypatch.setattr(synthesis_service, "call_claude", fake_call_claude)
        monkeypatch.setattr(synthesis_service, "call_claude_raw", fake_call_claude_raw)

        await synthesis_service.handle_screen_ingestion(workflow_run_id)
        await synthesis_service.handle_overlap_matrix(workflow_run_id)
        await synthesis_service.handle_thesis_interactions(workflow_run_id)
        await synthesis_service.handle_synthesis_readiness_gate(workflow_run_id)
        await synthesis_service.handle_combined_bottleneck_analysis(workflow_run_id)
        await synthesis_service.handle_cross_screen_effects(workflow_run_id)
        await synthesis_service.handle_re_tiering(workflow_run_id)
        await synthesis_service.handle_synthesis_dialectic_optimist(workflow_run_id)
        await synthesis_service.handle_synthesis_dialectic_pessimist(workflow_run_id)
        await synthesis_service.handle_synthesis_final(workflow_run_id)

        detail_resp = client.get(f"/api/ist/syntheses/{synthesis_id}")
        assert detail_resp.status_code == 200
        detail = detail_resp.json()
        assert isinstance(detail["thesisInteractions"], list)
        assert len(detail["thesisInteractions"]) > 0
        assert isinstance(detail["combinedBrief"], dict)
        assert detail["combinedBrief"]
        assert isinstance(detail["tierChanges"], list)
        assert detail["report"]

        synth_dialectic_resp = client.get(
            f"/api/ist/syntheses/{synthesis_id}/dialectic/SYNTHESIS"
        )
        assert synth_dialectic_resp.status_code == 200
        synth_dialectic = synth_dialectic_resp.json()["content"]
        assert isinstance(synth_dialectic.get("narrative"), str)
        assert synth_dialectic["narrative"]
        assert isinstance(synth_dialectic.get("key_points"), list)

        equities_resp = client.get(f"/api/ist/syntheses/{synthesis_id}/equities")
        assert equities_resp.status_code == 200
        equities = equities_resp.json()["equities"]
        assert equities
        assert any(
            (equity.get("tierChangeRationale") or "") != "No cross-screen adjustment"
            for equity in equities
        )
