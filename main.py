#!/usr/bin/env python3
"""
RCal — Brazilian Simples Nacional Tax Calculator (Anexo III / Fator R)

This CLI tool calculates the optimal Pró-labore (administrator salary),
taxes, and dividends for a Brazilian tech company that exports services
under the Simples Nacional regime (Anexo III).

Target Audience:
    Brazilian micro and small businesses (ME/EPP) in the tech sector
    (e.g., software development, website planning/hosting — LC 116/03,
    Sub-item 01.08) that export services internationally.

Export Exemptions:
    Under Brazilian law, the export of services — where the client is
    abroad and the result of the service is verified abroad — is exempt
    from municipal ISSQN and federal PIS/COFINS taxes. The DAS rate used
    in this tool (~3.054%) already reflects those exemptions removed from
    the standard Anexo III nominal rate.

Key Concept — Fator R:
    The "Fator R" is a ratio defined by Brazilian tax law that determines
    which tax annex (table) applies to a company under Simples Nacional.

    Fator R = Payroll Expenses (last 12 months) / Gross Revenue (last 12 months)

    If Fator R >= 0.28 (28%), the company is taxed under Anexo III (lower rates,
    starting at ~6%). If Fator R < 0.28, the company falls into Anexo V (higher
    rates, starting at ~15.5%).

    Therefore, paying a minimum Pró-labore that keeps Fator R >= 28% is a
    common and legal tax-optimization strategy for service-exporting companies.

See Also:
    docs/AI_REFERENCE_DOC.md — The canonical source of truth for business
    logic, edge cases, and validation test cases.

Author: RCal Contributors
License: MIT
"""

import json
import math
import re
import time
from dataclasses import dataclass
from typing import Any, Mapping
from datetime import datetime
from pathlib import Path

from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console, Group
from rich.panel import Panel
from rich.prompt import Confirm, FloatPrompt, InvalidResponse, Prompt
from rich.rule import Rule
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.traceback import install as install_rich_traceback

# ──────────────────────────────────────────────────────────────────
# Rich Traceback Handler — beautiful errors for unexpected crashes
# ──────────────────────────────────────────────────────────────────
install_rich_traceback(show_locals=True)

# ──────────────────────────────────────────────────────────────────
# Design System — Consistent theme for the entire application
#
# All visual styles are defined here as semantic tokens. This makes
# the entire palette changeable from a single location and ensures
# every component shares a cohesive visual identity.
# ──────────────────────────────────────────────────────────────────

RCAL_THEME = Theme(
    {
        # ─ Primary brand
        "brand": "bold #00b4d8",  # vivid cyan — the "RCal blue"
        "brand.dim": "#0096c7",  # deeper cyan, increased brightness from previous
        # ─ Semantic money tokens
        "money.positive": "bold #2ec4b6",  # teal-green for income
        "money.negative": "bold #e63946",  # warm red for deductions
        "money.highlight": "bold #f4a261",  # amber for key results
        "money.total": "bold bright_white on #1d3557",  # grand total (higher contrast bg)
        # ─ Text hierarchy
        "label": "#f8f9fa",  # bright white/gray for maximum readability
        "label.dim": "#adb5bd",  # medium-light gray (removed 'dim' ANSI flag)
        "heading": "bold bright_white",
        # ─ Status indicators
        "status.ok": "bold #2ec4b6",
        "status.warn": "bold #f4a261",
        "status.danger": "bold #e63946",
        # ─ Surfaces & borders
        "border.primary": "#00b4d8",
        "border.dim": "#457b9d",  # brighter border for distinct separation
        # ─ Input prompts
        "prompt.label": "bold #00b4d8",
        "prompt.hint": "#adb5bd",  # matches label.dim, bright enough to read easily
    }
)

# ──────────────────────────────────────────────────────────────────
# ASCII Logo — Visually attractive branded header
# ──────────────────────────────────────────────────────────────────

LOGO = """\
  ██████╗   ██████╗  █████╗  ██╗
  ██╔══██╗ ██╔════╝ ██╔══██╗ ██║
  ██████╔╝ ██║      ███████║ ██║
  ██╔══██╗ ██║      ██╔══██║ ██║
  ██║  ██║ ╚██████╗ ██║  ██║ ███████╗
  ╚═╝  ╚═╝  ╚═════╝ ╚═╝  ╚═╝ ╚══════╝"""

# ──────────────────────────────────────────────────────────────────
# Tax Constants for 2026
# ──────────────────────────────────────────────────────────────────

LEGAL_MINIMUM_WAGE: float = 1621.00
"""The Brazilian federal minimum wage for 2026 (R$ 1.621,00).
The Pró-labore cannot be lower than this value.

Note: Some states (e.g., Santa Catarina) have higher regional minimum
wages (e.g., R$ 2.106,00 for tech workers in Faixa 4). However, for
the sole purpose of a business owner's Pró-labore / INSS contribution,
the Federal minimum wage is the legally accepted floor. This tool
defaults to the Federal level to optimize tax savings."""

DAS_TAX_RATE: float = 0.03054
"""Effective DAS (Documento de Arrecadação do Simples Nacional) rate
for Anexo III, Bracket 1 (gross annual revenue up to R$ 180.000,00).

This is the NET tax rate after ISS, PIS, and COFINS export exemptions
are removed from the nominal Anexo III rate (~6%). It is applied as a
percentage of monthly gross revenue.

IMPORTANT: If accumulated annual revenue exceeds R$ 180k, the effective
rate must be dynamically calculated using the Receita Federal's
progressive formula: ((RBT12 * Nominal Rate) - Deductible) / RBT12."""

INSS_TAX_RATE: float = 0.11
"""INSS (Instituto Nacional do Seguro Social) contribution rate
withheld from the administrator's Pró-labore. Fixed at 11%
for Simples Nacional companies."""

INSS_CEILING: float = 8_475.55
"""INSS contribution ceiling (teto previdenciário) for 2026 (R$ 8.475,55).

Regardless of how high the Pró-labore is, the INSS contribution base
is capped at this value. The maximum monthly INSS a contributor pays
is therefore R$ 932,31 (11% × R$ 8.475,55).

Source: INSS / Receita Federal — Portaria Interministerial MPS/MF 2026."""

FATOR_R_TARGET: float = 0.28
"""Minimum Fator R threshold (28%) to qualify for Anexo III
taxation instead of the higher Anexo V."""

# ──────────────────────────────────────────────────────────────────
# 2026 IRPF — Progressive Table & Lei nº 15.270/2025 Reducer
#
# The Individual Income Tax (IRPF) is calculated in three steps:
#   1. Apply the standard progressive table to the taxable base.
#   2. Apply the 2026 reducer (full exemption up to R$ 5.000,
#      phase-out between R$ 5.000 and R$ 7.350).
#   3. Final IRPF = max(Standard IRPF - Reducer, 0).
#
# Sources:
#   Receita Federal: https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/tabelas/2026
#   Lei nº 15.270/2025: https://www.gov.br/fazenda/pt-br/assuntos/noticias/2026/janeiro/receita-divulga-nova-tabela-do-irpf-com-as-mudancas-apos-isencao-para-quem-ganha-ate-r-5-mil
# ──────────────────────────────────────────────────────────────────

IRPF_TABLE_2026: list[tuple[float, float, float]] = [
    #  (upper_limit,   rate,     deduction)
    (2_428.80, 0.000, 0.00),  # Isento
    (2_826.65, 0.075, 182.16),  # 7.5%
    (3_751.05, 0.150, 394.16),  # 15%
    (4_664.68, 0.225, 675.49),  # 22.5%
    (float("inf"), 0.275, 908.73),  # 27.5%
]
"""2026 IRPF progressive monthly table (Tabela Progressiva Mensal).

Each tuple is (upper_limit, alíquota, deduction). The last bracket
uses float('inf') as the upper bound. To calculate the standard
IRPF: find the matching bracket, then compute
(taxable_base × rate) - deduction."""

IRPF_DEPENDENT_DEDUCTION: float = 189.59
"""Monthly deduction per dependent for IRPF calculation (R$ 189,59).
Applied before computing the taxable base."""

IRPF_SIMPLIFIED_DEDUCTION: float = 607.20
"""Optional monthly simplified deduction for IRPF in 2026 (R$ 607,20).
This replaces the legal deductions whenever it is more favorable."""

IRPF_REDUCER_FULL_EXEMPTION_LIMIT: float = 5_000.00
"""Gross taxable income threshold for full IRPF reduction in 2026."""

IRPF_REDUCER_PHASE_OUT_LIMIT: float = 7_350.00
"""Gross taxable income threshold above which the 2026 reduction ends."""

IRPF_REDUCER_BASE: float = 978.62
"""Base value for the 2026 reducer formula."""

IRPF_REDUCER_FACTOR: float = 0.133145
"""Multiplier for the 2026 reducer formula."""

STATE_FILE: Path = Path.home() / ".rcal_state.json"
"""Path to the persistent state file.

Stores the user's last-used inputs (month, revenue, exchange rate,
and optional IRPF deduction settings) as JSON so they can be
pre-filled on the next application launch.
Located in the user's home directory as a hidden file.

The file is human-readable and can be manually edited or deleted.
Use the in-app '[4] Clear Memory' option to wipe it cleanly."""

MINIMUM_VIABLE_REVENUE_BRL: float = LEGAL_MINIMUM_WAGE + (
    LEGAL_MINIMUM_WAGE * DAS_TAX_RATE
)
"""Minimum monthly BRL revenue needed to cover minimum Pró-labore + DAS.

Below this threshold (~R$ 1.670,52 for 2026), the company must inject
capital to cover expenses — dividends will be negative."""

FLORIPA_TFF_REFERENCE: str = (
    "TFF (Taxa de Fiscalização de Funcionamento) — Florianópolis "
    "municipal licensing fee. Fixed annual charge regardless of revenue."
)
"""Reference note about the Florianópolis municipal licensing fee."""


# ──────────────────────────────────────────────────────────────────
# State Persistence — Cross-Session Memory
#
# RCal remembers the user's last inputs between sessions using a
# simple JSON file in the home directory. This means returning
# users get their previous values pre-filled as smart defaults.
# ──────────────────────────────────────────────────────────────────


def load_state() -> dict[str, Any]:
    """Load the last-used inputs from the persistent state file.

    Reads ~/.rcal_state.json and returns a dictionary with keys:
        - month_year (str): e.g. "03/2026"
        - revenue_usd (float): e.g. 883.0
        - exchange_rate (float): e.g. 5.23
        - num_dependents (int): e.g. 2 (optional, defaults to 0 if missing)
        - pgbl_contribution (float): e.g. 500.0 (optional, defaults to 0.0)
        - alimony (float): e.g. 1000.0 (optional, defaults to 0.0)

    If the file doesn't exist, is corrupted, or has an unexpected
    format, returns an empty dict so the app falls back to fresh
    prompts. This function never raises exceptions.

    Backward compatible: old state files without deduction keys
    are loaded successfully — missing keys are simply absent.

    Returns:
        Dictionary with saved state, or empty dict on any error.
    """
    try:
        if STATE_FILE.exists():
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            if isinstance(data, dict):
                return data
    except (json.JSONDecodeError, OSError, ValueError):
        pass
    return {}


def save_state(
    month_year: str,
    revenue_usd: float,
    exchange_rate: float,
    *,
    num_dependents: int = 0,
    pgbl_contribution: float = 0.0,
    alimony: float = 0.0,
) -> None:
    """Save the current inputs to the persistent state file.

    Writes to ~/.rcal_state.json as human-readable JSON.
    Silently ignores write failures (e.g., permissions issues)
    since persistence is a convenience feature, not critical.

    Deduction values are always saved (even if 0) to provide
    explicit defaults on next launch.

    Args:
        month_year: The reference month/year string.
        revenue_usd: Monthly revenue in USD.
        exchange_rate: USD → BRL exchange rate.
        num_dependents: Number of IRPF dependents.
        pgbl_contribution: PGBL pension contribution in BRL.
        alimony: Alimony (Pensão Alimentícia) amount in BRL.
    """
    state = {
        "month_year": month_year,
        "revenue_usd": revenue_usd,
        "exchange_rate": exchange_rate,
        "num_dependents": num_dependents,
        "pgbl_contribution": pgbl_contribution,
        "alimony": alimony,
    }
    try:
        STATE_FILE.write_text(
            json.dumps(state, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
    except OSError:
        pass


def clear_state() -> bool:
    """Delete the persistent state file.

    Returns:
        True if the file was deleted, False if it didn't exist
        or couldn't be removed.
    """
    try:
        if STATE_FILE.exists():
            STATE_FILE.unlink()
            return True
    except OSError:
        pass
    return False


# ──────────────────────────────────────────────────────────────────
# Custom Validated Prompts
# ──────────────────────────────────────────────────────────────────


class MonthYearPrompt(Prompt):
    """Prompt that validates MM/YYYY format with valid month range.

    Automatically retries on invalid input using Rich's built-in
    InvalidResponse mechanism — no manual while loops needed.
    """

    def process_response(self, value: str) -> str:
        """Validate month/year format and range.

        Args:
            value: User-entered string.

        Returns:
            Validated month/year string.

        Raises:
            InvalidResponse: If format or month range is invalid.
        """
        value = value.strip()
        if not re.match(r"^\d{2}/\d{4}$", value):
            raise InvalidResponse(
                "[status.danger]  ✗ Please enter a valid month/year "
                "(format: MM/YYYY, e.g. 03/2026).[/]"
            )
        month = int(value[:2])
        if not 1 <= month <= 12:
            raise InvalidResponse(
                "[status.danger]  ✗ Month must be between 01 and 12.[/]"
            )
        return value


class PositiveFloatPrompt(FloatPrompt):
    """FloatPrompt that rejects zero and negative values.

    Ensures the user cannot enter invalid financial amounts
    that would break the calculation engine.
    """

    def process_response(self, value: str) -> float:  # type: ignore[override]
        """Validate that the entered value is a positive number.

        Args:
            value: User-entered string.

        Returns:
            Validated positive float.

        Raises:
            InvalidResponse: If value is not a positive number.
        """
        try:
            result = float(value)
        except ValueError as exc:
            raise InvalidResponse(
                "[status.danger]  ✗ Please enter a valid number.[/]"
            ) from exc
        if not math.isfinite(result) or result <= 0:
            raise InvalidResponse(
                "[status.danger]  ✗ Value must be a finite number greater than zero.[/]"
            )
        return result


class NonNegativeIntPrompt(Prompt):
    """Prompt that validates non-negative integer input.

    Accepts 0 and positive integers. Used for the number of
    dependents input where 0 is a valid choice.
    """

    def process_response(self, value: str) -> int:  # type: ignore[override]
        """Validate that the entered value is a non-negative integer.

        Args:
            value: User-entered string.

        Returns:
            Validated non-negative integer.

        Raises:
            InvalidResponse: If value is not a non-negative integer.
        """
        value = value.strip()
        try:
            result = int(value)
        except ValueError as exc:
            raise InvalidResponse(
                "[status.danger]  ✗ Please enter a whole number (0 or above).[/]"
            ) from exc
        if result < 0:
            raise InvalidResponse("[status.danger]  ✗ Value cannot be negative.[/]")
        return result


class NonNegativeFloatPrompt(FloatPrompt):
    """FloatPrompt that accepts zero and positive values.

    Unlike PositiveFloatPrompt, this accepts 0.0 — used for
    optional deduction amounts (PGBL, alimony) where zero
    means "no deduction".
    """

    def process_response(self, value: str) -> float:  # type: ignore[override]
        """Validate that the entered value is a non-negative number.

        Args:
            value: User-entered string.

        Returns:
            Validated non-negative float.

        Raises:
            InvalidResponse: If value is not a non-negative number.
        """
        try:
            result = float(value)
        except ValueError as exc:
            raise InvalidResponse(
                "[status.danger]  ✗ Please enter a valid number.[/]"
            ) from exc
        if not math.isfinite(result) or result < 0:
            raise InvalidResponse(
                "[status.danger]  ✗ Value must be a finite, non-negative number.[/]"
            )
        return result


# ──────────────────────────────────────────────────────────────────
# IRPF 2026 Calculation Engine
#
# Pure function implementing the 3-step IRPF algorithm:
#   1. Standard progressive table (Tabela Progressiva Mensal)
#   2. Lei nº 15.270/2025 reducer (exemption + phase-out)
#   3. Final IRPF = max(Standard - Reducer, 0)
#
# This function has no side effects and can be unit-tested in
# isolation from the rest of the application.
# ──────────────────────────────────────────────────────────────────


def calculate_irpf_2026(
    taxable_base: float,
    *,
    reduction_basis: float | None = None,
) -> tuple[float, float, float]:
    """Calculate the 2026 IRPF using the progressive table + Lei 15.270/2025 reducer.

    This implements the 3-step IRPF calculation mandated for tax year 2026:

    Step 1 — Standard Progressive Table:
        Apply the Tabela Progressiva Mensal to the taxable base.
        Standard IRPF = (taxable_base × alíquota) - dedução.

    Step 2 — Lei nº 15.270/2025 Reducer:
        - If gross taxable income ≤ R$ 5.000: the reduction can zero the tax.
        - If gross taxable income is between R$ 5.000,01 and R$ 7.350:
          Reduction = R$ 978,62 - (0,133145 × gross taxable income).
          Final IRPF = max(Standard IRPF - Reduction, 0).
        - If gross taxable income > R$ 7.350: Final IRPF = Standard IRPF.

    Step 3 — Return all three values for transparency.

    Args:
        taxable_base: The IRPF taxable base after all deductions
            or after the optional simplified deduction.
        reduction_basis: Gross taxable income used by the official
            2026 reduction table. Defaults to taxable_base for
            backward compatibility in isolated tests.

    Returns:
        Tuple of (standard_irpf, reducer_amount, final_irpf).
        - standard_irpf: Tax from the progressive table alone.
        - reducer_amount: Reduction applied by Lei 15.270/2025.
        - final_irpf: The actual tax owed after the reducer.
    """
    if taxable_base <= 0:
        return (0.0, 0.0, 0.0)

    if reduction_basis is None:
        reduction_basis = taxable_base

    standard_irpf: float = 0.0
    for upper_limit, rate, deduction in IRPF_TABLE_2026:
        if taxable_base <= upper_limit:
            standard_irpf = max(taxable_base * rate - deduction, 0.0)
            break

    if reduction_basis <= IRPF_REDUCER_FULL_EXEMPTION_LIMIT:
        reducer_amount: float = standard_irpf
        final_irpf: float = 0.0
    elif reduction_basis <= IRPF_REDUCER_PHASE_OUT_LIMIT:
        reducer_amount = max(
            IRPF_REDUCER_BASE - (IRPF_REDUCER_FACTOR * reduction_basis),
            0.0,
        )
        reducer_amount = min(reducer_amount, standard_irpf)
        final_irpf = max(standard_irpf - reducer_amount, 0.0)
    else:
        reducer_amount = 0.0
        final_irpf = standard_irpf

    return (standard_irpf, reducer_amount, final_irpf)


# ──────────────────────────────────────────────────────────────────
# Formatting Utilities
# ──────────────────────────────────────────────────────────────────


def format_brl(value: float) -> str:
    """Format a float as Brazilian Reais currency string.

    Follows the Brazilian convention:
        - Thousands separated by dots
        - Decimal separated by comma
        - Prefixed with R$

    Example:
        >>> format_brl(12345.67)
        'R$ 12.345,67'
    """
    # Format with 2 decimal places, then swap separators for pt-BR
    formatted = f"{value:,.2f}"
    # Swap commas and dots: 12,345.67 → 12.345,67
    formatted = formatted.replace(",", "X").replace(".", ",").replace("X", ".")
    return f"R$ {formatted}"


def format_pct(value: float) -> str:
    """Format a float ratio as a percentage string.

    Example:
        >>> format_pct(0.28)
        '28.0%'
    """
    return f"{value * 100:.1f}%"


# ──────────────────────────────────────────────────────────────────
# Visual Components — Revenue Distribution Bar
# ──────────────────────────────────────────────────────────────────


def render_breakdown_bar(results: "TaxCalculationResult", width: int = 44) -> Text:
    """Render a proportional stacked bar showing how revenue is split.

    Uses Unicode block characters (█) to create a stacked horizontal
    bar chart that instantly communicates: "How much do I keep?"

    Each segment is proportionally sized and color-coded:
        - Amber:      Net Salary (Pró-labore after INSS and IRPF)
        - Red-Orange: INSS contribution
        - Deep Red:   IRPF (when > 0)
        - Red:        DAS tax
        - Teal:       What you keep (dividends)

    Args:
        results: Dataclass returned by calculate_taxes().
        width: Character width of the bar (default 44).

    Returns:
        Rich Text object with the colored stacked bar + legend.
    """
    gross = results.gross_revenue_brl
    if gross <= 0:
        return Text("  (No revenue to display)", style="label.dim")

    # Segment definitions: (value, color, label)
    irpf = results.irpf_tax
    pro_labore_net = results.ideal_pro_labore - results.inss_tax - irpf
    inss = results.inss_tax
    das = results.estimated_das
    remaining = gross - results.ideal_pro_labore - das

    # When dividends are negative, expenses exceed revenue.
    # Normalize against total outflows so the bar stays within width.
    if remaining < 0:
        # Show costs as proportion of total cost (not revenue)
        total_cost = pro_labore_net + inss + irpf + das
        segments = [
            (pro_labore_net, "#f4a261", "Salary"),
            (inss, "#e76f51", "INSS"),
        ]
        if irpf > 0:
            segments.append((irpf, "#c1121f", "IRPF"))
        segments.append((das, "#e63946", "DAS"))
        denominator = total_cost
        suffix = " of costs"
    else:
        segments = [
            (pro_labore_net, "#f4a261", "Salary"),
            (inss, "#e76f51", "INSS"),
        ]
        if irpf > 0:
            segments.append((irpf, "#c1121f", "IRPF"))
        segments.append((das, "#e63946", "DAS"))
        segments.append((remaining, "#2ec4b6", "Yours"))
        denominator = gross
        suffix = ""

    # Build proportional bar
    breakdown = Text()
    legend_parts = []

    for value, color, label in segments:
        pct = max(value / denominator, 0) if denominator > 0 else 0
        chars = max(round(pct * width), 1 if value > 0 else 0)
        breakdown.append("█" * chars, style=color)
        if value > 0:
            legend_parts.append(
                Text.assemble(
                    ("█ ", color),
                    (f"{label} {pct * 100:.0f}%{suffix}", "label.dim"),
                )
            )

    # Compose: bar on one line, legend on the next
    result = Text()
    result.append("  ")
    result.append_text(breakdown)
    result.append("\n  ")
    for i, part in enumerate(legend_parts):
        result.append_text(part)
        if i < len(legend_parts) - 1:
            result.append("   ", style="label.dim")

    return result


# ──────────────────────────────────────────────────────────────────
# Core Business Logic — Tax Calculation Engine
#
# This function is the mathematical heart of RCal. Its signature
# remains stable, but it now returns a strongly-typed dataclass.
# ──────────────────────────────────────────────────────────────────


@dataclass
class TaxCalculationResult:
    """Strongly-typed container for tax calculation results."""

    gross_revenue_brl: float
    fator_r_minimum: float
    ideal_pro_labore: float
    inss_tax: float
    estimated_das: float
    irpf_status: str
    irpf_tax: float
    irpf_standard: float
    irpf_reducer: float
    taxable_base: float
    irpf_deduction_model: str
    irpf_deduction_total: float
    irpf_reduction_basis: float
    irpf_deductions: dict[str, float]
    bracket_warning: str
    available_dividends: float
    total_net_take_home: float
    is_zero_revenue: bool
    is_below_viable_threshold: bool


def calculate_taxes(
    revenue_usd: float,
    exchange_rate: float,
    *,
    num_dependents: int = 0,
    pgbl_contribution: float = 0.0,
    alimony: float = 0.0,
) -> TaxCalculationResult:
    """Calculate all tax components for a given monthly revenue.

    This function implements the Fator R optimization strategy and,
    as of v3.0, the exact 2026 IRPF calculation with deductions:

    1. Convert USD revenue to BRL using the provided exchange rate.
    2. Calculate the minimum Pró-labore needed to keep Fator R >= 28%.
    3. Ensure Pró-labore is at least the legal minimum wage.
    4. Compute INSS and DAS.
    5. Compute the IRPF taxable base (Pró-labore - INSS - deductions).
    6. Apply the 2026 progressive table + Lei nº 15.270/2025 reducer.
    7. Compute dividends and net take-home (now minus IRPF).

    Args:
        revenue_usd: Monthly revenue in US dollars.
        exchange_rate: Current USD → BRL exchange rate.
        num_dependents: Number of IRPF dependents (R$ 189,59 each).
        pgbl_contribution: PGBL pension contribution in BRL
            (capped at 12% of Pró-labore).
        alimony: Alimony (Pensão Alimentícia) amount in BRL.

    Returns:
        Dictionary with all calculated tax components. New keys added
        in v3.0: irpf_tax, irpf_standard, irpf_reducer, taxable_base,
        irpf_deductions.
    """
    # Step 1: Convert revenue to BRL
    gross_revenue_brl: float = revenue_usd * exchange_rate

    # Step 2: Calculate the Fator R minimum payroll
    # To stay in Anexo III, payroll must be >= 28% of gross revenue
    fator_r_minimum: float = gross_revenue_brl * FATOR_R_TARGET

    # Step 3: Ideal Pró-labore — the higher of Fator R minimum or legal minimum wage
    # This ensures we both comply with labor law AND optimize for Anexo III
    ideal_pro_labore: float = max(fator_r_minimum, LEGAL_MINIMUM_WAGE)

    # Step 4: INSS contribution (withheld from administrator's salary)
    # The contribution base is capped at the INSS ceiling (teto
    # previdenciário). Above R$ 8.475,55 the contribution stops growing.
    inss_base: float = min(ideal_pro_labore, INSS_CEILING)
    inss_tax: float = inss_base * INSS_TAX_RATE

    # Step 5: DAS tax (monthly Simples Nacional tax on gross revenue)
    estimated_das: float = gross_revenue_brl * DAS_TAX_RATE

    dependent_deduction: float = num_dependents * IRPF_DEPENDENT_DEDUCTION
    pgbl_capped: float = min(pgbl_contribution, ideal_pro_labore * 0.12)
    alimony_applied: float = max(alimony, 0.0)
    legal_deduction_total = (
        inss_tax + dependent_deduction + pgbl_capped + alimony_applied
    )

    if IRPF_SIMPLIFIED_DEDUCTION > legal_deduction_total:
        irpf_deduction_model = "Simplified"
        irpf_deduction_total = IRPF_SIMPLIFIED_DEDUCTION
    else:
        irpf_deduction_model = "Legal"
        irpf_deduction_total = legal_deduction_total

    taxable_base = max(ideal_pro_labore - irpf_deduction_total, 0.0)

    standard_irpf, reducer_amount, final_irpf = calculate_irpf_2026(
        taxable_base,
        reduction_basis=ideal_pro_labore,
    )

    # IRPF status label for display
    if final_irpf == 0.0:
        irpf_status: str = "✅ Tax Free"
    else:
        irpf_status = f"⚠️  IRPF: {format_brl(final_irpf)}"

    # Step 6b: Bracket 1 ceiling warning
    # The hardcoded DAS rate assumes annual revenue <= R$ 180.000,00.
    # Warn the user if their monthly revenue suggests they may exceed this.
    bracket_1_ceiling: float = 180_000.00
    estimated_annual: float = gross_revenue_brl * 12
    if estimated_annual > bracket_1_ceiling:
        bracket_warning: str = (
            f"⚠️  Estimated annual revenue ({format_brl(estimated_annual)}) "
            f"exceeds Bracket 1 ceiling ({format_brl(bracket_1_ceiling)}). "
            "The effective DAS rate may be higher — consult your accountant."
        )
    else:
        bracket_warning = ""

    # Step 7: Available dividends (distributed tax-free to the partner)
    # Dividends = Revenue minus salary minus Simples Nacional tax
    # Note: IRPF is NOT subtracted from dividends — it is withheld from the salary.
    available_dividends: float = gross_revenue_brl - ideal_pro_labore - estimated_das

    # Step 8: Total net take-home
    # (Pró-labore after INSS and IRPF deduction) + (tax-free dividends)
    total_net_take_home: float = (
        ideal_pro_labore - inss_tax - final_irpf
    ) + available_dividends

    is_zero_revenue: bool = gross_revenue_brl == 0.0
    is_below_viable_threshold: bool = gross_revenue_brl < MINIMUM_VIABLE_REVENUE_BRL

    return TaxCalculationResult(
        gross_revenue_brl=gross_revenue_brl,
        fator_r_minimum=fator_r_minimum,
        ideal_pro_labore=ideal_pro_labore,
        inss_tax=inss_tax,
        estimated_das=estimated_das,
        irpf_status=irpf_status,
        irpf_tax=final_irpf,
        irpf_standard=standard_irpf,
        irpf_reducer=reducer_amount,
        taxable_base=taxable_base,
        irpf_deduction_model=irpf_deduction_model,
        irpf_deduction_total=irpf_deduction_total,
        irpf_reduction_basis=ideal_pro_labore,
        irpf_deductions={
            "inss": inss_tax,
            "dependents": dependent_deduction,
            "pgbl": pgbl_capped,
            "alimony": alimony_applied,
            "simplified": IRPF_SIMPLIFIED_DEDUCTION,
            "applied_total": irpf_deduction_total,
        },
        bracket_warning=bracket_warning,
        available_dividends=available_dividends,
        total_net_take_home=total_net_take_home,
        is_zero_revenue=is_zero_revenue,
        is_below_viable_threshold=is_below_viable_threshold,
    )


# ──────────────────────────────────────────────────────────────────
# Display — Branded Header
# ──────────────────────────────────────────────────────────────────


def display_header(console: Console) -> None:
    """Print the visually attractive branded RCal header.

    Renders the ASCII art logo centered with brand colors, followed
    by the application subtitle and a decorative rule separator.

    Args:
        console: Rich console instance for output.
    """
    console.print()
    console.print(Align.center(Text(LOGO, style="brand")))
    console.print()
    console.print(
        Align.center(Text("Simples Nacional Tax Calculator", style="heading"))
    )
    console.print(
        Align.center(
            Text(
                "Anexo III  ·  Fator R  ·  Export Exemptions",
                style="label.dim",
            )
        )
    )
    console.print()
    console.print(Rule(style="border.dim"))
    console.print()


# ──────────────────────────────────────────────────────────────────
# Display — Input Collection (with smart defaults and memory)
# ──────────────────────────────────────────────────────────────────


def collect_inputs(
    console: Console,
    prev_exchange_rate: float | None = None,
    saved_state: Mapping[str, Any] | None = None,
) -> tuple[str, float, float]:
    """Collect and validate all three user inputs with smart defaults.

    On the first run, saved state from the JSON file is used to
    pre-fill defaults. On subsequent runs within the same session,
    prev_exchange_rate takes priority.

    Priority order for defaults:
        1. prev_exchange_rate (in-session memory, highest priority)
        2. saved_state (cross-session JSON file)
        3. System clock for month/year
        4. No default (user must enter fresh)

    Args:
        console: Rich console instance for output.
        prev_exchange_rate: Exchange rate from previous calculation
            within this session, or None for the first run.
        saved_state: Dictionary loaded from ~/.rcal_state.json,
            or None if no saved state exists.

    Returns:
        Tuple of (month_year, revenue_usd, exchange_rate).
    """
    saved = saved_state or {}

    # Smart default: saved month or current month/year
    default_month_year = str(saved.get("month_year", datetime.now().strftime("%m/%Y")))

    month_year: str = MonthYearPrompt.ask(
        "[prompt.label]📅 Current Month/Year[/] [prompt.hint](MM/YYYY)[/]",
        console=console,
        default=default_month_year,
    )

    # Revenue: use saved default if available
    saved_revenue = saved.get("revenue_usd")
    if saved_revenue is not None and prev_exchange_rate is None:
        revenue_usd: float = NonNegativeFloatPrompt.ask(
            "[prompt.label]💵 Monthly Revenue in USD[/] [prompt.hint](0 = zero-revenue advisory)[/]",
            console=console,
            default=float(saved_revenue),
        )
    else:
        revenue_usd = NonNegativeFloatPrompt.ask(
            "[prompt.label]💵 Monthly Revenue in USD[/] [prompt.hint](0 = zero-revenue advisory)[/]",
            console=console,
        )

    # Exchange rate: in-session memory > saved state > no default
    saved_rate = saved.get("exchange_rate")
    default_rate = prev_exchange_rate
    if default_rate is None and saved_rate is not None:
        default_rate = float(saved_rate)

    if default_rate is not None:
        exchange_rate: float = PositiveFloatPrompt.ask(
            "[prompt.label]💱 USD → BRL Exchange Rate[/]",
            console=console,
            default=default_rate,
        )
    else:
        exchange_rate = PositiveFloatPrompt.ask(
            "[prompt.label]💱 USD → BRL Exchange Rate[/]",
            console=console,
        )

    return month_year, revenue_usd, exchange_rate


def collect_deductions(
    console: Console,
    saved_state: Mapping[str, Any] | None = None,
) -> tuple[int, float, float]:
    """Collect optional IRPF deduction inputs with smart defaults.

    Prompts the user to optionally apply IRPF deductions. If saved state
    contains non-zero deduction values from a previous session, the prompt
    defaults to "yes" and pre-fills the amounts. Otherwise defaults to "no".

    The logic for smart defaults:
        - If saved state has any non-zero deduction value → default to yes
        - If saved state has all-zero deductions → default to no
        - If no saved state → default to no

    A user who previously applied deductions gets them pre-filled, while
    a user who never used deductions won't be bothered with extra prompts.

    Args:
        console: Rich console instance for output.
        saved_state: Dictionary loaded from ~/.rcal_state.json.

    Returns:
        Tuple of (num_dependents, pgbl_contribution, alimony).
    """
    saved = saved_state or {}

    # Determine if saved state has non-zero deductions
    saved_dependents = saved.get("num_dependents", 0)
    saved_pgbl = saved.get("pgbl_contribution", 0.0)
    saved_alimony = saved.get("alimony", 0.0)

    has_saved_deductions = (
        (saved_dependents and saved_dependents > 0)
        or (saved_pgbl and float(saved_pgbl) > 0)
        or (saved_alimony and float(saved_alimony) > 0)
    )

    console.print()
    apply_deductions = Confirm.ask(
        "[prompt.label]📝 Apply IRPF deductions?[/] "
        "[prompt.hint](dependents, PGBL, alimony)[/]",
        console=console,
        default=has_saved_deductions,
    )

    if not apply_deductions:
        return (0, 0.0, 0.0)

    console.print()

    # ── Number of dependents ─────────────────────────────────────
    default_dep = int(saved_dependents) if saved_dependents else 0
    num_dependents: int = int(
        NonNegativeIntPrompt.ask(
            "[prompt.label]👨‍👩‍👧 Number of Dependents[/] "
            f"[prompt.hint](R$ {IRPF_DEPENDENT_DEDUCTION:,.2f}/each)[/]",
            console=console,
            default=default_dep,
        )
    )

    # ── PGBL contribution ────────────────────────────────────────
    default_pgbl = float(saved_pgbl) if saved_pgbl else 0.0
    pgbl_contribution: float = NonNegativeFloatPrompt.ask(
        "[prompt.label]🏦 PGBL Contribution (BRL)[/] "
        "[prompt.hint](capped at 12% of Pró-labore)[/]",
        console=console,
        default=default_pgbl,
    )

    # ── Alimony ──────────────────────────────────────────────────
    default_alimony = float(saved_alimony) if saved_alimony else 0.0
    alimony: float = NonNegativeFloatPrompt.ask(
        "[prompt.label]⚖️  Alimony / Pensão Alimentícia (BRL)[/]",
        console=console,
        default=default_alimony,
    )

    return (num_dependents, pgbl_contribution, alimony)


# ──────────────────────────────────────────────────────────────────
# Display — Results Output (3-Zone Visual Architecture)
#
# Zone 1: Input Recap    — compact horizontal cards
# Zone 2: Tax Breakdown  — structured table with semantic styles
# Zone 3: Bottom Line    — highlighted panel with breakdown bar
# Footer: Legal context  — structured, subdued rule sections
# ──────────────────────────────────────────────────────────────────


def display_results(
    console: Console,
    month_year: str,
    revenue_usd: float,
    exchange_rate: float,
    results: TaxCalculationResult,
) -> None:
    """Render calculation results in a 3-zone visual architecture.

    This function replaces the original monolithic table with three
    visually distinct zones that mirror the user's mental model:
    "What did I enter?" → "What are the numbers?" → "What do I keep?"

    Args:
        console: Rich console instance for output.
        month_year: The reference month/year string (e.g., "03/2026").
        revenue_usd: Original revenue input in USD.
        exchange_rate: USD → BRL exchange rate used.
        results: Dataclass returned by calculate_taxes().
    """
    console.print()

    # ── Zone 1: Input Recap (compact horizontal cards) ───────────
    cards = [
        Panel(
            Align.center(Text(month_year, style="heading")),
            title="[label]📅 Month[/]",
            border_style="border.dim",
            width=18,
            padding=(0, 1),
        ),
        Panel(
            Align.center(Text(f"US$ {revenue_usd:,.2f}", style="heading")),
            title="[label]💵 Revenue[/]",
            border_style="border.dim",
            width=22,
            padding=(0, 1),
        ),
        Panel(
            Align.center(Text(f"R$ {exchange_rate:,.4f}", style="heading")),
            title="[label]💱 Rate[/]",
            border_style="border.dim",
            width=18,
            padding=(0, 1),
        ),
    ]
    console.print(Align.center(Columns(cards, padding=(0, 1))))
    console.print()

    # ── Zone 2: Tax Breakdown Table ──────────────────────────────
    table = Table(
        box=box.ROUNDED,
        header_style="heading",
        border_style="border.primary",
        show_lines=True,
        padding=(0, 2),
        min_width=58,
    )

    table.add_column("📋 Item", style="label", min_width=28)
    table.add_column("💰 Value", justify="right", min_width=20)

    # ─ Revenue
    table.add_row(
        "Gross Revenue (BRL)",
        Text(format_brl(results.gross_revenue_brl), style="money.positive"),
    )

    # ─ Salary Strategy
    table.add_row(
        Text("Fator R Minimum (28%)", style="label.dim"),
        Text(format_brl(results.fator_r_minimum), style="label.dim"),
    )
    table.add_row(
        Text("✨ Ideal Pró-labore", style="money.highlight"),
        Text(format_brl(results.ideal_pro_labore), style="money.highlight"),
    )

    # ─ Deductions
    # Show INSS label with "capped" indicator when the ceiling is active
    inss_capped = results.ideal_pro_labore > INSS_CEILING
    inss_label = "INSS (11%, capped)" if inss_capped else "INSS (11%)"
    table.add_row(
        inss_label,
        Text(f"- {format_brl(results.inss_tax)}", style="money.negative"),
    )
    table.add_row(
        "DAS (Simples Nacional)",
        Text(
            f"- {format_brl(results.estimated_das)}",
            style="money.negative",
        ),
    )

    # ─ IRPF
    irpf_tax = results.irpf_tax
    taxable_base = results.taxable_base
    table.add_row(
        Text("IRPF Taxable Base", style="label.dim"),
        Text(format_brl(taxable_base), style="label.dim"),
    )
    table.add_row(
        Text("IRPF Deduction Mode", style="label.dim"),
        Text(
            f"{results.irpf_deduction_model} ({format_brl(results.irpf_deduction_total)})",
            style="label.dim",
        ),
    )
    if irpf_tax > 0:
        table.add_row(
            "IRPF (Lei 15.270/2025)",
            Text(f"- {format_brl(irpf_tax)}", style="money.negative"),
        )
    else:
        table.add_row(
            "IRPF Status",
            Text("✅ Tax Free", style="status.ok"),
        )

    # ─ Bracket Warning (conditional)
    bracket_warn = str(results.bracket_warning)
    if bracket_warn:
        table.add_row(
            "📈 Bracket Warning",
            Text(bracket_warn, style="status.warn"),
        )

    console.print(
        Align.center(
            Panel(
                table,
                title="[heading]📊 Tax Breakdown[/]",
                border_style="border.primary",
                padding=(1, 1),
            )
        )
    )
    console.print()

    # ── Zone 3: Bottom Line Panel ────────────────────────────────
    dividends = results.available_dividends
    net = results.total_net_take_home
    gross = results.gross_revenue_brl

    # Build the bottom-line summary table
    bottom_table = Table(
        box=None,
        show_header=False,
        padding=(0, 2),
        min_width=44,
    )
    bottom_table.add_column("Label", min_width=26)
    bottom_table.add_column("Value", justify="right", min_width=16)

    # Dividends row — style differs when negative
    div_style = "status.danger" if dividends < 0 else "money.positive"
    bottom_table.add_row(
        Text("📦 Tax-Free Dividends", style="label"),
        Text(format_brl(dividends), style=div_style),
    )

    # Net take-home row (grand total)
    bottom_table.add_row(
        Text("🏠 Net Take-Home", style="heading"),
        Text(format_brl(net), style="money.total"),
    )

    # Effective tax burden percentage (now includes IRPF)
    if gross > 0:
        total_taxes = results.inss_tax + results.estimated_das + results.irpf_tax
        tax_pct = total_taxes / gross
        bottom_table.add_row(
            Text("📉 Effective Tax Burden", style="label"),
            Text(format_pct(tax_pct), style="status.warn"),
        )

    # Revenue distribution breakdown bar
    breakdown_bar = render_breakdown_bar(results)

    # Compose the bottom-line content
    if dividends < 0:
        # ── Negative Dividends: Explicit Danger Panel ────────
        # Explains the problem and offers two actionable options
        warning_content = Text.assemble(
            ("⚠️  Revenue Too Low\n\n", "status.danger"),
            (" Your monthly revenue (", "label"),
            (format_brl(gross), "heading"),
            (") is not enough to cover the\n", "label"),
            (" minimum Pró-labore (", "label"),
            (format_brl(results.ideal_pro_labore), "money.highlight"),
            (") + DAS tax (", "label"),
            (format_brl(results.estimated_das), "money.negative"),
            (").\n\n", "label"),
            (" Dividends are negative: ", "label"),
            (format_brl(dividends), "status.danger"),
            ("\n This means the company would need to ", "label"),
            ("inject capital", "status.danger"),
            (" to cover expenses.\n\n", "label"),
            (" ━━━ What you can do ━━━\n\n", "status.warn"),
            ("   ① ", "status.warn"),
            ("Increase revenue", "heading"),
            (" — Raise your monthly billing above ", "label"),
            (
                format_brl(results.ideal_pro_labore + results.estimated_das),
                "money.highlight",
            ),
            ("\n     to generate positive dividends.\n\n", "label"),
            ("  ② ", "status.warn"),
            ("Accept minimum wage salary", "heading"),
            (" — At this revenue level the\n", "label"),
            ("     Pró-labore is already at the legal minimum (", "label"),
            (format_brl(LEGAL_MINIMUM_WAGE), "money.highlight"),
            (
                ").\n     The company must still cover DAS + INSS "
                "from available funds.\n\n",
                "label",
            ),
            ("━━━ SC / Florianópolis Reminders ━━━\n\n", "status.warn"),
            ("  📌 ", ""),
            ("PGDAS-D filing", "heading"),
            (" — Required every month, even with\n", "label"),
            ("     low revenue. Declare the actual amount.\n\n", "label.dim"),
            ("  📌 ", ""),
            ("TFF (municipal fee)", "heading"),
            (" — Florianópolis charges a fixed\n", "label"),
            ("     annual licensing fee regardless of revenue.", "label.dim"),
        )

        if results.is_zero_revenue:
            warning_content = Text.assemble(
                ("⚠️  Zero Revenue Advisory\n\n", "status.warn"),
                ("Your company generated no revenue this month.\n\n", "label"),
                ("━━━ Brazilian Legal Guidelines ━━━\n\n", "heading"),
                ("  📌 ", ""),
                ("Pró-labore is Optional", "status.warn"),
                (" — If the company is genuinely\n", "label"),
                ("     inactive, you do ", "label"),
                ("not", "status.danger"),
                (" have to withdraw Pró-labore.\n", "label"),
                (
                    "     (This means no INSS cost, but no coverage either).\n\n",
                    "label.dim",
                ),
                ("  📌 ", ""),
                ("DAS is Zero", "status.warn"),
                (" — Your Simples Nacional tax is legally R$ 0,00.\n\n", "label"),
                ("  📌 ", ""),
                ("PGDAS-D Filing", "status.warn"),
                (" — You ", "label"),
                ("MUST", "status.danger"),
                (" still file your monthly\n", "label"),
                (
                    "     declaration informing zero revenue to avoid fines.\n\n",
                    "label",
                ),
                ("  📌 ", ""),
                ("TFF (Florianópolis)", "status.warn"),
                (" — Annual municipal licensing fee\n", "label"),
                ("     must still be paid regardless of revenue.\n", "label.dim"),
            )

        bottom_content = Group(
            bottom_table,
            Text(""),
            Panel(
                warning_content,
                border_style="status.danger",
                title="[status.danger]⚠️  Action Required[/]",
                padding=(1, 2),
            ),
            Text(""),
            Text("  Revenue Distribution", style="label"),
            breakdown_bar,
        )
    else:
        bottom_content = Group(
            bottom_table,
            Text(""),
            Text("  Revenue Distribution", style="label"),
            breakdown_bar,
        )

    console.print(
        Align.center(
            Panel(
                bottom_content,
                title="[heading]💰 Your Bottom Line[/]",
                border_style="brand",
                padding=(1, 2),
            )
        )
    )
    console.print()

    # ── Footer: Legal Context (structured, subdued) ──────────────
    display_footer(console)


# ──────────────────────────────────────────────────────────────────
# Display — Structured Footer
# ──────────────────────────────────────────────────────────────────


def display_footer(console: Console) -> None:
    """Print the legal context footer as structured Rule-separated sections.

    Each section is visually distinct but clearly secondary to the
    main results, using dim styles and Rule titles.

    Args:
        console: Rich console instance for output.
    """
    console.print(Rule(title="💡 Strategy", style="border.dim"))
    console.print(
        Text(
            "  Paying ≥28% of gross as salary keeps you in Anexo III (~6%) "
            "instead of Anexo V (~15.5%).\n"
            "  The ideal Pró-labore is the minimum needed to maintain this "
            "threshold while respecting the legal minimum wage.",
            style="label.dim",
        )
    )
    console.print()

    console.print(Rule(title="💱 Exchange Rate", style="border.dim"))
    console.print(
        Text(
            "  Use the BRL rate on the date the funds are made available or "
            "the invoice is issued — not the withdrawal date.",
            style="label.dim",
        )
    )
    console.print()

    console.print(Rule(title="⚖️  Disclaimer", style="border.dim"))
    console.print(
        Text(
            "  Estimates for planning purposes only. PGDAS-D and DAS filings still "
            "depend on rolling 12-month revenue, payroll history, and municipal "
            "licensing facts. Always consult a qualified Brazilian accountant "
            "(contador) for official filings.",
            style="label.dim",
        )
    )
    console.print()


# ──────────────────────────────────────────────────────────────────
# Loop Mode — "Calculate Another Month?"
#
# After each calculation, the user is asked whether to continue.
# If yes, they choose what to change:
#   [1] All inputs (fresh calculation)
#   [2] Only revenue (keeps month + exchange rate)
#   [3] Only exchange rate (keeps month + revenue)
#
# The exchange rate is always remembered from the previous run
# and offered as a default, since it rarely changes within a session.
# ──────────────────────────────────────────────────────────────────


def prompt_next_action(console: Console) -> str | None:
    """Ask the user what they want to do next after a calculation.

    Returns:
        "all"      — re-enter all inputs
        "revenue"  — change only revenue (keep month + rate)
        "rate"     — change only exchange rate (keep month + revenue)
        None       — exit the application
    """
    console.print(Rule(style="border.dim"))
    console.print()

    if not Confirm.ask(
        "[prompt.label]🔄 Calculate another month?[/]",
        console=console,
        default=True,
    ):
        return None

    console.print()
    console.print(Text("  What would you like to change?", style="heading"))
    console.print()
    console.print(Text("  [1]  All inputs (month, revenue, rate)", style="label"))
    console.print(Text("  [2]  Only revenue (keep current rate)", style="label"))
    console.print(
        Text("  [3]  Only exchange rate (keep current revenue)", style="label")
    )
    console.print(Text("  [4]  🗑️  Clear memory (wipe saved state)", style="label.dim"))
    console.print()

    choice = Prompt.ask(
        "[prompt.label]  Your choice[/]",
        console=console,
        choices=["1", "2", "3", "4"],
        default="1",
    )

    return {"1": "all", "2": "revenue", "3": "rate", "4": "clear"}[choice]


# ──────────────────────────────────────────────────────────────────
# Main Entry Point — Interactive Loop with State Memory
# ──────────────────────────────────────────────────────────────────


def main() -> None:
    """Entry point — collect user input, calculate, display, and loop.

    Implements a stateful interactive loop with two layers of memory:
        1. In-session: Values remembered between loop iterations
        2. Cross-session: Last inputs saved to ~/.rcal_state.json

    On launch, the app loads saved state and pre-fills defaults.
    After each calculation, it saves the current inputs (including
    deduction settings) to disk.
    The user can clear the saved state via the menu.
    """
    console = Console(theme=RCAL_THEME)

    # ── Load cross-session state ────────────────────────────────
    saved_state = load_state()

    # State carried between loop iterations
    prev_month_year: str | None = None
    prev_revenue_usd: float | None = None
    prev_exchange_rate: float | None = None
    prev_num_dependents: int = 0
    prev_pgbl: float = 0.0
    prev_alimony: float = 0.0

    try:
        # ── Header ──────────────────────────────────────────────
        display_header(console)

        # Show saved state indicator if available
        if saved_state:
            console.print(
                Text(
                    "  💾 Previous session restored — "
                    "your last values are pre-filled as defaults.",
                    style="label.dim",
                )
            )
            console.print()

        # ── First Run: Collect all inputs ───────────────────────
        month_year, revenue_usd, exchange_rate = collect_inputs(
            console, saved_state=saved_state
        )
        num_dependents, pgbl, alimony_val = collect_deductions(
            console, saved_state=saved_state
        )

        while True:
            # ── Calculation with tactile spinner feedback ────────
            console.print()
            with console.status(
                "[brand]  Calculating…[/]",
                spinner="dots",
                spinner_style="brand",
            ):
                results = calculate_taxes(
                    revenue_usd,
                    exchange_rate,
                    num_dependents=num_dependents,
                    pgbl_contribution=pgbl,
                    alimony=alimony_val,
                )
                time.sleep(0.35)

            # ── Display Results ─────────────────────────────────
            display_results(console, month_year, revenue_usd, exchange_rate, results)

            # ── Persist state to disk ───────────────────────────
            save_state(
                month_year,
                revenue_usd,
                exchange_rate,
                num_dependents=num_dependents,
                pgbl_contribution=pgbl,
                alimony=alimony_val,
            )

            # ── Remember state for next iteration ───────────────
            prev_month_year = month_year
            prev_revenue_usd = revenue_usd
            prev_exchange_rate = exchange_rate
            prev_num_dependents = num_dependents
            prev_pgbl = pgbl
            prev_alimony = alimony_val

            # ── Ask what to do next ─────────────────────────────
            action = prompt_next_action(console)
            if action is None:
                break

            console.print()
            console.print(Rule(style="border.dim"))
            console.print()

            if action == "all":
                # Re-enter everything (rate pre-filled from last run)
                month_year, revenue_usd, exchange_rate = collect_inputs(
                    console, prev_exchange_rate=prev_exchange_rate
                )
                # Build a synthetic state dict so deduction defaults carry over
                deduction_state = {
                    "num_dependents": prev_num_dependents,
                    "pgbl_contribution": prev_pgbl,
                    "alimony": prev_alimony,
                }
                num_dependents, pgbl, alimony_val = collect_deductions(
                    console, saved_state=deduction_state
                )

            elif action == "revenue":
                # Only change revenue — keep month + rate
                console.print(
                    Text(
                        f"  Keeping: 📅 {prev_month_year}  ·  "
                        f"💱 R$ {prev_exchange_rate:,.4f}",
                        style="label.dim",
                    )
                )
                console.print()
                revenue_usd = NonNegativeFloatPrompt.ask(
                    "[prompt.label]💵 Monthly Revenue in USD[/] [prompt.hint](0 = zero-revenue advisory)[/]",
                    console=console,
                )
                month_year = prev_month_year  # type: ignore[assignment]
                exchange_rate = prev_exchange_rate  # type: ignore[assignment]
                # Re-prompt deductions (Pró-labore may change with revenue)
                deduction_state = {
                    "num_dependents": prev_num_dependents,
                    "pgbl_contribution": prev_pgbl,
                    "alimony": prev_alimony,
                }
                num_dependents, pgbl, alimony_val = collect_deductions(
                    console, saved_state=deduction_state
                )

            elif action == "rate":
                # Only change exchange rate — keep month + revenue
                console.print(
                    Text(
                        f"  Keeping: 📅 {prev_month_year}  ·  "
                        f"💵 US$ {prev_revenue_usd:,.2f}",
                        style="label.dim",
                    )
                )
                console.print()
                exchange_rate = PositiveFloatPrompt.ask(
                    "[prompt.label]💱 USD → BRL Exchange Rate[/]",
                    console=console,
                    default=prev_exchange_rate,
                )
                month_year = prev_month_year  # type: ignore[assignment]
                revenue_usd = prev_revenue_usd  # type: ignore[assignment]
                # Re-prompt deductions (Pró-labore may change with rate)
                deduction_state = {
                    "num_dependents": prev_num_dependents,
                    "pgbl_contribution": prev_pgbl,
                    "alimony": prev_alimony,
                }
                num_dependents, pgbl, alimony_val = collect_deductions(
                    console, saved_state=deduction_state
                )

            elif action == "clear":
                # Wipe saved state from disk
                if clear_state():
                    console.print(
                        Text(
                            "  🗑️  Memory cleared! Saved state wiped.",
                            style="status.ok",
                        )
                    )
                else:
                    console.print(
                        Text(
                            "  ℹ️  No saved state to clear.",
                            style="label.dim",
                        )
                    )
                console.print()
                # Re-enter all inputs from scratch (no defaults)
                month_year, revenue_usd, exchange_rate = collect_inputs(console)
                # No saved state → deductions default to no
                num_dependents, pgbl, alimony_val = collect_deductions(console)

        # ── Goodbye ─────────────────────────────────────────────
        console.print()
        console.print(Rule(title="👋 Obrigado!", style="brand"))
        console.print()

    except KeyboardInterrupt:
        console.print("\n")
        console.print(Rule(title="👋 Até logo!", style="border.dim"))
        console.print()


if __name__ == "__main__":  # pragma: no cover
    main()
