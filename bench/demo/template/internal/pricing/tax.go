package pricing

import "shopd/internal/money"

// perLineTax computes the tax of every line, rounds it, and sums the
// rounded amounts.
func perLineTax(amounts []money.Money, bp int64) money.Money {
	total := money.Zero(amounts[0].Currency)
	for _, a := range amounts {
		total = total.Add(a.Percent(bp))
	}
	return total
}
