package money

import (
	"fmt"
	"strconv"
	"strings"
)

// Format renders m for people, for example "$1,234.56".
func Format(m Money) string {
	sign := ""
	a := m.Amount
	if a < 0 {
		sign = "-"
		a = -a
	}
	d := m.Currency.Decimals()
	unit := pow10(d)
	s := sign + m.Currency.Symbol() + groupThousands(a/unit)
	if d > 0 {
		s += fmt.Sprintf(".%0*d", d, a%unit)
	}
	return s
}

func pow10(n int) int64 {
	p := int64(1)
	for i := 0; i < n; i++ {
		p *= 10
	}
	return p
}

func groupThousands(n int64) string {
	s := strconv.FormatInt(n, 10)
	for i := len(s) - 3; i > 0; i -= 3 {
		s = s[:i] + "," + s[i:]
	}
	return s
}

// ParseAmount parses a non-negative decimal string such as "12.50" into
// minor units of c.
func ParseAmount(s string, c Currency) (Money, error) {
	s = strings.TrimSpace(s)
	if strings.HasPrefix(s, "-") {
		return Money{}, fmt.Errorf("money: negative amount %q", s)
	}
	d := c.Decimals()
	whole, frac, hasFrac := strings.Cut(s, ".")
	if hasFrac && d == 0 || len(frac) > d {
		return Money{}, fmt.Errorf("money: too many decimals in %q", s)
	}
	for len(frac) < d {
		frac += "0"
	}
	w, err := strconv.ParseInt(whole, 10, 64)
	if err != nil {
		return Money{}, fmt.Errorf("money: bad amount %q", s)
	}
	var f int64
	if d > 0 {
		if f, err = strconv.ParseInt(frac, 10, 64); err != nil {
			return Money{}, fmt.Errorf("money: bad amount %q", s)
		}
	}
	return New(w*pow10(d)+f, c), nil
}
