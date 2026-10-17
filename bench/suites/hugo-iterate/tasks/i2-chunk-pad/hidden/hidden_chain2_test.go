package collections

import (
	"testing"

	qt "github.com/frankban/quicktest"
)

func TestHiddenChunkPad(t *testing.T) {
	c := qt.New(t)
	ns := newNs()

	got, err := ns.Chunk(2, []int{1, 2, 3}, 0)
	c.Assert(err, qt.IsNil)
	c.Assert(got, qt.DeepEquals, [][]any{{1, 2}, {3, 0}})

	got, err = ns.Chunk(3, []string{"a"}, "-")
	c.Assert(err, qt.IsNil)
	c.Assert(got, qt.DeepEquals, [][]any{{"a", "-", "-"}})

	got, err = ns.Chunk(2, []int{1, 2, 3, 4}, 9)
	c.Assert(err, qt.IsNil)
	c.Assert(got, qt.DeepEquals, [][]any{{1, 2}, {3, 4}})

	// only the first pad is used, and nil is a valid pad
	got, err = ns.Chunk(2, []int{1}, nil, "ignored")
	c.Assert(err, qt.IsNil)
	c.Assert(got, qt.DeepEquals, [][]any{{1, nil}})

	// no pad: unchanged
	got, err = ns.Chunk(2, []int{1, 2, 3})
	c.Assert(err, qt.IsNil)
	c.Assert(got, qt.DeepEquals, [][]any{{1, 2}, {3}})

	// padding must not alias neighbouring chunks
	in := []int{1, 2, 3}
	got, err = ns.Chunk(2, in, 0)
	c.Assert(err, qt.IsNil)
	c.Assert(in, qt.DeepEquals, []int{1, 2, 3})
	c.Assert(got[0], qt.DeepEquals, []any{1, 2})

	_, err = ns.Chunk(0, in, 0)
	c.Assert(err, qt.Not(qt.IsNil))
}
