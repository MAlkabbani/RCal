#!/usr/bin/env python3
# pylint: disable=unused-argument, too-many-arguments
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

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from rich.prompt import InvalidResponse

from main import (
    DAS_TAX_RATE,
    FATOR_R_TARGET,
    INSS_CEILING,
    INSS_TAX_RATE,
    IRPF_DEPENDENT_DEDUCTION,
    IRPF_SIMPLIFIED_DEDUCTION,
    LEGAL_MINIMUM_WAGE,
    MINIMUM_VIABLE_REVENUE_BRL,
    MonthYearPrompt,
    NonNegativeFloatPrompt,
    NonNegativeIntPrompt,
    PositiveFloatPrompt,
    TaxCalculationResult,
    calculate_irpf_2026,
    calculate_taxes,
    clear_state,
    format_brl,
    format_pct,
    load_state,
    render_breakdown_bar,
    save_state,
)


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
        self.assertAlmostEqual(self.results.gross_revenue_brl, 4618.09, places=2)

    def test_pro_labore_uses_minimum_wage(self) -> None:
        """§5: 28% of 4618.09 = 1293.06, which is below minimum wage.
        Pró-labore should snap to the federal minimum wage floor."""
        self.assertAlmostEqual(
            self.results.ideal_pro_labore, LEGAL_MINIMUM_WAGE, places=2
        )

    def test_fator_r_minimum_below_wage(self) -> None:
        """§5: Fator R minimum (1293.06) must be below minimum wage."""
        self.assertLess(self.results.fator_r_minimum, LEGAL_MINIMUM_WAGE)

    def test_inss(self) -> None:
        """§5: Expected INSS is R$ 178,31."""
        self.assertAlmostEqual(self.results.inss_tax, 178.31, places=2)

    def test_irpf_tax_free(self) -> None:
        """§5: Taxable base = 1621 - 178.31 = 1442.69 → below R$ 2.428,80
        → IRPF is R$ 0,00 (exempt bracket)."""
        self.assertAlmostEqual(self.results.irpf_tax, 0.0, places=2)
        self.assertIn("Tax Free", str(self.results.irpf_status))

    def test_taxable_base(self) -> None:
        """§5: Simplified monthly deduction should apply when it is better."""
        expected = LEGAL_MINIMUM_WAGE - IRPF_SIMPLIFIED_DEDUCTION
        self.assertAlmostEqual(self.results.taxable_base, expected, places=2)

    # ── Additional Edge Cases ────────────────────────────────────

    def test_dividends_positive(self) -> None:
        """Dividends must always be positive for valid inputs."""
        self.assertGreater(self.results.available_dividends, 0)

    def test_net_take_home_less_than_gross(self) -> None:
        """Net take-home must be less than gross (taxes are deducted)."""
        self.assertLess(
            self.results.total_net_take_home,
            self.results.gross_revenue_brl,
        )

    def test_net_take_home_identity(self) -> None:
        """Net = (Pró-labore - INSS - IRPF) + Dividends."""
        expected = (
            self.results.ideal_pro_labore
            - self.results.inss_tax
            - self.results.irpf_tax
            + self.results.available_dividends
        )
        self.assertAlmostEqual(self.results.total_net_take_home, expected, places=2)


class TestHighRevenueScenario(unittest.TestCase):
    """Test with high revenue where Fator R minimum exceeds minimum wage
    and IRPF applies.

    Input: $5000 USD × 5.75 rate = R$ 28.750 gross
    Pró-labore: R$ 8.050,00 (28% of R$ 28.750)
    INSS: R$ 885,50 (11% of R$ 8.050)
    Taxable base: R$ 8.050 - R$ 885,50 = R$ 7.164,50
    → Falls in 27.5% bracket: 7164.50 × 0.275 - 908.73 = R$ 1.061,51
    → No 2026 reducer applies because the gross taxable income is R$ 8.050,00
        which is above the R$ 7.350,00 reduction ceiling.
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
            self.results.ideal_pro_labore, expected_pro_labore, places=2
        )

    def test_taxable_base(self) -> None:
        """Taxable base = Pró-labore - INSS = 8050 - 885.50 = 7164.50."""
        self.assertAlmostEqual(self.results.taxable_base, 7164.50, places=2)

    def test_irpf_is_calculated(self) -> None:
        """IRPF should be a positive value for this high-income scenario."""
        self.assertGreater(self.results.irpf_tax, 0)

    def test_irpf_calculation_without_reducer(self) -> None:
        """Verify the exact IRPF value when the gross salary exceeds R$ 7.350.

        Standard table: 7164.50 × 0.275 - 908.73 = 1061.5075
        Final: 1061.5075
        """
        self.assertAlmostEqual(self.results.irpf_tax, 1061.51, places=2)

    def test_irpf_status_shows_amount(self) -> None:
        """IRPF status should show the calculated amount, not just 'Triggered'."""
        self.assertIn("IRPF", str(self.results.irpf_status))
        self.assertIn("R$", str(self.results.irpf_status))

    def test_net_take_home_includes_irpf(self) -> None:
        """Net take-home must subtract IRPF from the salary portion."""
        expected = (
            self.results.ideal_pro_labore
            - self.results.inss_tax
            - self.results.irpf_tax
            + self.results.available_dividends
        )
        self.assertAlmostEqual(self.results.total_net_take_home, expected, places=2)

    def test_bracket_warning_triggered(self) -> None:
        """Annual revenue of R$ 345k exceeds Bracket 1 ceiling of R$ 180k."""
        self.assertIn("Bracket", str(self.results.bracket_warning))


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
            self.results.ideal_pro_labore, LEGAL_MINIMUM_WAGE, places=2
        )

    def test_no_bracket_warning(self) -> None:
        """Low revenue should not trigger bracket warning."""
        self.assertEqual(self.results.bracket_warning, "")

    def test_negative_dividends_possible(self) -> None:
        """With very low revenue, dividends can be negative
        (Pró-labore + DAS > revenue)."""
        # R$ 500 gross - R$ 1621 pro-labore - DAS = negative
        self.assertLess(float(self.results.available_dividends), 0)

    def test_irpf_zero_for_low_income(self) -> None:
        """IRPF should be zero for minimum wage Pró-labore."""
        self.assertAlmostEqual(float(self.results.irpf_tax), 0.0, places=2)


class TestZeroRevenueCompliance(unittest.TestCase):
    """Test zero and near-zero revenue scenarios (Simples Nacional compliance)."""

    def test_minimum_viable_threshold_constant(self) -> None:
        """Verify the constant mathematically matches the formula."""
        expected = LEGAL_MINIMUM_WAGE + (LEGAL_MINIMUM_WAGE * DAS_TAX_RATE)
        self.assertAlmostEqual(MINIMUM_VIABLE_REVENUE_BRL, expected, places=2)

    def test_zero_revenue_flags(self) -> None:
        """Exact zero revenue should set both tracking flags."""
        results = calculate_taxes(revenue_usd=0.0, exchange_rate=5.00)
        self.assertTrue(results.is_zero_revenue)
        self.assertTrue(results.is_below_viable_threshold)

    def test_near_zero_revenue_flags(self) -> None:
        """Near-zero revenue should only set the threshold flag."""
        results = calculate_taxes(revenue_usd=100.0, exchange_rate=5.00)
        self.assertFalse(results.is_zero_revenue)
        self.assertTrue(results.is_below_viable_threshold)

    def test_normal_revenue_flags(self) -> None:
        """Normal revenue should set neither flag."""
        results = calculate_taxes(revenue_usd=5000.0, exchange_rate=5.00)
        self.assertFalse(results.is_zero_revenue)
        self.assertFalse(results.is_below_viable_threshold)

    def test_zero_revenue_dividends_negative(self) -> None:
        """Zero revenue forces negative dividends since the minimum Pró-labore + DAS represents a cost."""
        results = calculate_taxes(revenue_usd=0.0, exchange_rate=5.00)
        self.assertEqual(float(results.gross_revenue_brl), 0.0)
        # Dividends = 0 - 1621.00 - 0 = -1621.00
        self.assertAlmostEqual(
            float(results.available_dividends), -LEGAL_MINIMUM_WAGE, places=2
        )

    def test_zero_revenue_inss_calculated(self) -> None:
        """Even with zero revenue, INSS should nominally calculate based on minimum wage floor
        to accurately reflect the tax burden of withdrawing a salary if the owner chooses to.
        """
        results = calculate_taxes(revenue_usd=0.0, exchange_rate=5.00)
        expected_inss = LEGAL_MINIMUM_WAGE * INSS_TAX_RATE
        self.assertAlmostEqual(float(results.inss_tax), expected_inss, places=2)

    def test_zero_revenue_das(self) -> None:
        """DAS is strictly proportional to gross revenue and must be zero."""
        results = calculate_taxes(revenue_usd=0.0, exchange_rate=5.00)
        self.assertAlmostEqual(float(results.estimated_das), 0.0, places=2)


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

    def test_receita_example_2_full_reduction(self) -> None:
        """Official Receita example: R$ 4.000 gross and R$ 3.392,80 base."""
        std, reducer, final = calculate_irpf_2026(
            3392.80,
            reduction_basis=4000.00,
        )
        self.assertAlmostEqual(std, 114.76, places=2)
        self.assertAlmostEqual(reducer, 114.76, places=2)
        self.assertAlmostEqual(final, 0.0, places=2)

    def test_receita_example_4_phase_out(self) -> None:
        """Official Receita example: R$ 6.000 gross and R$ 5.350,40 base."""
        std, reducer, final = calculate_irpf_2026(
            5350.40,
            reduction_basis=6000.00,
        )
        self.assertAlmostEqual(std, 562.63, places=2)
        self.assertAlmostEqual(reducer, 179.75, places=2)
        self.assertAlmostEqual(final, 382.88, places=2)

    def test_reduction_uses_gross_income_not_base(self) -> None:
        """Gross salary above R$ 7.350 removes the reduction even if the base does not."""
        std, reducer, final = calculate_irpf_2026(
            7164.50,
            reduction_basis=8050.00,
        )
        self.assertAlmostEqual(std, 1061.51, places=2)
        self.assertAlmostEqual(reducer, 0.0, places=2)
        self.assertAlmostEqual(final, 1061.51, places=2)

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
        self.assertAlmostEqual(results.taxable_base, expected_base, places=2)

    def test_pgbl_reduces_taxable_base(self) -> None:
        """PGBL of R$ 500 should reduce the taxable base."""
        results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
            pgbl_contribution=500.00,
        )
        # PGBL capped at 12% of 8050 = 966.00 → 500 is below cap
        expected_base = 8050.00 - 885.50 - 500.00
        self.assertAlmostEqual(results.taxable_base, expected_base, places=2)

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
        self.assertAlmostEqual(results.taxable_base, expected_base, places=2)
        self.assertAlmostEqual(results.irpf_deductions["pgbl"], pgbl_capped, places=2)

    def test_alimony_reduces_taxable_base(self) -> None:
        """Alimony should reduce the taxable base by the full amount."""
        results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
            alimony=1000.00,
        )
        expected_base = 8050.00 - 885.50 - 1000.00
        self.assertAlmostEqual(results.taxable_base, expected_base, places=2)

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
            8050.00 - 885.50 - (1 * IRPF_DEPENDENT_DEDUCTION) - 300.00 - 500.00
        )
        self.assertAlmostEqual(results.taxable_base, expected_base, places=2)

    def test_deductions_cannot_make_base_negative(self) -> None:
        """Massive deductions should floor the taxable base at zero."""
        results = calculate_taxes(
            revenue_usd=883.00,
            exchange_rate=5.23,
            num_dependents=10,  # 10 × 189.59 = 1895.90 > pro-labore
            alimony=5000.00,
        )
        self.assertGreaterEqual(results.taxable_base, 0.0)
        self.assertAlmostEqual(results.irpf_tax, 0.0, places=2)

    def test_no_deductions_is_default(self) -> None:
        """Without deduction kwargs, taxable base is Pró-labore - INSS."""
        results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
        )
        expected_base = 8050.00 - 885.50
        self.assertAlmostEqual(results.taxable_base, expected_base, places=2)

    def test_irpf_deductions_dict_present(self) -> None:
        """Return dict should contain irpf_deductions breakdown."""
        results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
            num_dependents=1,
            pgbl_contribution=200.00,
            alimony=300.00,
        )
        deductions = results.irpf_deductions
        self.assertIn("inss", deductions)
        self.assertIn("dependents", deductions)
        self.assertIn("pgbl", deductions)
        self.assertIn("alimony", deductions)
        self.assertIn("simplified", deductions)
        self.assertIn("applied_total", deductions)
        self.assertAlmostEqual(
            deductions["dependents"], IRPF_DEPENDENT_DEDUCTION, places=2
        )
        self.assertAlmostEqual(deductions["pgbl"], 200.00, places=2)
        self.assertAlmostEqual(deductions["alimony"], 300.00, places=2)

    def test_simplified_deduction_wins_for_low_salary(self) -> None:
        """Low pró-labore should switch to the simplified monthly deduction."""
        results = calculate_taxes(
            revenue_usd=883.00,
            exchange_rate=5.23,
        )
        self.assertEqual(results.irpf_deduction_model, "Simplified")
        self.assertAlmostEqual(
            results.irpf_deduction_total,
            IRPF_SIMPLIFIED_DEDUCTION,
            places=2,
        )


class TestNetTakeHomeWithIRPF(unittest.TestCase):
    """Verify the net take-home identity: Net = (Pro-labore - INSS - IRPF) + Dividends.

    Tested across multiple revenue scenarios to ensure the formula holds
    regardless of whether IRPF is zero, in the phase-out zone, or full.
    """

    def _verify_identity(
        self, revenue_usd: float, exchange_rate: float, **kwargs
    ) -> None:
        """Helper to verify net take-home identity for any scenario."""
        results = calculate_taxes(
            revenue_usd=revenue_usd,
            exchange_rate=exchange_rate,
            **kwargs,
        )
        expected = (
            results.ideal_pro_labore
            - results.inss_tax
            - results.irpf_tax
            + results.available_dividends
        )
        self.assertAlmostEqual(
            results.total_net_take_home,
            expected,
            places=2,
            msg=f"Net take-home identity failed for ${revenue_usd} @ {exchange_rate}",
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
            5000.00,
            5.75,
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
        self.assertEqual(self.prompt.process_response("  03/2026  "), "03/2026")


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
        results = TaxCalculationResult(
            gross_revenue_brl=0.0,
            fator_r_minimum=0.0,
            ideal_pro_labore=0.0,
            inss_tax=0.0,
            estimated_das=0.0,
            irpf_status="",
            irpf_tax=0.0,
            irpf_standard=0.0,
            irpf_reducer=0.0,
            taxable_base=0.0,
            irpf_deduction_model="Legal",
            irpf_deduction_total=0.0,
            irpf_reduction_basis=0.0,
            irpf_deductions={},
            bracket_warning="",
            available_dividends=0.0,
            total_net_take_home=0.0,
            is_zero_revenue=True,
            is_below_viable_threshold=False,
        )
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

    def test_negative_dividends_with_irpf_segment(self) -> None:
        """Artificial scenario: IRPF > 0 but dividends are negative.
        Covers main.py Line ~617 block.
        """
        results = TaxCalculationResult(
            gross_revenue_brl=1000.0,
            fator_r_minimum=0.0,
            ideal_pro_labore=5000.0,
            inss_tax=550.0,
            estimated_das=0.0,
            irpf_status="Ouch",
            irpf_tax=100.0,
            irpf_standard=0.0,
            irpf_reducer=0.0,
            taxable_base=4450.0,
            irpf_deduction_model="Legal",
            irpf_deduction_total=550.0,
            irpf_reduction_basis=5000.0,
            irpf_deductions={},
            bracket_warning="",
            available_dividends=-4650.0,
            total_net_take_home=0.0,
            is_zero_revenue=False,
            is_below_viable_threshold=True,
        )
        bar = render_breakdown_bar(results)
        self.assertIn("IRPF", bar.plain)
        self.assertIn("of costs", bar.plain)


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
        self.assertAlmostEqual(float(state["revenue_usd"]), 883.0)
        self.assertAlmostEqual(float(state["exchange_rate"]), 5.23)

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
            "03/2026",
            5000.0,
            5.75,
            num_dependents=2,
            pgbl_contribution=500.0,
            alimony=1000.0,
        )
        state = load_state()
        self.assertEqual(state["num_dependents"], 2)
        self.assertAlmostEqual(float(state["pgbl_contribution"]), 500.0)
        self.assertAlmostEqual(float(state["alimony"]), 1000.0)

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
        self.assertAlmostEqual(float(state["pgbl_contribution"]), 0.0)
        self.assertAlmostEqual(float(state["alimony"]), 0.0)


# ── v3.0.1 Mathematical Validation Tests ─────────────────────────


class TestINSSCeiling(unittest.TestCase):
    """Test the INSS contribution ceiling (teto previdenciário).

    In 2026, the INSS contribution base is capped at R$ 8.475,55.
    The maximum monthly INSS is R$ 932,31 (11% × R$ 8.475,55).

    The ceiling triggers when Pró-labore > R$ 8.475,55, which occurs
    when gross BRL revenue > R$ 8.475,55 / 0.28 = R$ 30.269,82.
    """

    def test_below_ceiling_unchanged(self) -> None:
        """Pró-labore below ceiling → INSS = 11% of full Pró-labore.

        $5000 × 5.75 = R$ 28.750 → Pró-labore R$ 8.050 < ceiling.
        INSS = 8050 × 0.11 = R$ 885,50.
        """
        results = calculate_taxes(revenue_usd=5000.00, exchange_rate=5.75)
        expected_inss = 8050.00 * INSS_TAX_RATE
        self.assertAlmostEqual(results.inss_tax, expected_inss, places=2)

    def test_at_ceiling_boundary(self) -> None:
        """Pró-labore at exactly the ceiling → INSS = ceiling × 11%.

        Gross needed for Pró-labore = R$ 8.475,55:
        8475.55 / 0.28 = R$ 30.269,82 → at rate 1.0: $30269.82.
        """
        # Use exchange rate = 1.0 for easy math
        target_gross = INSS_CEILING / FATOR_R_TARGET
        results = calculate_taxes(revenue_usd=target_gross, exchange_rate=1.0)
        self.assertAlmostEqual(results.ideal_pro_labore, INSS_CEILING, places=2)
        expected_inss = INSS_CEILING * INSS_TAX_RATE
        self.assertAlmostEqual(results.inss_tax, expected_inss, places=2)

    def test_above_ceiling_capped(self) -> None:
        """Pró-labore above ceiling → INSS capped at R$ 932,31.

        $5500 × 5.75 = R$ 31.625 → Pró-labore R$ 8.855 > ceiling.
        INSS should be min(8855, 8475.55) × 0.11 = 8475.55 × 0.11 = 932.31.
        NOT 8855 × 0.11 = 974.05.
        """
        results = calculate_taxes(revenue_usd=5500.00, exchange_rate=5.75)
        expected_pro_labore = 5500.00 * 5.75 * FATOR_R_TARGET
        self.assertAlmostEqual(results.ideal_pro_labore, expected_pro_labore, places=2)
        max_inss = INSS_CEILING * INSS_TAX_RATE
        self.assertAlmostEqual(results.inss_tax, max_inss, places=2)
        # Must NOT equal the uncapped value
        uncapped = expected_pro_labore * INSS_TAX_RATE
        self.assertNotAlmostEqual(results.inss_tax, uncapped, places=2)

    def test_very_high_revenue_still_capped(self) -> None:
        """$10,000 × 6.00 = R$ 60,000 → Pró-labore R$ 16.800.
        INSS must still be capped at R$ 932,31."""
        results = calculate_taxes(revenue_usd=10000.00, exchange_rate=6.00)
        max_inss = INSS_CEILING * INSS_TAX_RATE
        self.assertAlmostEqual(results.inss_tax, max_inss, places=2)

    def test_ceiling_affects_taxable_base(self) -> None:
        """Capped INSS produces a higher taxable base → higher IRPF.

        Without ceiling: taxable_base = 8855 - 974.05 = 7880.95
        With ceiling:    taxable_base = 8855 - 932.31 = 7922.69

        The capped scenario should have a higher taxable base.
        """
        results = calculate_taxes(revenue_usd=5500.00, exchange_rate=5.75)
        pro_labore = results.ideal_pro_labore  # 8855.00
        inss = results.inss_tax  # 932.31 (capped)
        expected_base = pro_labore - inss
        self.assertAlmostEqual(results.taxable_base, expected_base, places=2)
        # Verify the taxable base is higher than it would be without ceiling
        uncapped_base = pro_labore - (pro_labore * INSS_TAX_RATE)
        self.assertGreater(results.taxable_base, uncapped_base)

    def test_ceiling_cascades_to_net_take_home(self) -> None:
        """The net take-home identity must hold with capped INSS.

        Net = (Pró-labore - INSS_capped - IRPF) + Dividends.
        """
        results = calculate_taxes(revenue_usd=5500.00, exchange_rate=5.75)
        expected = (
            results.ideal_pro_labore
            - results.inss_tax
            - results.irpf_tax
            + results.available_dividends
        )
        self.assertAlmostEqual(results.total_net_take_home, expected, places=2)

    def test_ceiling_irpf_correct_value(self) -> None:
        """Verify exact IRPF for the above-ceiling scenario.

        Pró-labore: R$ 8.855,00.  INSS (capped): R$ 932,31.
        Taxable base: 8855 - 932.31 = 7922.69.
        Bracket: 27.5% → Standard = 7922.69 × 0.275 - 908.73 = 1270.01.
        Reducer: none (7922.69 > 7350) → Final IRPF = 1270.01.
        """
        results = calculate_taxes(revenue_usd=5500.00, exchange_rate=5.75)
        self.assertAlmostEqual(results.irpf_tax, 1270.01, places=1)

    def test_inss_deductions_dict_reflects_cap(self) -> None:
        """The irpf_deductions.inss value should use the capped amount."""
        results = calculate_taxes(revenue_usd=5500.00, exchange_rate=5.75)
        max_inss = INSS_CEILING * INSS_TAX_RATE
        self.assertAlmostEqual(results.irpf_deductions["inss"], max_inss, places=2)


class TestDASRateDerivation(unittest.TestCase):
    """Verify the DAS_TAX_RATE constant derivation is mathematically correct.

    Anexo III, Bracket 1 (up to R$ 180k/year):
        Nominal rate: 6.00%
        Repartition: IRPJ 4% + CSLL 3.5% + COFINS 12.82% + PIS 2.78%
                     + CPP 43.4% + ISS 33.5% = 100%

    Export exemptions remove ISS (33.5%), PIS (2.78%), COFINS (12.82%):
        Remaining = IRPJ + CSLL + CPP = 4% + 3.5% + 43.4% = 50.9%
        Effective = 6% × 50.9% = 3.054%
    """

    def test_das_rate_value(self) -> None:
        """DAS_TAX_RATE constant must equal 3.054%."""
        self.assertAlmostEqual(DAS_TAX_RATE, 0.03054, places=5)

    def test_das_rate_derivation(self) -> None:
        """Independently derive the DAS rate from first principles."""
        nominal_rate = 0.06

        # Repartition percentages (must sum to 100)
        irpj = 4.00
        csll = 3.50
        cofins = 12.82
        pis = 2.78
        cpp = 43.40
        iss = 33.50
        total = irpj + csll + cofins + pis + cpp + iss
        self.assertAlmostEqual(total, 100.00, places=2)

        # Export-exempt: ISS + PIS + COFINS
        remaining_pct = (irpj + csll + cpp) / 100.0
        derived_rate = nominal_rate * remaining_pct

        self.assertAlmostEqual(derived_rate, DAS_TAX_RATE, places=5)

    def test_das_applied_correctly(self) -> None:
        """DAS = gross_revenue × DAS_TAX_RATE."""
        results = calculate_taxes(revenue_usd=883.00, exchange_rate=5.23)
        expected_das = 883.00 * 5.23 * DAS_TAX_RATE
        self.assertAlmostEqual(results.estimated_das, expected_das, places=2)


class TestInputGuardsNaNInfinity(unittest.TestCase):
    """Test that NaN and Infinity values are rejected by float prompts.

    Python's float('nan') and float('inf') pass the basic float()
    conversion but would produce nonsensical tax calculations.
    The math.isfinite() guard catches these at the input boundary.
    """

    def setUp(self) -> None:
        self.pos_prompt = PositiveFloatPrompt("test")
        self.nn_prompt = NonNegativeFloatPrompt("test")

    # ── PositiveFloatPrompt ──────────────────────────────────────

    def test_positive_rejects_nan(self) -> None:
        """NaN should be rejected by PositiveFloatPrompt."""
        with self.assertRaises(InvalidResponse):
            self.pos_prompt.process_response("nan")

    def test_positive_rejects_inf(self) -> None:
        """Infinity should be rejected by PositiveFloatPrompt."""
        with self.assertRaises(InvalidResponse):
            self.pos_prompt.process_response("inf")

    def test_positive_rejects_negative_inf(self) -> None:
        """-Infinity should be rejected by PositiveFloatPrompt."""
        with self.assertRaises(InvalidResponse):
            self.pos_prompt.process_response("-inf")

    def test_positive_accepts_normal_float(self) -> None:
        """Normal positive floats should still be accepted."""
        self.assertEqual(self.pos_prompt.process_response("5.75"), 5.75)

    # ── NonNegativeFloatPrompt ───────────────────────────────────

    def test_nonneg_rejects_nan(self) -> None:
        """NaN should be rejected by NonNegativeFloatPrompt."""
        with self.assertRaises(InvalidResponse):
            self.nn_prompt.process_response("nan")

    def test_nonneg_rejects_inf(self) -> None:
        """Infinity should be rejected by NonNegativeFloatPrompt."""
        with self.assertRaises(InvalidResponse):
            self.nn_prompt.process_response("inf")

    def test_nonneg_rejects_negative_inf(self) -> None:
        """-Infinity should be rejected by NonNegativeFloatPrompt."""
        with self.assertRaises(InvalidResponse):
            self.nn_prompt.process_response("-inf")

    def test_nonneg_accepts_zero(self) -> None:
        """Zero should still be accepted."""
        self.assertEqual(self.nn_prompt.process_response("0"), 0.0)

    def test_nonneg_accepts_normal_float(self) -> None:
        """Normal positive floats should still be accepted."""
        self.assertEqual(self.nn_prompt.process_response("500.50"), 500.50)


class TestEdgeCases(unittest.TestCase):
    """Additional edge cases discovered during the mathematical audit.

    These tests cover extreme input ranges, boundary conditions,
    and scenarios that could expose floating-point or logic issues.
    """

    def test_exact_minimum_wage_threshold(self) -> None:
        """Revenue where Fator R minimum exactly equals minimum wage.

        Gross = 1621 / 0.28 = 5789.2857... BRL.
        At this threshold, Pró-labore should equal the minimum wage.
        """
        threshold_gross = LEGAL_MINIMUM_WAGE / FATOR_R_TARGET
        results = calculate_taxes(revenue_usd=threshold_gross, exchange_rate=1.0)
        self.assertAlmostEqual(results.ideal_pro_labore, LEGAL_MINIMUM_WAGE, places=2)

    def test_just_above_fator_r_threshold(self) -> None:
        """Revenue slightly above the Fator R = minimum wage boundary.

        When gross is high enough that 28% > minimum wage, Pró-labore
        should be exactly 28% of gross (not minimum wage).
        """
        gross_brl = LEGAL_MINIMUM_WAGE / FATOR_R_TARGET + 100.0
        results = calculate_taxes(revenue_usd=gross_brl, exchange_rate=1.0)
        expected = gross_brl * FATOR_R_TARGET
        self.assertAlmostEqual(results.ideal_pro_labore, expected, places=2)
        self.assertGreater(results.ideal_pro_labore, LEGAL_MINIMUM_WAGE)

    def test_very_high_revenue_extreme(self) -> None:
        """$50,000 × 6.0 = R$ 300,000 — extreme scenario.

        Pró-labore: R$ 84,000. INSS: capped at R$ 932,31.
        Should not crash or produce incorrect signs.
        """
        results = calculate_taxes(revenue_usd=50000.00, exchange_rate=6.00)
        # Sanity checks
        self.assertGreater(results.gross_revenue_brl, 0)
        self.assertGreater(results.ideal_pro_labore, 0)
        self.assertGreater(results.available_dividends, 0)
        self.assertGreater(results.total_net_take_home, 0)
        # INSS must be capped
        max_inss = INSS_CEILING * INSS_TAX_RATE
        self.assertAlmostEqual(results.inss_tax, max_inss, places=2)

    def test_all_deductions_maxed(self) -> None:
        """All deductions at extreme values — taxable base should floor at 0.

        10 dependents + huge PGBL + huge alimony on a low income.
        """
        results = calculate_taxes(
            revenue_usd=883.00,
            exchange_rate=5.23,
            num_dependents=10,
            pgbl_contribution=99999.00,
            alimony=99999.00,
        )
        self.assertEqual(results.taxable_base, 0.0)
        self.assertAlmostEqual(results.irpf_tax, 0.0, places=2)

    def test_pgbl_exactly_at_12_percent_cap(self) -> None:
        """PGBL contribution at exactly 12% of Pró-labore.

        $5000 × 5.75 → Pró-labore R$ 8.050.
        12% of 8050 = 966.00. PGBL = 966.00 → should be accepted fully.
        """
        results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
            pgbl_contribution=966.00,
        )
        self.assertAlmostEqual(results.irpf_deductions["pgbl"], 966.00, places=2)

    def test_pgbl_one_cent_above_cap(self) -> None:
        """PGBL at 12% of Pró-labore + R$ 0.01 → must be capped.

        12% of 8050 = 966.00. PGBL = 966.01 → should cap at 966.00.
        """
        results = calculate_taxes(
            revenue_usd=5000.00,
            exchange_rate=5.75,
            pgbl_contribution=966.01,
        )
        self.assertAlmostEqual(results.irpf_deductions["pgbl"], 966.00, places=2)

    def test_effective_tax_burden_identity(self) -> None:
        """Effective tax burden = (INSS + DAS + IRPF) / Gross.

        This identity must hold for any revenue scenario.
        """
        for rev, rate in [(883, 5.23), (5000, 5.75), (5500, 5.75), (100, 5.0)]:
            results = calculate_taxes(revenue_usd=rev, exchange_rate=rate)
            gross = results.gross_revenue_brl
            if gross > 0:
                total_taxes = (
                    results.inss_tax + results.estimated_das + results.irpf_tax
                )
                burden = total_taxes / gross
                # Just verify it's a valid percentage (0% to 100%)
                self.assertGreaterEqual(burden, 0.0)
                self.assertLessEqual(burden, 1.0)

    def test_one_dollar_revenue(self) -> None:
        """Edge case: $1.00 revenue → extreme negative dividends.

        Must not crash. Pró-labore = minimum wage, dividends deeply negative.
        """
        results = calculate_taxes(revenue_usd=1.00, exchange_rate=5.00)
        self.assertAlmostEqual(results.ideal_pro_labore, LEGAL_MINIMUM_WAGE, places=2)
        self.assertLess(results.available_dividends, 0)

    def test_exchange_rate_very_small(self) -> None:
        """Small exchange rate (0.01) → very low BRL revenue.

        $100 × 0.01 = R$ 1.00. Pró-labore = minimum wage.
        """
        results = calculate_taxes(revenue_usd=100.00, exchange_rate=0.01)
        self.assertAlmostEqual(results.ideal_pro_labore, LEGAL_MINIMUM_WAGE, places=2)

    def test_exchange_rate_very_large(self) -> None:
        """Large exchange rate (100.0) → very high BRL revenue.

        $1000 × 100 = R$ 100,000. Pró-labore = R$ 28,000.
        INSS must be capped. Should not crash.
        """
        results = calculate_taxes(revenue_usd=1000.00, exchange_rate=100.0)
        expected_pro_labore = 1000.00 * 100.0 * FATOR_R_TARGET
        self.assertAlmostEqual(results.ideal_pro_labore, expected_pro_labore, places=2)
        max_inss = INSS_CEILING * INSS_TAX_RATE
        self.assertAlmostEqual(results.inss_tax, max_inss, places=2)


class TestCLI(unittest.TestCase):
    """Test the CLI UI components using unittest.mock."""

    @patch("main.Console")
    def test_display_header(self, mock_console_cls) -> None:
        """Test that the application header renders without error."""
        from main import display_header

        console = mock_console_cls()
        display_header(console)
        self.assertTrue(console.print.called)

    @patch("main.MonthYearPrompt.ask", return_value="03/2026")
    @patch("main.NonNegativeFloatPrompt.ask", return_value=1000.0)
    @patch("main.PositiveFloatPrompt.ask", return_value=5.0)
    def test_collect_inputs(self, mock_rate, mock_rev, mock_month) -> None:
        """Test base input collection prompt parsing."""
        from main import collect_inputs
        from unittest.mock import MagicMock

        console = MagicMock()
        month, rev, rate = collect_inputs(console)
        self.assertEqual(month, "03/2026")
        self.assertEqual(rev, 1000.0)
        self.assertEqual(rate, 5.0)

    @patch("main.PositiveFloatPrompt.ask", return_value=5.5)
    @patch("main.NonNegativeFloatPrompt.ask", return_value=1000.0)
    @patch("main.MonthYearPrompt.ask", return_value="03/2026")
    def test_collect_inputs_with_prev_rate(
        self, mock_month, mock_rev, mock_rate
    ) -> None:
        """Test input collection using previous rate skips rate prompt."""
        from main import collect_inputs
        from unittest.mock import MagicMock

        console = MagicMock()
        month, rev, rate = collect_inputs(console, prev_exchange_rate=5.5)
        self.assertEqual(month, "03/2026")
        self.assertEqual(rev, 1000.0)
        self.assertEqual(rate, 5.5)

    @patch("main.PositiveFloatPrompt.ask", return_value=5.1)
    @patch("main.NonNegativeFloatPrompt.ask", return_value=1500.0)
    @patch("main.MonthYearPrompt.ask", return_value="01/2026")
    def test_collect_inputs_with_saved_state(
        self, mock_month, mock_rev, mock_rate
    ) -> None:
        """Test input collection uses saved_state defaults."""
        from main import collect_inputs
        from unittest.mock import MagicMock

        console = MagicMock()
        saved = {"month_year": "01/2026", "revenue_usd": 1500.0, "exchange_rate": 5.1}
        month, rev, rate = collect_inputs(console, saved_state=saved)
        self.assertEqual(month, "01/2026")
        self.assertEqual(rev, 1500.0)
        self.assertEqual(rate, 5.1)

    @patch("main.Confirm.ask", return_value=True)
    @patch("main.NonNegativeIntPrompt.ask", return_value=1)
    @patch("main.NonNegativeFloatPrompt.ask", side_effect=[500.0, 100.0])
    def test_collect_deductions_yes(self, mock_float, mock_int, mock_confirm) -> None:
        """Test full deduction collection path."""
        from main import collect_deductions
        from unittest.mock import MagicMock

        console = MagicMock()
        deps, pgbl, ali = collect_deductions(console)
        self.assertEqual(deps, 1)
        self.assertEqual(pgbl, 500.0)
        self.assertEqual(ali, 100.0)

    @patch("main.Confirm.ask", return_value=False)
    def test_collect_deductions_no(self, mock_confirm) -> None:
        """Test skipping deduction collection path."""
        from main import collect_deductions
        from unittest.mock import MagicMock

        console = MagicMock()
        deps, pgbl, ali = collect_deductions(console)
        self.assertEqual(deps, 0)
        self.assertEqual(pgbl, 0.0)
        self.assertEqual(ali, 0.0)

    @patch("main.Console")
    def test_display_results(self, mock_console) -> None:
        """Test displaying taxes works for varying logic branches."""
        from main import display_results

        results = calculate_taxes(1000.0, 5.0)
        display_results(mock_console, "03/2026", 1000.0, 5.0, results)
        self.assertTrue(mock_console.print.called)

        # Test zero revenue warning
        results_zero = calculate_taxes(0.0, 5.0)
        display_results(mock_console, "03/2026", 0.0, 5.0, results_zero)

        # Test bracket warning
        results_high = calculate_taxes(10000.0, 5.0)
        display_results(mock_console, "03/2026", 10000.0, 5.0, results_high)

        # Test negative dividends
        results_low = calculate_taxes(100.0, 5.0)
        display_results(mock_console, "03/2026", 100.0, 5.0, results_low)

    @patch("main.Console")
    def test_display_footer(self, mock_console) -> None:
        """Test footer display renders without error."""
        from main import display_footer

        display_footer(mock_console)
        self.assertTrue(mock_console.print.called)

    @patch("main.Confirm.ask", return_value=False)
    def test_prompt_next_action_no(self, mock_confirm) -> None:
        """Test user rejecting continuation loop returns None."""
        from main import prompt_next_action
        from unittest.mock import MagicMock

        console = MagicMock()
        self.assertIsNone(prompt_next_action(console))

    @patch("main.Confirm.ask", return_value=True)
    @patch("main.Prompt.ask", side_effect=["1", "2", "3", "4"])
    def test_prompt_next_action_choices(self, mock_prompt, mock_confirm) -> None:
        """Test all 4 loop choice routes return correct keys."""
        from main import prompt_next_action
        from unittest.mock import MagicMock

        console = MagicMock()
        self.assertEqual(prompt_next_action(console), "all")
        self.assertEqual(prompt_next_action(console), "revenue")
        self.assertEqual(prompt_next_action(console), "rate")
        self.assertEqual(prompt_next_action(console), "clear")

    @patch("main.NonNegativeFloatPrompt.ask", return_value=800.0)
    @patch("main.PositiveFloatPrompt.ask", return_value=6.0)
    @patch("main.collect_inputs", return_value=("03/2026", 1000.0, 5.0))
    @patch("main.collect_deductions", return_value=(0, 0.0, 0.0))
    @patch(
        "main.prompt_next_action", side_effect=["all", "revenue", "rate", "clear", None]
    )
    @patch("main.display_results")
    @patch("main.display_header")
    @patch("main.time.sleep")
    def test_main_loop_branches(
        self,
        mock_sleep,
        mock_header,
        mock_results,
        mock_action,
        mock_deduct,
        mock_input,
        mock_pos_rate_prompt,
        mock_nn_rev_prompt,
    ) -> None:
        """Walk through all loop paths in main() to hit 100% coverage."""
        from main import main as rcal_main

        rcal_main()
        self.assertEqual(mock_input.call_count, 3)
        self.assertEqual(mock_deduct.call_count, 5)
        self.assertEqual(mock_results.call_count, 5)

    @patch("main.clear_state", return_value=False)
    @patch("main.collect_inputs", return_value=("03/2026", 1000.0, 5.0))
    @patch("main.collect_deductions", return_value=(0, 0.0, 0.0))
    @patch("main.prompt_next_action", side_effect=["clear", None])
    @patch("main.display_results")
    @patch("main.display_header")
    @patch("main.time.sleep")
    def test_main_loop_clear_failed(self, *mocks) -> None:
        """Test the 'clear' path when there is no state."""
        from main import main as rcal_main

        rcal_main()

    @patch("main.Path.write_text", side_effect=OSError("Permission denied"))
    def test_save_state_oserror(self, mock_write) -> None:
        """Test save_state gracefully handles OSError."""
        from main import save_state

        save_state("03/2026", 1000.0, 5.0)

    @patch("main.Path.unlink", side_effect=OSError("Permission denied"))
    @patch("main.Path.exists", return_value=True)
    def test_clear_state_oserror(self, mock_exists, mock_unlink) -> None:
        """Test clear_state gracefully handles OSError."""
        from main import clear_state

        self.assertFalse(clear_state())

    @patch("main.Console")
    @patch("main.load_state", return_value={"month_year": "01/2026"})
    @patch("main.collect_inputs", side_effect=KeyboardInterrupt)
    def test_main_keyboard_interrupt(self, mock_input, mock_load, mock_console) -> None:
        """Test graceful exit on Ctrl+C."""
        from main import main as rcal_main

        rcal_main()
        self.assertTrue(mock_console().print.called)


if __name__ == "__main__":
    unittest.main()
