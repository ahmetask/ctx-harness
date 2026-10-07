package payments

import (
	"errors"
	"fmt"
	"sync"

	"shopd/internal/money"
)

var (
	// ErrTransient marks failures worth retrying: timeouts, provider 5xx.
	ErrTransient = errors.New("payments: transient failure")
	// ErrDeclined means the provider refused the charge; retrying will not help.
	ErrDeclined = errors.New("payments: card declined")
)

// Charge is a captured payment.
type Charge struct {
	ID     string
	Key    string
	Amount money.Money
}

// Gateway is the payment provider.
type Gateway interface {
	Charge(key string, amount money.Money) (Charge, error)
	Refund(chargeID string, amount money.Money) error
}

// FakeGateway is an in-memory provider. Like the real one, it treats two
// charges with the same key as one.
type FakeGateway struct {
	mu          sync.Mutex
	byKey       map[string]Charge
	refunded    map[string]int64
	seq         int
	FailNext    int  // the next FailNext calls fail with ErrTransient
	DeclineNext bool // the next charge is declined
	Calls       int
}

// NewFakeGateway returns a provider with no charges.
func NewFakeGateway() *FakeGateway {
	return &FakeGateway{byKey: map[string]Charge{}, refunded: map[string]int64{}}
}

// Charge captures amount under key, or returns the earlier charge for key.
func (g *FakeGateway) Charge(key string, amount money.Money) (Charge, error) {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.Calls++
	if g.FailNext > 0 {
		g.FailNext--
		return Charge{}, ErrTransient
	}
	if g.DeclineNext {
		g.DeclineNext = false
		return Charge{}, ErrDeclined
	}
	if c, ok := g.byKey[key]; ok {
		return c, nil
	}
	g.seq++
	c := Charge{ID: fmt.Sprintf("ch_%04d", g.seq), Key: key, Amount: amount}
	g.byKey[key] = c
	return c, nil
}

// Refund returns amount of a charge to the customer.
func (g *FakeGateway) Refund(chargeID string, amount money.Money) error {
	g.mu.Lock()
	defer g.mu.Unlock()
	g.Calls++
	for _, c := range g.byKey {
		if c.ID != chargeID {
			continue
		}
		if g.refunded[chargeID]+amount.Amount > c.Amount.Amount {
			return fmt.Errorf("payments: refund exceeds charge %s", chargeID)
		}
		g.refunded[chargeID] += amount.Amount
		return nil
	}
	return fmt.Errorf("payments: unknown charge %s", chargeID)
}

// Charges is the number of distinct charges captured.
func (g *FakeGateway) Charges() int {
	g.mu.Lock()
	defer g.mu.Unlock()
	return len(g.byKey)
}

// Refunded is the amount refunded so far on a charge.
func (g *FakeGateway) Refunded(chargeID string) int64 {
	g.mu.Lock()
	defer g.mu.Unlock()
	return g.refunded[chargeID]
}
