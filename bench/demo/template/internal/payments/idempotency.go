package payments

// IdempotencyKey is the provider key for charging an order. It depends on
// the order alone, so every attempt for the same order maps to one charge.
func IdempotencyKey(orderID string) string { return "order:" + orderID + ":charge" }
