#!/usr/bin/env bash
set -e

echo "======================================"
echo "    RCal Quality Assurance Script     "
echo "======================================"

source .venv/bin/activate

echo "1. Formatting with Black..."
black main.py test_main.py

echo "2. Linting with flake8..."
flake8 --max-line-length=88 --extend-ignore=E203,E501 main.py test_main.py

echo "3. Linting with pylint..."
pylint main.py test_main.py

echo "4. Type checking with mypy..."
mypy main.py test_main.py

echo "5. Running tests and coverage..."
pytest test_main.py -v --cov=main --cov-report=term-missing --cov-fail-under=100

echo "✅ All QA checks passed successfully."
