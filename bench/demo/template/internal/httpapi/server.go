package httpapi

import (
	"net/http"

	"shopd/internal/catalog"
	"shopd/internal/orders"
)

// Server is the JSON HTTP API.
type Server struct {
	orders  *orders.Service
	catalog *catalog.Store
	mux     *http.ServeMux
}

// New returns the API handler with middleware applied.
func New(o *orders.Service, c *catalog.Store) http.Handler {
	s := &Server{orders: o, catalog: c, mux: http.NewServeMux()}
	s.routes()
	return withRequestID(withRecover(s.mux))
}

func (s *Server) routes() {
	s.mux.HandleFunc("GET /products", s.listProducts)
	s.mux.HandleFunc("GET /products/{sku}", s.getProduct)
	s.mux.HandleFunc("POST /orders", s.placeOrder)
	s.mux.HandleFunc("GET /orders/{id}", s.getOrder)
	s.mux.HandleFunc("POST /orders/{id}/pay", s.payOrder)
	s.mux.HandleFunc("POST /orders/{id}/ship", s.shipOrder)
	s.mux.HandleFunc("POST /orders/{id}/deliver", s.deliverOrder)
	s.mux.HandleFunc("POST /orders/{id}/cancel", s.cancelOrder)
}
