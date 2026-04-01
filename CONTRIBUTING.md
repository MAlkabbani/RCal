# Contributing to RCal

Thank you for contributing to RCal.

## Project scope

Contributions should stay aligned with the repository's current scope:

- Python CLI
- Simples Nacional planning assumptions represented in `main.py`
- Founder/operator scenario support for service-exporting Ltda/SLU contexts

## Local setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install black flake8 pylint mypy pytest pytest-cov pytest-benchmark
```

## Quality gate

Before opening a pull request:

```bash
source .venv/bin/activate
bash qa.sh
```

Your PR should pass all checks in `qa.sh`:

- Black formatting
- Flake8 linting
- Pylint linting
- Mypy typing
- Pytest suite with configured coverage threshold
- Benchmark command execution

## Pull request guidelines

- Keep changes focused and small when possible
- Update docs when behavior changes
- Add or update tests for every behavior change
- Preserve legal/compliance disclaimer language where applicable
- Avoid expanding product scope beyond CLI planning use cases without discussion

## Documentation expectations

When modifying calculations or assumptions, update:

- `README.md`
- `docs/AI_REFERENCE_DOC.md`
- Any relevant compliance note under `docs/`

## Issues

If filing a bug, include:

- Inputs used (month, revenue, exchange rate, deductions)
- Expected behavior
- Actual behavior
- Terminal output or traceback
