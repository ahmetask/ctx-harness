package collections

import (
	"testing"

	qt "github.com/frankban/quicktest"
)

func TestHiddenChunk(t *testing.T) {
	c := qt.New(t)
	ns := newNs()

	for _, test := range []struct {
		size   any
		l      any
		expect [][]any
	}{
		{2, []int{1, 2, 3, 4, 5}, [][]any{{1, 2}, {3, 4}, {5}}},
		{int64(3), []string{"a", "b", "c"}, [][]any{{"a", "b", "c"}}},
		{5, []int{1, 2}, [][]any{{1, 2}}},
		{1, [2]string{"x", "y"}, [][]any{{"x"}, {"y"}}},
		{2, []int{}, [][]any{}},
	} {
		got, err := ns.Chunk(test.size, test.l)
		c.Assert(err, qt.IsNil)
		c.Assert(got, qt.DeepEquals, test.expect)
	}
}

func TestHiddenChunkErrors(t *testing.T) {
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
		_, err := ns.Chunk(test.size, test.l)
		c.Assert(err, qt.Not(qt.IsNil), qt.Commentf("%v %v", test.size, test.l))
	}
}
