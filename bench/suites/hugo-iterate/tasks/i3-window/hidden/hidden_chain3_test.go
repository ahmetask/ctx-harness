package collections

import (
	"testing"

	qt "github.com/frankban/quicktest"
)

func TestHiddenWindow(t *testing.T) {
	c := qt.New(t)
	ns := newNs()

	for _, test := range []struct {
		size   any
		l      any
		expect [][]any
	}{
		{3, []int{1, 2, 3, 4}, [][]any{{1, 2, 3}, {2, 3, 4}}},
		{2, []string{"a", "b", "c"}, [][]any{{"a", "b"}, {"b", "c"}}},
		{1, []int{7, 8}, [][]any{{7}, {8}}},
		{3, []int{1, 2}, [][]any{}},
		{2, [2]int{5, 6}, [][]any{{5, 6}}},
		{int64(2), []int{}, [][]any{}},
	} {
		got, err := ns.Window(test.size, test.l)
		c.Assert(err, qt.IsNil)
		c.Assert(got, qt.DeepEquals, test.expect)
	}
}

// window must reject exactly what chunk rejects, with the same message.
func TestHiddenWindowValidatesLikeChunk(t *testing.T) {
	c := qt.New(t)
	ns := newNs()

	for _, test := range []struct {
		size any
		l    any
	}{
		{0, []int{1}},
		{-2, []int{1}},
		{"x", []int{1}},
		{2, "abc"},
		{2, nil},
		{2, 42},
	} {
		_, cerr := ns.Chunk(test.size, test.l)
		_, werr := ns.Window(test.size, test.l)
		c.Assert(cerr, qt.Not(qt.IsNil))
		c.Assert(werr, qt.Not(qt.IsNil))
		c.Assert(werr.Error(), qt.Equals, cerr.Error(), qt.Commentf("%v %v", test.size, test.l))
	}
}
