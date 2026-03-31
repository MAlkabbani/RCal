# AI Context & Tax Logic Reference (Live Document)

> **Instructions for AI Agents:** Treat this file as the primary source of truth for the business logic underpinning this application. If you are asked to update, refactor, or expand this codebase, you must cross-reference the `Current Tax Constants` section with the latest Brazilian federal tax legislation (Receita Federal) for the current year.

## 1. The Core Business Context

This application is built for Brazilian micro and small businesses (ME/EPP) operating under the **Simples Nacional** tax regime, specifically tailored for tech companies (e.g., software development, website planning/hosting - LC 116/03 Sub-item 01.08) that export services internationally.

- **Export Exemptions:** Under Brazilian law, the export of services (where the client is abroad and the result of the service is verified abroad) is exempt from municipal ISSQN and federal PIS/COFINS taxes.
- **The "Fator R" Mechanism:** Tech services typically fall under Anexo V of Simples Nacional (starting at 15.5% tax). However, if the company's payroll (including the administrator's _Pró-labore_) is equal to or greater than **28%** of its gross revenue over the last 12 months, the company is allowed to be taxed under **Anexo III** (starting at 6%).
- **The Goal:** The application calculates the mathematically optimal _Pró-labore_ to hit the exact 28% Fator R target, keeping the company in Anexo III, while minimizing the 11% INSS tax paid on that salary, and maximizing tax-free dividend distributions.

---

## 2. Current Tax Constants (Base Year: 2026)

_AI Agents: Verify these values for the current operational year before executing code changes._

| Variable                      | 2026 Value  | Context / Trigger                                                                                             |
| :---------------------------- | :---------- | :------------------------------------------------------------------------------------------------------------ |
| **Federal Minimum Wage**      | R$ 1.621,00 | The absolute legal floor for a _Pró-labore_.                                                                  |
| **Fator R Target**            | 28% (0.28)  | The ratio of payroll to revenue required for Anexo III.                                                       |
| **INSS Tax Rate**             | 11% (0.11)  | Social security contribution levied on the _Pró-labore_.                                                      |
| **Effective DAS (Bracket 1)** | ~3.054%     | The net tax rate for Anexo III (up to R$ 180k/year) after ISS, PIS, and COFINS export exemptions are applied. |
| **IRPF Exemption Limit**      | R$ 5.000,00 | The monthly income threshold before Individual Income Tax is triggered.                                       |

---

## 3. The Mathematical Engine

The core algorithm relies on this specific sequence of operations:

1.  **Currency Conversion:** `Gross Revenue (BRL)` = `Foreign Revenue (USD)` \* `Exchange Rate`
2.  **Target Calculation:** `Fator R Minimum` = `Gross Revenue (BRL)` \* `0.28`
3.  **Optimal Salary Selection:** `Ideal Pró-labore` = `MAX(Fator R Minimum, Federal Minimum Wage)`
4.  **Tax Calculations:**
    - `INSS Due` = `Ideal Pró-labore` \* `0.11`
    - `DAS Due` = `Gross Revenue (BRL)` \* `0.03054`
5.  **Profit Distribution:** `Tax-Free Dividends` = `Gross Revenue (BRL)` - `Ideal Pró-labore` - `DAS Due`
6.  **Net Take-Home:** `(Ideal Pró-labore - INSS Due)` + `Tax-Free Dividends`
7.  **Effective Tax Burden:** `(INSS Due + DAS Due)` / `Gross Revenue (BRL)`

---

## 4. Edge Cases & Geographic Variables

When modifying the application, account for the following real-world complexities:

- **Regional Minimum Wages:** States like Santa Catarina (SC) have regional minimum wages (e.g., R$ 2.106,00 for tech workers in Faixa 4 as of 2026). However, for the sole purpose of a business owner's _Pró-labore_ to contribute to INSS, the Federal Minimum Wage is the legally accepted floor. The application defaults to the Federal level to optimize tax savings.
- **Payment Gateways:** Foreign income (e.g., via Stripe) must be calculated using the BRL exchange rate on the exact date the funds are made available or the invoice is issued, not the date of withdrawal to a Brazilian bank account.
- **Bracket Scaling:** The current hardcoded DAS rate (~3.05%) assumes the user is in Bracket 1 of Anexo III (Gross annual revenue up to R$ 180.000,00). If the company exceeds this, the effective rate must be dynamically calculated using the Receita Federal's progressive formula `((RBT12 * Nominal Rate) - Deductible Amount) / RBT12`.
- **Negative Dividends:** When monthly revenue is too low (below roughly R$ 1.636,27 BRL), the minimum Pró-labore + DAS will exceed gross revenue, resulting in negative dividends. This means the company must inject capital. The application surfaces an explicit warning panel with actionable options in this scenario.

---

## 5. Standard Test Case (Validation)

Use this specific scenario to test the application's math engine during CI/CD pipelines:

- **Input:** $883.00 USD Revenue, 5.23 Exchange Rate
- **Expected BRL Gross:** R$ 4.618,09
- **Expected Pró-labore:** R$ 1.621,00 _(Because 28% of 4618.09 is 1293.06, which is below the minimum wage floor)._
- **Expected INSS:** R$ 178,31
- **Expected IRPF Status:** Tax Free

---

## 6. Application Architecture (v2.0)

_AI Agents: When modifying the codebase, respect these architectural constraints._

### Critical Invariants
- The `calculate_taxes()` function signature and return dictionary shape **must not change** — 18 unit tests depend on it.
- All visual styling uses semantic tokens from `RCAL_THEME`. Do not use inline color strings.
- Input validation is handled by `MonthYearPrompt` and `PositiveFloatPrompt` subclasses.

### UI Components
| Function | Purpose |
|----------|---------|
| `display_header()` | ASCII logo + subtitle + rule separator |
| `collect_inputs()` | Validated prompts with smart defaults and exchange rate memory |
| `display_results()` | 3-zone output: input recap → tax breakdown → bottom line |
| `display_footer()` | Rule-separated legal context sections |
| `render_breakdown_bar()` | Proportional stacked bar chart (Unicode █) |
| `prompt_next_action()` | Loop mode menu (all/revenue/rate) |

### Dependencies
- `rich>=13.0.0` — the **only** external dependency
- Python standard library: `re`, `time`, `datetime`

---

_(End of Document)_
