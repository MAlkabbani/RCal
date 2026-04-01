# AI Context & Tax Logic Reference (Live Document)

> **Instructions for AI Agents:** Treat this file as the primary source of truth for the business logic underpinning this application. If you are asked to update, refactor, or expand this codebase, you must cross-reference the `Current Tax Constants` section with the latest Brazilian federal tax legislation (Receita Federal) for the current year.

## 1. The Core Business Context

This application is built for Brazilian micro and small businesses (ME/EPP) structured as **Ltda** (Sociedade Limitada) or **SLU** (Sociedade Limitada Unipessoal) operating under the **Simples Nacional** tax regime, specifically tailored for tech companies (e.g., software development, website planning/hosting - LC 116/03 Sub-item 01.08) that export services internationally.

- **Export Exemptions:** Under Brazilian law, the export of services (where the client is abroad and the result of the service is verified abroad) is exempt from municipal ISSQN and federal PIS/COFINS taxes.
- **The "Fator R" Mechanism:** Tech services typically fall under Anexo V of Simples Nacional (starting at 15.5% tax). However, if the company's payroll (including the administrator's _Pró-labore_) is equal to or greater than **28%** of its gross revenue over the last 12 months, the company is allowed to be taxed under **Anexo III** (starting at 6%).
- **The Goal:** The application calculates the mathematically optimal _Pró-labore_ to hit the exact 28% Fator R target, keeping the company in Anexo III, while minimizing the 11% INSS tax paid on that salary, and maximizing tax-free dividend distributions.

---

## 2. Current Tax Constants (Base Year: 2026)

_AI Agents: Verify these values for the current operational year before executing code changes._

| Variable                      | 2026 Value      | Context / Trigger                                                                                             |
| :---------------------------- | :-------------- | :------------------------------------------------------------------------------------------------------------ |
| **Federal Minimum Wage**      | R$ 1.621,00     | The absolute legal floor for a _Pró-labore_.                                                                  |
| **Fator R Target**            | 28% (0.28)      | The ratio of payroll to revenue required for Anexo III.                                                       |
| **INSS Tax Rate**             | 11% (0.11)      | Social security contribution levied on the _Pró-labore_.                                                      |
| **INSS Ceiling**              | R$ 8.475,55     | Teto previdenciário — maximum INSS contribution base. INSS is capped at R$ 932,31/month.                     |
| **Effective DAS (Bracket 1)** | ~3.054%         | The net tax rate for Anexo III (up to R$ 180k/year) after ISS, PIS, and COFINS export exemptions are applied. |
| **IRPF Dependent Deduction**  | R$ 189,59       | Monthly IRPF deduction per declared dependent.                                                                |

---

## 3. The Mathematical Engine

The core algorithm relies on this specific sequence of operations:

1.  **Currency Conversion:** `Gross Revenue (BRL)` = `Foreign Revenue (USD)` \* `Exchange Rate`
2.  **Target Calculation:** `Fator R Minimum` = `Gross Revenue (BRL)` \* `0.28`
3.  **Optimal Salary Selection:** `Ideal Pró-labore` = `MAX(Fator R Minimum, Federal Minimum Wage)`
4.  **Tax Calculations:**
    - `INSS Due` = `Ideal Pró-labore` \* `0.11`
    - `DAS Due` = `Gross Revenue (BRL)` \* `0.03054`
5.  **IRPF Taxable Base:** `Ideal Pró-labore` - `INSS Due` - `Dependents` - `PGBL (capped)` - `Alimony`
6.  **IRPF Calculation:** Apply the 2026 progressive table, then the Lei nº 15.270/2025 reducer (see §7).
7.  **Profit Distribution:** `Tax-Free Dividends` = `Gross Revenue (BRL)` - `Ideal Pró-labore` - `DAS Due`
8.  **Net Take-Home:** `(Ideal Pró-labore - INSS Due - IRPF)` + `Tax-Free Dividends`
9.  **Effective Tax Burden:** `(INSS Due + DAS Due + IRPF)` / `Gross Revenue (BRL)`

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
- **Expected Taxable Base:** R$ 1.442,69 _(1621.00 - 178.31)._
- **Expected IRPF:** R$ 0,00 _(Taxable base is below the R$ 2.428,80 exempt bracket)._

---

## 6. Application Architecture (v3.0)

_AI Agents: When modifying the codebase, respect these architectural constraints._

### Critical Invariants

- The `calculate_taxes()` function accepts `(revenue_usd, exchange_rate)` as positional args plus optional keyword args for deductions. All existing callers work without changes.
- The return dictionary preserves all original keys and adds new IRPF keys: `irpf_tax`, `irpf_standard`, `irpf_reducer`, `taxable_base`, `irpf_deductions`.
- 122 unit tests across 17 test classes validate the mathematical engine.
- All visual styling uses semantic tokens from `RCAL_THEME`. Do not use inline color strings.
- Input validation is handled by `MonthYearPrompt`, `PositiveFloatPrompt`, `NonNegativeIntPrompt`, and `NonNegativeFloatPrompt` subclasses. Float prompts reject `NaN` and `Infinity` via `math.isfinite()` guards.
- State persistence functions (`load_state`, `save_state`, `clear_state`) must never raise exceptions — they are convenience features that fail silently.

### Calculation Functions

| Function | Purpose |
|----------|---------|
| `calculate_irpf_2026()` | Pure function: 3-step IRPF (table → reducer → final) |
| `calculate_taxes()` | Core engine: Fator R + INSS + DAS + IRPF + dividends + net |

### UI Components

| Function | Purpose |
|----------|---------|
| `display_header()` | ASCII logo + subtitle + rule separator |
| `collect_inputs()` | Validated prompts with 4-tier defaults: in-session → JSON → clock → none |
| `collect_deductions()` | Optional IRPF deduction prompts with smart defaults from saved state |
| `display_results()` | 3-zone output: input recap → tax breakdown → bottom line |
| `display_footer()` | Rule-separated legal context sections |
| `render_breakdown_bar()` | Proportional stacked bar chart (Unicode █) with IRPF segment |
| `prompt_next_action()` | Loop mode menu (all/revenue/rate/clear) |

### State Persistence

| Function | Purpose |
|----------|---------|
| `load_state()` | Reads `~/.rcal_state.json`, returns dict or empty dict on error. Backward compatible with pre-v3.0 files. |
| `save_state()` | Writes month/revenue/rate + deduction values to JSON file, silently ignores failures |
| `clear_state()` | Deletes the state file, returns True/False |

### Entry Points

- `./rcal` — Bash launcher (auto-venv, auto-install, auto-run)
- `python3 main.py` — Direct execution (requires manual venv activation)

### Dependencies

- `rich>=13.0.0` — the **only** external dependency
- Python standard library: `json`, `pathlib`, `re`, `time`, `datetime`

---

## 7. 2026 IRPF Rules & Deductions

_AI Agents: This section documents the IRPF (Individual Income Tax) calculation logic implemented in v3.0. Verify these values against the official sources below for the current operational year._

### Official Sources

- **Tributação de 2026 (Receita Federal):** [https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/tabelas/2026](https://www.gov.br/receitafederal/pt-br/assuntos/meu-imposto-de-renda/tabelas/2026)
- **Lei nº 15.270/2025 (Isenção R$ 5 mil):** [https://www.gov.br/fazenda/pt-br/assuntos/noticias/2026/janeiro/receita-divulga-nova-tabela-do-irpf-com-as-mudancas-apos-isencao-para-quem-ganha-ate-r-5-mil](https://www.gov.br/fazenda/pt-br/assuntos/noticias/2026/janeiro/receita-divulga-nova-tabela-do-irpf-com-as-mudancas-apos-isencao-para-quem-ganha-ate-r-5-mil)
- **Simulador Oficial Receita Federal:** [https://www27.receita.fazenda.gov.br/simulador-irpf](https://www27.receita.fazenda.gov.br/simulador-irpf)

### Step 1 — Taxable Base (Base de Cálculo)

`Taxable Base` = `Ideal Pró-labore` − `INSS` − `Dependents` − `PGBL (capped)` − `Alimony`

| Deduction | Value | Notes |
|-----------|-------|-------|
| INSS | Automatic (11%) | Always subtracted; mandatory. |
| Dependents | R$ 189,59 per dependent | User-provided count. |
| PGBL | Up to 12% of Pró-labore | Private pension (Previdência Complementar). Capped by law. |
| Alimony | Full amount | Pensão Alimentícia, court-ordered. |

### Step 2 — Standard IRPF (Tabela Progressiva Mensal 2026)

| Base de Cálculo Mensal | Alíquota | Dedução |
|------------------------|----------|---------|
| Até R$ 2.428,80 | Isento | — |
| R$ 2.428,81 a R$ 2.826,65 | 7,5% | R$ 182,16 |
| R$ 2.826,66 a R$ 3.751,05 | 15% | R$ 394,16 |
| R$ 3.751,06 a R$ 4.664,68 | 22,5% | R$ 675,49 |
| Acima de R$ 4.664,68 | 27,5% | R$ 908,73 |

`Standard IRPF` = (`Taxable Base` × Alíquota) − Dedução

### Step 3 — 2026 IRPF Reducer (Lei nº 15.270/2025)

| Taxable Base | Reduction | Effect |
|--------------|-----------|--------|
| ≤ R$ 5.000,00 | Full exemption | Final IRPF = R$ 0,00 |
| R$ 5.000,01 to R$ 7.350,00 | `R$ 978,62 − (0,133145 × Taxable Base)` | Phase-out zone: gradual reduction |
| > R$ 7.350,00 | No reduction | Final IRPF = Standard IRPF |

`Final IRPF` = max(`Standard IRPF` − `Reducer`, 0)

### Step 4 — Updated Net Take-Home

`Net Take-Home` = `Dividends` + (`Ideal Pró-labore` − `INSS` − `Final IRPF`)

---

## 8. Zero-Revenue & Low-Revenue Edge Cases (v3.1)

_AI Agents: The codebase safely handles zero and near-zero revenue inputs without breaking the calculation engine. Understanding the edge cases is crucial for UI advisory messages._

### Mathematical Handling

- `MINIMUM_VIABLE_REVENUE_BRL` = `LEGAL_MINIMUM_WAGE + (LEGAL_MINIMUM_WAGE * DAS_TAX_RATE)` (approx. R$ 1.670,52).
- When `Gross Revenue (BRL)` < `MINIMUM_VIABLE_REVENUE_BRL`: The company generates **negative dividends** because the cost of maintaining the minimum Pró-labore + DAS exceeds the revenue. The owner must inject capital to cover expenses.
- Calculations naturally handle 0 revenue without division-by-zero errors because the `render_breakdown_bar` and `effective_tax_burden` implementations safely guard against `gross <= 0`. If revenue is exactly 0, `Pró-labore` defaults to the `LEGAL_MINIMUM_WAGE` floor.

### Regulatory Advisory

The codebase provides targeted guidance through the UI when revenue hits these thresholds:

1. **Zero Revenue Check (`is_zero_revenue` flag):** Notifies the user that Pró-labore withdrawal is legally optional when genuinely inactive, but emphasizes that choosing not to pay it results in losing INSS coverage.
2. **Low Revenue Check (`is_below_viable_threshold` flag):** Emphasizes that PGDAS-D filing remains mandatory despite low revenue.
3. **SC/Florianópolis Municipal Fees:** Reminds users about the fixed annual `TFF (Taxa de Fiscalização de Funcionamento)` imposed by the municipality irrespective of revenue.

---

_(End of Document)_
