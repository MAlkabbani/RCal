# 🧮 RCal — Simples Nacional Planning CLI

```text
  ██████╗   ██████╗  █████╗  ██╗
  ██╔══██╗ ██╔════╝ ██╔══██╗ ██║
  ██████╔╝ ██║      ███████║ ██║
  ██╔══██╗ ██║      ██╔══██║ ██║
  ██║  ██║ ╚██████╗ ██║  ██║ ███████╗
  ╚═╝  ╚═╝  ╚═════╝ ╚═╝  ╚═╝ ╚══════╝
```

RCal is a standalone Python terminal calculator for Brazilian micro and small businesses under Simples Nacional, focused on founder-operated Ltda/SLU service exporters using Fator R planning.

It helps estimate monthly Pró-labore, INSS, IRPF, DAS, dividends, and net take-home under the repository's current assumptions.

## ⚡ Quick Attraction

- 🚀 One command to run: `./rcal`
- 🎯 Built for fast what-if comparisons across revenue and exchange-rate changes
- 🧾 Clear breakdown of Pró-labore, INSS, IRPF, DAS, dividends, and net take-home
- 💾 Remembers your last inputs for faster monthly planning

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

## 👀 CLI Preview (partial view)

```text
🗑️ Memory cleared! Saved state wiped.

📅 Current Month/Year (MM/YYYY) (04/2026): 04/2026
💵 Monthly Revenue in USD (0 = zero-revenue advisory): 883
💱 USD → BRL Exchange Rate: 5.237

📝 Apply IRPF deductions? (dependents, PGBL, alimony) [y/n]: n

Month: 04/2026    Revenue: US$ 883.00    Rate: R$ 5.237

📊 Tax Breakdown
- Gross Revenue (BRL):          R$ 4.624,27
- Fator R Minimum (28%):        R$ 1.294,80
- ✨ Ideal Pró-labore:          R$ 1.621,00
- INSS (11%):                 - R$ 178,31
- DAS (Simples Nacional):     - R$ 141,23
- IRPF Taxable Base:            R$ 1.013,80
- IRPF Deduction Mode:          Simplified (R$ 607,20)
- IRPF Status:                  ✅ Tax Free

💰 Your Bottom Line
- 📦 Tax-Free Dividends:         R$ 2.862,05
- 🏠 Net Take-Home:              R$ 4.304,74
- 📉 Effective Tax Burden:       6.9%
```

This is a text preview. In the real terminal app, the output is colorized with Rich panels, borders, and a distribution bar.

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
