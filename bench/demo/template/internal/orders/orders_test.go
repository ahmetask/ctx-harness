package orders_test

import (
	"errors"
	"testing"

	"shopd/internal/app"
	"shopd/internal/orders"
	"shopd/internal/payments"
)

func TestLifecycle(t *testing.T) {
	a := app.NewDemo()
	o, err := a.Orders.Place("c1", []orders.Item{{SKU: "MUG-001", Qty: 2}}, "SAVE10")
	if err != nil {
		t.Fatal(err)
	}
	if o.Quote.Total.Amount != 2592 {
		t.Fatalf("total = %d, want 2592", o.Quote.Total.Amount)
	}
	for _, step := range []func(string) (orders.Order, error){a.Orders.Pay, a.Orders.Ship, a.Orders.Deliver} {
		if o, err = step(o.ID); err != nil {
			t.Fatal(err)
		}
	}
	if o.State != orders.StateDelivered || o.Tracking == "" {
		t.Fatalf("order = %+v", o)
	}
	if got := a.Inventory.OnHand("MUG-001"); got != 8 {
		t.Fatalf("on hand = %d, want 8", got)
	}
	if a.Sender.Last().Subject != "Order "+o.ID+" delivered" {
		t.Fatalf("last message = %+v", a.Sender.Last())
	}
}

func TestPayIsChargedOnceAcrossRetries(t *testing.T) {
	a := app.NewDemo()
	a.Gateway.FailNext = 2
	o, _ := a.Orders.Place("c1", []orders.Item{{SKU: "BOOK-001", Qty: 1}}, "")
	if _, err := a.Orders.Pay(o.ID); err != nil {
		t.Fatal(err)
	}
	if a.Gateway.Charges() != 1 {
		t.Fatalf("charges = %d", a.Gateway.Charges())
	}
}

func TestDeclinedPaymentCancelsAndReleasesStock(t *testing.T) {
	a := app.NewDemo()
	a.Gateway.DeclineNext = true
	o, _ := a.Orders.Place("c1", []orders.Item{{SKU: "TEE-001", Qty: 3}}, "")
	if _, err := a.Orders.Pay(o.ID); !errors.Is(err, payments.ErrDeclined) {
		t.Fatalf("err = %v", err)
	}
	if got, _ := a.Orders.Get(o.ID); got.State != orders.StateCancelled {
		t.Fatalf("state = %s", got.State)
	}
	if a.Inventory.Available("TEE-001") != 10 {
		t.Fatalf("available = %d", a.Inventory.Available("TEE-001"))
	}
}

func TestInvalidTransitions(t *testing.T) {
	a := app.NewDemo()
	o, _ := a.Orders.Place("c1", []orders.Item{{SKU: "LAMP-001", Qty: 1}}, "")
	if _, err := a.Orders.Ship(o.ID); !errors.Is(err, orders.ErrInvalidTransition) {
		t.Fatalf("ship unpaid: err = %v", err)
	}
	a.Orders.Pay(o.ID)
	if _, err := a.Orders.Cancel(o.ID); !errors.Is(err, orders.ErrInvalidTransition) {
		t.Fatalf("cancel paid: err = %v", err)
	}
}

func TestPlaceRejectsArchivedAndUnknown(t *testing.T) {
	a := app.NewDemo()
	for _, sku := range []string{"OLD-001", "NOPE"} {
		if _, err := a.Orders.Place("c1", []orders.Item{{SKU: sku, Qty: 1}}, ""); !errors.Is(err, orders.ErrInvalid) {
			t.Fatalf("%s: err = %v", sku, err)
		}
	}
}
