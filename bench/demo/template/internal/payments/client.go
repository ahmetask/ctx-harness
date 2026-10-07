package payments

import "shopd/internal/money"

// Client talks to the provider with retries.
type Client struct {
	gw     Gateway
	policy RetryPolicy
}

// NewClient wraps gw with policy.
func NewClient(gw Gateway, policy RetryPolicy) *Client { return &Client{gw: gw, policy: policy} }

// Charge captures amount under key, retrying transient failures.
func (c *Client) Charge(key string, amount money.Money) (Charge, error) {
	var ch Charge
	err := c.policy.Do(func() error {
		var err error
		ch, err = c.gw.Charge(key, amount)
		return err
	})
	return ch, err
}

// Refund returns amount of a charge, retrying transient failures.
func (c *Client) Refund(chargeID string, amount money.Money) error {
	return c.policy.Do(func() error { return c.gw.Refund(chargeID, amount) })
}
