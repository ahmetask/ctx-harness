---
module: internal/money
updated: 2026-10-08
anchors:
  internal/money/money.go: 8394a745a273
  internal/money/currency.go: f1d95f994832
  internal/money/format.go: bab012af69b7
---
Owns amounts: `Money` is an `int64` in the currency's minor unit plus a `Currency`.

## Invariants
- Mixing currencies in `Add`, `Sub` or `Less` panics (`mustMatch`); it is treated as a programming error.
- All amount rounding goes through `Money.Percent` (basis points, half away from zero via `roundDiv`).
- Supported currencies are the `currencies` map in `internal/money/currency.go`; `ParseCurrency` rejects anything else.
- `Format` and `ParseAmount` assume two minor-unit digits (`/100`, at most 2 decimals) rather than reading `Currency.Decimals`.

## Tests
`internal/money/money_test.go`. Every other module depends on this one, so a change here reaches all of them.
