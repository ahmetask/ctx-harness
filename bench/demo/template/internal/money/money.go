package money

import "fmt"

// Money is an amount in the minor unit of its currency (cents for USD).
// Arithmetic never mixes currencies: a mismatch panics, because it is a
// programming error rather than bad user input.
type Money struct {
	Amount   int64    `json:"amount"`
	Currency Currency `json:"currency"`
}

// New returns amount minor units of c.
func New(amount int64, c Currency) Money { return Money{Amount: amount, Currency: c} }

// Zero returns a zero amount of c.
func Zero(c Currency) Money { return Money{Currency: c} }

func (m Money) mustMatch(o Money) {
	if m.Currency != o.Currency {
		panic(fmt.Sprintf("money: currency mismatch %s vs %s", m.Currency, o.Currency))
	}
}

// Add returns m + o.
func (m Money) Add(o Money) Money {
	m.mustMatch(o)
	return Money{Amount: m.Amount + o.Amount, Currency: m.Currency}
}

// Sub returns m - o.
func (m Money) Sub(o Money) Money {
	m.mustMatch(o)
	return Money{Amount: m.Amount - o.Amount, Currency: m.Currency}
}

// MulInt returns m * n.
func (m Money) MulInt(n int64) Money { return Money{Amount: m.Amount * n, Currency: m.Currency} }

// Percent returns bp basis points of m (2000 = 20%), rounded half away
// from zero. All rounding of amounts goes through here.
func (m Money) Percent(bp int64) Money {
	return Money{Amount: roundDiv(m.Amount*bp, 10000), Currency: m.Currency}
}

// IsZero reports whether m is zero.
func (m Money) IsZero() bool { return m.Amount == 0 }

// IsNegative reports whether m is below zero.
func (m Money) IsNegative() bool { return m.Amount < 0 }

// Less reports whether m < o.
func (m Money) Less(o Money) bool {
	m.mustMatch(o)
	return m.Amount < o.Amount
}

func (m Money) String() string { return Format(m) }

func roundDiv(n, d int64) int64 {
	q, r := n/d, n%d
	if r < 0 {
		r = -r
	}
	if 2*r >= d {
		if n < 0 {
			q--
		} else {
			q++
		}
	}
	return q
}
