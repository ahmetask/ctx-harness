// Command shopd serves the shop API with in-memory demo data.
package main

import (
	"log"
	"net/http"

	"shopd/internal/app"
	"shopd/internal/clock"
	"shopd/internal/config"
	"shopd/internal/payments"
)

func main() {
	cfg := config.Load()
	a := app.New(cfg, clock.System{}, payments.DefaultRetry())
	log.Printf("shopd listening on %s", cfg.Addr)
	log.Fatal(http.ListenAndServe(cfg.Addr, a.Handler))
}
