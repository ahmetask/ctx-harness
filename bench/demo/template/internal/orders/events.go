package orders

// Audit event names written by the service.
const (
	eventPlaced        = "order.placed"
	eventTransition    = "order.transition"
	eventPaymentFailed = "order.payment_failed"
)
