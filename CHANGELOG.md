# 📋 Changelog

All notable changes to the RCal project are documented here.

---

## [3.0.1] — 2026-03-31

### 🔬 Mathematical Validation & INSS Ceiling Fix

Comprehensive mathematical audit against official Brazilian government sources (Receita Federal, Lei nº 15.270/2025, LC 123/2006). All 9 tax constants and 5 IRPF brackets confirmed correct. One critical regulatory bug fixed.

### Fixed

- **INSS Ceiling (Teto Previdenciário)** — INSS contribution is now correctly capped at the 2026 ceiling of R$ 8.475,55. The maximum monthly INSS is R$ 932,31 (11% × R$ 8.475,55), regardless of how high the Pró-labore is. Previously, INSS was calculated as an uncapped 11% of Pró-labore, producing incorrect results for users with monthly BRL revenue above ~R$ 30.270.
- **Display label** — The INSS row in the tax breakdown table now shows "INSS (11%, capped)" when the ceiling is active.

### Added

- **`INSS_CEILING` Constant** — R$ 8.475,55 with docstring citing Portaria Interministerial MPS/MF 2026.
- **NaN/Infinity Input Guards** — `PositiveFloatPrompt` and `NonNegativeFloatPrompt` now reject `NaN`, `Infinity`, and `-Infinity` via `math.isfinite()` checks, preventing nonsensical calculations from non-finite float inputs.
- **`TestINSSCeiling`** — 8 tests validating ceiling behavior: below/at/above boundary, cascading effects on taxable base, IRPF, net take-home, and deductions dictionary.
- **`TestDASRateDerivation`** — 3 tests independently deriving the 3.054% DAS rate from Anexo III repartition percentages (IRPJ 4% + CSLL 3.5% + CPP 43.4% = 50.9% of 6% nominal rate).
- **`TestInputGuardsNaNInfinity`** — 9 tests for NaN/Infinity/−Infinity rejection on both float prompt classes.
- **`TestEdgeCases`** — 10 tests covering extreme revenues ($1–$50k), boundary conditions (exact minimum wage threshold, PGBL at exactly 12% cap), and effective tax burden identity.

### Changed

- **`calculate_taxes()`** — INSS now uses `min(ideal_pro_labore, INSS_CEILING)` as the contribution base.
- **test_main.py** — Expanded from 92 to 122 tests (13 → 17 test classes).
- **AI_REFERENCE_DOC.md** — Added INSS ceiling to §2 constants table, updated test count to 122/17, added `math.isfinite()` note to critical invariants.
- **README.md** — Added `INSS_CEILING` to constants table, updated test count.

### Technical

- **New import** — `math` (stdlib) for `math.isfinite()` guard
- **No new dependencies** — all changes use Python stdlib + `rich>=13.0.0`
- **Backward compatible** — `calculate_taxes()` API unchanged; existing callers unaffected

---

## [3.0.0] — 2026-03-31

### 🧮 Full 2026 IRPF Calculation Engine (Lei nº 15.270/2025)

The application now performs the exact Individual Income Tax (IRPF) calculation instead of displaying a binary status check. This is a major update that affects the Net Take-Home figure for high-income scenarios.

### Added

- **`calculate_irpf_2026()` Pure Function** — 3-step IRPF algorithm: standard progressive table → Lei nº 15.270/2025 reducer → final tax amount. Returns `(standard_irpf, reducer_amount, final_irpf)` tuple.
- **2026 IRPF Progressive Table** — `IRPF_TABLE_2026` constant with all 5 brackets from Receita Federal (Isento / 7.5% / 15% / 22.5% / 27.5%).
- **Lei nº 15.270/2025 Reducer** — Full exemption for taxable base ≤ R$ 5.000, phase-out zone R$ 5.000–R$ 7.350, no reduction above R$ 7.350.
- **CLI Deduction Inputs** — Optional prompts for dependents (R$ 189,59 each), PGBL pension (capped at 12% of Pró-labore), and alimony (Pensão Alimentícia). Gated behind a `Confirm` prompt that defaults based on saved state.
- **`NonNegativeIntPrompt`** — Prompt subclass accepting 0 and positive integers (for dependents count).
- **`NonNegativeFloatPrompt`** — Prompt subclass accepting 0.0 and positive floats (for PGBL/alimony amounts).
- **`collect_deductions()`** — Collects optional deduction inputs with smart defaults from saved state.
- **Deduction Persistence** — Deduction values (num_dependents, pgbl_contribution, alimony) saved to `~/.rcal_state.json` and pre-filled on next launch. Smart defaulting: if previous deductions were non-zero, prompts default to "yes".
- **IRPF Taxable Base Row** — Displayed in the Tax Breakdown table (Zone 2).
- **IRPF Amount Row** — Shows the calculated IRPF or "✅ Tax Free" in the Tax Breakdown table.
- **IRPF Bar Segment** — Revenue distribution bar includes an IRPF segment (deep red) when IRPF > 0.
- **New Test Classes** — `TestIRPF2026` (12 tests), `TestIRPFDeductions` (8 tests), `TestNetTakeHomeWithIRPF` (5 tests), `TestNonNegativeIntPrompt` (6 tests), `TestNonNegativeFloatPrompt` (4 tests).
- **AI_REFERENCE_DOC.md §7** — New section "2026 IRPF Rules & Deductions" with progressive table, reducer formula, deduction types, and three official Receita Federal source URLs.

### Changed

- **`calculate_taxes()`** — Now accepts optional keyword args: `num_dependents`, `pgbl_contribution`, `alimony`. Returns 5 new keys: `irpf_tax`, `irpf_standard`, `irpf_reducer`, `taxable_base`, `irpf_deductions`. All existing keys preserved.
- **Net Take-Home Formula** — Now subtracts IRPF: `(Pró-labore - INSS - IRPF) + Dividends`. Previously assumed 0% IRPF.
- **Effective Tax Burden** — Now includes IRPF: `(INSS + DAS + IRPF) / Gross`.
- **IRPF Status Display** — Shows calculated amount (e.g., "⚠️ IRPF: R$ 1.036,80") instead of the old binary "Triggered / Tax Free".
- **`save_state()`** / **`load_state()`** — Extended to persist deduction values. Backward compatible with pre-v3.0 state files.
- **`render_breakdown_bar()`** — Net salary segment now subtracts IRPF. IRPF segment added when > 0.
- **`main()`** — Integrates deduction collection into the interactive loop. Deductions re-prompted on each calculation (since Pró-labore changes with revenue/rate).
- **test_main.py** — Expanded from 46 to 92 tests (13 test classes). Updated `TestHighRevenueScenario` with exact IRPF expectations.
- **README.md** — Updated constants table, math table, and project structure.
- **CHANGELOG.md** — Added this version entry.

### Removed

- **`IRPF_LIMIT` constant** — Replaced by the full progressive table + Lei nº 15.270/2025 reducer. The old R$ 5.000 threshold was a simplified proxy that has been superseded by exact calculation.

### Technical

- **No new dependencies** — all enhancements use `rich>=13.0.0` + Python stdlib
- **New constants** — `IRPF_TABLE_2026`, `IRPF_DEPENDENT_DEDUCTION`, `IRPF_REDUCER_FULL_EXEMPTION_LIMIT`, `IRPF_REDUCER_PHASE_OUT_LIMIT`, `IRPF_REDUCER_BASE`, `IRPF_REDUCER_FACTOR`
- **Backward compatible** — `calculate_taxes()` default kwargs ensure all existing callers work unchanged

---

## [2.1.0] — 2026-03-31

### 🚀 One-Command Launcher & Cross-Session Memory

Quality-of-life improvements: launch with a single command and never re-enter the same values twice.

### Added

- **`rcal` Bash Launcher** — Executable script that auto-detects Python 3, creates a virtual environment if missing, installs dependencies, and launches the app. Just type `./rcal`.
- **Cross-Session Memory** — `load_state()`, `save_state()`, `clear_state()` functions persisting last-used inputs to `~/.rcal_state.json`. Returning users get pre-filled defaults automatically.
- **[4] Clear Memory** — New loop menu option to wipe saved state and start fresh.
- **Session Restored Indicator** — "💾 Previous session restored" message on launch when saved state exists.

### Changed

- **`collect_inputs()`** — Now accepts `saved_state` parameter with 4-tier default priority: in-session memory → JSON file → system clock → no default.
- **`prompt_next_action()`** — Extended from 3 to 4 choices (added "clear" action).
- **`main()`** — Loads state on launch, saves after each calculation, handles clear action.
- **README.md** — New Quick Start with `./rcal` launcher, added Memory section, updated project structure.
- **CHANGELOG.md** — Added this version entry.
- **test_main.py** — Expanded from 39 to 46 tests. Added `TestStatePersistence` (7 tests covering save/load/clear roundtrip, corrupted file handling, missing file fallback).

### Technical

- **No new dependencies** — uses `json` and `pathlib` from Python stdlib
- **New constant** — `STATE_FILE: Path = Path.home() / ".rcal_state.json"`
- **New imports** — `json`, `pathlib.Path` (stdlib)

---

## [2.0.0] — 2026-03-31

### 🎨 UI/UX Complete Overhaul

A full redesign of the terminal experience, transforming RCal from a single-run calculator into a premium interactive tool.

### Added

- **Design System** — `RCAL_THEME` with 15 semantic color tokens (brand, money, status, text hierarchy, surfaces, prompts) using Rich's `Theme` class. All visual styles centralized in one location.
- **ASCII Art Header** — Visually attractive branded logo rendered in brand color, centered with subtitle and decorative Rule separator.
- **Input Validation** — `MonthYearPrompt` subclass validating `MM/YYYY` format and month range (01-12). `PositiveFloatPrompt` subclass rejecting zero and negative numbers. Both use Rich's `InvalidResponse` for automatic retry.
- **Smart Defaults** — Month/year field auto-populated from the system clock. Exchange rate remembered from the previous calculation within a session.
- **3-Zone Visual Output** — Redesigned results into three distinct visual zones:
  - Zone 1: Input Recap — three compact horizontal card panels
  - Zone 2: Tax Breakdown — structured table with semantic themed styles
  - Zone 3: Bottom Line — highlighted panel with dividends, net take-home, effective tax burden %, and stacked Unicode bar chart (█)
- **Revenue Distribution Bar** — `render_breakdown_bar()` function creating a proportional stacked bar chart showing Salary/INSS/DAS/Yours split. Normalizes gracefully when expenses exceed revenue.
- **Effective Tax Burden** — `format_pct()` utility and tax burden percentage displayed in the Bottom Line panel.
- **Loop Mode** — "Calculate another month?" prompt after each result with three options:
  - [1] All inputs (exchange rate pre-filled from last run)
  - [2] Only revenue (keeps month + exchange rate)
  - [3] Only exchange rate (keeps month + revenue)
- **Negative Dividends Warning** — Explicit danger panel with title "⚠️ Action Required" explaining the problem (revenue too low to cover Pró-labore + DAS) and two actionable options: ① Increase revenue, ② Accept minimum wage salary.
- **Graceful Ctrl+C** — `KeyboardInterrupt` handler prints "👋 Até logo!" instead of a Python traceback.
- **Rich Tracebacks** — `install_rich_traceback(show_locals=True)` for unexpected errors.
- **Structured Footer** — Three Rule-separated sections (💡 Strategy, 💱 Exchange Rate, ⚖️ Disclaimer) replacing the original dense text block.
- **Calculation Spinner** — Brief `console.status()` spinner (0.35s) providing tactile feedback during calculation.
- **CHANGELOG.md** — This file, documenting all changes.

### Changed

- **README.md** — Complete rewrite with updated features list, new sample output matching ASCII header + 3-zone layout, loop mode documentation, corrected commands to `python3`, added test running instructions.
- **docs/walkthrough.md** — Rewritten with version history, v2.0 feature details, architecture notes.
- **docs/AI_REFERENCE_DOC.md** — Added Net Take-Home and Effective Tax Burden to math engine (§3), negative dividends edge case (§4), new §6 documenting v2.0 architecture constraints and UI component inventory.
- **test_main.py** — Expanded from 18 to 39 tests. Added `TestFormatPct` (4 tests), `TestMonthYearPrompt` (8 tests), `TestPositiveFloatPrompt` (6 tests), `TestBreakdownBar` (3 tests).

### Technical

- **No new dependencies** — all enhancements use `rich>=13.0.0`
- **Stable API** — `calculate_taxes()` function signature and return dictionary unchanged
- **New imports** — `re`, `time`, `datetime` (stdlib); `Theme`, `Rule`, `Align`, `Columns`, `Group`, `Confirm`, `InvalidResponse` (rich)

---

## [1.0.0] — 2026-03-31

### Initial Release

- Interactive Python CLI for Brazilian Simples Nacional tax calculation
- Fator R optimization (28% threshold) with Anexo III / Anexo V classification
- USD → BRL currency conversion with Brazilian formatting (`R$ 1.621,00`)
- Tax calculations: DAS (3.054%), INSS (11%), IRPF warning, dividends, net take-home
- Bracket 1 ceiling warning (R$ 180k/year)
- Rich-powered terminal output with tables, panels, and color coding
- Unit test suite (18 tests across 4 test classes)
- Comprehensive README with Fator R explanation and macOS setup guide
- AI_REFERENCE_DOC.md for AI agent context
