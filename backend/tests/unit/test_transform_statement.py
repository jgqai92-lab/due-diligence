"""Tests for transform_statement() in yfinance_service."""

import math
import pytest

from app.services.yfinance_service import transform_statement


class TestTransformStatementBasic:
    """Happy-path tests for the transform_statement function."""

    def test_basic_transformation(self, sample_financials):
        """Transforms yfinance column-oriented data into row-oriented format."""
        result = transform_statement(sample_financials)

        assert "periods" in result
        assert "line_items" in result
        assert len(result["periods"]) == 2
        # Most recent first (descending)
        assert result["periods"][0] == "2024-09-28"
        assert result["periods"][1] == "2023-09-30"

    def test_periods_sorted_descending(self):
        """Periods are sorted most recent first."""
        raw = {
            "2021-01-01T00:00:00.000Z": {"Revenue": 100},
            "2023-01-01T00:00:00.000Z": {"Revenue": 300},
            "2022-01-01T00:00:00.000Z": {"Revenue": 200},
        }
        result = transform_statement(raw)
        assert result["periods"] == ["2023-01-01", "2022-01-01", "2021-01-01"]

    def test_period_truncation(self):
        """Period strings are truncated to date-only (first 10 chars)."""
        raw = {
            "2024-09-28T00:00:00.000Z": {"Revenue": 100},
        }
        result = transform_statement(raw)
        assert result["periods"] == ["2024-09-28"]

    def test_line_item_values_aligned_with_periods(self, sample_financials):
        """Each line item's values array is positionally aligned with periods."""
        result = transform_statement(sample_financials)

        # Find Total Revenue line item
        revenue = next(li for li in result["line_items"] if li["label"] == "Total Revenue")
        # periods[0] = 2024, periods[1] = 2023
        assert revenue["values"][0] == 391035000000.0
        assert revenue["values"][1] == 383285000000.0

    def test_preserves_line_item_order(self, sample_financials):
        """Line items preserve first-seen order from yfinance data."""
        result = transform_statement(sample_financials)
        labels = [li["label"] for li in result["line_items"]]
        # First-seen order from the most recent period dict
        assert labels[0] == "Total Revenue"
        assert "Gross Profit" in labels
        assert "Net Income" in labels

    def test_max_periods_limit(self):
        """Respects max_periods parameter, keeping the most recent."""
        raw = {
            f"202{i}-01-01T00:00:00.000Z": {"Revenue": i * 100}
            for i in range(9)
        }
        result = transform_statement(raw, max_periods=3)
        assert len(result["periods"]) == 3
        # Should keep the 3 most recent
        assert result["periods"][0] == "2028-01-01"
        assert result["periods"][1] == "2027-01-01"
        assert result["periods"][2] == "2026-01-01"

    def test_default_max_periods_is_five(self):
        """Default max_periods is 5."""
        raw = {
            f"20{20+i}-01-01T00:00:00.000Z": {"Revenue": i * 100}
            for i in range(8)
        }
        result = transform_statement(raw)
        assert len(result["periods"]) == 5


class TestTransformStatementEdgeCases:
    """Edge-case and error handling tests."""

    def test_empty_dict(self):
        """Returns empty structure for empty dict input."""
        result = transform_statement({})
        assert result == {"periods": [], "line_items": []}

    def test_none_like_empty(self):
        """Returns empty structure for None-ish input (empty dict is falsy-enough)."""
        result = transform_statement({})
        assert result["periods"] == []
        assert result["line_items"] == []

    def test_missing_value_becomes_none(self):
        """Line items missing from some periods get None in those positions."""
        raw = {
            "2024-01-01T00:00:00.000Z": {"Revenue": 100, "Expenses": 50},
            "2023-01-01T00:00:00.000Z": {"Revenue": 90},
        }
        result = transform_statement(raw)
        expenses = next(li for li in result["line_items"] if li["label"] == "Expenses")
        # 2024 has Expenses, 2023 does not
        assert expenses["values"][0] == 50.0
        assert expenses["values"][1] is None

    def test_nan_values_become_none(self):
        """NaN values are replaced with None."""
        raw = {
            "2024-01-01T00:00:00.000Z": {"Revenue": float("nan"), "Profit": 100},
        }
        result = transform_statement(raw)
        # Revenue is NaN in all periods -> should be skipped entirely
        labels = [li["label"] for li in result["line_items"]]
        assert "Revenue" not in labels
        # Profit should remain
        profit = next(li for li in result["line_items"] if li["label"] == "Profit")
        assert profit["values"] == [100.0]

    def test_nan_in_some_periods(self):
        """NaN in some periods becomes None, but line item is kept if it has any valid value."""
        raw = {
            "2024-01-01T00:00:00.000Z": {"Revenue": float("nan")},
            "2023-01-01T00:00:00.000Z": {"Revenue": 200},
        }
        result = transform_statement(raw)
        revenue = next(li for li in result["line_items"] if li["label"] == "Revenue")
        assert revenue["values"][0] is None  # 2024 was NaN
        assert revenue["values"][1] == 200.0  # 2023 was valid

    def test_all_none_line_item_skipped(self):
        """Line items that are None/NaN across all periods are skipped."""
        raw = {
            "2024-01-01T00:00:00.000Z": {"Revenue": 100, "Ghost": None},
            "2023-01-01T00:00:00.000Z": {"Revenue": 90, "Ghost": None},
        }
        result = transform_statement(raw)
        labels = [li["label"] for li in result["line_items"]]
        assert "Ghost" not in labels
        assert "Revenue" in labels

    def test_all_nan_line_item_skipped(self):
        """Line items that are NaN across all periods are skipped."""
        raw = {
            "2024-01-01T00:00:00.000Z": {"Revenue": 100, "BadMetric": float("nan")},
            "2023-01-01T00:00:00.000Z": {"Revenue": 90, "BadMetric": float("nan")},
        }
        result = transform_statement(raw)
        labels = [li["label"] for li in result["line_items"]]
        assert "BadMetric" not in labels

    def test_non_dict_period_value_handled(self):
        """Gracefully handles period values that are not dicts."""
        raw = {
            "2024-01-01T00:00:00.000Z": "not a dict",
            "2023-01-01T00:00:00.000Z": {"Revenue": 100},
        }
        result = transform_statement(raw)
        # Should not crash; period with bad data just yields no labels from that period
        assert len(result["periods"]) == 2
        revenue = next(li for li in result["line_items"] if li["label"] == "Revenue")
        assert revenue["values"][0] is None  # 2024 period had no dict
        assert revenue["values"][1] == 100.0

    def test_zero_value_preserved(self):
        """Zero is a valid value, not treated as None."""
        raw = {
            "2024-01-01T00:00:00.000Z": {"Revenue": 0},
        }
        result = transform_statement(raw)
        revenue = next(li for li in result["line_items"] if li["label"] == "Revenue")
        assert revenue["values"] == [0.0]

    def test_negative_values_preserved(self):
        """Negative values are preserved as-is."""
        raw = {
            "2024-01-01T00:00:00.000Z": {"Retained Earnings": -214460000000},
        }
        result = transform_statement(raw)
        item = result["line_items"][0]
        assert item["values"] == [-214460000000.0]

    def test_single_period(self):
        """Works with a single fiscal period."""
        raw = {
            "2024-01-01T00:00:00.000Z": {"Revenue": 100, "Expenses": 50},
        }
        result = transform_statement(raw)
        assert len(result["periods"]) == 1
        assert len(result["line_items"]) == 2

    def test_values_are_floats(self):
        """All numeric values in the output are floats, not ints."""
        raw = {
            "2024-01-01T00:00:00.000Z": {"Revenue": 100},
        }
        result = transform_statement(raw)
        val = result["line_items"][0]["values"][0]
        assert isinstance(val, float)

    def test_union_of_labels_across_periods(self):
        """Collects labels from all periods, not just the first."""
        raw = {
            "2024-01-01T00:00:00.000Z": {"Revenue": 100},
            "2023-01-01T00:00:00.000Z": {"Revenue": 90, "NewMetric": 50},
        }
        result = transform_statement(raw)
        labels = [li["label"] for li in result["line_items"]]
        assert "Revenue" in labels
        assert "NewMetric" in labels
        # NewMetric should have None for 2024, 50 for 2023
        new_metric = next(li for li in result["line_items"] if li["label"] == "NewMetric")
        assert new_metric["values"][0] is None
        assert new_metric["values"][1] == 50.0


class TestTransformStatementWithFixtures:
    """Tests using the shared conftest fixtures."""

    def test_with_sample_financials(self, sample_financials):
        """Works with the standard sample_financials fixture."""
        result = transform_statement(sample_financials)
        assert len(result["periods"]) == 2
        assert len(result["line_items"]) == 6  # All 6 line items from the fixture

    def test_with_sample_balance_sheet(self, sample_balance_sheet):
        """Works with the standard sample_balance_sheet fixture."""
        result = transform_statement(sample_balance_sheet)
        assert len(result["periods"]) == 2
        # Retained Earnings has negative values, should be preserved
        re = next(li for li in result["line_items"] if li["label"] == "Retained Earnings")
        assert re["values"][0] == -214460000000.0

    def test_with_sample_cashflow(self, sample_cashflow):
        """Works with the standard sample_cashflow fixture."""
        result = transform_statement(sample_cashflow)
        assert len(result["periods"]) == 2
        # Capital Expenditure should preserve negative sign
        capex = next(li for li in result["line_items"] if li["label"] == "Capital Expenditure")
        assert capex["values"][0] == -9959000000.0
