package pricing

import (
	"errors"
	"testing"

	"shopd/internal/money"
)

func usd(a int64) money.Money { return money.New(a, money.USD) }

func engine() *Engine {
	return NewEngine(2000, NewCouponBook(Coupon{Code: "SAVE10", PercentBP: 1000}))
}

func TestQuoteWithoutCoupon(t *testing.T) {
	q, err := engine().Quote([]Line{{SKU: "A", Qty: 2, Unit: usd(2500)}}, "")
	if err != nil {
		t.Fatal(err)
	}
	if q.Subtotal.Amount != 5000 || q.Tax.Amount != 1000 || q.Total.Amount != 6000 {
		t.Fatalf("quote = %+v", q)
	}
}

func TestPercentCouponReducesTaxableAmount(t *testing.T) {
	q, err := engine().Quote([]Line{{SKU: "A", Qty: 1, Unit: usd(10000)}}, "save10")
	if err != nil {
		t.Fatal(err)
	}
	if q.Discount.Amount != 1000 || q.Tax.Amount != 1800 || q.Total.Amount != 10800 {
		t.Fatalf("quote = %+v", q)
	}
}

func TestTaxIsRoundedPerLine(t *testing.T) {
	q, err := engine().Quote([]Line{{SKU: "A", Qty: 1, Unit: usd(333)}, {SKU: "B", Qty: 1, Unit: usd(333)}}, "")
	if err != nil {
		t.Fatal(err)
	}
	if q.Tax.Amount != 134 {
		t.Fatalf("tax = %d, want 134 (67 per line)", q.Tax.Amount)
	}
}

func TestUnknownCoupon(t *testing.T) {
	_, err := engine().Quote([]Line{{SKU: "A", Qty: 1, Unit: usd(100)}}, "NOPE")
	if !errors.Is(err, ErrUnknownCoupon) {
		t.Fatalf("err = %v", err)
	}
}

func TestEmptyOrder(t *testing.T) {
	if _, err := engine().Quote(nil, ""); !errors.Is(err, ErrEmpty) {
		t.Fatalf("err = %v", err)
	}
}
