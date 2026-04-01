# Product Requirements Document (PRD)

## Product

RCal is a standalone Python CLI calculator for Brazilian Simples Nacional planning focused on founder-operated service-exporting companies.

## Document status

- Source of truth basis: current repository implementation and docs
- Product maturity: functional single-user CLI with strong local QA
- Distribution maturity: improving toward open-source readiness

## Problem statement

Founder-operators of small Brazilian service-exporting companies under Simples Nacional need fast monthly planning for salary and tax tradeoffs. They need to compare revenue and exchange-rate scenarios quickly to estimate:

- Pró-labore
- INSS
- IRPF
- DAS
- Dividends
- Net take-home

without building spreadsheets or running filing-grade systems.

## Target users

- Brazilian ME/EPP owner-operators in Ltda or SLU structures
- Simples Nacional users planning around Anexo III assumptions and Fator R
- Users with basic terminal comfort and moderate tax vocabulary familiarity

## Non-target users

- Teams seeking end-to-end filing automation
- Businesses outside Brazilian Simples Nacional assumptions modeled in this repository
- Users needing full municipal tax engines or full rolling RBT12 filing logic

## Product scope

### In scope

- Interactive terminal workflow with persistent local state
- Revenue planning from USD to BRL
- Fator R target strategy with federal minimum wage floor
- INSS with 2026 ceiling behavior
- DAS estimate using fixed effective Bracket 1 planning rate
- IRPF 2026 calculation with legal vs simplified deductions and reducer
- Scenario loop for month/revenue/rate iteration
- Advisory warnings for low/zero revenue and bracket constraints

### Out of scope

- PGDAS-D submission or official filing generation
- Full RBT12 progressive DAS computation for all business states
- Legal determination of export exemption eligibility
- Replacement of professional accounting advice

## Business logic assumptions (current implementation)

- Simples Nacional planning focus with Anexo III assumptions
- Fator R threshold target fixed at 28%
- Effective DAS rate fixed at 3.054% for Bracket 1 planning context
- Federal minimum wage floor applied for Pró-labore optimization
- IRPF 2026 table and Lei nº 15.270/2025 reducer logic applied
- SC / Florianópolis references presented as compliance reminders in UI panels

## Functional requirements

### Core input/output

1. Collect month/year in `MM/YYYY` format with validation.
2. Collect monthly revenue in USD, allowing zero.
3. Collect USD→BRL exchange rate as finite positive float.
4. Optionally collect IRPF deductions:
   - dependents
   - PGBL contribution
   - alimony
5. Return and display:
   - gross BRL revenue
   - Fator R minimum
   - ideal Pró-labore
   - INSS, DAS, IRPF details
   - dividends
   - net take-home
   - effective tax burden

### Workflow behavior

1. Persist last run in `~/.rcal_state.json`.
2. Restore previous values on launch.
3. Support loop actions:
   - change all
   - change revenue
   - change exchange rate
   - clear memory
4. Show contextual warnings for:
   - estimated annual revenue beyond Bracket 1 planning ceiling
   - negative dividends / low-viability scenarios
   - zero-revenue advisory path

## UX requirements (CLI)

- Branded header and structured 3-zone output:
  - recap
  - tax breakdown
  - bottom line
- Prompt validation with clear retry messages
- Terminology remains legally accurate for Brazilian tax context
- Footer must reiterate planning-only boundary and accountant consultation

## Quality requirements

- Maintain local QA pipeline in `qa.sh`:
  - Black
  - Flake8
  - Pylint
  - Mypy
  - Pytest with coverage threshold
  - Benchmark run
- Preserve current strong test posture and mathematical regression safety

## Security and privacy requirements

- No remote data transmission in core CLI flow
- Local state only in user home directory file
- No secret collection or API key handling in current scope
- Security reporting path documented in `SECURITY.md`

## Documentation requirements

- README must remain aligned with implemented behavior and limitations
- Changes to formulas or assumptions must update:
  - `README.md`
  - `docs/AI_REFERENCE_DOC.md`
  - relevant compliance docs
- Changelog must reflect behavior changes by release version

## Open-source release requirements

- Required governance files:
  - `LICENSE`
  - `CONTRIBUTING.md`
  - `CODE_OF_CONDUCT.md`
  - `SECURITY.md`
- Required collaboration templates:
  - bug report
  - feature request
  - pull request template
- Required automation:
  - CI workflow for lint, type, tests, coverage, benchmark smoke

## Success criteria

- First-time user can run `./rcal` and complete one full scenario in terminal.
- Users can compare at least three scenarios in one session using loop mode.
- QA pipeline remains passing with full coverage target.
- Public contributors can open issues/PRs with clear process and templates.
- Repo messaging clearly distinguishes planning estimation from official filing.

## Current gaps and next actions

1. Keep docs synchronized whenever tax constants/rules change.
2. Preserve CI parity with local QA expectations.
3. Gradually reduce stale internal-only docs from root/docs surface.
4. Maintain strict scope to CLI planning unless a new PRD revision expands it.
