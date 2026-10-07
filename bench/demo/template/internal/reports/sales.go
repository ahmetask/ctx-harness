package reports

import (
	"sort"

	"shopd/internal/money"
	"shopd/internal/orders"
)

// DaySales is the revenue of one day in one currency.
type DaySales struct {
	Day     string      `json:"day"` // YYYY-MM-DD, UTC
	Orders  int         `json:"orders"`
	Revenue money.Money `json:"revenue"`
}

// collected reports whether the money of an order in state s was taken.
func collected(s orders.State) bool {
	return s == orders.StatePaid || s == orders.StateShipped || s == orders.StateDelivered
}

// SalesByDay sums collected revenue per day and currency, oldest day first.
func SalesByDay(os []orders.Order) []DaySales {
	type key struct {
		day string
		cur money.Currency
	}
	acc := map[key]*DaySales{}
	for _, o := range os {
		if !collected(o.State) {
			continue
		}
		k := key{o.CreatedAt.UTC().Format("2006-01-02"), o.Quote.Total.Currency}
		d, ok := acc[k]
		if !ok {
			d = &DaySales{Day: k.day, Revenue: money.Zero(k.cur)}
			acc[k] = d
		}
		d.Orders++
		d.Revenue = d.Revenue.Add(o.Quote.Total)
	}
	out := make([]DaySales, 0, len(acc))
	for _, d := range acc {
		out = append(out, *d)
	}
	sort.Slice(out, func(i, j int) bool {
		if out[i].Day != out[j].Day {
			return out[i].Day < out[j].Day
		}
		return out[i].Revenue.Currency < out[j].Revenue.Currency
	})
	return out
}
