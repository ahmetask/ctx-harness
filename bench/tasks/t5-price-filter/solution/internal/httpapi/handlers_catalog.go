package httpapi

import (
	"fmt"
	"math"
	"net/http"
	"strconv"

	"shopd/internal/catalog"
	"shopd/internal/money"
)

type productView struct {
	SKU      string `json:"sku"`
	Name     string `json:"name"`
	Price    int64  `json:"price"` // minor units
	Currency string `json:"currency"`
	Display  string `json:"display"`
}

func view(p catalog.Product) productView {
	return productView{
		SKU: p.SKU, Name: p.Name, Price: p.Price.Amount,
		Currency: string(p.Price.Currency), Display: money.Format(p.Price),
	}
}

// listProducts serves GET /products?q=<text>&min_price=<minor units>&max_price=<minor units>.
func (s *Server) listProducts(w http.ResponseWriter, r *http.Request) {
	q := r.URL.Query()
	minPrice, err := priceParam(q.Get("min_price"), 0)
	if err != nil {
		writeError(w, err)
		return
	}
	maxPrice, err := priceParam(q.Get("max_price"), math.MaxInt64)
	if err != nil {
		writeError(w, err)
		return
	}
	ps := s.catalog.Search(q.Get("q"))
	out := make([]productView, 0, len(ps))
	for _, p := range ps {
		if p.Price.Amount < minPrice || p.Price.Amount > maxPrice {
			continue
		}
		out = append(out, view(p))
	}
	writeJSON(w, http.StatusOK, out)
}

func priceParam(v string, def int64) (int64, error) {
	if v == "" {
		return def, nil
	}
	n, err := strconv.ParseInt(v, 10, 64)
	if err != nil || n < 0 {
		return 0, badRequest(fmt.Errorf("invalid price %q", v))
	}
	return n, nil
}

// getProduct serves GET /products/{sku}.
func (s *Server) getProduct(w http.ResponseWriter, r *http.Request) {
	p, err := s.catalog.Lookup(r.PathValue("sku"))
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, view(p))
}
