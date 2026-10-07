package httpapi_test

import (
	"net/http"
	"reflect"
	"testing"
)

func TestHiddenPriceFilter(t *testing.T) {
	srv, _ := newTestServer(t)
	skus := func(query string) []string {
		t.Helper()
		var ps []product
		if code := getJSON(t, srv.URL+"/products"+query, &ps); code != http.StatusOK {
			t.Fatalf("%s: status %d", query, code)
		}
		out := []string{}
		for _, p := range ps {
			out = append(out, p.SKU)
		}
		return out
	}
	cases := map[string][]string{
		"?q=mug&min_price=1500":           {"MUG-002"},
		"?max_price=2000":                 {"MUG-001", "TEE-001"},
		"?min_price=1999&max_price=4500":  {"BOOK-001", "MUG-002", "TEE-001"},
		"?min_price=20000":                {},
		"?q=kitchen&max_price=1200":       {"MUG-001"},
	}
	for query, want := range cases {
		if got := skus(query); !reflect.DeepEqual(got, want) {
			t.Errorf("%s: got %v, want %v", query, got, want)
		}
	}
	for _, bad := range []string{"?min_price=abc", "?max_price=-5", "?min_price=1.5"} {
		var e map[string]string
		if code := getJSON(t, srv.URL+"/products"+bad, &e); code != http.StatusBadRequest {
			t.Errorf("%s: status %d, want 400", bad, code)
		}
	}
}
