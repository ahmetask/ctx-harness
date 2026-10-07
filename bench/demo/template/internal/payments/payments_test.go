package payments

import (
	"errors"
	"testing"

	"shopd/internal/money"
)

func client(gw Gateway) *Client { return NewClient(gw, RetryPolicy{Attempts: 3}) }

func TestRetryReusesKey(t *testing.T) {
	gw := NewFakeGateway()
	gw.FailNext = 2
	ch, err := client(gw).Charge(IdempotencyKey("o1"), money.New(500, money.USD))
	if err != nil {
		t.Fatal(err)
	}
	if gw.Calls != 3 || gw.Charges() != 1 || ch.Amount.Amount != 500 {
		t.Fatalf("calls %d, charges %d, charge %+v", gw.Calls, gw.Charges(), ch)
	}
}

func TestDeclineIsNotRetried(t *testing.T) {
	gw := NewFakeGateway()
	gw.DeclineNext = true
	_, err := client(gw).Charge(IdempotencyKey("o1"), money.New(500, money.USD))
	if !errors.Is(err, ErrDeclined) || gw.Calls != 1 {
		t.Fatalf("err %v after %d calls", err, gw.Calls)
	}
}

func TestRefundCannotExceedCharge(t *testing.T) {
	gw := NewFakeGateway()
	c := client(gw)
	ch, _ := c.Charge(IdempotencyKey("o1"), money.New(500, money.USD))
	if err := c.Refund(ch.ID, money.New(300, money.USD)); err != nil {
		t.Fatal(err)
	}
	if err := c.Refund(ch.ID, money.New(300, money.USD)); err == nil {
		t.Fatal("expected over-refund to fail")
	}
	if gw.Refunded(ch.ID) != 300 {
		t.Fatalf("refunded %d", gw.Refunded(ch.ID))
	}
}
