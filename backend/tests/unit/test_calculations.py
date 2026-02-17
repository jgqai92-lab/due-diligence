"""Tests for shared calculation utilities."""

from app.utils.calculations import safe_divide, safe_ratio_change, pct_change


class TestSafeDivide:
    def test_normal(self):
        assert safe_divide(10, 2) == 5.0

    def test_zero_denominator(self):
        assert safe_divide(10, 0) is None

    def test_none_numerator(self):
        assert safe_divide(None, 5) is None

    def test_none_denominator(self):
        assert safe_divide(5, None) is None

    def test_both_none(self):
        assert safe_divide(None, None) is None

    def test_negative(self):
        assert safe_divide(-10, 2) == -5.0

    def test_float_precision(self):
        assert abs(safe_divide(1, 3) - 0.3333333) < 0.001


class TestSafeRatioChange:
    def test_normal(self):
        assert safe_ratio_change(10, 5) == 2.0

    def test_none(self):
        assert safe_ratio_change(None, 5) is None


class TestPctChange:
    def test_positive(self):
        result = pct_change(110, 100)
        assert abs(result - 10.0) < 0.01

    def test_negative(self):
        result = pct_change(90, 100)
        assert abs(result - (-10.0)) < 0.01

    def test_zero_prior(self):
        assert pct_change(100, 0) is None

    def test_none_values(self):
        assert pct_change(None, 100) is None
        assert pct_change(100, None) is None
