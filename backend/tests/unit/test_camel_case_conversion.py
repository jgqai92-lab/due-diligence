"""Unit tests for IST API snake_case -> camelCase conversion utilities.

Tests cover:
- _snake_to_camel: basic conversion, already-camelCase passthrough, single words
- _deep_camel: nested dicts, lists, mixed types, None/primitive passthrough
- _normalize_catalyst: ticker->tickers, impact->expectedImpact, defaults
- _normalize_stress_test: impactAssessment->impact, empty arrays, framework fallback
"""

import pytest

from app.routers.ist import (
    _snake_to_camel,
    _deep_camel,
    _normalize_catalyst,
    _normalize_stress_test,
)


# ── _snake_to_camel tests ──────────────────────────────────────────────────


class TestSnakeToCamel:
    """Tests for the _snake_to_camel string conversion function."""

    def test_basic_snake_case(self):
        assert _snake_to_camel("key_arguments") == "keyArguments"

    def test_multiple_underscores(self):
        assert _snake_to_camel("conviction_level_score") == "convictionLevelScore"

    def test_single_word(self):
        """Single words without underscores should pass through unchanged."""
        assert _snake_to_camel("name") == "name"

    def test_already_camel_case(self):
        """Already camelCase strings (no underscores) should pass through unchanged."""
        assert _snake_to_camel("screenId") == "screenId"

    def test_already_camel_case_complex(self):
        assert _snake_to_camel("finalTierAdjustments") == "finalTierAdjustments"

    def test_leading_underscore(self):
        """Leading underscores produce empty first component."""
        result = _snake_to_camel("_private_field")
        assert result == "PrivateField"

    def test_empty_string(self):
        assert _snake_to_camel("") == ""

    def test_all_caps_segments(self):
        """ALL_CAPS segments get title-cased after the first."""
        assert _snake_to_camel("impact_assessment") == "impactAssessment"

    def test_single_char_segments(self):
        assert _snake_to_camel("a_b_c") == "aBC"

    def test_trailing_underscore(self):
        result = _snake_to_camel("field_")
        assert result == "field"

    def test_numeric_segments(self):
        assert _snake_to_camel("tier_1_count") == "tier1Count"


# ── _deep_camel tests ──────────────────────────────────────────────────────


class TestDeepCamel:
    """Tests for the recursive _deep_camel dict key conversion function."""

    def test_flat_dict(self):
        result = _deep_camel({"key_arguments": "value", "conviction_level": 5})
        assert result == {"keyArguments": "value", "convictionLevel": 5}

    def test_nested_dict(self):
        result = _deep_camel({
            "outer_key": {
                "inner_key": "value",
                "deep_nested": {"another_key": True}
            }
        })
        assert result == {
            "outerKey": {
                "innerKey": "value",
                "deepNested": {"anotherKey": True}
            }
        }

    def test_list_of_dicts(self):
        result = _deep_camel([
            {"first_name": "Alice"},
            {"first_name": "Bob"},
        ])
        assert result == [
            {"firstName": "Alice"},
            {"firstName": "Bob"},
        ]

    def test_dict_with_list_values(self):
        result = _deep_camel({
            "key_risks": [
                {"risk_name": "inflation", "severity_level": "HIGH"}
            ]
        })
        assert result == {
            "keyRisks": [
                {"riskName": "inflation", "severityLevel": "HIGH"}
            ]
        }

    def test_primitives_passthrough(self):
        assert _deep_camel("hello") == "hello"
        assert _deep_camel(42) == 42
        assert _deep_camel(3.14) == 3.14
        assert _deep_camel(True) is True
        assert _deep_camel(None) is None

    def test_empty_dict(self):
        assert _deep_camel({}) == {}

    def test_empty_list(self):
        assert _deep_camel([]) == []

    def test_mixed_list(self):
        """Lists with mixed types: dicts and primitives."""
        result = _deep_camel([{"snake_key": 1}, "string_val", 42])
        assert result == [{"snakeKey": 1}, "string_val", 42]

    def test_already_camel_keys_preserved(self):
        """Keys that are already camelCase should not be corrupted."""
        result = _deep_camel({"screenId": 1, "keyRisks": ["a"]})
        assert result == {"screenId": 1, "keyRisks": ["a"]}

    def test_mixed_case_keys(self):
        """Mix of snake_case and camelCase keys in the same dict."""
        result = _deep_camel({
            "already_camel": "no",
            "alreadyCamel": "yes",
            "some_key": {"nested_val": 1, "nestedVal": 2}
        })
        assert result == {
            "alreadyCamel": "yes",
            "alreadyCamel": "yes",
            "someKey": {"nestedVal": 2, "nestedVal": 2}
        }

    def test_none_input(self):
        """None should pass through."""
        assert _deep_camel(None) is None

    def test_realistic_dialectic_content(self):
        """Realistic test with data shaped like Claude's dialectic output."""
        input_data = {
            "key_arguments": [
                {
                    "argument_text": "Nuclear capacity constrained",
                    "conviction_level": "HIGH",
                    "supporting_evidence": ["Source A", "Source B"],
                }
            ],
            "overall_assessment": "Bullish",
            "risk_factors": [{"risk_name": "Regulatory change"}],
        }
        expected = {
            "keyArguments": [
                {
                    "argumentText": "Nuclear capacity constrained",
                    "convictionLevel": "HIGH",
                    "supportingEvidence": ["Source A", "Source B"],
                }
            ],
            "overallAssessment": "Bullish",
            "riskFactors": [{"riskName": "Regulatory change"}],
        }
        assert _deep_camel(input_data) == expected

    def test_realistic_synthesis_content(self):
        """Realistic test with data shaped like Claude's synthesis output."""
        input_data = {
            "narrative": "The thesis is sound.",
            "disagreements": [
                {"topic": "Growth rate", "optimist_view": "20%", "pessimist_view": "5%"}
            ],
            "final_tier_adjustments": [
                {"ticker": "GEV", "old_tier": 2, "new_tier": 1, "rationale": "Strong moat"}
            ],
            "overall_conviction": "HIGH",
            "key_risks": ["Regulatory", "Competition"],
        }
        result = _deep_camel(input_data)
        assert result["finalTierAdjustments"][0]["oldTier"] == 2
        assert result["finalTierAdjustments"][0]["newTier"] == 1
        assert result["overallConviction"] == "HIGH"
        assert result["disagreements"][0]["optimistView"] == "20%"
        assert result["keyRisks"] == ["Regulatory", "Competition"]


# ── _normalize_catalyst tests ──────────────────────────────────────────────


class TestNormalizeCatalyst:
    """Tests for catalyst normalization after _deep_camel is applied."""

    def test_ticker_to_tickers(self):
        """String ticker should become tickers array."""
        cat = {"date": "Q1 2025", "ticker": "GEV", "event": "Earnings"}
        result = _normalize_catalyst(cat)
        assert result["tickers"] == ["GEV"]
        assert "ticker" not in result

    def test_tickers_already_present(self):
        """If tickers array already exists, don't touch it."""
        cat = {"date": "Q1 2025", "tickers": ["GEV", "CEG"], "event": "Earnings"}
        result = _normalize_catalyst(cat)
        assert result["tickers"] == ["GEV", "CEG"]

    def test_impact_to_expected_impact(self):
        """impact should be mapped to expectedImpact."""
        cat = {"event": "Earnings", "impact": "Positive"}
        result = _normalize_catalyst(cat)
        assert result["expectedImpact"] == "Positive"
        assert "impact" not in result

    def test_expected_impact_already_present(self):
        """If expectedImpact already exists, don't overwrite."""
        cat = {"event": "Earnings", "expectedImpact": "Negative", "impact": "Positive"}
        result = _normalize_catalyst(cat)
        assert result["expectedImpact"] == "Negative"

    def test_default_importance(self):
        """Missing importance should default to MEDIUM."""
        cat = {"event": "Earnings"}
        result = _normalize_catalyst(cat)
        assert result["importance"] == "MEDIUM"

    def test_default_date_type(self):
        """Missing dateType should default to estimated."""
        cat = {"event": "Earnings"}
        result = _normalize_catalyst(cat)
        assert result["dateType"] == "estimated"

    def test_existing_importance_preserved(self):
        cat = {"event": "Earnings", "importance": "HIGH"}
        result = _normalize_catalyst(cat)
        assert result["importance"] == "HIGH"

    def test_existing_date_type_preserved(self):
        cat = {"event": "Earnings", "dateType": "confirmed"}
        result = _normalize_catalyst(cat)
        assert result["dateType"] == "confirmed"

    def test_empty_ticker_string(self):
        """Empty ticker string should produce empty tickers array."""
        cat = {"ticker": "", "event": "Earnings"}
        result = _normalize_catalyst(cat)
        assert result["tickers"] == []

    def test_full_pipeline(self):
        """End-to-end: raw snake_case dict -> _deep_camel -> _normalize_catalyst."""
        raw = {
            "date": "Q1 2025",
            "ticker": "GEV",
            "event": "Earnings release",
            "impact": "Positive",
            "pillar": "Nuclear Energy",
        }
        result = _normalize_catalyst(_deep_camel(raw))
        assert result == {
            "date": "Q1 2025",
            "tickers": ["GEV"],
            "event": "Earnings release",
            "expectedImpact": "Positive",
            "pillar": "Nuclear Energy",
            "importance": "MEDIUM",
            "dateType": "estimated",
        }


# ── _normalize_stress_test tests ──────────────────────────────────────────


class TestNormalizeStressTest:
    """Tests for stress test normalization after _deep_camel is applied."""

    def test_impact_assessment_to_impact(self):
        """impactAssessment should be copied to impact if impact missing."""
        test = {"impactAssessment": "Severe downturn expected", "scenario": "Rate shock"}
        result = _normalize_stress_test(test)
        assert result["impact"] == "Severe downturn expected"

    def test_description_to_impact_fallback(self):
        """description should be used for impact if impactAssessment also missing."""
        test = {"description": "Moderate disruption", "scenario": "Supply shock"}
        result = _normalize_stress_test(test)
        assert result["impact"] == "Moderate disruption"

    def test_impact_already_present(self):
        """If impact already exists, don't overwrite."""
        test = {"impact": "Original", "impactAssessment": "Overwrite attempt"}
        result = _normalize_stress_test(test)
        assert result["impact"] == "Original"

    def test_default_survivor_tickers(self):
        test = {"scenario": "Test"}
        result = _normalize_stress_test(test)
        assert result["survivorTickers"] == []

    def test_default_casualty_tickers(self):
        test = {"scenario": "Test"}
        result = _normalize_stress_test(test)
        assert result["casualtyTickers"] == []

    def test_existing_survivor_tickers_preserved(self):
        test = {"scenario": "Test", "survivorTickers": ["GEV", "CEG"]}
        result = _normalize_stress_test(test)
        assert result["survivorTickers"] == ["GEV", "CEG"]

    def test_framework_fallback_to_scenario(self):
        """If no framework field, use scenario as framework."""
        test = {"scenario": "Interest Rate Shock"}
        result = _normalize_stress_test(test)
        assert result["framework"] == "Interest Rate Shock"

    def test_existing_framework_preserved(self):
        test = {"scenario": "Test", "framework": "Custom Framework"}
        result = _normalize_stress_test(test)
        assert result["framework"] == "Custom Framework"

    def test_full_pipeline(self):
        """End-to-end: raw snake_case -> _deep_camel -> _normalize_stress_test."""
        raw = {
            "scenario": "Regulatory Crackdown",
            "description": "New regulations limit nuclear expansion",
            "impact_assessment": "Severe negative impact on pipeline companies",
            "severity": "HIGH",
            "affected_pillars": ["Nuclear Energy", "Grid Infrastructure"],
        }
        result = _normalize_stress_test(_deep_camel(raw))
        assert result["impact"] == "Severe negative impact on pipeline companies"
        assert result["impactAssessment"] == "Severe negative impact on pipeline companies"
        assert result["severity"] == "HIGH"
        assert result["affectedPillars"] == ["Nuclear Energy", "Grid Infrastructure"]
        assert result["survivorTickers"] == []
        assert result["casualtyTickers"] == []
        assert result["framework"] == "Regulatory Crackdown"
