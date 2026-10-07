package customers

import (
	"errors"

	"shopd/internal/storage"
)

// ErrNotFound is returned for unknown customer IDs.
var ErrNotFound = errors.New("customers: not found")

// Store keeps customers in memory.
type Store struct {
	rows *storage.Memory[Customer]
}

// NewStore returns an empty store.
func NewStore() *Store { return &Store{rows: storage.NewMemory[Customer]()} }

// Put validates and stores c.
func (s *Store) Put(c Customer) error {
	if err := c.Validate(); err != nil {
		return err
	}
	s.rows.Put(c.ID, c)
	return nil
}

// Get returns the customer with id.
func (s *Store) Get(id string) (Customer, error) {
	c, ok := s.rows.Get(id)
	if !ok {
		return Customer{}, ErrNotFound
	}
	return c, nil
}
