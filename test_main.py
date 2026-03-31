#!/usr/bin/env python3
"""
Unit tests for RCal — Brazilian Simples Nacional Tax Calculator.

The standard test case in this file is taken directly from:
    docs/AI_REFERENCE_DOC.md § 5 — Standard Test Case (Validation)

These tests validate the core mathematical engine and should be run
as part of CI/CD pipelines to catch regressions in tax logic.
"""

import unittest
from main import (
    calculate_taxes,
    format_brl,
    format_pct,
    render_breakdown_bar,
    MonthYearPrompt,
    PositiveFloatPrompt,
    LEGAL_MINIMUM_WAGE,
)
from rich.prompt import InvalidResponse


class TestFormatBRL(unittest.TestCase):
    """Test Brazilian Reais currency formatting."""

    def test_simple_value(self) -> None:
        self.assertEqual(format_brl(1621.00), "R$ 1.621,00")

    def test_large_value(self) -> None:
        self.assertEqual(format_brl(28750.00), "R$ 28.750,00")

    def test_zero(self) -> None:
        self.assertEqual(format_brl(0.00), "R$ 0,00")

    def test_cents(self) -> None:
        self.assertEqual(format_brl(178.31), "R$ 178,31")

    def test_millions(self) -> None:
        self.assertEqual(format_brl(1234567.89), "R$ 1.234.567,89")


class TestFormatPct(unittest.TestCase):
    """Test percentage formatting."""

    def test_fator_r(self) -> None:
        """Standard Fator R target should format as 28.0%."""
        self.assertEqual(format_pct(0.28), "28.0%")

    def test_zero(self) -> None:
        self.assertEqual(format_pct(0.0), "0.0%")

    def test_full(self) -> None:
        self.assertEqual(format_pct(1.0), "100.0%")

    def test_small_pct(self) -> None:
        self.assertEqual(format_pct(0.03054), "3.1%")


class TestCalculateTaxes(unittest.TestCase):
    """Test the core tax calculation engine.

    Standard test case from AI_REFERENCE_DOC.md § 5:
        Input:  $883.00 USD, 5.23 exchange rate
        Expected:
            - BRL Gross:    R$ 4.618,09
            - Pró-labore:   R$ 1.621,00 (minimum wage floor)
            - INSS:         R$ 178,31
            - IRPF Status:  Tax Free
    """

    def setUp(self) -> None:
        """Set up the standard test case from AI_REFERENCE_DOC.md § 5."""
        self.results = calculate_taxes(
            revenue_usd=883.00,
            exchange_rate=5.23,
        )

    # ── § 5 Standard Test Case ───────────────────────────────────

    def test_gross_revenue(self) -> None:
        """§5: Expected BRL Gross is R$ 4.618,09."""
        self.assertAlmostEqual(
            self.results["gross_revenue_brl"], 4618.09, places=2
        )

    def test_pro_labore_uses_minimum_wage(self) -> None:
        """§5: 28% of 4618.09 = 1293.06, which is below minimum wage.
        Pró-labore should snap to the federal minimum wage floor."""
        self.assertAlmostEqual(
            self.results["ideal_pro_labore"], LEGAL_MINIMUM_WAGE, places=2
        )

    def test_fator_r_minimum_below_wage(self) -> None:
        """§5: Fator R minimum (1293.06) must be below minimum wage."""
        self.assertLess(
            self.results["fator_r_minimum"], LEGAL_MINIMUM_WAGE
        )

    def test_inss(self) -> None:
        """§5: Expected INSS is R$ 178,31."""
        self.assertAlmostEqual(
            self.results["inss_tax"], 178.31, places=2
        )

    def test_irpf_tax_free(self) -> None:
        """§5: Expected IRPF Status is 'Tax Free'."""
        self.assertIn("Tax Free", str(self.results["irpf_status"]))

    # ── Additional Edge Cases ────────────────────────────────────

    def test_dividends_positive(self) -> None:
        """Dividends must always be positive for valid inputs."""
        self.assertGreater(self.results["available_dividends"], 0)

    def test_net_take_home_less_than_gross(self) -> None:
        """Net take-home must be less than gross (taxes are deducted)."""
        self.assertLess(
            self.results["total_net_take_home"],
            self.results["gross_revenue_brl"],
        )


class TestHighRevenueScenario(unittest.TestCase):
    """Test with high revenue where Fator R minimum exceeds minimum wage
    and IRPF is triggered."""

    def setUp(self) -> None:
        self.results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
        )

    def test_pro_labore_uses_fator_r(self) -> None:
        """When revenue is high, Pró-labore should be 28% of gross."""
        expected_gross = 5000.00 * 5.75  # 28750.00
        expected_pro_labore = expected_gross * 0.28  # 8050.00
        self.assertAlmostEqual(
            self.results["ideal_pro_labore"], expected_pro_labore, places=2
        )

    def test_irpf_triggered(self) -> None:
        """When Pró-labore > R$ 5.000, IRPF should be triggered."""
        self.assertIn("IRPF Triggered", str(self.results["irpf_status"]))

    def test_bracket_warning_triggered(self) -> None:
        """Annual revenue of R$ 345k exceeds Bracket 1 ceiling of R$ 180k."""
        self.assertIn("Bracket", str(self.results["bracket_warning"]))


class TestMinimumRevenueScenario(unittest.TestCase):
    """Test with very low revenue."""

    def setUp(self) -> None:
        self.results = calculate_taxes(
            revenue_usd=100.00,
            exchange_rate=5.00,
        )

    def test_pro_labore_is_minimum_wage(self) -> None:
        """Very low revenue should still use the minimum wage floor."""
        self.assertAlmostEqual(
            self.results["ideal_pro_labore"], LEGAL_MINIMUM_WAGE, places=2
        )

    def test_no_bracket_warning(self) -> None:
        """Low revenue should not trigger bracket warning."""
        self.assertEqual(self.results["bracket_warning"], "")

    def test_negative_dividends_possible(self) -> None:
        """With very low revenue, dividends can be negative
        (Pró-labore + DAS > revenue)."""
        # R$ 500 gross - R$ 1621 pro-labore - DAS = negative
        self.assertLess(self.results["available_dividends"], 0)


# ── v2.0 UI/UX Component Tests ──────────────────────────────────


class TestMonthYearPrompt(unittest.TestCase):
    """Test the MonthYearPrompt input validation."""

    def setUp(self) -> None:
        self.prompt = MonthYearPrompt("test")

    def test_valid_month_year(self) -> None:
        """Standard MM/YYYY format should be accepted."""
        self.assertEqual(self.prompt.process_response("03/2026"), "03/2026")

    def test_valid_december(self) -> None:
        """Month 12 should be accepted."""
        self.assertEqual(self.prompt.process_response("12/2026"), "12/2026")

    def test_valid_january(self) -> None:
        """Month 01 should be accepted."""
        self.assertEqual(self.prompt.process_response("01/2026"), "01/2026")

    def test_invalid_format_no_slash(self) -> None:
        """Missing slash should be rejected."""
        with self.assertRaises(InvalidResponse):
            self.prompt.process_response("032026")

    def test_invalid_format_wrong_separator(self) -> None:
        """Dash separator should be rejected."""
        with self.assertRaises(InvalidResponse):
            self.prompt.process_response("03-2026")

    def test_invalid_month_zero(self) -> None:
        """Month 00 should be rejected."""
        with self.assertRaises(InvalidResponse):
            self.prompt.process_response("00/2026")

    def test_invalid_month_thirteen(self) -> None:
        """Month 13 should be rejected."""
        with self.assertRaises(InvalidResponse):
            self.prompt.process_response("13/2026")

    def test_whitespace_stripped(self) -> None:
        """Leading/trailing whitespace should be stripped."""
        self.assertEqual(
            self.prompt.process_response("  03/2026  "), "03/2026"
        )


class TestPositiveFloatPrompt(unittest.TestCase):
    """Test the PositiveFloatPrompt input validation."""

    def setUp(self) -> None:
        self.prompt = PositiveFloatPrompt("test")

    def test_valid_positive_number(self) -> None:
        """Positive float should be accepted."""
        self.assertEqual(self.prompt.process_response("883.00"), 883.00)

    def test_valid_integer_string(self) -> None:
        """Integer string should be accepted as float."""
        self.assertEqual(self.prompt.process_response("5000"), 5000.0)

    def test_reject_zero(self) -> None:
        """Zero should be rejected."""
        with self.assertRaises(InvalidResponse):
            self.prompt.process_response("0")

    def test_reject_negative(self) -> None:
        """Negative numbers should be rejected."""
        with self.assertRaises(InvalidResponse):
            self.prompt.process_response("-100")

    def test_reject_text(self) -> None:
        """Non-numeric text should be rejected."""
        with self.assertRaises(InvalidResponse):
            self.prompt.process_response("abc")

    def test_reject_empty(self) -> None:
        """Empty string should be rejected."""
        with self.assertRaises(InvalidResponse):
            self.prompt.process_response("")


class TestBreakdownBar(unittest.TestCase):
    """Test the revenue distribution breakdown bar."""

    def test_normal_scenario_contains_yours(self) -> None:
        """Normal scenario should show 'Yours' segment."""
        results = calculate_taxes(revenue_usd=883.00, exchange_rate=5.23)
        bar = render_breakdown_bar(results)
        self.assertIn("Yours", bar.plain)

    def test_negative_dividends_no_yours(self) -> None:
        """Negative dividends scenario should not show 'Yours' segment."""
        results = calculate_taxes(revenue_usd=100.00, exchange_rate=5.00)
        bar = render_breakdown_bar(results)
        self.assertNotIn("Yours", bar.plain)
        self.assertIn("of costs", bar.plain)

    def test_zero_revenue_message(self) -> None:
        """Zero revenue should show informational message."""
        results = {
            "gross_revenue_brl": 0.0,
            "ideal_pro_labore": 0.0,
            "inss_tax": 0.0,
            "estimated_das": 0.0,
        }
        bar = render_breakdown_bar(results)
        self.assertIn("No revenue", bar.plain)


if __name__ == "__main__":
    unittest.main()
