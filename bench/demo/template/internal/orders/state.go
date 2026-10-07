package orders

// State is a step in the order lifecycle.
type State string

const (
	StatePending   State = "pending"
	StatePaid      State = "paid"
	StateShipped   State = "shipped"
	StateDelivered State = "delivered"
	StateCancelled State = "cancelled"
)

var transitions = map[State][]State{
	StatePending: {StatePaid, StateCancelled},
	StatePaid:    {StateShipped},
	StateShipped: {StateDelivered},
}

// CanTransition reports whether an order may move from one state to another.
func CanTransition(from, to State) bool {
	for _, s := range transitions[from] {
		if s == to {
			return true
		}
	}
	return false
}

// Terminal reports whether no transition leaves s.
func (s State) Terminal() bool { return len(transitions[s]) == 0 }
