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

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.prompt import Prompt, FloatPrompt
from rich import box

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

FATOR_R_TARGET: float = 0.28
"""Minimum Fator R threshold (28%) to qualify for Anexo III
taxation instead of the higher Anexo V."""

IRPF_LIMIT: float = 5000.00
"""Monthly Pró-labore threshold above which IRPF (Imposto de Renda
Pessoa Física — personal income tax) withholding applies.
Below this amount, the income falls within the tax-exempt bracket."""


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


def calculate_taxes(
    revenue_usd: float,
    exchange_rate: float,
) -> dict[str, float | str]:
    """Calculate all tax components for a given monthly revenue.
    
    This function implements the Fator R optimization strategy:
    1. Convert USD revenue to BRL using the provided exchange rate.
    2. Calculate the minimum Pró-labore needed to keep Fator R >= 28%.
    3. Ensure Pró-labore is at least the legal minimum wage.
    4. Compute INSS, DAS, IRPF status, dividends, and net take-home.
    
    Args:
        revenue_usd: Monthly revenue in US dollars.
        exchange_rate: Current USD → BRL exchange rate.
    
    Returns:
        Dictionary with all calculated tax components.
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
    inss_tax: float = ideal_pro_labore * INSS_TAX_RATE

    # Step 5: DAS tax (monthly Simples Nacional tax on gross revenue)
    estimated_das: float = gross_revenue_brl * DAS_TAX_RATE

    # Step 6: IRPF check — personal income tax applies if Pró-labore > R$ 5.000
    if ideal_pro_labore > IRPF_LIMIT:
        irpf_status: str = (
            "⚠️  IRPF Triggered! Pró-labore exceeds "
            f"{format_brl(IRPF_LIMIT)}. Apply deductions."
        )
    else:
        irpf_status = "✅ Tax Free"

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
    available_dividends: float = gross_revenue_brl - ideal_pro_labore - estimated_das

    # Step 8: Total net take-home
    # (Pró-labore after INSS deduction) + (tax-free dividends)
    total_net_take_home: float = (ideal_pro_labore - inss_tax) + available_dividends

    return {
        "gross_revenue_brl": gross_revenue_brl,
        "fator_r_minimum": fator_r_minimum,
        "ideal_pro_labore": ideal_pro_labore,
        "inss_tax": inss_tax,
        "estimated_das": estimated_das,
        "irpf_status": irpf_status,
        "bracket_warning": bracket_warning,
        "available_dividends": available_dividends,
        "total_net_take_home": total_net_take_home,
    }


def display_results(
    console: Console,
    month_year: str,
    revenue_usd: float,
    exchange_rate: float,
    results: dict[str, float | str],
) -> None:
    """Render the calculation results as a beautifully formatted Rich table.
    
    Args:
        console: Rich console instance for output.
        month_year: The reference month/year string (e.g., "03/2026").
        revenue_usd: Original revenue input in USD.
        exchange_rate: USD → BRL exchange rate used.
        results: Dictionary returned by calculate_taxes().
    """
    # ── Input Summary Panel ──────────────────────────────────────
    input_table = Table(
        box=box.SIMPLE_HEAD,
        show_header=False,
        padding=(0, 2),
    )
    input_table.add_column("Label", style="dim", min_width=22)
    input_table.add_column("Value", style="bold white")

    input_table.add_row("📅 Reference Month", month_year)
    input_table.add_row("💵 Revenue (USD)", f"US$ {revenue_usd:,.2f}")
    input_table.add_row("💱 Exchange Rate", f"1 USD = R$ {exchange_rate:,.4f}")

    console.print()
    console.print(
        Panel(
            input_table,
            title="[bold cyan]📥 Input Parameters[/]",
            border_style="cyan",
            padding=(1, 2),
        )
    )

    # ── Results Table ────────────────────────────────────────────
    table = Table(
        title="",
        box=box.ROUNDED,
        title_style="bold bright_white",
        header_style="bold bright_cyan",
        border_style="bright_blue",
        show_lines=True,
        padding=(0, 2),
        min_width=60,
    )

    table.add_column("📋 Item", style="bold white", min_width=30)
    table.add_column("💰 Value", justify="right", style="bold green", min_width=20)

    # Row 1: Gross Revenue
    table.add_row(
        "Gross Revenue (BRL)",
        format_brl(results["gross_revenue_brl"]),
    )

    # Row 2: Fator R Minimum (informational)
    table.add_row(
        "Fator R Minimum (28%)",
        format_brl(results["fator_r_minimum"]),
        style="dim",
    )

    # Row 3: Ideal Pró-labore (highlighted)
    table.add_row(
        "✨ Ideal Pró-labore",
        format_brl(results["ideal_pro_labore"]),
        style="bold bright_yellow",
    )

    # Row 4: INSS Tax (deduction)
    table.add_row(
        "INSS (11%)",
        f"- {format_brl(results['inss_tax'])}",
        style="red",
    )

    # Row 5: DAS Tax (deduction)
    table.add_row(
        "DAS (Simples Nacional)",
        f"- {format_brl(results['estimated_das'])}",
        style="red",
    )

    # Row 6: IRPF Status
    irpf = str(results["irpf_status"])
    irpf_style = "bold red" if "⚠️" in irpf else "bold green"
    table.add_row("IRPF Status", irpf, style=irpf_style)

    # Row 6b: Bracket Warning (only if applicable)
    bracket_warn = str(results.get("bracket_warning", ""))
    if bracket_warn:
        table.add_row(
            "📈 Bracket Warning",
            bracket_warn,
            style="bold yellow",
        )

    # Row 7: Available Dividends
    table.add_row(
        "📦 Available Dividends",
        format_brl(results["available_dividends"]),
        style="bright_green",
    )

    # Row 8: Total Net Take-Home (grand total)
    table.add_row(
        "🏠 Total Net Take-Home",
        format_brl(results["total_net_take_home"]),
        style="bold bright_white on blue",
    )

    console.print()
    console.print(
        Panel(
            table,
            title="[bold bright_white]📊 Tax Calculation Results[/]",
            border_style="bright_blue",
            padding=(1, 1),
        )
    )

    # ── Footer with Fator R explanation ──────────────────────────
    footer_text = Text.assemble(
        ("💡 Fator R Strategy: ", "bold cyan"),
        (
            "Paying at least 28% of gross revenue as Pró-labore keeps your "
            "company in Anexo III (lower tax rates) instead of Anexo V. "
            "The ideal Pró-labore above is the minimum needed to maintain "
            "this threshold while respecting the legal minimum wage.\n\n",
            "dim white",
        ),
        ("💱 Exchange Rate Note: ", "bold cyan"),
        (
            "Per Brazilian tax law, foreign income must be converted using "
            "the BRL exchange rate on the date the funds are made available "
            "or the invoice is issued — not the withdrawal date.\n\n",
            "dim white",
        ),
        ("⚖️  Disclaimer: ", "bold yellow"),
        (
            "This tool provides estimates for planning purposes only. "
            "Always consult a qualified Brazilian accountant (contador) "
            "for official tax filings.",
            "dim white",
        ),
    )
    console.print()
    console.print(
        Panel(
            footer_text,
            border_style="dim",
            padding=(1, 2),
        )
    )


def main() -> None:
    """Entry point — collect user input and display the tax calculation."""
    console = Console()

    # ── Header ──────────────────────────────────────────────────
    header = Text("RCal", style="bold bright_cyan")
    subtitle = Text(
        "Simples Nacional Tax Calculator • Anexo III • Fator R",
        style="dim white",
    )
    console.print()
    console.print(Panel.fit(
        Text.assemble(header, "\n", subtitle),
        border_style="bright_blue",
        padding=(1, 4),
    ))
    console.print()

    # ── Collect Inputs ──────────────────────────────────────────
    month_year: str = Prompt.ask(
        "[bold cyan]📅 Current Month/Year[/] [dim](e.g. 03/2026)[/]"
    )

    revenue_usd: float = FloatPrompt.ask(
        "[bold cyan]💵 Monthly Revenue in USD[/]"
    )

    exchange_rate: float = FloatPrompt.ask(
        "[bold cyan]💱 USD → BRL Exchange Rate[/]"
    )

    # ── Calculate & Display ─────────────────────────────────────
    results = calculate_taxes(revenue_usd, exchange_rate)
    display_results(console, month_year, revenue_usd, exchange_rate, results)
    console.print()


if __name__ == "__main__":
    main()
