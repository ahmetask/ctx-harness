package pricing

import (
	"errors"

	"shopd/internal/money"
)

// ErrEmpty is returned when quoting an order without lines.
var ErrEmpty = errors.New("pricing: no lines")

// Line is one priced order line.
type Line struct {
	SKU  string      `json:"sku"`
	Qty  int64       `json:"qty"`
	Unit money.Money `json:"unit"`
}

// Amount is the line total before discounts and tax.
func (l Line) Amount() money.Money { return l.Unit.MulInt(l.Qty) }

// Quote is the price breakdown of an order.
type Quote struct {
	Subtotal money.Money `json:"subtotal"`
	Discount money.Money `json:"discount"`
	Tax      money.Money `json:"tax"`
	Total    money.Money `json:"total"`
}

// Engine prices orders.
type Engine struct {
	TaxBP   int64 // sales tax in basis points, 2000 = 20%
	Coupons *CouponBook
}

// NewEngine returns an engine with the given tax rate and coupons.
func NewEngine(taxBP int64, coupons *CouponBook) *Engine {
	return &Engine{TaxBP: taxBP, Coupons: coupons}
}

// Quote prices an order. Discounts reduce the taxable amount, and tax is
// computed and rounded per line.
func (e *Engine) Quote(lines []Line, couponCode string) (Quote, error) {
	if len(lines) == 0 {
		return Quote{}, ErrEmpty
	}
	cur := lines[0].Unit.Currency
	subtotal := money.Zero(cur)
	amounts := make([]money.Money, len(lines))
	for i, l := range lines {
		amounts[i] = l.Amount()
		subtotal = subtotal.Add(amounts[i])
	}
	c, err := e.Coupons.Find(couponCode)
	if err != nil {
		return Quote{}, err
	}
	taxable, discount := applyPercent(amounts, c.PercentBP)
	tax := perLineTax(taxable, e.TaxBP)
	total := subtotal.Sub(discount).Add(tax)
	if c.Fixed.Amount > 0 {
		discount = discount.Add(c.Fixed)
		total = total.Sub(c.Fixed)
	}
	if total.IsNegative() {
		total = money.Zero(cur)
	}
	return Quote{Subtotal: subtotal, Discount: discount, Tax: tax, Total: total}, nil
}
