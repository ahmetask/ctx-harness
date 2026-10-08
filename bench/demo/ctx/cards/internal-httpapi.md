---
module: internal/httpapi
updated: 2026-10-08
anchors:
  internal/httpapi/server.go: 763fa1c70165
  internal/httpapi/errors.go: 213407586271
  internal/httpapi/handlers_catalog.go: 97820868f1e6
  internal/httpapi/handlers_orders.go: 25f797ebe192
  internal/httpapi/json.go: cea951a39211
  internal/httpapi/middleware.go: ab58bede1cfb
---
Owns the JSON HTTP API: routes are registered in `New` in `internal/httpapi/server.go`.

## Invariants
- Error statuses come only from `writeError` in `internal/httpapi/errors.go`: `orders.ErrInvalid` -> 400, not found -> 404, `orders.ErrInvalidTransition` and `inventory.ErrInsufficient` -> 409, `payments.ErrDeclined` -> 402, anything else -> 500.
- Order actions are `POST /orders/{id}/<action>` routes, one per lifecycle step.
- Product responses carry the price in minor units plus a formatted `display` string (`view` in `handlers_catalog.go`).
- `withRequestID` echoes or assigns `X-Request-ID` on every response.

## Tests
`internal/httpapi/httpapi_test.go`, which drives the server built by `internal/app`.
