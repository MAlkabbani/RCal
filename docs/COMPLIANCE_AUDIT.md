# Compliance Audit

## Scope

This audit reviews the recent IRPF, zero-revenue, and enterprise-QA updates in RCal against the public guidance currently published by Receita Federal, Simples Nacional, ALESC, and Prefeitura de Florianópolis.

## Government Sources Cross-Checked

- Receita Federal 2026 IRPF tables and examples
- Simples Nacional PGDAS-D monthly declaration guidance
- ALESC approval of the 2025 Santa Catarina regional floor
- Prefeitura de Florianópolis Alvará de Funcionamento guidance

## Findings Applied To Code

### Corrected in code

- IRPF now applies the optional monthly simplified deduction of R$ 607,20 whenever it is more favorable than legal deductions.
- The 2026 IRPF reduction now uses gross taxable monthly income as its legal trigger, matching Receita Federal examples.
- High-income pró-labore scenarios above R$ 7.350,00 no longer receive the reduction incorrectly.
- The result payload now exposes the deduction model, deduction total, and reduction basis for auditability.

### Corrected in tests and QA

- The test suite now validates official Receita Federal 2026 IRPF examples.
- The QA pipeline now includes formatting, linting, typing, full tests, full coverage, and a repeatable benchmark run.
- Pylint is now governed by repository configuration so the QA script fails consistently on meaningful regressions.

### Corrected in operational resilience

- Workspace autosave and hot-exit behavior are now committed in `.vscode/settings.json`.
- Python launch targets are now committed in `.vscode/launch.json` so the main app and test entry points are restorable after IDE interruption.
- The repository now includes `backup_workspace.py`, and `qa.sh` creates a timestamped ZIP backup before verification begins.

### Corrected in documentation

- README and internal reference docs now describe the simplified deduction rule, updated test totals, and current QA workflow.
- Repository documentation now explicitly states that official PGDAS-D and DAS filings still depend on rolling 12-month revenue and payroll history.

## Current Compliance Boundaries

- The calculator still uses a monthly Fator R proxy and a first-bracket DAS shortcut for planning.
- Official Simples Nacional filing accuracy still requires rolling RBT12 and payroll history, plus case-specific confirmation that export exemptions apply.
- Florianópolis licensing and TFF obligations remain surfaced as compliance reminders, not as automatically computed municipal tax amounts.

## Peer Review Checklist

- Confirm the target company is an Ltda or SLU under Simples Nacional.
- Confirm the revenue is export revenue eligible for ISS and PIS/COFINS treatment assumed by the app.
- Confirm the filing period uses the correct RBT12 and payroll history before relying on DAS results.
- Confirm the chosen IRPF deduction path matches payroll practice for the month.
- Confirm municipal licensing facts for Florianópolis, including Alvará and TFF obligations.
