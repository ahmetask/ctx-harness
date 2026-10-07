package money

import "testing"

func TestHiddenJPY(t *testing.T) {
	c, err := ParseCurrency("jpy")
	if err != nil || c != Currency("JPY") {
		t.Fatalf("ParseCurrency(jpy) = %q, %v", c, err)
	}
	if got := Format(New(1200, c)); got != "¥1,200" {
		t.Errorf("Format(1200 JPY) = %q, want ¥1,200", got)
	}
	if got := Format(New(-5, c)); got != "-¥5" {
		t.Errorf("Format(-5 JPY) = %q, want -¥5", got)
	}
	m, err := ParseAmount("1200", c)
	if err != nil || m.Amount != 1200 || m.Currency != c {
		t.Errorf("ParseAmount(1200, JPY) = %+v, %v", m, err)
	}
	if _, err := ParseAmount("12.5", c); err == nil {
		t.Error("ParseAmount(12.5, JPY) should fail")
	}
	if got := Format(New(123456, USD)); got != "$1,234.56" {
		t.Errorf("USD format changed: %q", got)
	}
	if m, err := ParseAmount("12.5", USD); err != nil || m.Amount != 1250 {
		t.Errorf("USD parse changed: %+v, %v", m, err)
	}
	if got := New(1000, c).Percent(1000).Amount; got != 100 {
		t.Errorf("10%% of 1000 JPY = %d", got)
	}
}
