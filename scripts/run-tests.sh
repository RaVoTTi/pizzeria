#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

COMPOSE="${COMPOSE:-docker compose}"
DB="${DB:-elgordo}"
MODULE="${MODULE:-pos_kitchen_screen_odoo}"

usage() {
    cat <<EOF
Usage: $(basename "$0") [TARGET]

Targets:
  unit          Run Odoo Python unit tests (TransactionCase)
  shell         Run Odoo shell-based integration tests
  e2e           Run Playwright E2E browser tests
  all           Run unit + shell + e2e
  kitchen       Run kitchen-specific unit tests only
  kitchen-shell Run kitchen shell integration test only
  lint          Run basic Python lint on custom addons

Environment:
  DB            Odoo database name (default: $DB)
  MODULE        Odoo module to test (default: $MODULE)
  COMPOSE       Docker compose command (default: docker compose)

Examples:
  $(basename "$0") unit
  $(basename "$0") kitchen
  $(basename "$0") e2e
  $(basename "$0") all
EOF
}

run_unit() {
    echo "=========================================="
    echo "  ODOO UNIT TESTS — $MODULE"
    echo "=========================================="
    echo ""
    echo "[1/1] Running TransactionCase tests..."
    $COMPOSE run --rm web python3 -m odoo \
        -d "$DB" \
        --test-enable \
        --test-tags="/$MODULE" \
        -u "$MODULE" \
        --stop-after-init \
        --log-level=test \
        --http-interface=127.0.0.1 \
        --workers=0 \
        -p 18069
    echo ""
    echo "=========================================="
    echo "  UNIT TESTS COMPLETE"
    echo "=========================================="
}

run_kitchen() {
    echo "=========================================="
    echo "  KITCHEN TICKET UNIT TESTS"
    echo "=========================================="
    $COMPOSE run --rm web python3 -m odoo \
        -d "$DB" \
        --test-enable \
        --test-tags="/$MODULE:TestKitchenTicketWorkflow" \
        -u "$MODULE" \
        --stop-after-init \
        --log-level=test \
        --http-interface=127.0.0.1 \
        --workers=0 \
        -p 18069
}

run_shell() {
    echo "=========================================="
    echo "  ODOO SHELL INTEGRATION TESTS"
    echo "=========================================="
    echo ""

    for test_file in tests/test_kitchen_workflow.py tests/test_kitchen_failure_modes.py tests/test_pos_inventory_deduction.py; do
        if [ -f "$test_file" ]; then
            echo "[shell] Running $(basename "$test_file")..."
            $COMPOSE run --rm web odoo shell \
                -c /etc/odoo/odoo.conf \
                -d "$DB" \
                --noprompt \
                < "$test_file"
            echo ""
        else
            echo "[shell] SKIP: $test_file not found"
        fi
    done

    echo "=========================================="
    echo "  SHELL TESTS COMPLETE"
    echo "=========================================="
}

run_kitchen_shell() {
    echo "=========================================="
    echo "  KITCHEN SHELL INTEGRATION TEST"
    echo "=========================================="
    $COMPOSE run --rm web odoo shell \
        -c /etc/odoo/odoo.conf \
        -d "$DB" \
        --noprompt \
        < tests/test_kitchen_workflow.py
}

run_e2e() {
    echo "=========================================="
    echo "  PLAYWRIGHT E2E TESTS"
    echo "=========================================="
    echo ""

    if ! command -v npx &>/dev/null; then
        echo "ERROR: npx not found. Install Node.js first."
        echo "  https://nodejs.org/"
        exit 1
    fi

    if [ ! -d "e2e/node_modules" ]; then
        echo "[1/2] Installing E2E dependencies..."
        (cd e2e && npm install)
    else
        echo "[1/2] Dependencies already installed."
    fi

    echo "[2/2] Running Playwright tests..."
    (cd e2e && npx playwright test --reporter=list)

    echo ""
    echo "=========================================="
    echo "  E2E TESTS COMPLETE"
    echo "=========================================="
}

run_lint() {
    echo "=========================================="
    echo "  PYTHON LINT — custom_addons"
    echo "=========================================="
    if command -v ruff &>/dev/null; then
        ruff check custom_addons/
    elif command -v flake8 &>/dev/null; then
        flake8 custom_addons/ --max-line-length=120
    else
        echo "No linter found (install ruff or flake8)."
        echo "Falling back to Python syntax check..."
        find custom_addons/ -name "*.py" -exec python3 -c "
import ast, sys
for f in sys.argv[1:]:
    try:
        ast.parse(open(f).read())
    except SyntaxError as e:
        print(f'SYNTAX ERROR: {f}: {e}')
" {} +
        echo "Syntax check complete."
    fi
}

case "${1:-}" in
    unit)     run_unit ;;
    kitchen)  run_kitchen ;;
    shell)    run_shell ;;
    kitchen-shell) run_kitchen_shell ;;
    e2e)      run_e2e ;;
    lint)     run_lint ;;
    all)
        run_unit
        echo ""
        run_shell
        echo ""
        run_e2e
        ;;
    *)
        usage
        exit 1
        ;;
esac