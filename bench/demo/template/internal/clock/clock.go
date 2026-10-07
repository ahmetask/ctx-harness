package clock

import "time"

// Clock tells the time. Services take a Clock instead of calling time.Now
// so tests can pin it.
type Clock interface {
	Now() time.Time
}

// System is the wall clock in UTC.
type System struct{}

// Now returns the current time in UTC.
func (System) Now() time.Time { return time.Now().UTC() }

// Fixed always returns T.
type Fixed struct{ T time.Time }

// Now returns T.
func (f Fixed) Now() time.Time { return f.T }
