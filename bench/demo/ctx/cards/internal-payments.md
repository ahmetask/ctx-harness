---
module: internal/payments
updated: 2026-10-08
anchors:
  internal/payments/client.go: 1646a30b273d
  internal/payments/gateway.go: 8be28013d218
  internal/payments/idempotency.go: 91dcd1846327
  internal/payments/retry.go: 149e1388fb31
---
Owns talking to the payment provider: `Client.Charge` and `Client.Refund` over the `Gateway` interface.

## Invariants
- Double charges are prevented by the provider key, not by local state: `IdempotencyKey` depends on the order ID alone, and the gateway returns the earlier charge for a repeated key (`FakeGateway.Charge`).
- `RetryPolicy.Do` retries only errors wrapping `ErrTransient`; `ErrDeclined` and other errors return at once. `DefaultRetry` is 3 attempts with linear backoff.
- `FakeGateway.Refund` rejects refunds that would exceed the charged amount and unknown charge IDs.
- `FakeGateway.FailNext` and `DeclineNext` let tests inject transient failures and declines.

## History
- `6b863e4` fix: each retry built a new idempotency key, so a retried charge could capture twice; the key moved into `IdempotencyKey` and `Client.Charge` takes it from the caller.

## Tests
`internal/payments/payments_test.go`.
