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
	whole, frac := a/100, a%100
	return fmt.Sprintf("%s%s%s.%02d", sign, m.Currency.Symbol(), groupThousands(whole), frac)
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
	whole, frac, _ := strings.Cut(s, ".")
	if len(frac) > 2 {
		return Money{}, fmt.Errorf("money: too many decimals in %q", s)
	}
	for len(frac) < 2 {
		frac += "0"
	}
	w, err := strconv.ParseInt(whole, 10, 64)
	if err != nil {
		return Money{}, fmt.Errorf("money: bad amount %q", s)
	}
	f, err := strconv.ParseInt(frac, 10, 64)
	if err != nil {
		return Money{}, fmt.Errorf("money: bad amount %q", s)
	}
	return New(w*100+f, c), nil
}
