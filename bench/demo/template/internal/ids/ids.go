package ids

import (
	"fmt"
	"sync"
)

// Generator hands out unique IDs such as "ord-0001".
type Generator interface {
	Next(prefix string) string
}

// Sequence is a Generator that counts per prefix. IDs are predictable,
// which keeps tests and demo data stable.
type Sequence struct {
	mu sync.Mutex
	n  map[string]int
}

// NewSequence returns a Sequence starting at 1 for every prefix.
func NewSequence() *Sequence { return &Sequence{n: map[string]int{}} }

// Next returns the next ID for prefix.
func (s *Sequence) Next(prefix string) string {
	s.mu.Lock()
	defer s.mu.Unlock()
	s.n[prefix]++
	return fmt.Sprintf("%s-%04d", prefix, s.n[prefix])
}
