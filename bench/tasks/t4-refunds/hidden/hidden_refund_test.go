package orders_test

import (
	"errors"
	"strings"
	"testing"

	"shopd/internal/app"
	"shopd/internal/orders"
)

func TestHiddenRefund(t *testing.T) {
	a := app.NewDemo()
	o, err := a.Orders.Place("c1", []orders.Item{{SKU: "LAMP-001", Qty: 1}}, "")
	if err != nil {
		t.Fatal(err)
	}
	if o, err = a.Orders.Pay(o.ID); err != nil {
		t.Fatal(err)
	}
	if o, err = a.Orders.Refund(o.ID); err != nil {
		t.Fatalf("refund paid order: %v", err)
	}
	if o.State != orders.State("refunded") {
		t.Fatalf("state = %s, want refunded", o.State)
	}
	if got := a.Gateway.Refunded(o.PaymentID); got != o.Quote.Total.Amount {
		t.Fatalf("refunded %d, want %d", got, o.Quote.Total.Amount)
	}
	if m := a.Sender.Last(); !strings.Contains(strings.ToLower(m.Subject+" "+m.Body), "refund") {
		t.Fatalf("last email does not mention the refund: %+v", m)
	}
	if _, err := a.Orders.Refund(o.ID); !errors.Is(err, orders.ErrInvalidTransition) {
		t.Fatalf("second refund: err = %v, want ErrInvalidTransition", err)
	}

	d, err := a.Orders.Place("c1", []orders.Item{{SKU: "BOOK-001", Qty: 1}}, "")
	if err != nil {
		t.Fatal(err)
	}
	steps := []func(string) (orders.Order, error){a.Orders.Pay, a.Orders.Ship, a.Orders.Deliver, a.Orders.Refund}
	for i, step := range steps {
		if d, err = step(d.ID); err != nil {
			t.Fatalf("delivered order, step %d: %v", i, err)
		}
	}

	p, err := a.Orders.Place("c1", []orders.Item{{SKU: "TEE-001", Qty: 1}}, "")
	if err != nil {
		t.Fatal(err)
	}
	if _, err := a.Orders.Refund(p.ID); !errors.Is(err, orders.ErrInvalidTransition) {
		t.Fatalf("refund pending order: err = %v, want ErrInvalidTransition", err)
	}
}
