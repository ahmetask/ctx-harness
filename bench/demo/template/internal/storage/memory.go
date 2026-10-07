package storage

import (
	"sort"
	"sync"
)

// Memory is a concurrency-safe in-memory table keyed by ID.
type Memory[T any] struct {
	mu    sync.RWMutex
	items map[string]T
}

// NewMemory returns an empty table.
func NewMemory[T any]() *Memory[T] { return &Memory[T]{items: map[string]T{}} }

// Get returns the item stored under id.
func (m *Memory[T]) Get(id string) (T, bool) {
	m.mu.RLock()
	defer m.mu.RUnlock()
	v, ok := m.items[id]
	return v, ok
}

// Put stores v under id, replacing any previous value.
func (m *Memory[T]) Put(id string, v T) {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.items[id] = v
}

// List returns all items ordered by ID.
func (m *Memory[T]) List() []T {
	m.mu.RLock()
	defer m.mu.RUnlock()
	ids := make([]string, 0, len(m.items))
	for id := range m.items {
		ids = append(ids, id)
	}
	sort.Strings(ids)
	out := make([]T, 0, len(ids))
	for _, id := range ids {
		out = append(out, m.items[id])
	}
	return out
}
