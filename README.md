# 🧮 RCal — Simples Nacional Planning CLI

[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-Support-FFDD00?style=for-the-badge&logo=buy-me-a-coffee&logoColor=black)](https://buymeacoffee.com/webeworx)

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

![RCal Demo](./rcal-demo.gif)

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

See source constants in `src/rcal/main.py` and regulatory notes in `docs/`.

## 🚀 Quick start

```bash
git clone https://github.com/MAlkabbani/RCal.git
cd RCal
./rcal
```

The `./rcal` launcher automatically:

- Finds Python 3
- Creates `.venv` if missing
- Installs runtime dependencies
- Installs the `rcal` package in editable mode
- Runs `rcal` via the installed entry point

## 🛠️ Manual setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
rcal
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
├── rcal                # Shell launcher
├── src/rcal/           # Main package
│   ├── __init__.py
│   └── main.py         # Tax logic and CLI
├── tests/              # Test suite
│   └── test_main.py
├── scripts/            # Dev tools
│   ├── benchmark.py
│   └── backup_workspace.py
├── qa.sh               # Full QA pipeline
├── requirements-dev.txt
├── pyproject.toml      # Modern packaging
├── CHANGELOG.md
└── docs/               # Tax context
```

## ✅ Development and QA

Install development tooling:

```bash
source .venv/bin/activate
pip install -e .
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

## 💖 Support

If you find RCal helpful for your business planning, consider supporting the project!

<a href="https://buymeacoffee.com/webeworx" target="_blank"><img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" style="height: 60px !important;width: 217px !important;" ></a>

## 📄 License

Licensed under MIT. See `LICENSE`.
