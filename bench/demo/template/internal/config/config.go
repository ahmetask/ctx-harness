package config

import (
	"os"
	"strconv"

	"shopd/internal/money"
)

// Config holds process settings.
type Config struct {
	Addr     string
	TaxBP    int64 // sales tax in basis points, 2000 = 20%
	Currency money.Currency
}

// Default is the configuration used by tests and the demo.
func Default() Config {
	return Config{Addr: ":8080", TaxBP: 2000, Currency: money.USD}
}

// Load reads SHOPD_ADDR, SHOPD_TAX_BP and SHOPD_CURRENCY over the defaults.
func Load() Config {
	c := Default()
	if v := os.Getenv("SHOPD_ADDR"); v != "" {
		c.Addr = v
	}
	if v := os.Getenv("SHOPD_TAX_BP"); v != "" {
		if bp, err := strconv.ParseInt(v, 10, 64); err == nil && bp >= 0 {
			c.TaxBP = bp
		}
	}
	if v := os.Getenv("SHOPD_CURRENCY"); v != "" {
		if cur, err := money.ParseCurrency(v); err == nil {
			c.Currency = cur
		}
	}
	return c
}
