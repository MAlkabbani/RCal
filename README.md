# 🧮 RCal — Brazilian Simples Nacional Tax Calculator

**RCal** is a standalone, interactive Python CLI tool that calculates the optimal **Pró-labore** (administrator salary), taxes, and dividends for a Brazilian tech company operating under the **Simples Nacional** tax regime (**Anexo III**), specifically for companies that export services.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-green)
![Platform](https://img.shields.io/badge/Platform-macOS%20M1%2FM2%2FM3-000000?logo=apple)
![Rich](https://img.shields.io/badge/Rich-13.0+-00b4d8?logo=python&logoColor=white)

---

## 📖 What Is the "Fator R" Rule?

The **Fator R** (Factor R) is a ratio defined by Brazilian tax legislation ([Lei Complementar 123/2006](http://www.planalto.gov.br/ccivil_03/leis/lcp/lcp123.htm)) that determines which **tax annex** (table of rates) applies to a service company under the Simples Nacional regime.

### The Formula

```
Fator R = Payroll Expenses (last 12 months) / Gross Revenue (last 12 months)
```

### Why It Matters

| Condition | Tax Annex | Effective Starting Rate |
|-----------|-----------|------------------------|
| Fator R **≥ 28%** | **Anexo III** | ~6.0% |
| Fator R **< 28%** | **Anexo V** | ~15.5% |

By ensuring the company's total payroll (primarily the administrator's **Pró-labore**) represents **at least 28% of gross revenue**, the company qualifies for the **significantly lower** Anexo III tax rates.

> **💡 In practice:** For a small tech company with a single administrator, this means setting the Pró-labore to at least 28% of monthly revenue — but never below the federal minimum wage.

---

## ✨ Features

- 🧮 **Automatic Fator R optimization** — calculates the ideal Pró-labore
- 💱 **USD → BRL conversion** — built for service exporters
- 🏛️ **Exact IRPF 2026 calculation** — progressive table + Lei nº 15.270/2025 reducer
- 📝 **Optional deductions** — dependents, PGBL pension, alimony (saved between sessions)
- 🎨 **Premium terminal UI** — branded ASCII header, 3-zone layout, themed colors via [Rich](https://github.com/Textualize/rich)
- 📊 **Visual revenue breakdown** — stacked bar chart showing salary/INSS/IRPF/DAS/dividends split
- 🛡️ **Input validation** — rejects invalid dates, zero/negative numbers with clear error messages
- 🔄 **Multi-scenario loop** — compare different months, revenues, or exchange rates without restarting
- ⚠️ **Smart warnings** — Bracket 1 ceiling warning, negative dividends danger panel
- 📦 **Dividend calculation** — shows tax-free dividend distribution
- 🏠 **Net take-home** — total after all deductions (INSS + IRPF) with effective tax burden %

---

## 🔢 Tax Constants (2026)

| Constant | Value | Description |
|----------|-------|-------------|
| `LEGAL_MINIMUM_WAGE` | R$ 1.621,00 | Federal minimum wage |
| `DAS_TAX_RATE` | 3,054% | Simples Nacional (Anexo III, 1st bracket) |
| `INSS_TAX_RATE` | 11% | Social security contribution |
| `FATOR_R_TARGET` | 28% | Minimum payroll-to-revenue ratio |
| `IRPF_TABLE_2026` | 5 brackets | Progressive table: Isento / 7.5% / 15% / 22.5% / 27.5% |
| `IRPF_DEPENDENT_DEDUCTION` | R$ 189,59 | Monthly IRPF deduction per dependent |
| `IRPF_REDUCER_*` | Lei 15.270/2025 | Full exemption ≤ R$ 5k, phase-out to R$ 7.35k |

---

## 🚀 Quick Start (macOS)

### 1. Clone the Repository

```bash
git clone https://github.com/MAlkabbani/RCal.git
cd RCal
```

### 2. Run (One Command)

```bash
./rcal
```

That's it! The `rcal` launcher automatically:
- Finds your Python 3 installation
- Creates a virtual environment (first run only)
- Installs dependencies (first run only)
- Launches the calculator

> **💡 First run** takes ~5 seconds for setup. Subsequent runs launch instantly.

### Alternative: Manual Setup

If you prefer to manage the environment yourself:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 main.py
```

### Run Tests

```bash
source .venv/bin/activate
python3 -m unittest test_main -v
```

---

## 💻 Usage Example

When you run the tool, it will interactively prompt you for:

1. **Current Month/Year** — defaults to the current month (e.g., `03/2026`)
2. **Monthly Revenue in USD** — e.g., `5000`
3. **USD → BRL Exchange Rate** — e.g., `5.75`

### Sample Output

```
  ██████╗   ██████╗  █████╗  ██╗
  ██╔══██╗ ██╔════╝ ██╔══██╗ ██║
  ██████╔╝ ██║      ███████║ ██║
  ██╔══██╗ ██║      ██╔══██║ ██║
  ██║  ██║ ╚██████╗ ██║  ██║ ███████╗
  ╚═╝  ╚═╝  ╚═════╝ ╚═╝  ╚═╝ ╚══════╝

          Simples Nacional Tax Calculator
    Anexo III  ·  Fator R  ·  Export Exemptions

────────────────────────────────────────────────

📅 Current Month/Year (MM/YYYY) (03/2026): 03/2026
💵 Monthly Revenue in USD: 5000
💱 USD → BRL Exchange Rate: 5.75

📝 Apply IRPF deductions? (dependents, PGBL, alimony) [y/N]: n

  ╭─── 📅 Month ───╮ ╭──── 💵 Revenue ────╮ ╭─── 💱 Rate ────╮
  │    03/2026     │ │    US$ 5,000.00    │ │   R$ 5.7500    │
  ╰────────────────╯ ╰────────────────────╯ ╰────────────────╯

  ╭──────────────── 📊 Tax Breakdown ─────────────────╮
  │ ┌──────────────────────┬──────────────────────────┐│
  │ │ Gross Revenue (BRL)  │              R$ 28.750,00 ││
  │ │ Fator R Min (28%)    │               R$ 8.050,00 ││
  │ │ ✨ Ideal Pró-labore  │               R$ 8.050,00 ││
  │ │ INSS (11%)           │              - R$ 885,50  ││
  │ │ DAS (Simples)        │              - R$ 878,02  ││
  │ │ IRPF Taxable Base    │               R$ 7.164,50 ││
  │ │ IRPF (Lei 15.270)    │            - R$ 1.036,80  ││
  │ │ 📈 Bracket Warning   │   ⚠️ Exceeds R$ 180k      ││
  │ └──────────────────────┴──────────────────────────┘│
  ╰────────────────────────────────────────────────────╯

  ╭────────────── 💰 Your Bottom Line ──────────────╮
  │  📦 Tax-Free Dividends         R$ 19.821,97     │
  │  🏠 Net Take-Home              R$ 25.949,67     │
  │  📉 Effective Tax Burden              9.7%      │
  │                                                  │
  │  Revenue Distribution                            │
  │  ██████████████████████████████████████████████  │
  │  █ Salary 21%  █ INSS 3%  █ IRPF 4%  █ DAS 3%  │
  │  █ Yours 69%                                     │
  ╰──────────────────────────────────────────────────╯

🔄 Calculate another month? [y/n] (y):
```
*(Actual output includes full colors and theming)*

### Loop Mode

After each calculation, you can:

- **[1] Change all inputs** — re-enter month, revenue, and rate (rate pre-filled)
- **[2] Change only revenue** — keep current month and exchange rate
- **[3] Change only exchange rate** — keep current month and revenue
- **[4] Clear memory** — wipe saved state and start fresh

This makes comparing multiple scenarios effortless.

### 💾 Memory

RCal **remembers your last inputs** between sessions. When you relaunch, your previous month, revenue, exchange rate, and IRPF deduction settings are pre-filled as defaults.

- State is stored in `~/.rcal_state.json` (human-readable JSON)
- Deduction values (dependents, PGBL, alimony) are also persisted
- If you used deductions last time, the prompt defaults to "yes" on next launch
- Use **[4] Clear memory** from the menu to wipe everything
- Or manually delete: `rm ~/.rcal_state.json`

---

## 📐 How the Math Works

Given inputs: **Revenue (USD)** and **Exchange Rate (BRL)**:

| Step | Calculation | Formula |
|------|-------------|---------|
| 1 | Gross Revenue | `Revenue_USD × Exchange_Rate` |
| 2 | Fator R Minimum | `Gross_Revenue × 0.28` |
| 3 | Ideal Pró-labore | `max(Fator_R_Min, 1621.00)` |
| 4 | INSS Tax | `Pró-labore × 0.11` |
| 5 | DAS Tax | `Gross_Revenue × 0.03054` |
| 6 | IRPF Taxable Base | `Pró-labore − INSS − Dependents − PGBL − Alimony` |
| 7 | IRPF Calculation | Progressive table + Lei 15.270/2025 reducer |
| 8 | Dividends | `Gross_Revenue − Pró-labore − DAS` |
| 9 | Net Take-Home | `(Pró-labore − INSS − IRPF) + Dividends` |

---

## 🏗️ Project Structure

```text
RCal/
├── rcal                 # One-command launcher (bash)
├── main.py              # Main application (UI + calculation engine)
├── test_main.py         # Unit tests (92 tests, 13 test classes)
├── requirements.txt     # Python dependencies (rich>=13.0.0)
├── README.md            # This file
├── CHANGELOG.md         # Version history and changes
├── .gitignore           # Git ignore rules
└── docs/
    ├── initial-prompt.md    # Original specification
    ├── AI_REFERENCE_DOC.md  # AI agent tax logic reference
    └── walkthrough.md       # Project walkthrough
```

---

## 🤝 Contributing

Contributions are welcome! The codebase uses:

- **Type hints** throughout for clarity
- **Docstrings** explaining the Brazilian tax context
- **Named constants** with explanatory comments
- **Rich Theme** for consistent, customizable styling
- **Custom Prompt subclasses** for input validation

If you're unfamiliar with Brazilian tax law, the comments in `main.py` provide context for each calculation step.

---

## ⚖️ Disclaimer

This tool provides **estimates for planning purposes only**. Tax calculations depend on many factors including accumulated revenue over the past 12 months, specific municipal taxes (ISS), and individual deductions.

**Always consult a qualified Brazilian accountant (contador) for official tax filings.**

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
