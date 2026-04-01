#!/usr/bin/env bash
set -e

echo "======================================"
echo "    RCal Quality Assurance Script     "
echo "======================================"

source .venv/bin/activate

echo "0. Creating recovery backup..."
python3 scripts/backup_workspace.py --keep 10

echo "1. Formatting with Black..."
black src/rcal tests scripts

echo "2. Linting with flake8..."
flake8 --max-line-length=88 --extend-ignore=E203,E501 src/rcal tests scripts

echo "3. Linting with pylint..."
pylint src/rcal tests scripts

echo "4. Type checking with mypy..."
mypy src/rcal tests scripts

echo "5. Running tests and coverage..."
pytest tests -v

echo "6. Running performance benchmark..."
python3 scripts/benchmark.py --iterations 5000

echo "✅ All QA checks passed successfully."
