package httpapi

import (
	"net/http"

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

// listProducts serves GET /products?q=<text>.
func (s *Server) listProducts(w http.ResponseWriter, r *http.Request) {
	ps := s.catalog.Search(r.URL.Query().Get("q"))
	out := make([]productView, 0, len(ps))
	for _, p := range ps {
		out = append(out, view(p))
	}
	writeJSON(w, http.StatusOK, out)
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
