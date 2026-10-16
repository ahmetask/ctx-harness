package tableofcontents

import (
	"strings"
	"testing"

	qt "github.com/frankban/quicktest"
)

func TestHiddenEndLevelIsInclusive(t *testing.T) {
	c := qt.New(t)

	var b Builder
	b.AddAt(&Heading{Title: "Title", ID: "lvl1"}, 0, 0)
	b.AddAt(&Heading{Title: "Section", ID: "lvl2"}, 0, 1)
	b.AddAt(&Heading{Title: "Subsection", ID: "lvl3"}, 0, 2)
	b.AddAt(&Heading{Title: "Detail", ID: "lvl4"}, 0, 3)
	toc := b.Build()

	for _, test := range []struct {
		start, stop int
		want        []string
		notWant     []string
	}{
		{2, 3, []string{"#lvl2", "#lvl3"}, []string{"#lvl1", "#lvl4"}},
		{2, 4, []string{"#lvl2", "#lvl3", "#lvl4"}, []string{"#lvl1"}},
		{2, 2, []string{"#lvl2"}, []string{"#lvl1", "#lvl3", "#lvl4"}},
		{1, -1, []string{"#lvl1", "#lvl2", "#lvl3", "#lvl4"}, nil},
	} {
		html, err := toc.ToHTML(test.start, test.stop, false)
		c.Assert(err, qt.IsNil)
		got := string(html)
		for _, w := range test.want {
			c.Assert(strings.Contains(got, w), qt.IsTrue, qt.Commentf("start %d stop %d: missing %s in %s", test.start, test.stop, w, got))
		}
		for _, w := range test.notWant {
			c.Assert(strings.Contains(got, w), qt.IsFalse, qt.Commentf("start %d stop %d: unexpected %s in %s", test.start, test.stop, w, got))
		}
	}
}
