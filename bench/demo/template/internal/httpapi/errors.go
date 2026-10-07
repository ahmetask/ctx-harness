package httpapi

import (
	"errors"
	"fmt"
	"net/http"

	"shopd/internal/catalog"
	"shopd/internal/inventory"
	"shopd/internal/orders"
	"shopd/internal/payments"
)

var errBadRequest = errors.New("bad request")

func badRequest(err error) error { return fmt.Errorf("%w: %v", errBadRequest, err) }

type apiError struct {
	Error string `json:"error"`
	Code  string `json:"code"`
}

// writeError maps domain errors to HTTP statuses.
func writeError(w http.ResponseWriter, err error) {
	status, code := http.StatusInternalServerError, "internal"
	switch {
	case errors.Is(err, errBadRequest), errors.Is(err, orders.ErrInvalid):
		status, code = http.StatusBadRequest, "invalid"
	case errors.Is(err, orders.ErrNotFound), errors.Is(err, catalog.ErrNotFound):
		status, code = http.StatusNotFound, "not_found"
	case errors.Is(err, orders.ErrInvalidTransition):
		status, code = http.StatusConflict, "conflict"
	case errors.Is(err, inventory.ErrInsufficient):
		status, code = http.StatusConflict, "out_of_stock"
	case errors.Is(err, payments.ErrDeclined):
		status, code = http.StatusPaymentRequired, "declined"
	}
	writeJSON(w, status, apiError{Error: err.Error(), Code: code})
}
