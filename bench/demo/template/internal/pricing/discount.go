package pricing

import "shopd/internal/money"

// applyPercent takes bp basis points off every line. It returns the
// discounted line amounts and the total discount; each line is rounded on
// its own.
func applyPercent(amounts []money.Money, bp int64) ([]money.Money, money.Money) {
	out := make([]money.Money, len(amounts))
	total := money.Zero(amounts[0].Currency)
	for i, a := range amounts {
		d := money.Zero(a.Currency)
		if bp > 0 {
			d = a.Percent(bp)
		}
		out[i] = a.Sub(d)
		total = total.Add(d)
	}
	return out, total
}
