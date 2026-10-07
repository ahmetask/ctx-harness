package money

import (
	"fmt"
	"strings"
)

// Currency is an ISO 4217 currency code.
type Currency string

const (
	USD Currency = "USD"
	EUR Currency = "EUR"
	GBP Currency = "GBP"
	JPY Currency = "JPY"
)

type currencyInfo struct {
	symbol   string
	decimals int
}

// currencies lists every supported currency.
var currencies = map[Currency]currencyInfo{
	USD: {symbol: "$", decimals: 2},
	EUR: {symbol: "€", decimals: 2},
	GBP: {symbol: "£", decimals: 2},
	JPY: {symbol: "¥", decimals: 0},
}

// ParseCurrency accepts a supported currency code in any case.
func ParseCurrency(code string) (Currency, error) {
	c := Currency(strings.ToUpper(strings.TrimSpace(code)))
	if _, ok := currencies[c]; !ok {
		return "", fmt.Errorf("money: unsupported currency %q", code)
	}
	return c, nil
}

// Decimals is the number of minor-unit digits of the currency.
func (c Currency) Decimals() int { return currencies[c].decimals }

// Symbol is the display symbol of the currency.
func (c Currency) Symbol() string { return currencies[c].symbol }
