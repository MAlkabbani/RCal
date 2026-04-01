# 🧮 RCal — Simples Nacional Planning CLI
<br>

<div align="center">
  <pre>
  ██████╗   ██████╗  █████╗  ██╗
  ██╔══██╗ ██╔════╝ ██╔══██╗ ██║
  ██████╔╝ ██║      ███████║ ██║
  ██╔══██╗ ██║      ██╔══██║ ██║
  ██║  ██║ ╚██████╗ ██║  ██║ ███████╗
  ╚═╝  ╚═╝  ╚═════╝ ╚═╝  ╚═╝ ╚══════╝
  </pre>
</div>

RCal is a standalone Python terminal calculator for Brazilian micro and small businesses under Simples Nacional, focused on founder-operated Ltda/SLU service exporters using Fator R planning.

It helps estimate monthly Pró-labore, INSS, IRPF, DAS, dividends, and net take-home under the repository's current assumptions.

## ⚡ Quick Attraction

- 🚀 One command to run: `./rcal`
- 🎯 Built for fast what-if comparisons across revenue and exchange-rate changes
- 🧾 Clear breakdown of Pró-labore, INSS, IRPF, DAS, dividends, and net take-home
- 💾 Remembers your last inputs for faster monthly planning

## 🖥️ CLI Preview (Partial)

Here is an example of the terminal output you can expect when running a calculation:

```ansi
[36m┌────────────────────────────────────────────────────────────────────┐[0m
[36m│[0m [32mMemory cleared! Saved state wiped.                                 [0m[36m│[0m
[36m│[0m [33mCurrent Month/Year[0m (MM/YYYY) (04/2026): [37m04/2026[0m                    [36m│[0m
[36m│[0m [33mMonthly Revenue in USD[0m (0 = zero-revenue advisory): [37m883[0m            [36m│[0m
[36m│[0m [33mUSD -> BRL Exchange Rate:[0m [37m5.237[0m                                    [36m│[0m
[36m│[0m [33mApply IRPF deductions?[0m (dependents, PGBL, alimony) [36m[y/n]:[0m [37mn[0m        [36m│[0m
[36m└────────────────────────────────────────────────────────────────────┘[0m

[36m┌───────────────┐  ┌─────────────────┐  ┌─────────────┐[0m
[36m│[0m 📅 Month      [36m│[0m  [36m│[0m 💰 Revenue      [36m│[0m  [36m│[0m ⚙️ Rate     [36m│[0m
[36m│[0m   04/2026     [36m│[0m  [36m│[0m   US$ 883.00    [36m│[0m  [36m│[0m   R$ 5.2370 [36m│[0m
[36m└───────────────┘  └─────────────────┘  └─────────────┘[0m

[36m┌────────────────────────────────────────────────────────────────────┐[0m
[36m│[0m 📊 Tax Breakdown                                                   [36m│[0m
[36m├───────────────────────────────┬────────────────────────────────────┤[0m
[36m│[0m [37mItem                          [0m[36m│[0m [33mValue                              [0m[36m│[0m
[36m├───────────────────────────────┼────────────────────────────────────┤[0m
[36m│[0m Gross Revenue (BRL)           [36m│[0m [36mR$ 4.624,27                        [0m[36m│[0m
[36m│[0m Fator R Minimum (28%)         [36m│[0m [36mR$ 1.294,80                        [0m[36m│[0m
[36m│[0m [33mIdeal Pró-labore              [0m[36m│[0m [33mR$ 1.621,00                        [0m[36m│[0m
[36m│[0m INSS (11%)                    [36m│[0m [31m- R$ 178,31                        [0m[36m│[0m
[36m│[0m DAS (Simples Nacional)        [36m│[0m [31m- R$ 141,23                        [0m[36m│[0m
[36m│[0m IRPF Taxable Base             [36m│[0m [36mR$ 1.013,80                        [0m[36m│[0m
[36m│[0m IRPF Deduction Mode           [36m│[0m Simplified ([36mR$ 607,20[0m)             [36m│[0m
[36m│[0m IRPF Status                   [36m│[0m ✅ [32mTax Free                         [0m[36m│[0m
[36m└───────────────────────────────┴────────────────────────────────────┘[0m

[36m┌────────────────────────────────────────────────────────────────────┐[0m
[36m│[0m 💰 Your Bottom Line                                                [36m│[0m
[36m│[0m   Tax-Free Dividends        [36mR$ 2.862,05                            [0m[36m│[0m
[36m│[0m   Net Take-Home             [34;1mR$ 4.304,74                            [0m[36m│[0m
[36m│[0m   Effective Tax Burden            [33m6.9%                             [0m[36m│[0m
[36m│[0m                                                                    [36m│[0m
[36m│[0m   Revenue Distribution:                                            [36m│[0m
[36m│[0m   [ [33mSalary 31%[0m | [31mINSS 4%[0m | [36mDAS 3%[0m | [32mYours 62%[0m ]                    [36m│[0m
[36m└────────────────────────────────────────────────────────────────────┘[0m
```

## ✨ Key Features

- 🧮 Fator R optimization for Anexo III planning assumptions
- 💱 USD → BRL conversion tuned for service exporters
- 🏛️ IRPF 2026 with deductions and legal reducer logic
- ⚠️ Advisory flows for zero-revenue and low-viability months
- 🎨 Rich-powered terminal output designed for readability

## ✅ What this tool is

- A planning calculator for monthly scenario analysis
- A Rich-based CLI focused on fast what-if comparisons
- A scoped model for Simples Nacional / Anexo III assumptions used in this repository

## 🚫 What this tool is not

- Not a PGDAS-D filing engine
- Not a replacement for contador review
- Not a full RBT12 simulation across all Simples annexes and municipal realities

## 👥 Who this is for

- Founder-operators and solo administrators of ME/EPP entities (Ltda/SLU)
- Service-exporting companies planning Fator R and take-home outcomes
- Users comfortable running terminal workflows

## 📌 Scope assumptions encoded in code

- Simples Nacional planning focus with Anexo III assumptions
- Fator R target fixed at 28%
- Effective DAS rate fixed at 3.054% for Bracket 1 planning scenarios
- Federal minimum wage floor for Pró-labore
- IRPF 2026 table, deductions, and reducer logic
- Advisory reminders for SC / Florianópolis zero-revenue compliance context

See source constants in `main.py` and regulatory notes in `docs/`.

## 🚀 Quick start

```bash
git clone https://github.com/MAlkabbani/RCal.git
cd RCal
./rcal
```

The `./rcal` launcher automatically:

- Finds Python 3
- Creates `.venv` if missing
- Installs runtime dependencies from `requirements.txt`
- Runs `main.py`

## 🛠️ Manual setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

## 💻 CLI usage flow

At runtime, RCal prompts for:

1. Current month/year (`MM/YYYY`)
2. Monthly revenue in USD (zero is allowed and triggers advisory paths)
3. USD→BRL exchange rate
4. Optional IRPF deductions (dependents, PGBL, alimony)

After each calculation:

- `[1]` Change all inputs
- `[2]` Change only revenue
- `[3]` Change only exchange rate
- `[4]` Clear saved memory (`~/.rcal_state.json`)

## 🧪 Realistic scenarios to validate

- Standard exporter case (`883 USD`, `5.23` rate)
- Higher revenue case with Bracket 1 warning (`5000 USD`, `5.75` rate)
- Zero-revenue advisory path (`0 USD`)
- Low-revenue negative dividends path

## 📐 Calculation model summary

1. Convert USD revenue to BRL
2. Compute Fator R minimum (`28%`)
3. Set ideal Pró-labore as `max(Fator R minimum, legal minimum wage)`
4. Compute INSS (with ceiling), DAS estimate, IRPF taxable base
5. Compute IRPF 2026 with deduction model and reducer
6. Compute dividends and net take-home

## 🗂️ Project layout

```text
RCal/
├── rcal
├── main.py
├── test_main.py
├── qa.sh
├── benchmark.py
├── backup_workspace.py
├── requirements.txt
├── pyproject.toml
├── CHANGELOG.md
└── docs/
    ├── AI_REFERENCE_DOC.md
    ├── COMPLIANCE_AUDIT.md
    └── COMPLIANCE_ZERO_REVENUE.md
```

## ✅ Development and QA

Install development tooling:

```bash
source .venv/bin/activate
pip install -r requirements-dev.txt
```

Full local QA pipeline:

```bash
source .venv/bin/activate
bash qa.sh
```

`qa.sh` runs formatting, linting, typing, tests with coverage, and benchmark.

## 📚 Documentation map

- `docs/AI_REFERENCE_DOC.md`: tax logic and invariants
- `docs/COMPLIANCE_AUDIT.md`: compliance boundaries and review notes
- `docs/COMPLIANCE_ZERO_REVENUE.md`: low/zero revenue legal advisory context

## ⚠️ Limitations

- DAS is estimated with a fixed effective rate intended for planning
- Official filing outcomes still depend on rolling revenue history and payroll history
- Export exemption applicability is fact-dependent and must be verified professionally
- Municipal obligations are surfaced as reminders, not fully computed tax modules

## ⚖️ Disclaimer

This tool provides planning estimates only. Always confirm filing decisions with a qualified Brazilian accountant (contador), especially for PGDAS-D, DAS, and municipal obligations.

## 🤝 Contributing

See `CONTRIBUTING.md` for contribution workflow and quality expectations.

## 📄 License

Licensed under MIT. See `LICENSE`.
