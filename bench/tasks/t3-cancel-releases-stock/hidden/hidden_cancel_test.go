package orders_test

import (
	"testing"

	"shopd/internal/app"
	"shopd/internal/orders"
)

func TestHiddenCancelReleasesStock(t *testing.T) {
	a := app.NewDemo()
	before := a.Inventory.Available("MUG-001")
	o, err := a.Orders.Place("c1", []orders.Item{{SKU: "MUG-001", Qty: 2}}, "")
	if err != nil {
		t.Fatal(err)
	}
	if got := a.Inventory.Available("MUG-001"); got != before-2 {
		t.Fatalf("available after place = %d, want %d", got, before-2)
	}
	if o, err = a.Orders.Cancel(o.ID); err != nil || o.State != orders.StateCancelled {
		t.Fatalf("cancel: %v, state %s", err, o.State)
	}
	if got := a.Inventory.Available("MUG-001"); got != before {
		t.Fatalf("available after cancel = %d, want %d", got, before)
	}
	if got := a.Inventory.OnHand("MUG-001"); got != before {
		t.Fatalf("on hand after cancel = %d, want %d", got, before)
	}
	if _, err := a.Orders.Place("c2", []orders.Item{{SKU: "MUG-001", Qty: before}}, ""); err != nil {
		t.Fatalf("ordering the full stock after a cancel: %v", err)
	}
}
