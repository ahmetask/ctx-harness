package orders

import (
	"errors"
	"fmt"

	"shopd/internal/audit"
	"shopd/internal/catalog"
	"shopd/internal/clock"
	"shopd/internal/customers"
	"shopd/internal/ids"
	"shopd/internal/inventory"
	"shopd/internal/notify"
	"shopd/internal/payments"
	"shopd/internal/pricing"
	"shopd/internal/shipping"
	"shopd/internal/storage"
)

var (
	// ErrNotFound is returned for unknown order IDs.
	ErrNotFound = errors.New("orders: order not found")
	// ErrInvalidTransition is returned when the lifecycle forbids a step.
	ErrInvalidTransition = errors.New("orders: invalid state transition")
)

// Deps are the collaborators of the order service.
type Deps struct {
	Catalog   *catalog.Store
	Customers *customers.Store
	Inventory *inventory.Inventory
	Pricing   *pricing.Engine
	Payments  *payments.Client
	Notifier  *notify.Notifier
	IDs       ids.Generator
	Clock     clock.Clock
	Audit     *audit.Log
}

// Service runs the order lifecycle.
type Service struct {
	Deps
	orders *storage.Memory[Order]
}

// NewService returns a service with no orders.
func NewService(d Deps) *Service { return &Service{Deps: d, orders: storage.NewMemory[Order]()} }

// Get returns the order with id.
func (s *Service) Get(id string) (Order, error) {
	o, ok := s.orders.Get(id)
	if !ok {
		return Order{}, ErrNotFound
	}
	return o, nil
}

// List returns all orders ordered by ID.
func (s *Service) List() []Order { return s.orders.List() }

// Place prices an order and reserves its stock. Payment is a separate step.
func (s *Service) Place(customerID string, items []Item, coupon string) (Order, error) {
	if err := validateItems(customerID, items); err != nil {
		return Order{}, err
	}
	if _, err := s.Customers.Get(customerID); err != nil {
		return Order{}, fmt.Errorf("%w: %v", ErrInvalid, err)
	}
	lines := make([]pricing.Line, 0, len(items))
	holds := make([]inventory.Line, 0, len(items))
	for _, it := range items {
		p, err := s.Catalog.Lookup(it.SKU)
		if err != nil {
			return Order{}, fmt.Errorf("%w: %s: %v", ErrInvalid, it.SKU, err)
		}
		lines = append(lines, pricing.Line{SKU: p.SKU, Qty: int64(it.Qty), Unit: p.Price})
		holds = append(holds, inventory.Line{SKU: p.SKU, Qty: it.Qty})
	}
	q, err := s.Pricing.Quote(lines, coupon)
	if err != nil {
		return Order{}, fmt.Errorf("%w: %v", ErrInvalid, err)
	}
	now := s.Clock.Now()
	o := Order{
		ID: s.IDs.Next("ord"), CustomerID: customerID, Lines: lines, Coupon: coupon,
		Quote: q, State: StatePending, CreatedAt: now, UpdatedAt: now,
	}
	if err := s.Inventory.Reserve(o.ID, holds); err != nil {
		return Order{}, err
	}
	s.orders.Put(o.ID, o)
	s.Audit.Record(eventPlaced, "order", o.ID, "total", o.Quote.Total.String())
	return o, nil
}

// Pay charges the order total. A failed payment cancels the order.
func (s *Service) Pay(id string) (Order, error) {
	o, err := s.Get(id)
	if err != nil {
		return Order{}, err
	}
	if !CanTransition(o.State, StatePaid) {
		return Order{}, fmt.Errorf("%w: %s -> %s", ErrInvalidTransition, o.State, StatePaid)
	}
	ch, err := s.Payments.Charge(payments.IdempotencyKey(o.ID), o.Quote.Total)
	if err != nil {
		s.Inventory.Release(o.ID)
		s.Audit.Record(eventPaymentFailed, "order", o.ID, "error", err.Error())
		if _, cerr := s.transition(o, StateCancelled); cerr != nil {
			return Order{}, errors.Join(err, cerr)
		}
		return Order{}, err
	}
	o.PaymentID = ch.ID
	if err := s.Inventory.Commit(o.ID); err != nil {
		return Order{}, err
	}
	return s.transition(o, StatePaid)
}

// Ship hands a paid order to a carrier.
func (s *Service) Ship(id string) (Order, error) {
	o, err := s.Get(id)
	if err != nil {
		return Order{}, err
	}
	weight := 0
	for _, l := range o.Lines {
		if p, err := s.Catalog.Get(l.SKU); err == nil {
			weight += p.WeightG * int(l.Qty)
		}
	}
	o.Tracking = shipping.TrackingNumber(shipping.CarrierFor(weight), o.ID)
	return s.transition(o, StateShipped)
}

// Deliver marks a shipped order as delivered.
func (s *Service) Deliver(id string) (Order, error) {
	o, err := s.Get(id)
	if err != nil {
		return Order{}, err
	}
	return s.transition(o, StateDelivered)
}

// Cancel cancels an order that has not been paid.
func (s *Service) Cancel(id string) (Order, error) {
	o, err := s.Get(id)
	if err != nil {
		return Order{}, err
	}
	return s.transition(o, StateCancelled)
}

// transition moves o to state to, notifies the customer, and saves it.
func (s *Service) transition(o Order, to State) (Order, error) {
	if !CanTransition(o.State, to) {
		return Order{}, fmt.Errorf("%w: %s -> %s", ErrInvalidTransition, o.State, to)
	}
	c, err := s.Customers.Get(o.CustomerID)
	if err != nil {
		return Order{}, err
	}
	data := map[string]string{
		"order": o.ID, "name": c.Name, "total": o.Quote.Total.String(), "tracking": o.Tracking,
	}
	if err := s.Notifier.Notify(c.Email, string(to), data); err != nil {
		return Order{}, fmt.Errorf("orders: notify %s: %w", to, err)
	}
	from := o.State
	o.State, o.UpdatedAt = to, s.Clock.Now()
	s.orders.Put(o.ID, o)
	s.Audit.Record(eventTransition, "order", o.ID, "from", string(from), "to", string(to))
	return o, nil
}
