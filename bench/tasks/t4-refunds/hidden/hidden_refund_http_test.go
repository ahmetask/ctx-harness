package httpapi_test

import (
	"net/http"
	"testing"
)

func TestHiddenRefundEndpoint(t *testing.T) {
	srv, _ := newTestServer(t)
	var o order
	body := map[string]any{"customer_id": "c1", "items": []map[string]any{{"sku": "LAMP-001", "qty": 1}}}
	if code := postJSON(t, srv.URL+"/orders", body, &o); code != http.StatusCreated {
		t.Fatalf("place: status %d", code)
	}
	var e map[string]string
	if code := postJSON(t, srv.URL+"/orders/"+o.ID+"/refund", nil, &e); code != http.StatusConflict {
		t.Fatalf("refund pending: status %d, want 409", code)
	}
	if code := postJSON(t, srv.URL+"/orders/"+o.ID+"/pay", nil, &o); code != http.StatusOK {
		t.Fatalf("pay: status %d", code)
	}
	if code := postJSON(t, srv.URL+"/orders/"+o.ID+"/refund", nil, &o); code != http.StatusOK || o.State != "refunded" {
		t.Fatalf("refund: status %d, order %+v", code, o)
	}
}
