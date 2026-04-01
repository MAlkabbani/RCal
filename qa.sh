#!/usr/bin/env bash
set -e

echo "======================================"
echo "    RCal Quality Assurance Script     "
echo "======================================"

source .venv/bin/activate

echo "0. Creating recovery backup..."
python3 backup_workspace.py --keep 10

echo "1. Formatting with Black..."
black main.py test_main.py benchmark.py backup_workspace.py

echo "2. Linting with flake8..."
flake8 --max-line-length=88 --extend-ignore=E203,E501 main.py test_main.py benchmark.py backup_workspace.py

echo "3. Linting with pylint..."
pylint main.py test_main.py benchmark.py backup_workspace.py

echo "4. Type checking with mypy..."
mypy main.py test_main.py benchmark.py backup_workspace.py

echo "5. Running tests and coverage..."
pytest test_main.py -v

echo "6. Running performance benchmark..."
python3 benchmark.py --iterations 5000

echo "✅ All QA checks passed successfully."
