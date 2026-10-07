package app

import (
	"net/http"
	"time"

	"shopd/internal/audit"
	"shopd/internal/catalog"
	"shopd/internal/clock"
	"shopd/internal/config"
	"shopd/internal/customers"
	"shopd/internal/httpapi"
	"shopd/internal/ids"
	"shopd/internal/inventory"
	"shopd/internal/notify"
	"shopd/internal/orders"
	"shopd/internal/payments"
	"shopd/internal/pricing"
)

// App is the wired application. Fields are exported so tests can reach
// every collaborator.
type App struct {
	Config    config.Config
	Catalog   *catalog.Store
	Customers *customers.Store
	Inventory *inventory.Inventory
	Gateway   *payments.FakeGateway
	Sender    *notify.MemorySender
	Audit     *audit.Log
	Orders    *orders.Service
	Handler   http.Handler
}

// New wires the application with seeded demo data.
func New(cfg config.Config, clk clock.Clock, retry payments.RetryPolicy) *App {
	a := &App{
		Config:    cfg,
		Catalog:   catalog.NewStore(),
		Customers: customers.NewStore(),
		Inventory: inventory.New(),
		Gateway:   payments.NewFakeGateway(),
		Sender:    &notify.MemorySender{},
		Audit:     audit.NewLog(),
	}
	seed(a)
	a.Orders = orders.NewService(orders.Deps{
		Catalog:   a.Catalog,
		Customers: a.Customers,
		Inventory: a.Inventory,
		Pricing:   pricing.NewEngine(cfg.TaxBP, coupons(cfg)),
		Payments:  payments.NewClient(a.Gateway, retry),
		Notifier:  notify.New(a.Sender),
		IDs:       ids.NewSequence(),
		Clock:     clk,
		Audit:     a.Audit,
	})
	a.Handler = httpapi.New(a.Orders, a.Catalog)
	return a
}

// NewDemo returns an app with the default config, a fixed clock and no
// retry backoff, for tests.
func NewDemo() *App {
	return New(config.Default(), clock.Fixed{T: time.Date(2024, 1, 15, 10, 0, 0, 0, time.UTC)},
		payments.RetryPolicy{Attempts: 3})
}
