# Repo map  <!-- generated @ d86e61b; keep under 60 lines -->

Stack: go (51). Manifests: go.mod.
Entry points: cmd/shopd/main.go.
Verified commands: `go vet ./...` · `go build ./...` · `go test ./...`.

## Modules (most central first)

| module | purpose | key files | depends on |
|---|---|---|---|
| internal/money | Integer minor-unit amounts per currency; arithmetic, rounding, formatting and parsing | money.go, currency.go, format.go | - |
| internal/orders | Order lifecycle: place, pay, ship, deliver, cancel; owns the state machine | service.go, state.go, order.go | internal/pricing, internal/payments, internal/catalog, internal/notify +7 more |
| internal/httpapi | JSON HTTP API over catalog and orders; maps domain errors to statuses | server.go, handlers_orders.go, middleware.go | internal/money, internal/orders, internal/payments, internal/catalog +1 more |
| internal/pricing | Quotes orders: subtotal, coupons, per-line tax, total | tax.go, coupon.go, pricing.go | internal/money |
| internal/payments | Payment provider client with retries and per-order idempotency keys | client.go, idempotency.go, gateway.go | internal/money |
| internal/catalog | In-memory product store and name/tag search | search.go, store.go, product.go | internal/money |
| internal/notify | Email templates per order state and the notifier that renders them | templates.go, notifier.go, sender.go | - |
| internal/customers | Customer records and contact validation | store.go, customer.go | internal/storage |
| internal/inventory | Stock on hand plus per-order reservations (reserve, release, commit) | reservation.go, stock.go | - |
| internal/app | Wires every service together and seeds demo data | app.go, seed.go | internal/money, internal/orders, internal/httpapi, internal/pricing +9 more |
| internal/shipping | Carrier choice by weight, shipping rates, tracking numbers | carrier.go, rates.go | internal/money |
| internal/storage | Generic concurrency-safe in-memory table | memory.go | - |

## Fragile files (fix/revert history)
- internal/orders/service.go: fix: release reserved stock when a payment fails (rule: .ctx/cards/internal-orders.md)
- internal/pricing/tax.go: hotfix: round tax per line, not on the order total (rule: .ctx/cards/internal-pricing.md)
- internal/pricing/pricing_test.go: hotfix: round tax per line, not on the order total (rule: .ctx/cards/internal-pricing.md)
- internal/payments/idempotency.go: fix: double charge when a payment retry built a new idempotency key (rule: .ctx/cards/internal-payments.md)

## Finding things
- Ask the index first: `ctxh q find|rdeps|impact|cochange|tests|owner|module <arg>`
- Module cards: `.ctx/cards/<module-with-dashes>.md` (open only for the module you touch)
- Gotchas learned from past tasks: `.ctx/learned.md`
