# 🚶 Walkthrough — RCal: Brazilian Simples Nacional Tax Calculator

## 🚀 Project Overview

RCal is a standalone Python CLI application that calculates the optimal **Pró-labore** and taxes for a Brazilian tech company exporting services under the Simples Nacional (Anexo III) regime using the **Fator R** rule.

## 📦 Version History

### v3.2 — Compliance Audit and QA Hardening (April 2026)

- IRPF updated to apply the optional simplified monthly deduction when it is more favorable
- Lei nº 15.270/2025 reduction now uses gross taxable monthly income as the legal trigger
- New benchmark runner and centralized QA configuration added to the repository
- Workspace autosave, debug launch profiles, and timestamped backup generation are now repository-managed
- Repository docs synchronized with the current 149-test suite and compliance audit notes

### v3.0 — Full 2026 IRPF Calculation Engine (March 2026)

Major upgrade replacing the binary IRPF status check with exact tax calculation per **Lei nº 15.270/2025**.

#### 🏦 IRPF Calculation Engine

- **`calculate_irpf_2026()` pure function** implementing 3-step algorithm:
  1. Standard progressive table (5 brackets from Receita Federal)
  2. Optional simplified deduction before table application when more favorable
  3. Lei nº 15.270/2025 reducer using gross taxable monthly income as the trigger
  4. Final IRPF = max(Standard − Reducer, 0)
- Net Take-Home now subtracts IRPF: `(Pró-labore − INSS − IRPF) + Dividends`
- Effective Tax Burden includes IRPF: `(INSS + DAS + IRPF) / Gross`

#### 📝 Optional IRPF Deductions

- CLI prompts for: dependents (R$ 189,59/each), PGBL pension (capped at 12% of Pró-labore), alimony
- Gated behind a `Confirm` prompt that defaults based on saved state
- Smart memory: if previous deductions were non-zero, defaults to "yes" on next launch
- All deduction values persisted in `~/.rcal_state.json` (backward compatible with old files)

#### 📊 Updated UI

- **Zone 2 Tax Breakdown**: New "IRPF Taxable Base" (dim) and "IRPF (Lei 15.270/2025)" (red) rows
- **Zone 3 Bottom Line**: IRPF included in effective tax burden percentage
- **Breakdown Bar**: IRPF segment (deep red `#c1121f`) appears when IRPF > 0

#### 🧪 Expanded Test Suite

- 46 → **149 tests** across 20 test classes in the current repository state
- New: `TestIRPF2026` (12), `TestIRPFDeductions` (8), `TestNetTakeHomeWithIRPF` (5)
- New: `TestNonNegativeIntPrompt` (6), `TestNonNegativeFloatPrompt` (4)
- Updated: `TestHighRevenueScenario` with the current official non-reduction case above R$ 7.350,00 gross salary

### v2.1 — One-Command Launcher & Cross-Session Memory (March 2026)

Quality-of-life improvements eliminating setup friction and adding persistent memory.

#### 🚀 Bash Launcher (`rcal`)

- Executable script that auto-detects Python 3, creates venv, installs deps
- Just type `./rcal` — nothing else needed
- Idempotent: first run ~5 seconds for setup, subsequent runs launch instantly

#### 💾 Cross-Session Memory

- Last-used month/revenue/rate saved to `~/.rcal_state.json` after every calculation
- On relaunch, values pre-filled as smart defaults
- Human-readable JSON file, manually editable or deletable
- 4-tier default priority: in-session memory → JSON file → system clock → no default

#### 🗑️ Clear Memory

- New `[4] Clear memory` option in the loop menu
- Instantly wipes saved state and starts fresh prompts
- Also available manually: `rm ~/.rcal_state.json`

### v2.0 — UI/UX Enhancement (March 2026)

A complete overhaul of the terminal experience, transforming RCal from a single-run calculator into a premium interactive tool.

#### 🎨 Design System
- Introduced `RCAL_THEME` using Rich's `Theme` class with 15 semantic color tokens
- All styles centralized in one location for easy palette customization
- Categories: brand, money, text hierarchy, status, surfaces, prompts

#### ✨ Enhanced Header
- Visually attractive ASCII art logo rendered in brand color
- Centered subtitle with application description
- Decorative Rule separator

#### 🛡️ Input Validation
- **MonthYearPrompt**: Custom `Prompt` subclass validating `MM/YYYY` format and month range (01-12)
- **PositiveFloatPrompt**: Custom `FloatPrompt` subclass rejecting zero and negative numbers
- Smart default: month/year auto-populated from system clock
- Exchange rate remembered across loop iterations

#### 📊 3-Zone Visual Output
1. **Zone 1 — Input Recap**: Three compact horizontal card panels
2. **Zone 2 — Tax Breakdown**: Structured table with semantic themed styles
3. **Zone 3 — Bottom Line**: Highlighted panel with dividends, net take-home, effective tax burden %, and a stacked Unicode bar chart (█) showing revenue distribution

#### 🔄 Stateful Loop Mode
- "Calculate another month?" prompt after each result
- Four options: [1] All inputs, [2] Only revenue, [3] Only exchange rate, [4] Clear memory
- Exchange rate pre-filled from previous run
- Keeps previously entered values for unchanged fields

#### ⚠️ Error Handling
- **Ctrl+C**: Graceful exit with "👋 Até logo!" message (no Python traceback)
- **Negative dividends**: Explicit danger panel explaining the problem with two actionable options
- **Breakdown bar edge case**: Normalizes to total costs when expenses exceed revenue
- **Rich tracebacks**: `install_rich_traceback(show_locals=True)` for unexpected errors

#### 📝 Footer Refinement
- Three Rule-separated sections replacing the original dense text block
- 💡 Strategy, 💱 Exchange Rate, ⚖️ Disclaimer — each visually distinct but subdued

### v1.0 — Initial Release

- Interactive Python CLI using the `rich` library
- Fator R optimization logic (28% threshold)
- USD → BRL conversion with Brazilian currency formatting
- DAS (3.054%), INSS (11%), IRPF warning, dividends, and net take-home
- Comprehensive README with tax context documentation
- Unit test suite with 18 tests across 4 scenarios

## 🛠️ Architecture

### File Structure

- `rcal`: One-command bash launcher (auto-venv, auto-install, auto-run)
- `benchmark.py`: Performance benchmark for repeated tax calculations
- `main.py`: Application entry point containing UI layer + calculation engine
- `test_main.py`: Unit test suite (149 tests, 20 test classes)
- `pyproject.toml`: Shared QA configuration for Black, pytest, mypy, and pylint
- `qa.sh`: Full formatting, lint, typing, tests, coverage, and benchmark pipeline
- `requirements.txt`: Single dependency — `rich>=13.0.0`
- `CHANGELOG.md`: Version history
- `docs/AI_REFERENCE_DOC.md`: Canonical source of truth for business logic
- `docs/COMPLIANCE_AUDIT.md`: Compliance findings, sources, and review checklist
- `docs/initial-prompt.md`: Original project specification

### Design Principles

- **Single file**: All code in `main.py` for maximum simplicity
- **No new dependencies**: Everything uses `rich>=13.0.0` + Python stdlib
- **Stable API**: `calculate_taxes()` signature accepts optional kwargs for deductions; all existing callers work unchanged
- **Pure calculation**: `calculate_irpf_2026()` is side-effect-free and independently testable
- **Separation of concerns**: Calculation logic (`calculate_taxes()`) is fully separate from UI (`display_*` functions)
- **Silent persistence**: State functions never raise — they are convenience features that degrade gracefully

## 📸 Verification

### Automated Tests (149/149 passing)

```bash
source .venv/bin/activate
bash qa.sh
```

### Comprehensive Audit (March 31, 2026)

A 26-point mathematical cross-reference was performed against AI_REFERENCE_DOC.md:

| Audit | Checks | Result |
|-------|--------|--------|
| §5 Standard Test Case ($883, 5.23) | Gross, Fator R, Pro-labore, INSS, DAS, IRPF, dividends, net | ✅ 9/9 |
| High Revenue ($5000, 5.75) | IRPF triggered, bracket warning, Fator R > min wage | ✅ 4/4 |
| Negative Dividends ($100, 5.00) | Gross, min wage floor, negative dividends | ✅ 3/3 |
| Boundary Crossover (5789 BRL) | Pro-labore snaps at exact Fator R / min wage boundary | ✅ 2/2 |
| format_brl Edge Cases | Negative values, tiny values, exact thousands | ✅ 3/3 |
| Net = Gross - INSS - DAS Identity | Algebraic identity across 4 scenarios | ✅ 4/4 |
| Bash Launcher Syntax | `bash -n rcal` | ✅ |
| Python AST Parse | `ast.parse(main.py)` — 13 functions, 2 classes | ✅ |

### Repository

All files pushed to: `https://github.com/MAlkabbani/RCal.git`
Branch: `main`

> [!TIP]
> To run the tool locally:
> ```bash
> ./rcal
> ```
