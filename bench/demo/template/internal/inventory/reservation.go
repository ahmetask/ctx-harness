package inventory

import "fmt"

// Reserve holds stock for an order: every line or none.
func (i *Inventory) Reserve(orderID string, lines []Line) error {
	i.mu.Lock()
	defer i.mu.Unlock()
	if _, dup := i.holds[orderID]; dup {
		return fmt.Errorf("inventory: order %s already holds stock", orderID)
	}
	want := map[string]int{}
	for _, l := range lines {
		want[l.SKU] += l.Qty
	}
	for sku, qty := range want {
		if i.onHand[sku]-i.reserved[sku] < qty {
			return fmt.Errorf("%w: %s needs %d", ErrInsufficient, sku, qty)
		}
	}
	for sku, qty := range want {
		i.reserved[sku] += qty
	}
	i.holds[orderID] = append([]Line(nil), lines...)
	return nil
}

// Release drops the hold of an order. Releasing an order without a hold
// is a no-op, so every failure path can call it.
func (i *Inventory) Release(orderID string) {
	i.mu.Lock()
	defer i.mu.Unlock()
	for _, l := range i.holds[orderID] {
		i.reserved[l.SKU] -= l.Qty
	}
	delete(i.holds, orderID)
}

// Commit turns the hold of a paid order into a deduction from stock on hand.
func (i *Inventory) Commit(orderID string) error {
	i.mu.Lock()
	defer i.mu.Unlock()
	lines, ok := i.holds[orderID]
	if !ok {
		return fmt.Errorf("inventory: order %s holds no stock", orderID)
	}
	for _, l := range lines {
		i.reserved[l.SKU] -= l.Qty
		i.onHand[l.SKU] -= l.Qty
	}
	delete(i.holds, orderID)
	return nil
}
