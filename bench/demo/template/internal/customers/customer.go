package customers

import (
	"errors"
	"fmt"
	"strings"
)

// ErrInvalid wraps validation failures.
var ErrInvalid = errors.New("customers: invalid customer")

// Customer is someone who can place orders.
type Customer struct {
	ID    string `json:"id"`
	Name  string `json:"name"`
	Email string `json:"email"`
}

// Validate checks the fields a customer needs to receive notifications.
func (c Customer) Validate() error {
	if c.ID == "" {
		return fmt.Errorf("%w: id is required", ErrInvalid)
	}
	if !strings.Contains(c.Email, "@") {
		return fmt.Errorf("%w: email %q", ErrInvalid, c.Email)
	}
	return nil
}
