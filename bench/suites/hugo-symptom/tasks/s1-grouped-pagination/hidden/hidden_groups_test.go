package page

import (
	"context"
	"testing"

	qt "github.com/frankban/quicktest"
)

func TestHiddenSplitPageGroupsKeepsGroupsApart(t *testing.T) {
	c := qt.New(t)
	pages := createTestPages(21)
	groups, _ := pages.GroupBy(context.Background(), "Weight", "desc")
	chunks := splitPageGroups(groups, 5)

	var total int
	var spanning int
	for _, chunk := range chunks {
		pg, ok := chunk.(PagesGroup)
		c.Assert(ok, qt.IsTrue)
		if len(pg) > 1 {
			spanning++
		}
		for _, g := range pg {
			for _, p := range g.Pages {
				total++
				even := p.FuzzyWordCount(context.Background())%2 == 0
				c.Assert(even, qt.Equals, g.Key == 10, qt.Commentf("page filed under group %v", g.Key))
			}
		}
	}
	c.Assert(total, qt.Equals, 21)
	c.Assert(spanning, qt.Equals, 1)

	mid := chunks[2].(PagesGroup)
	c.Assert(mid, qt.HasLen, 2)
	c.Assert(mid[0].Key, qt.Equals, 10)
	c.Assert(mid[0].Pages, qt.HasLen, 1)
	c.Assert(mid[1].Key, qt.Equals, 5)
	c.Assert(mid[1].Pages, qt.HasLen, 4)
}
