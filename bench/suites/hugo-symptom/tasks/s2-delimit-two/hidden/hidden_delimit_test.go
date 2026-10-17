package collections

import (
	"context"
	"testing"

	qt "github.com/frankban/quicktest"
)

func TestHiddenDelimitLastSeparator(t *testing.T) {
	c := qt.New(t)
	ns := newNs()

	for _, test := range []struct {
		seq    any
		last   any
		expect string
	}{
		{[]string{"Hugo", "Go"}, " and ", "Hugo and Go"},
		{[]int{1, 2}, " & ", "1 & 2"},
		{[]string{"A", "B", "C"}, " and ", "A, B and C"},
		{[]string{"A"}, " and ", "A"},
	} {
		got, err := ns.Delimit(context.Background(), test.seq, ", ", test.last)
		c.Assert(err, qt.IsNil)
		c.Assert(got, qt.Equals, test.expect)
	}
}
