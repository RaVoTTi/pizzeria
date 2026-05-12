# Recommended Modules for Pizzeria El Gordo

## Essential (install immediately)

| Module | Purpose |
|--------|---------|
| `pos_preparation_display` | Kitchen display — shows orders on kitchen tablet |
| `pos_discount` | Apply discounts at POS (happy hour, promos) |
| `pos_loyalty` | Customer loyalty/rewards program (free pizza after X orders) |
| `purchase` | Purchase orders to suppliers (flour, cheese, beer kegs) |
| `product_expiry` | Track ingredient expiration dates (food safety) |
| `l10n_ar` | Argentine localization — taxes, AFIP, invoice formats |
| `l10n_ar_pos` | Argentine POS tax handling (IVA, IIBB on receipts) |
| `l10n_ar_stock` | Argentine stock localization |

## Recommended (install later)

| Module | Purpose |
|--------|---------|
| `pos_hr` | Employee access control at POS (cashier vs manager roles) |
| `pos_hr_restaurant` | Waiter/table assignment per employee |
| `pos_sale` | Link POS orders to sales orders (useful for delivery tracking) |
| `sale_management` | Quotations and sales orders for catering/large orders |
| `contacts` | Customer and supplier contact management |
| `account_debit_note` | Handle refunds and credit notes |
| `product_matrix` | Product variants grid (useful if offering pizza sizes as variants) |
| `pos_restaurant_loyalty` | Restaurant-specific loyalty integration |

## Not Needed

| Module | Why Not |
|--------|---------|
| `pos_mercado_pago` | Skip for now — causes validation errors without real credentials |
| `pos_adyen` / `pos_stripe` / etc. | Non-Argentine payment providers |
| `website` / `website_sale` | No online store needed (offline-first restaurant) |
| `crm` | Overkill for a single pizzeria |
| `project` / `hr` / `fleet` | Not relevant to restaurant operations |
| `repair` | Not applicable |
| `delivery` | Could be useful later, but delivery products already exist in POS |
| All `l10n_*` except AR | Non-Argentine localizations |