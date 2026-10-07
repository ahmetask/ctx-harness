package inventory

import (
	"errors"
	"sync"
)

// ErrInsufficient is returned when a reservation cannot be met.
var ErrInsufficient = errors.New("inventory: insufficient stock")

// Line is a quantity of one SKU.
type Line struct {
	SKU string
	Qty int
}

// Inventory tracks stock on hand and stock held for unpaid orders.
type Inventory struct {
	mu       sync.Mutex
	onHand   map[string]int
	reserved map[string]int
	holds    map[string][]Line // by order ID
}

// New returns an empty inventory.
func New() *Inventory {
	return &Inventory{onHand: map[string]int{}, reserved: map[string]int{}, holds: map[string][]Line{}}
}

// Set sets the on-hand quantity of sku.
func (i *Inventory) Set(sku string, qty int) {
	i.mu.Lock()
	defer i.mu.Unlock()
	i.onHand[sku] = qty
}

// Available is on-hand stock minus stock held for unpaid orders.
func (i *Inventory) Available(sku string) int {
	i.mu.Lock()
	defer i.mu.Unlock()
	return i.onHand[sku] - i.reserved[sku]
}

// OnHand is the physical stock of sku.
func (i *Inventory) OnHand(sku string) int {
	i.mu.Lock()
	defer i.mu.Unlock()
	return i.onHand[sku]
}
