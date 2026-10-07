package httpapi

import (
	"net/http"

	"shopd/internal/orders"
)

type placeRequest struct {
	CustomerID string        `json:"customer_id"`
	Items      []orders.Item `json:"items"`
	Coupon     string        `json:"coupon"`
}

// placeOrder serves POST /orders.
func (s *Server) placeOrder(w http.ResponseWriter, r *http.Request) {
	var req placeRequest
	if err := readJSON(r, &req); err != nil {
		writeError(w, err)
		return
	}
	o, err := s.orders.Place(req.CustomerID, req.Items, req.Coupon)
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusCreated, o)
}

// getOrder serves GET /orders/{id}.
func (s *Server) getOrder(w http.ResponseWriter, r *http.Request) {
	s.act(w, r, s.orders.Get)
}

func (s *Server) payOrder(w http.ResponseWriter, r *http.Request)     { s.act(w, r, s.orders.Pay) }
func (s *Server) shipOrder(w http.ResponseWriter, r *http.Request)    { s.act(w, r, s.orders.Ship) }
func (s *Server) deliverOrder(w http.ResponseWriter, r *http.Request) { s.act(w, r, s.orders.Deliver) }
func (s *Server) cancelOrder(w http.ResponseWriter, r *http.Request)  { s.act(w, r, s.orders.Cancel) }
func (s *Server) refundOrder(w http.ResponseWriter, r *http.Request)  { s.act(w, r, s.orders.Refund) }

// act runs a lifecycle step on the order named in the path.
func (s *Server) act(w http.ResponseWriter, r *http.Request, step func(string) (orders.Order, error)) {
	o, err := step(r.PathValue("id"))
	if err != nil {
		writeError(w, err)
		return
	}
	writeJSON(w, http.StatusOK, o)
}
