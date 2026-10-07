package catalog

import (
	"errors"
	"sort"
	"sync"
)

// ErrNotFound is returned for unknown or archived SKUs.
var ErrNotFound = errors.New("catalog: product not found")

// Store holds the product catalog in memory.
type Store struct {
	mu       sync.RWMutex
	products map[string]Product
}

// NewStore returns an empty catalog.
func NewStore() *Store { return &Store{products: map[string]Product{}} }

// Put adds or replaces p.
func (s *Store) Put(p Product) {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.products[p.SKU] = p
}

// Get returns the product with sku, archived or not.
func (s *Store) Get(sku string) (Product, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()
	p, ok := s.products[sku]
	if !ok {
		return Product{}, ErrNotFound
	}
	return p, nil
}

// Lookup returns the product with sku if it can still be sold.
func (s *Store) Lookup(sku string) (Product, error) {
	p, err := s.Get(sku)
	if err != nil || p.Archived {
		return Product{}, ErrNotFound
	}
	return p, nil
}

// All returns sellable products ordered by SKU.
func (s *Store) All() []Product {
	s.mu.RLock()
	defer s.mu.RUnlock()
	out := make([]Product, 0, len(s.products))
	for _, p := range s.products {
		if !p.Archived {
			out = append(out, p)
		}
	}
	sort.Slice(out, func(i, j int) bool { return out[i].SKU < out[j].SKU })
	return out
}
