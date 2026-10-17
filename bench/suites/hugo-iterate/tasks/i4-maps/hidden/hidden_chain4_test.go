package collections

import (
	"testing"

	qt "github.com/frankban/quicktest"
)

func TestHiddenChunkAndWindowMaps(t *testing.T) {
	c := qt.New(t)
	ns := newNs()

	m := map[string]int{"b": 2, "a": 1, "c": 3}

	got, err := ns.Chunk(2, m)
	c.Assert(err, qt.IsNil)
	c.Assert(got, qt.DeepEquals, [][]any{{1, 2}, {3}})

	got, err = ns.Chunk(2, m, 0)
	c.Assert(err, qt.IsNil)
	c.Assert(got, qt.DeepEquals, [][]any{{1, 2}, {3, 0}})

	got, err = ns.Window(2, m)
	c.Assert(err, qt.IsNil)
	c.Assert(got, qt.DeepEquals, [][]any{{1, 2}, {2, 3}})

	got, err = ns.Chunk(2, map[string]string{})
	c.Assert(err, qt.IsNil)
	c.Assert(got, qt.DeepEquals, [][]any{})

	// strings and numbers are still rejected, with the same message from both
	for _, bad := range []any{"abc", 42, nil} {
		_, cerr := ns.Chunk(2, bad)
		_, werr := ns.Window(2, bad)
		c.Assert(cerr, qt.Not(qt.IsNil))
		c.Assert(werr, qt.Not(qt.IsNil))
		c.Assert(werr.Error(), qt.Equals, cerr.Error())
	}
}
