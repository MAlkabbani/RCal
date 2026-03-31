# 📋 Changelog

All notable changes to the RCal project are documented here.

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
