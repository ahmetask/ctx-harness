package pricing

import (
	"errors"
	"fmt"
	"strings"

	"shopd/internal/money"
)

// ErrUnknownCoupon is returned for codes that are not in the book.
var ErrUnknownCoupon = errors.New("pricing: unknown coupon")

// Coupon is either a percentage (PercentBP) or a fixed amount (Fixed) off.
type Coupon struct {
	Code      string
	PercentBP int64
	Fixed     money.Money
}

// CouponBook holds the active coupons.
type CouponBook struct {
	coupons map[string]Coupon
}

// NewCouponBook returns a book with cs.
func NewCouponBook(cs ...Coupon) *CouponBook {
	b := &CouponBook{coupons: map[string]Coupon{}}
	for _, c := range cs {
		b.coupons[strings.ToUpper(c.Code)] = c
	}
	return b
}

// Find returns the coupon for code. An empty code means no coupon.
func (b *CouponBook) Find(code string) (Coupon, error) {
	code = strings.ToUpper(strings.TrimSpace(code))
	if code == "" {
		return Coupon{}, nil
	}
	c, ok := b.coupons[code]
	if !ok {
		return Coupon{}, fmt.Errorf("%w: %q", ErrUnknownCoupon, code)
	}
	return c, nil
}
