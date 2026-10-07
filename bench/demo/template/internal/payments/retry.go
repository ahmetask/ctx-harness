package payments

import (
	"errors"
	"time"
)

// RetryPolicy retries transient provider failures.
type RetryPolicy struct {
	Attempts int
	Backoff  time.Duration // multiplied by the attempt number
}

// DefaultRetry is three attempts with a short linear backoff.
func DefaultRetry() RetryPolicy { return RetryPolicy{Attempts: 3, Backoff: 50 * time.Millisecond} }

// Do calls fn until it succeeds, fails with a non-transient error, or runs
// out of attempts.
func (p RetryPolicy) Do(fn func() error) error {
	attempts := p.Attempts
	if attempts < 1 {
		attempts = 1
	}
	var err error
	for i := 0; i < attempts; i++ {
		if err = fn(); err == nil || !errors.Is(err, ErrTransient) {
			return err
		}
		if p.Backoff > 0 && i < attempts-1 {
			time.Sleep(p.Backoff * time.Duration(i+1))
		}
	}
	return err
}
