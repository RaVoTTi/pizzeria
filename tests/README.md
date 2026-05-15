# Tests — Pizzeria El Gordo

## Test Layers

| Layer | Tool | When to Run | What it Covers |
|-------|------|-------------|----------------|
| **Unit (Python)** | `odoo.tests` + `@tagged` | Every code change | Ticket model, state machine, delta creation, payment status |
| **Integration (Shell)** | `odoo shell` scripts | Before releases | Full workflow with real products, ESC/POS formatting, failure modes |
| **E2E (Browser)** | Playwright | Before releases, CI | KDS UI rendering, tab switching, ticket card interaction, JSON-RPC model validation |

## Quick Start

Run via the test runner script:

```bash
# All layers
./scripts/run-tests.sh all

# Individual layers
./scripts/run-tests.sh unit          # Odoo TransactionCase tests
./scripts/run-tests.sh kitchen       # Kitchen ticket unit tests only
./scripts/run-tests.sh shell         # odoo shell integration scripts
./scripts/run-tests.sh kitchen-shell # Kitchen workflow shell test only
./scripts/run-tests.sh e2e           # Playwright browser tests
./scripts/run-tests.sh lint          # Python syntax/lint check
```

## 1. Unit Tests (Python / TransactionCase)

Located in `custom_addons/pos_kitchen_screen_odoo/tests/`.

Run with:
```bash
./scripts/run-tests.sh unit
# or directly:
docker compose run --rm web python3 -m odoo \
    -d elgordo --test-enable --test-tags="/pos_kitchen_screen_odoo" \
    -u pos_kitchen_screen_odoo --stop-after-init \
    --log-level=test --http-interface=127.0.0.1 --workers=0 -p 18069
```

Test classes use `@tagged('post_install', '-at_install')` for Odoo 19 discovery.

### What's tested:
- Ticket auto-creation on `pos.order.create()`
- Payment status update on `action_pos_order_paid()`
- No ticket without kitchen screen
- No ticket with non-matching POS category
- Ticket idempotency (no duplicates)
- Line state cycle (pending → cooking → ready → cancelled → pending)
- Ticket state progression (pending → cooking → ready → delivered)
- Delta additions and cancellations with batch letters
- `get_details()` filtering (cancelled/delivered excluded)
- Immutability of the "new" ticket type

## 2. Integration Tests (Odoo Shell)

Located in `tests/`. Run via the Odoo shell with live database access.

```bash
# Kitchen ticket full workflow
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo \
    --noprompt < tests/test_kitchen_workflow.py

# Failure modes (printers, race conditions, etc.)
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo \
    --noprompt < tests/test_kitchen_failure_modes.py

# Inventory deduction (phantom BoM)
docker compose run --rm web odoo shell -c /etc/odoo/odoo.conf -d elgordo \
    --noprompt < tests/test_pos_inventory_deduction.py
```

These tests use `env.cr.rollback()` at the end to avoid polluting the database.

### What's tested:
- Kitchen ticket complete lifecycle (creation → cooking → ready → delivered)
- ESC/POS ticket formatting
- Delta ticket creation (additions + cancellations)
- Batch letter sequencing (A → B → C → D)
- Note preservation in ticket lines
- Zombie printer fallback
- Race condition idempotency
- Partial voids

## 3. E2E Tests (Playwright)

Located in `e2e/`. Uses Playwright to drive a real browser against the running Odoo instance.

```bash
# First-time setup
cd e2e && npm install && cd ..

# Run all E2E tests
./scripts/run-tests.sh e2e

# Or directly
cd e2e && npx playwright test --reporter=list

# Run specific test tags
cd e2e && npx playwright test --grep @kds
cd e2e && npx playwright test --grep @pos
cd e2e && npx playwright test --grep @smoke

# Debug mode (opens browser)
cd e2e && npx playwright test --debug
```

### Configuration

Set environment variables for non-default targets:

```bash
export ODOO_URL=http://elgordo.local    # or http://192.168.1.100
export ODOO_DB=elgordo
export ODOO_USER=admin
export ODOO_PASS=your-password
```

### E2E test files:

| File | What it tests |
|------|--------------|
| `specs/login.smoke.spec.js` | Login works, kitchen menu exists |
| `specs/kds.spec.js` | KDS renders, tabs switch, cards display, auto-refresh |
| `specs/kds-advance.spec.js` | Ticket state transitions, line clicks, cancel |
| `specs/kds-model.spec.js` | JSON-RPC model validation, `get_details` endpoint |

### View test results:

```bash
cd e2e && npx playwright show-report
```

## 4. Test Products

Unit and shell tests use **real products** from your CSV files (Mozzarella). This ensures tests match production behavior.

## 5. CI/CD Integration

For automated pipelines:

```bash
# Fast: unit tests only
./scripts/run-tests.sh unit

# Medium: unit + shell
./scripts/run-tests.sh unit && ./scripts/run-tests.sh shell

# Full: all layers
./scripts/run-tests.sh all
```

## Troubleshooting

### "No POS config found"
Run the import pipeline first:
```bash
./scripts/import-data.sh
```

### "0 tests" from Odoo test runner
Ensure test classes have `@tagged('post_install', '-at_install')` and tests are in the module's `tests/__init__.py`.

### Playwright connection refused
Make sure Docker containers are running and accessible:
```bash
docker compose ps
curl -I http://localhost:80/web/login
```

### Port conflict during unit tests
The unit test runner uses port 18069 to avoid conflicting with the running Odoo instance on 8069.