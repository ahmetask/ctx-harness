package catalog

import (
	"testing"

	"shopd/internal/money"
)

func seeded() *Store {
	s := NewStore()
	s.Put(Product{SKU: "B", Name: "Blue Mug", Price: money.New(1200, money.USD), Tags: []string{"kitchen"}})
	s.Put(Product{SKU: "A", Name: "Lamp", Price: money.New(5000, money.USD), Tags: []string{"Office"}})
	s.Put(Product{SKU: "C", Name: "Old Mug", Price: money.New(900, money.USD), Archived: true})
	return s
}

func TestLookupHidesArchived(t *testing.T) {
	s := seeded()
	if _, err := s.Lookup("C"); err != ErrNotFound {
		t.Fatalf("Lookup(archived) err = %v, want ErrNotFound", err)
	}
	if _, err := s.Get("C"); err != nil {
		t.Fatalf("Get(archived) err = %v, want nil", err)
	}
}

func TestSearch(t *testing.T) {
	s := seeded()
	got := s.Search("MUG")
	if len(got) != 1 || got[0].SKU != "B" {
		t.Fatalf("Search(MUG) = %+v", got)
	}
	if got := s.Search("office"); len(got) != 1 || got[0].SKU != "A" {
		t.Fatalf("Search(office) = %+v", got)
	}
	if got := s.Search(""); len(got) != 2 || got[0].SKU != "A" {
		t.Fatalf("Search() = %+v", got)
	}
}
