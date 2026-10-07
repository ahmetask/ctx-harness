package orders

import (
	"errors"
	"fmt"
)

// ErrInvalid wraps every rejected request.
var ErrInvalid = errors.New("orders: invalid request")

const (
	maxLines = 50
	maxQty   = 100
)

func validateItems(customerID string, items []Item) error {
	if customerID == "" {
		return fmt.Errorf("%w: customer_id is required", ErrInvalid)
	}
	if len(items) == 0 {
		return fmt.Errorf("%w: at least one item is required", ErrInvalid)
	}
	if len(items) > maxLines {
		return fmt.Errorf("%w: at most %d items", ErrInvalid, maxLines)
	}
	for _, it := range items {
		if it.SKU == "" {
			return fmt.Errorf("%w: item without sku", ErrInvalid)
		}
		if it.Qty < 1 || it.Qty > maxQty {
			return fmt.Errorf("%w: qty for %s must be 1..%d", ErrInvalid, it.SKU, maxQty)
		}
	}
	return nil
}
