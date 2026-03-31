# 🚶 Walkthrough - RCal: Brazilian Simples Nacional Tax Calculator

I have built a standalone Python CLI application to calculate the optimal **Pró-labore** and taxes for a Brazilian tech company exporting services under the Simples Nacional (Anexo III) regime and the **Fator R** rule.

## 🚀 Accomplishments

- **Interactive Python CLI**: A user-friendly tool developed using the `rich` library for high-quality terminal output.
- **Fator R Optimization Logic**: Implemented calculations that automatically suggest the minimum administrator salary (Pró-labore) to minimize taxes (ensuring the 28% payroll-to-revenue ratio).
- **Internationalization Ready**: Converts USD to BRL and formats all currency values in the standard Brazilian format (e.g., `R$ 1.621,00`).
- **Complete Documentation**: A comprehensive `README.md` explaining the "Fator R" rule, installation for macOS Silicon (M1/M2/M3), and usage examples.
- **GitHub Ready**: Initialized Git, added a `.gitignore`, committed the codebase, and pushed it to the repository.

## 🛠️ Implementation Details

### 📂 File Structure
- `main.py`: The core application containing the calculation logic and the `rich`-based UI.
- `requirements.txt`: Lists the `rich` dependency.
- `README.md`: Detailed documentation for users and contributors.
- `.gitignore`: Excludes environment files and caches.

### 🧪 Features & Logic
- **Automatic Pró-labore calculation**: Finds the maximum between the legal minimum wage and the 28% "Fator R" threshold.
- **Tax Breakdown**: Calculates DAS (3.054%), INSS (11%), and provides an IRPF warning if the Pró-labore exceeds R$ 5.000,00.
- **Dividends & Take-Home**: Shows the final net value distributed as tax-free dividends.

## 📸 Final Verification

A full test run with a USD revenue of $5,000 and a 5.75 exchange rate was performed:
- **Gross Revenue**: R$ 28.750,00
- **Fator R Minimum**: R$ 8.050,00
- **DAS Tax**: R$ 878,02 (estimated)
- **Total Net Take-Home**: R$ 26.986,47

### 📦 Repository Status
All files have been pushed to: `https://github.com/MAlkabbani/RCal.git`
Branch: `main`

> [!TIP]
> To run the tool locally:
> ```bash
> python3 -m venv .venv && source .venv/bin/activate
> pip install -r requirements.txt
> python main.py
> ```
