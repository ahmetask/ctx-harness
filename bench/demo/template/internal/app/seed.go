package app

import (
	"shopd/internal/catalog"
	"shopd/internal/config"
	"shopd/internal/customers"
	"shopd/internal/money"
	"shopd/internal/pricing"
)

// seed loads the demo catalog, stock and customers. Every product starts
// with 10 units.
func seed(a *App) {
	cur := a.Config.Currency
	products := []catalog.Product{
		{SKU: "MUG-001", Name: "Coffee mug", Price: money.New(1200, cur), Tags: []string{"kitchen"}, WeightG: 350},
		{SKU: "MUG-002", Name: "Travel mug", Price: money.New(2450, cur), Tags: []string{"kitchen", "outdoor"}, WeightG: 400},
		{SKU: "TEE-001", Name: "T-shirt", Price: money.New(1999, cur), Tags: []string{"apparel"}, WeightG: 200},
		{SKU: "BOOK-001", Name: "Go in practice", Price: money.New(4500, cur), Tags: []string{"books"}, WeightG: 900},
		{SKU: "LAMP-001", Name: "Desk lamp", Price: money.New(10000, cur), Tags: []string{"office"}, WeightG: 2400},
		{SKU: "OLD-001", Name: "Retro mug", Price: money.New(900, cur), Tags: []string{"kitchen"}, WeightG: 350, Archived: true},
	}
	for _, p := range products {
		a.Catalog.Put(p)
		a.Inventory.Set(p.SKU, 10)
	}
	for _, c := range []customers.Customer{
		{ID: "c1", Name: "Ada", Email: "ada@example.com"},
		{ID: "c2", Name: "Linus", Email: "linus@example.com"},
	} {
		if err := a.Customers.Put(c); err != nil {
			panic(err)
		}
	}
}

func coupons(cfg config.Config) *pricing.CouponBook {
	return pricing.NewCouponBook(
		pricing.Coupon{Code: "SAVE10", PercentBP: 1000},
		pricing.Coupon{Code: "TENOFF", Fixed: money.New(1000, cfg.Currency)},
	)
}
