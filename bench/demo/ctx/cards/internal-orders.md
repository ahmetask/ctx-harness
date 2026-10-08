---
module: internal/orders
updated: 2026-10-08
anchors:
  internal/orders/events.go: 6e8308f1fe3e
  internal/orders/order.go: 5ec059e9dfa0
  internal/orders/service.go: 349c3d4d636c
  internal/orders/state.go: 68bd1f5e2b63
  internal/orders/validate.go: 3cdc693e6b3f
---
Owns the order lifecycle: `Service.Place`, `Pay`, `Ship`, `Deliver`, `Cancel` over an in-memory `storage.Memory[Order]`.

## Invariants
- Allowed moves live only in the `transitions` map in `internal/orders/state.go` (pending -> paid|cancelled, paid -> shipped, shipped -> delivered); `CanTransition` checks them and `State.Terminal` derives from them.
- Every state change goes through `Service.transition`, which checks the move, sends the customer an email via `Notifier.Notify` with the new state name as the event, saves, then writes an audit record. A state with no template in `internal/notify/templates.go` makes the transition fail.
- `Place` validates input in `validateItems` (max 50 lines, qty 1..100); every rejection wraps `ErrInvalid`.
- `Place` reserves stock via `Inventory.Reserve` with the order ID as the hold key; `Pay` commits it on success and releases it on a failed charge before cancelling.
- `Pay` charges under `payments.IdempotencyKey(o.ID)`, so retries of one order map to one provider charge.

## History
- `d86e61b` fix: a failed payment left stock reserved; `Pay` now calls `Inventory.Release`.
- `6b863e4` fix: double charge when a retry built a new idempotency key; the key moved to `payments.IdempotencyKey`.
- Adding a state has touched `state.go`, `service.go`, `internal/notify/templates.go`, `internal/reports/sales.go` and `internal/httpapi` together (`b0a49f5`, `835ff1a`). `notify` and `reports` are not linked by imports from here.

## Tests
`internal/orders/orders_test.go`; HTTP-level coverage in `internal/httpapi/httpapi_test.go`.
