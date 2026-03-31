#!/usr/bin/env python3
"""
Unit tests for RCal — Brazilian Simples Nacional Tax Calculator.

The standard test case in this file is taken directly from:
    docs/AI_REFERENCE_DOC.md § 5 — Standard Test Case (Validation)

These tests validate the core mathematical engine and should be run
as part of CI/CD pipelines to catch regressions in tax logic.

v3.0 additions:
    - TestIRPF2026: Pure function tests for the IRPF progressive table
      and Lei nº 15.270/2025 reducer.
    - TestIRPFDeductions: Deduction parameters (dependents, PGBL, alimony)
      correctly reduce the IRPF taxable base.
    - TestNetTakeHomeWithIRPF: Net take-home identity verification with IRPF.
    - Updated TestHighRevenueScenario with exact IRPF expectations.
"""

import unittest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch

from main import (
    calculate_irpf_2026,
    calculate_taxes,
    clear_state,
    format_brl,
    format_pct,
    load_state,
    render_breakdown_bar,
    save_state,
    MonthYearPrompt,
    NonNegativeFloatPrompt,
    NonNegativeIntPrompt,
    PositiveFloatPrompt,
    IRPF_DEPENDENT_DEDUCTION,
    IRPF_REDUCER_FULL_EXEMPTION_LIMIT,
    IRPF_REDUCER_PHASE_OUT_LIMIT,
    IRPF_TABLE_2026,
    LEGAL_MINIMUM_WAGE,
    STATE_FILE,
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
            - IRPF:         R$ 0,00 (taxable base below exempt bracket)
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
        """§5: Taxable base = 1621 - 178.31 = 1442.69 → below R$ 2.428,80
        → IRPF is R$ 0,00 (exempt bracket)."""
        self.assertAlmostEqual(self.results["irpf_tax"], 0.0, places=2)
        self.assertIn("Tax Free", str(self.results["irpf_status"]))

    def test_taxable_base(self) -> None:
        """§5: Taxable base should be Pró-labore minus INSS."""
        expected = LEGAL_MINIMUM_WAGE - 178.31  # 1442.69
        self.assertAlmostEqual(
            self.results["taxable_base"], expected, places=2
        )

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

    def test_net_take_home_identity(self) -> None:
        """Net = (Pró-labore - INSS - IRPF) + Dividends."""
        expected = (
            self.results["ideal_pro_labore"]
            - self.results["inss_tax"]
            - self.results["irpf_tax"]
            + self.results["available_dividends"]
        )
        self.assertAlmostEqual(
            self.results["total_net_take_home"], expected, places=2
        )


class TestHighRevenueScenario(unittest.TestCase):
    """Test with high revenue where Fator R minimum exceeds minimum wage
    and IRPF applies.

    Input: $5000 USD × 5.75 rate = R$ 28.750 gross
    Pró-labore: R$ 8.050,00 (28% of R$ 28.750)
    INSS: R$ 885,50 (11% of R$ 8.050)
    Taxable base: R$ 8.050 - R$ 885,50 = R$ 7.164,50
    → Falls in 27.5% bracket: 7164.50 × 0.275 - 908.73 = R$ 1.061,51
    → 2026 reducer: taxable_base (7164.50) is between R$ 5.000 and R$ 7.350
        reducer = 978.62 - (0.133145 × 7164.50) = 978.62 - 953.78 = R$ 24.84
    → Final IRPF = 1.061,51 - 24,84 = R$ 1.036,67
    """

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

    def test_taxable_base(self) -> None:
        """Taxable base = Pró-labore - INSS = 8050 - 885.50 = 7164.50."""
        self.assertAlmostEqual(
            self.results["taxable_base"], 7164.50, places=2
        )

    def test_irpf_is_calculated(self) -> None:
        """IRPF should be a positive value for this high-income scenario."""
        self.assertGreater(self.results["irpf_tax"], 0)

    def test_irpf_calculation_with_reducer(self) -> None:
        """Verify the exact IRPF value with the 2026 reducer applied.

        Standard table: 7164.50 × 0.275 - 908.73 = 1061.5075
        Reducer: 978.62 - (0.133145 × 7164.50) = 24.7026
        Final: 1061.5075 - 24.7026 = 1036.80
        """
        self.assertAlmostEqual(
            self.results["irpf_tax"], 1036.80, places=1
        )

    def test_irpf_status_shows_amount(self) -> None:
        """IRPF status should show the calculated amount, not just 'Triggered'."""
        self.assertIn("IRPF", str(self.results["irpf_status"]))
        self.assertIn("R$", str(self.results["irpf_status"]))

    def test_net_take_home_includes_irpf(self) -> None:
        """Net take-home must subtract IRPF from the salary portion."""
        expected = (
            self.results["ideal_pro_labore"]
            - self.results["inss_tax"]
            - self.results["irpf_tax"]
            + self.results["available_dividends"]
        )
        self.assertAlmostEqual(
            self.results["total_net_take_home"], expected, places=2
        )

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

    def test_irpf_zero_for_low_income(self) -> None:
        """IRPF should be zero for minimum wage Pró-labore."""
        self.assertAlmostEqual(self.results["irpf_tax"], 0.0, places=2)


# ── v3.0 IRPF 2026 Tests ────────────────────────────────────────


class TestIRPF2026(unittest.TestCase):
    """Test the calculate_irpf_2026() pure function.

    Verifies the 3-step algorithm:
        1. Standard progressive table (5 brackets)
        2. Lei nº 15.270/2025 reducer (full exemption / phase-out / none)
        3. Final IRPF = max(standard - reducer, 0)
    """

    def test_zero_base(self) -> None:
        """Zero taxable base → all-zero output."""
        std, reducer, final = calculate_irpf_2026(0.0)
        self.assertEqual(std, 0.0)
        self.assertEqual(reducer, 0.0)
        self.assertEqual(final, 0.0)

    def test_negative_base(self) -> None:
        """Negative taxable base → all-zero output."""
        std, reducer, final = calculate_irpf_2026(-500.0)
        self.assertEqual(std, 0.0)
        self.assertEqual(reducer, 0.0)
        self.assertEqual(final, 0.0)

    def test_exempt_bracket(self) -> None:
        """R$ 2.000 → in the Isento bracket, standard IRPF = 0."""
        std, reducer, final = calculate_irpf_2026(2000.00)
        self.assertAlmostEqual(std, 0.0, places=2)
        self.assertAlmostEqual(final, 0.0, places=2)

    def test_exempt_bracket_boundary(self) -> None:
        """R$ 2.428,80 → exactly at the top of the Isento bracket."""
        std, reducer, final = calculate_irpf_2026(2428.80)
        self.assertAlmostEqual(std, 0.0, places=2)
        self.assertAlmostEqual(final, 0.0, places=2)

    def test_second_bracket(self) -> None:
        """R$ 2.700 → in the 7.5% bracket.
        Standard = 2700 × 0.075 - 182.16 = 202.50 - 182.16 = 20.34
        Below R$ 5.000 → full exemption → final = 0."""
        std, reducer, final = calculate_irpf_2026(2700.00)
        self.assertAlmostEqual(std, 20.34, places=2)
        self.assertAlmostEqual(final, 0.0, places=2)

    def test_full_exemption_at_5000(self) -> None:
        """R$ 5.000 → taxable base at the exemption limit.
        Standard = 5000 × 0.275 - 908.73 = 1375.00 - 908.73 = 466.27
        Full exemption → final = 0."""
        std, reducer, final = calculate_irpf_2026(5000.00)
        self.assertAlmostEqual(std, 466.27, places=2)
        self.assertAlmostEqual(final, 0.0, places=2)

    def test_phase_out_zone_6000(self) -> None:
        """R$ 6.000 → in the phase-out zone (R$ 5.000,01 - R$ 7.350).
        Standard = 6000 × 0.275 - 908.73 = 1650.00 - 908.73 = 741.27
        Reducer = 978.62 - (0.133145 × 6000) = 978.62 - 798.87 = 179.75
        Final = 741.27 - 179.75 = 561.52."""
        std, reducer, final = calculate_irpf_2026(6000.00)
        self.assertAlmostEqual(std, 741.27, places=2)
        self.assertAlmostEqual(reducer, 179.75, places=2)
        self.assertAlmostEqual(final, 561.52, places=2)

    def test_phase_out_boundary_7350(self) -> None:
        """R$ 7.350 → at the top of the phase-out zone.
        Standard = 7350 × 0.275 - 908.73 = 2021.25 - 908.73 = 1112.52
        Reducer = 978.62 - (0.133145 × 7350) = 978.62 - 978.6158 ≈ 0.0042
        Final = 1112.52 - 0.0042 ≈ 1112.52."""
        std, reducer, final = calculate_irpf_2026(7350.00)
        self.assertAlmostEqual(std, 1112.52, places=2)
        self.assertAlmostEqual(final, 1112.52, places=1)
        # Reducer should be approximately zero at R$ 7.350
        self.assertLess(reducer, 0.01)

    def test_no_reducer_above_7350(self) -> None:
        """R$ 8.000 → above the phase-out limit, no reducer applies.
        Standard = 8000 × 0.275 - 908.73 = 2200.00 - 908.73 = 1291.27
        Reducer = 0
        Final = 1291.27."""
        std, reducer, final = calculate_irpf_2026(8000.00)
        self.assertAlmostEqual(std, 1291.27, places=2)
        self.assertAlmostEqual(reducer, 0.0, places=2)
        self.assertAlmostEqual(final, 1291.27, places=2)

    def test_third_bracket_with_exemption(self) -> None:
        """R$ 3.500 → in the 15% bracket, but below R$ 5.000 → exempt.
        Standard = 3500 × 0.15 - 394.16 = 525.00 - 394.16 = 130.84
        Full exemption → final = 0."""
        std, reducer, final = calculate_irpf_2026(3500.00)
        self.assertAlmostEqual(std, 130.84, places=2)
        self.assertAlmostEqual(final, 0.0, places=2)

    def test_fourth_bracket_with_exemption(self) -> None:
        """R$ 4.500 → in the 22.5% bracket, but below R$ 5.000 → exempt.
        Standard = 4500 × 0.225 - 675.49 = 1012.50 - 675.49 = 337.01
        Full exemption → final = 0."""
        std, reducer, final = calculate_irpf_2026(4500.00)
        self.assertAlmostEqual(std, 337.01, places=2)
        self.assertAlmostEqual(final, 0.0, places=2)


class TestIRPFDeductions(unittest.TestCase):
    """Test that IRPF deductions correctly reduce the taxable base.

    Uses a high-revenue scenario where Pró-labore is R$ 8.050,00
    so we can observe the effect of deductions on the final IRPF.
    """

    def test_dependents_reduce_taxable_base(self) -> None:
        """Two dependents should reduce taxable base by 2 × R$ 189,59."""
        results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
            num_dependents=2,
        )
        # Base without deductions: 8050 - 885.50 = 7164.50
        # With 2 dependents: 7164.50 - (2 × 189.59) = 6785.32
        expected_base = 8050.00 - 885.50 - (2 * IRPF_DEPENDENT_DEDUCTION)
        self.assertAlmostEqual(
            results["taxable_base"], expected_base, places=2
        )

    def test_pgbl_reduces_taxable_base(self) -> None:
        """PGBL of R$ 500 should reduce the taxable base."""
        results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
            pgbl_contribution=500.00,
        )
        # PGBL capped at 12% of 8050 = 966.00 → 500 is below cap
        expected_base = 8050.00 - 885.50 - 500.00
        self.assertAlmostEqual(
            results["taxable_base"], expected_base, places=2
        )

    def test_pgbl_capped_at_12_percent(self) -> None:
        """PGBL contribution exceeding 12% of Pró-labore is capped."""
        results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
            pgbl_contribution=5000.00,  # Way above 12% cap
        )
        # Cap = 12% of 8050 = 966.00
        pgbl_capped = 8050.00 * 0.12
        expected_base = 8050.00 - 885.50 - pgbl_capped
        self.assertAlmostEqual(
            results["taxable_base"], expected_base, places=2
        )
        self.assertAlmostEqual(
            results["irpf_deductions"]["pgbl"], pgbl_capped, places=2
        )

    def test_alimony_reduces_taxable_base(self) -> None:
        """Alimony should reduce the taxable base by the full amount."""
        results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
            alimony=1000.00,
        )
        expected_base = 8050.00 - 885.50 - 1000.00
        self.assertAlmostEqual(
            results["taxable_base"], expected_base, places=2
        )

    def test_combined_deductions(self) -> None:
        """All deductions combined should reduce the taxable base."""
        results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
            num_dependents=1,
            pgbl_contribution=300.00,
            alimony=500.00,
        )
        expected_base = (
            8050.00 - 885.50
            - (1 * IRPF_DEPENDENT_DEDUCTION)
            - 300.00
            - 500.00
        )
        self.assertAlmostEqual(
            results["taxable_base"], expected_base, places=2
        )

    def test_deductions_cannot_make_base_negative(self) -> None:
        """Massive deductions should floor the taxable base at zero."""
        results = calculate_taxes(
            revenue_usd=883.00,
            exchange_rate=5.23,
            num_dependents=10,  # 10 × 189.59 = 1895.90 > pro-labore
            alimony=5000.00,
        )
        self.assertGreaterEqual(results["taxable_base"], 0.0)
        self.assertAlmostEqual(results["irpf_tax"], 0.0, places=2)

    def test_no_deductions_is_default(self) -> None:
        """Without deduction kwargs, taxable base is Pró-labore - INSS."""
        results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
        )
        expected_base = 8050.00 - 885.50
        self.assertAlmostEqual(
            results["taxable_base"], expected_base, places=2
        )

    def test_irpf_deductions_dict_present(self) -> None:
        """Return dict should contain irpf_deductions breakdown."""
        results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
            num_dependents=1,
            pgbl_contribution=200.00,
            alimony=300.00,
        )
        deductions = results["irpf_deductions"]
        self.assertIn("inss", deductions)
        self.assertIn("dependents", deductions)
        self.assertIn("pgbl", deductions)
        self.assertIn("alimony", deductions)
        self.assertAlmostEqual(
            deductions["dependents"], IRPF_DEPENDENT_DEDUCTION, places=2
        )
        self.assertAlmostEqual(deductions["pgbl"], 200.00, places=2)
        self.assertAlmostEqual(deductions["alimony"], 300.00, places=2)


class TestNetTakeHomeWithIRPF(unittest.TestCase):
    """Verify the net take-home identity: Net = (Pro-labore - INSS - IRPF) + Dividends.

    Tested across multiple revenue scenarios to ensure the formula holds
    regardless of whether IRPF is zero, in the phase-out zone, or full.
    """

    def _verify_identity(self, revenue_usd: float, exchange_rate: float,
                         **kwargs) -> None:
        """Helper to verify net take-home identity for any scenario."""
        results = calculate_taxes(
            revenue_usd=revenue_usd,
            exchange_rate=exchange_rate,
            **kwargs,
        )
        expected = (
            results["ideal_pro_labore"]
            - results["inss_tax"]
            - results["irpf_tax"]
            + results["available_dividends"]
        )
        self.assertAlmostEqual(
            results["total_net_take_home"], expected, places=2,
            msg=f"Net take-home identity failed for ${revenue_usd} @ {exchange_rate}"
        )

    def test_standard_case(self) -> None:
        """Standard test case ($883, 5.23) — IRPF = 0."""
        self._verify_identity(883.00, 5.23)

    def test_high_revenue(self) -> None:
        """High revenue ($5000, 5.75) — IRPF > 0 with reducer."""
        self._verify_identity(5000.00, 5.75)

    def test_low_revenue(self) -> None:
        """Low revenue ($100, 5.00) — IRPF = 0, negative dividends."""
        self._verify_identity(100.00, 5.00)

    def test_with_deductions(self) -> None:
        """High revenue with deductions."""
        self._verify_identity(
            5000.00, 5.75,
            num_dependents=2,
            pgbl_contribution=500.00,
            alimony=1000.00,
        )

    def test_very_high_revenue_no_reducer(self) -> None:
        """Very high revenue where taxable base > R$ 7.350 → no reducer."""
        self._verify_identity(10000.00, 5.75)


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


class TestNonNegativeIntPrompt(unittest.TestCase):
    """Test the NonNegativeIntPrompt input validation (v3.0)."""

    def setUp(self) -> None:
        self.prompt = NonNegativeIntPrompt("test")

    def test_accepts_zero(self) -> None:
        """Zero should be accepted (0 dependents is valid)."""
        self.assertEqual(self.prompt.process_response("0"), 0)

    def test_accepts_positive(self) -> None:
        """Positive integers should be accepted."""
        self.assertEqual(self.prompt.process_response("3"), 3)

    def test_rejects_negative(self) -> None:
        """Negative numbers should be rejected."""
        with self.assertRaises(InvalidResponse):
            self.prompt.process_response("-1")

    def test_rejects_float(self) -> None:
        """Float strings should be rejected (must be integer)."""
        with self.assertRaises(InvalidResponse):
            self.prompt.process_response("2.5")

    def test_rejects_text(self) -> None:
        """Non-numeric text should be rejected."""
        with self.assertRaises(InvalidResponse):
            self.prompt.process_response("abc")

    def test_strips_whitespace(self) -> None:
        """Leading/trailing whitespace should be stripped."""
        self.assertEqual(self.prompt.process_response("  2  "), 2)


class TestNonNegativeFloatPrompt(unittest.TestCase):
    """Test the NonNegativeFloatPrompt input validation (v3.0)."""

    def setUp(self) -> None:
        self.prompt = NonNegativeFloatPrompt("test")

    def test_accepts_zero(self) -> None:
        """Zero should be accepted (no deduction is valid)."""
        self.assertEqual(self.prompt.process_response("0"), 0.0)

    def test_accepts_positive(self) -> None:
        """Positive floats should be accepted."""
        self.assertEqual(self.prompt.process_response("500.50"), 500.50)

    def test_rejects_negative(self) -> None:
        """Negative numbers should be rejected."""
        with self.assertRaises(InvalidResponse):
            self.prompt.process_response("-100")

    def test_rejects_text(self) -> None:
        """Non-numeric text should be rejected."""
        with self.assertRaises(InvalidResponse):
            self.prompt.process_response("abc")


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
            "irpf_tax": 0.0,
        }
        bar = render_breakdown_bar(results)
        self.assertIn("No revenue", bar.plain)

    def test_high_revenue_shows_irpf_segment(self) -> None:
        """High income with IRPF > 0 should show 'IRPF' bar segment."""
        results = calculate_taxes(revenue_usd=5000.00, exchange_rate=5.75)
        bar = render_breakdown_bar(results)
        self.assertIn("IRPF", bar.plain)

    def test_low_revenue_no_irpf_segment(self) -> None:
        """Low income with IRPF = 0 should not show 'IRPF' bar segment."""
        results = calculate_taxes(revenue_usd=883.00, exchange_rate=5.23)
        bar = render_breakdown_bar(results)
        self.assertNotIn("IRPF", bar.plain)


class TestStatePersistence(unittest.TestCase):
    """Test the cross-session JSON state persistence.

    Uses a temporary directory to isolate tests from the user's
    real ~/.rcal_state.json file.
    """

    def setUp(self) -> None:
        """Create a temporary state file path for each test."""
        self.tmp_dir = tempfile.mkdtemp()
        self.tmp_state = Path(self.tmp_dir) / ".rcal_state.json"
        self.patcher = patch("main.STATE_FILE", self.tmp_state)
        self.patcher.start()

    def tearDown(self) -> None:
        """Clean up temporary files."""
        self.patcher.stop()
        if self.tmp_state.exists():
            self.tmp_state.unlink()
        Path(self.tmp_dir).rmdir()

    def test_save_creates_file(self) -> None:
        """save_state() should create the JSON file."""
        self.assertFalse(self.tmp_state.exists())
        save_state("03/2026", 883.0, 5.23)
        self.assertTrue(self.tmp_state.exists())

    def test_save_load_roundtrip(self) -> None:
        """Data should survive a save → load cycle."""
        save_state("03/2026", 883.0, 5.23)
        state = load_state()
        self.assertEqual(state["month_year"], "03/2026")
        self.assertAlmostEqual(state["revenue_usd"], 883.0)
        self.assertAlmostEqual(state["exchange_rate"], 5.23)

    def test_load_missing_file(self) -> None:
        """Loading from a non-existent file should return empty dict."""
        state = load_state()
        self.assertEqual(state, {})

    def test_load_corrupted_file(self) -> None:
        """Loading from a corrupted JSON file should return empty dict."""
        self.tmp_state.write_text("not valid json {{{", encoding="utf-8")
        state = load_state()
        self.assertEqual(state, {})

    def test_clear_deletes_file(self) -> None:
        """clear_state() should delete the state file."""
        save_state("03/2026", 883.0, 5.23)
        self.assertTrue(self.tmp_state.exists())
        result = clear_state()
        self.assertTrue(result)
        self.assertFalse(self.tmp_state.exists())

    def test_clear_missing_file(self) -> None:
        """clear_state() on missing file should return False."""
        result = clear_state()
        self.assertFalse(result)

    def test_state_file_is_valid_json(self) -> None:
        """The saved file should be valid, human-readable JSON."""
        save_state("04/2026", 5000.0, 5.75)
        raw = self.tmp_state.read_text(encoding="utf-8")
        data = json.loads(raw)
        self.assertIn("month_year", data)
        self.assertIn("revenue_usd", data)
        self.assertIn("exchange_rate", data)
        # Should be indented (human-readable)
        self.assertIn("\n", raw)

    def test_deduction_persistence(self) -> None:
        """v3.0: Deduction values should be saved and loaded."""
        save_state(
            "03/2026", 5000.0, 5.75,
            num_dependents=2,
            pgbl_contribution=500.0,
            alimony=1000.0,
        )
        state = load_state()
        self.assertEqual(state["num_dependents"], 2)
        self.assertAlmostEqual(state["pgbl_contribution"], 500.0)
        self.assertAlmostEqual(state["alimony"], 1000.0)

    def test_backward_compatible_load(self) -> None:
        """v3.0: Old state files without deduction keys should load fine."""
        old_state = {
            "month_year": "02/2026",
            "revenue_usd": 883.0,
            "exchange_rate": 5.23,
        }
        self.tmp_state.write_text(
            json.dumps(old_state, indent=2) + "\n",
            encoding="utf-8",
        )
        state = load_state()
        self.assertEqual(state["month_year"], "02/2026")
        # Deduction keys are simply absent — caller handles defaults
        self.assertNotIn("num_dependents", state)

    def test_zero_deductions_saved(self) -> None:
        """v3.0: Zero deductions should still be explicitly saved."""
        save_state("03/2026", 883.0, 5.23)  # defaults are all 0
        state = load_state()
        self.assertEqual(state["num_dependents"], 0)
        self.assertAlmostEqual(state["pgbl_contribution"], 0.0)
        self.assertAlmostEqual(state["alimony"], 0.0)


if __name__ == "__main__":
    unittest.main()
