# Repo map  <!-- generated @ d86e61b; keep under 60 lines -->

Stack: go (51). Manifests: go.mod.
Entry points: cmd/shopd/main.go.
Verified commands: `go vet ./...` · `go build ./...` · `go test ./...`.

## Modules (most central first)

| module | purpose | key files | depends on |
|---|---|---|---|
| internal/money | Integer minor-unit amounts per currency; arithmetic, rounding, formatting and parsing | currency.go, format.go, money.go | - |
| internal/orders | Order lifecycle: place, pay, ship, deliver, cancel; owns the state machine | events.go, order.go, service.go | internal/audit, internal/catalog, internal/clock, internal/customers, internal/ids, internal/inventory, internal/notify, internal/payments, internal/pricing, internal/shipping, internal/storage |
| internal/httpapi | JSON HTTP API over catalog and orders; maps domain errors to statuses | errors.go, handlers_catalog.go, handlers_orders.go | internal/catalog, internal/inventory, internal/money, internal/orders, internal/payments |
| internal/pricing | Quotes orders: subtotal, coupons, per-line tax, total | coupon.go, discount.go, pricing.go | internal/money |
| internal/payments | Payment provider client with retries and per-order idempotency keys | client.go, gateway.go, idempotency.go | internal/money |
| internal/catalog | In-memory product store and name/tag search | product.go, search.go, store.go | internal/money |
| internal/notify | Email templates per order state and the notifier that renders them | notifier.go, sender.go, templates.go | - |
| internal/customers | Customer records and contact validation | customer.go, store.go | internal/storage |
| internal/inventory | Stock on hand plus per-order reservations (reserve, release, commit) | reservation.go, stock.go | - |
| internal/app | Wires every service together and seeds demo data | app.go, seed.go | internal/audit, internal/catalog, internal/clock, internal/config, internal/customers, internal/httpapi, internal/ids, internal/inventory, internal/money, internal/notify, internal/orders, internal/payments, internal/pricing |
| internal/shipping | Carrier choice by weight, shipping rates, tracking numbers | carrier.go, rates.go | internal/money |
| internal/storage | Generic concurrency-safe in-memory table | memory.go | - |

## Change together (from git history)
- internal/orders/state.go <-> internal/reports/sales.go (2 commits)
- internal/orders/service.go <-> internal/reports/sales.go (2 commits)
- internal/notify/templates.go <-> internal/reports/sales.go (2 commits, no import link)
- internal/notify/templates.go <-> internal/orders/state.go (2 commits, no import link)
- internal/notify/templates.go <-> internal/orders/service.go (2 commits)

## Fragile files (fix/revert history)
- internal/orders/service.go: fix: release reserved stock when a payment fails
- internal/pricing/tax.go: hotfix: round tax per line, not on the order total
- internal/pricing/pricing_test.go: hotfix: round tax per line, not on the order total
- internal/payments/idempotency.go: fix: double charge when a payment retry built a new idempotency key

## Finding things
- Ask the index first: `ctxh q find|rdeps|impact|cochange|tests|owner|module <arg>`
- Module cards: `.ctx/cards/<module-with-dashes>.md` (open only for the module you touch)
- Gotchas learned from past tasks: `.ctx/learned.md`
