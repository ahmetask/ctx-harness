package httpapi_test

import (
	"bytes"
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"testing"

	"shopd/internal/app"
)

func newTestServer(t *testing.T) (*httptest.Server, *app.App) {
	t.Helper()
	a := app.NewDemo()
	srv := httptest.NewServer(a.Handler)
	t.Cleanup(srv.Close)
	return srv, a
}

func do(t *testing.T, method, url string, body, out any) int {
	t.Helper()
	var buf bytes.Buffer
	if body != nil {
		if err := json.NewEncoder(&buf).Encode(body); err != nil {
			t.Fatal(err)
		}
	}
	req, err := http.NewRequest(method, url, &buf)
	if err != nil {
		t.Fatal(err)
	}
	resp, err := http.DefaultClient.Do(req)
	if err != nil {
		t.Fatal(err)
	}
	defer resp.Body.Close()
	if out != nil {
		if err := json.NewDecoder(resp.Body).Decode(out); err != nil {
			t.Fatalf("%s %s: decode: %v", method, url, err)
		}
	}
	return resp.StatusCode
}

func getJSON(t *testing.T, url string, out any) int { return do(t, http.MethodGet, url, nil, out) }

func postJSON(t *testing.T, url string, body, out any) int {
	return do(t, http.MethodPost, url, body, out)
}

type product struct {
	SKU     string `json:"sku"`
	Price   int64  `json:"price"`
	Display string `json:"display"`
}

type order struct {
	ID    string `json:"id"`
	State string `json:"state"`
}

func TestListProducts(t *testing.T) {
	srv, _ := newTestServer(t)
	var ps []product
	if code := getJSON(t, srv.URL+"/products?q=mug", &ps); code != http.StatusOK {
		t.Fatalf("status %d", code)
	}
	if len(ps) != 2 || ps[0].SKU != "MUG-001" || ps[0].Display != "$12.00" {
		t.Fatalf("products = %+v", ps)
	}
}

func TestArchivedProductIsNotFound(t *testing.T) {
	srv, _ := newTestServer(t)
	if code := getJSON(t, srv.URL+"/products/OLD-001", nil); code != http.StatusNotFound {
		t.Fatalf("status %d", code)
	}
}

func TestOrderFlow(t *testing.T) {
	srv, _ := newTestServer(t)
	var o order
	body := map[string]any{"customer_id": "c1", "items": []map[string]any{{"sku": "TEE-001", "qty": 1}}}
	if code := postJSON(t, srv.URL+"/orders", body, &o); code != http.StatusCreated || o.State != "pending" {
		t.Fatalf("place: status %d, order %+v", code, o)
	}
	if code := postJSON(t, srv.URL+"/orders/"+o.ID+"/pay", nil, &o); code != http.StatusOK || o.State != "paid" {
		t.Fatalf("pay: status %d, order %+v", code, o)
	}
	var e map[string]string
	if code := postJSON(t, srv.URL+"/orders/"+o.ID+"/cancel", nil, &e); code != http.StatusConflict {
		t.Fatalf("cancel paid: status %d, %v", code, e)
	}
}

func TestBadRequests(t *testing.T) {
	srv, _ := newTestServer(t)
	var e map[string]string
	body := map[string]any{"customer_id": "c1", "items": []map[string]any{{"sku": "TEE-001", "qty": 0}}}
	if code := postJSON(t, srv.URL+"/orders", body, &e); code != http.StatusBadRequest {
		t.Fatalf("qty 0: status %d", code)
	}
	if code := postJSON(t, srv.URL+"/orders", map[string]any{"nope": 1}, &e); code != http.StatusBadRequest {
		t.Fatalf("unknown field: status %d", code)
	}
	if code := postJSON(t, srv.URL+"/orders/ord-9999/pay", nil, &e); code != http.StatusNotFound {
		t.Fatalf("unknown order: status %d", code)
	}
}

func TestRequestID(t *testing.T) {
	srv, _ := newTestServer(t)
	resp, err := http.Get(srv.URL + "/products")
	if err != nil {
		t.Fatal(err)
	}
	resp.Body.Close()
	if resp.Header.Get("X-Request-ID") == "" {
		t.Fatal("missing X-Request-ID")
	}
}
