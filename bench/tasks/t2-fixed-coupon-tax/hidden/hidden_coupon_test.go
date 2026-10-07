package pricing

import (
	"testing"

	"shopd/internal/money"
)

func TestHiddenFixedCouponBeforeTax(t *testing.T) {
	usd := func(a int64) money.Money { return money.New(a, money.USD) }
	e := NewEngine(2000, NewCouponBook(Coupon{Code: "TENOFF", Fixed: usd(1000)}))

	q, err := e.Quote([]Line{{SKU: "LAMP-001", Qty: 1, Unit: usd(10000)}}, "TENOFF")
	if err != nil {
		t.Fatal(err)
	}
	if q.Discount.Amount != 1000 || q.Tax.Amount != 1800 || q.Total.Amount != 10800 {
		t.Fatalf("single line: discount %d, tax %d, total %d; want 1000, 1800, 10800",
			q.Discount.Amount, q.Tax.Amount, q.Total.Amount)
	}

	q, err = e.Quote([]Line{{SKU: "A", Qty: 1, Unit: usd(6000)}, {SKU: "B", Qty: 1, Unit: usd(4000)}}, "tenoff")
	if err != nil {
		t.Fatal(err)
	}
	if q.Tax.Amount != 1800 || q.Total.Amount != 10800 {
		t.Fatalf("two lines: tax %d, total %d; want 1800, 10800", q.Tax.Amount, q.Total.Amount)
	}

	q, err = e.Quote([]Line{{SKU: "A", Qty: 1, Unit: usd(500)}}, "TENOFF")
	if err != nil {
		t.Fatal(err)
	}
	if q.Tax.Amount != 0 || q.Total.Amount != 0 {
		t.Fatalf("coupon above order value: tax %d, total %d; want 0, 0", q.Tax.Amount, q.Total.Amount)
	}
}
