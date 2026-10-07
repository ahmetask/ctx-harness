package catalog

import "shopd/internal/money"

// Product is a sellable item.
type Product struct {
	SKU      string      `json:"sku"`
	Name     string      `json:"name"`
	Price    money.Money `json:"price"`
	Tags     []string    `json:"tags,omitempty"`
	WeightG  int         `json:"weight_g"`
	Archived bool        `json:"archived,omitempty"`
}
