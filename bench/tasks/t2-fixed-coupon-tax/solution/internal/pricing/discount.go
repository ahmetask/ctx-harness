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

// applyFixed spreads a fixed amount off across the lines in proportion to
// their amounts, never taking a line below zero; the last line absorbs
// rounding. It returns the new amounts and how much actually came off.
func applyFixed(amounts []money.Money, off money.Money) ([]money.Money, money.Money) {
	cur := amounts[0].Currency
	var sum int64
	for _, a := range amounts {
		sum += a.Amount
	}
	want := off.Amount
	if want > sum {
		want = sum
	}
	out := make([]money.Money, len(amounts))
	left := want
	for i, a := range amounts {
		share := left
		if i < len(amounts)-1 && sum > 0 {
			share = a.Amount * want / sum
		}
		if share > a.Amount {
			share = a.Amount
		}
		out[i] = money.New(a.Amount-share, cur)
		left -= share
	}
	return out, money.New(want-left, cur)
}
