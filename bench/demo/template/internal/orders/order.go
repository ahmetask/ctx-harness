package orders

import (
	"time"

	"shopd/internal/pricing"
)

// Item is a requested SKU and quantity.
type Item struct {
	SKU string `json:"sku"`
	Qty int    `json:"qty"`
}

// Order is a customer order and its lifecycle state.
type Order struct {
	ID         string         `json:"id"`
	CustomerID string         `json:"customer_id"`
	Lines      []pricing.Line `json:"lines"`
	Coupon     string         `json:"coupon,omitempty"`
	Quote      pricing.Quote  `json:"quote"`
	State      State          `json:"state"`
	PaymentID  string         `json:"payment_id,omitempty"`
	Tracking   string         `json:"tracking,omitempty"`
	CreatedAt  time.Time      `json:"created_at"`
	UpdatedAt  time.Time      `json:"updated_at"`
}
