package catalog

import "strings"

// Search returns sellable products whose name or tags contain q, ignoring
// case, ordered by SKU. An empty query returns everything sellable.
func (s *Store) Search(q string) []Product {
	q = strings.ToLower(strings.TrimSpace(q))
	var out []Product
	for _, p := range s.All() {
		if q == "" || matches(p, q) {
			out = append(out, p)
		}
	}
	return out
}

func matches(p Product, q string) bool {
	if strings.Contains(strings.ToLower(p.Name), q) {
		return true
	}
	for _, t := range p.Tags {
		if strings.Contains(strings.ToLower(t), q) {
			return true
		}
	}
	return false
}
