---
module: internal/pricing
updated: 2026-10-08
anchors:
  internal/pricing/pricing.go: 82764fff8aaa
  internal/pricing/tax.go: 92a5fccf960c
  internal/pricing/coupon.go: 10f08c20c0f7
  internal/pricing/discount.go: 64bfce943f69
---
Owns order quotes: `Engine.Quote` returns subtotal, discount, tax and total.

## Invariants
- Tax is computed and rounded per line, then summed (`perLineTax`); rounding goes through `money.Money.Percent`.
- Percent coupons (`Coupon.PercentBP`) reduce each line's taxable amount before tax (`applyPercent`).
- Fixed coupons (`Coupon.Fixed`) are subtracted from the total after tax is computed, in `Engine.Quote`.
- A negative total is clamped to zero.
- Coupon codes are matched case-insensitively and trimmed (`CouponBook.Find`); an empty code means no coupon, an unknown one returns `ErrUnknownCoupon`.
- The quote currency is taken from the first line.

## History
- `c25ddd9` hotfix: tax was rounded once on the order total; it is now rounded per line, with a regression test in `internal/pricing/pricing_test.go`.
- `9e7355c` made coupon codes case-insensitive.

## Tests
`internal/pricing/pricing_test.go`.
