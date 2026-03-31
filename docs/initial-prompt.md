> **Role:** You are an expert Python developer and Brazilian tax logic specialist.
> 
> **Task:** Build a standalone, interactive Python CLI application that calculates the optimal "Pró-labore" (administrator salary) and taxes for a Brazilian tech company operating under the Simples Nacional tax regime (Anexo III, Exporting Services, subject to the "Fator R" rule).
> 
> **Environment:** The app must be compatible with macOS (M1/Apple Silicon) and run directly in the terminal.
> 
> **Business Logic & Formulas:**
> The calculator must process the following variables and math. 
> *Constants for 2026:* > * `LEGAL_MINIMUM_WAGE` = 1621.00
> * `DAS_TAX_RATE` = 0.03054 (3.054%)
> * `INSS_TAX_RATE` = 0.11 (11%)
> * `FATOR_R_TARGET` = 0.28 (28%)
> * `IRPF_LIMIT` = 5000.00
> 
> *Calculations:*
> 1.  **Gross Revenue (BRL):** `Revenue (USD)` * `Exchange Rate (BRL)`
> 2.  **Fator R Minimum:** `Gross Revenue (BRL)` * `FATOR_R_TARGET`
> 3.  **Ideal Pró-labore:** Maximum value between `Fator R Minimum` and `LEGAL_MINIMUM_WAGE`.
> 4.  **INSS Tax:** `Ideal Pró-labore` * `INSS_TAX_RATE`
> 5.  **Estimated DAS Tax:** `Gross Revenue (BRL)` * `DAS_TAX_RATE`
> 6.  **IRPF Status:** If `Ideal Pró-labore` > `IRPF_LIMIT`, trigger a warning string: "⚠️ IRPF Triggered! Pró-labore exceeds R$ 5.000,00. Apply deductions." Otherwise, "✅ Tax Free".
> 7.  **Available Dividends (Tax-Free):** `Gross Revenue (BRL)` - `Ideal Pró-labore` - `Estimated DAS Tax`
> 8.  **Total Net "Take Home":** (`Ideal Pró-labore` - `INSS Tax`) + `Available Dividends`
> 
> **Application Requirements:**
> 1.  **Interactivity:** When run, the script should prompt the user to input:
>     * The Current Month/Year
>     * Revenue in USD (float)
>     * Current USD to BRL Exchange Rate (float)
> 2.  **Output Formatting:** Use the `rich` library to print a beautiful, readable table in the terminal displaying all calculated values formatted as Brazilian Reais (e.g., R$ 1.621,00). 
> 3.  **Code Quality:** Use clear variable names, type hinting, and include comments explaining the Fator R logic so other open-source contributors understand the Brazilian tax context.
> 
> **Deliverables:**
> Please provide:
> 1.  The complete, fully functional Python script (`main.py`).
> 2.  A `requirements.txt` file (including `rich`).
> 3.  A comprehensive `README.md` formatted for GitHub, explaining what the tool does, the Fator R rule, and how a Mac M1 user can install and run it locally.

***
