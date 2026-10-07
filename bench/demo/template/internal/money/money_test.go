package money

import "testing"

func TestPercentRoundsHalfAwayFromZero(t *testing.T) {
	cases := []struct{ amount, bp, want int64 }{
		{10000, 2000, 2000},
		{333, 2000, 67},
		{25, 2000, 5},
		{-333, 2000, -67},
	}
	for _, c := range cases {
		if got := New(c.amount, USD).Percent(c.bp).Amount; got != c.want {
			t.Errorf("Percent(%d, %d) = %d, want %d", c.amount, c.bp, got, c.want)
		}
	}
}

func TestFormat(t *testing.T) {
	cases := map[Money]string{
		New(123456, USD): "$1,234.56",
		New(5, EUR):      "€0.05",
		New(-1999, GBP):  "-£19.99",
	}
	for m, want := range cases {
		if got := Format(m); got != want {
			t.Errorf("Format(%v) = %q, want %q", m.Amount, got, want)
		}
	}
}

func TestParseAmount(t *testing.T) {
	m, err := ParseAmount("12.5", USD)
	if err != nil || m.Amount != 1250 {
		t.Fatalf("ParseAmount(12.5) = %v, %v", m, err)
	}
	if _, err := ParseAmount("1.234", USD); err == nil {
		t.Fatal("expected error for three decimals")
	}
	if _, err := ParseAmount("-1", USD); err == nil {
		t.Fatal("expected error for negative amount")
	}
}

func TestParseCurrency(t *testing.T) {
	if c, err := ParseCurrency(" eur "); err != nil || c != EUR {
		t.Fatalf("ParseCurrency(eur) = %v, %v", c, err)
	}
	if _, err := ParseCurrency("XXX"); err == nil {
		t.Fatal("expected error for unknown currency")
	}
}

func TestMismatchPanics(t *testing.T) {
	defer func() {
		if recover() == nil {
			t.Fatal("expected panic")
		}
	}()
	New(1, USD).Add(New(1, EUR))
}
