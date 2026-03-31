# 🚶 Walkthrough — RCal: Brazilian Simples Nacional Tax Calculator

## 🚀 Project Overview

RCal is a standalone Python CLI application that calculates the optimal **Pró-labore** and taxes for a Brazilian tech company exporting services under the Simples Nacional (Anexo III) regime using the **Fator R** rule.

## 📦 Version History

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
- Three options: [1] All inputs, [2] Only revenue, [3] Only exchange rate
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
- `main.py`: Application entry point containing UI layer + calculation engine
- `test_main.py`: Unit test suite (18 tests, 4 test classes)
- `requirements.txt`: Single dependency — `rich>=13.0.0`
- `CHANGELOG.md`: Version history
- `docs/AI_REFERENCE_DOC.md`: Canonical source of truth for business logic
- `docs/initial-prompt.md`: Original project specification

### Design Principles
- **Single file**: All code in `main.py` for maximum simplicity
- **No new dependencies**: Everything uses `rich>=13.0.0`
- **Stable API**: `calculate_taxes()` function signature and return dict unchanged across versions
- **Separation of concerns**: Calculation logic (`calculate_taxes()`) is fully separate from UI (`display_*` functions)

## 📸 Verification

### Automated Tests (18/18 passing)
```bash
python3 -m unittest test_main -v
```

### Manual Test Scenarios
| Scenario | Revenue | Rate | Validates |
|----------|---------|------|-----------|
| Standard (§5) | $883 | 5.23 | Normal output, minimum wage floor, tax-free IRPF |
| High Revenue | $5,000 | 5.75 | IRPF warning, bracket warning, Fator R > min wage |
| Low Revenue | $100 | 5.00 | Negative dividends danger panel, bar normalization |

### Repository
All files pushed to: `https://github.com/MAlkabbani/RCal.git`
Branch: `main`

> [!TIP]
> To run the tool locally:
> ```bash
> python3 -m venv .venv && source .venv/bin/activate
> pip install -r requirements.txt
> python3 main.py
> ```
