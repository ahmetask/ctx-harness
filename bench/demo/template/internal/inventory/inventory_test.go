package inventory

import (
	"errors"
	"testing"
)

func TestReserveAllOrNothing(t *testing.T) {
	inv := New()
	inv.Set("A", 2)
	inv.Set("B", 1)
	err := inv.Reserve("o1", []Line{{"A", 1}, {"B", 2}})
	if !errors.Is(err, ErrInsufficient) {
		t.Fatalf("err = %v, want ErrInsufficient", err)
	}
	if inv.Available("A") != 2 {
		t.Fatalf("partial reservation leaked: A available %d", inv.Available("A"))
	}
}

func TestDuplicateSKUsAreSummed(t *testing.T) {
	inv := New()
	inv.Set("A", 3)
	if err := inv.Reserve("o1", []Line{{"A", 2}, {"A", 2}}); !errors.Is(err, ErrInsufficient) {
		t.Fatalf("err = %v, want ErrInsufficient", err)
	}
}

func TestReleaseAndCommit(t *testing.T) {
	inv := New()
	inv.Set("A", 5)
	if err := inv.Reserve("o1", []Line{{"A", 2}}); err != nil {
		t.Fatal(err)
	}
	inv.Release("o1")
	inv.Release("o1")
	if inv.Available("A") != 5 {
		t.Fatalf("available after release = %d", inv.Available("A"))
	}
	if err := inv.Reserve("o2", []Line{{"A", 3}}); err != nil {
		t.Fatal(err)
	}
	if err := inv.Commit("o2"); err != nil {
		t.Fatal(err)
	}
	if inv.OnHand("A") != 2 || inv.Available("A") != 2 {
		t.Fatalf("on hand %d, available %d", inv.OnHand("A"), inv.Available("A"))
	}
}
