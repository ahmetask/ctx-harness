package page

import (
	"testing"
	"time"

	qt "github.com/frankban/quicktest"
)

func TestHiddenIsoWeekTokens(t *testing.T) {
	c := qt.New(t)

	for _, test := range []struct {
		date   time.Time
		expect string
	}{
		{time.Date(2012, 4, 6, 3, 1, 59, 0, time.UTC), "/2012/w14/"},
		{time.Date(2021, 1, 3, 12, 0, 0, 0, time.UTC), "/2020/w53/"},   // year is 2021, ISO year is 2020
		{time.Date(2024, 12, 30, 12, 0, 0, 0, time.UTC), "/2025/w01/"}, // ISO year is ahead of the year
		{time.Date(2019, 2, 5, 12, 0, 0, 0, time.UTC), "/2019/w06/"},   // week is zero-padded
	} {
		page := newTestPageWithFile("/test-page/index.md")
		page.date = test.date
		page.kind = "page"

		expander, err := NewPermalinkExpander(urlize, map[string]map[string]string{
			"page": {"posts": "/:isoyear/w:isoweek/"},
		})
		c.Assert(err, qt.IsNil)
		got, err := expander.Expand("posts", page)
		c.Assert(err, qt.IsNil)
		c.Assert(got, qt.Equals, test.expect, qt.Commentf("date %s", test.date))
	}

	// Existing tokens keep working next to the new ones.
	page := newTestPageWithFile("/test-page/index.md")
	page.date = time.Date(2021, 1, 3, 12, 0, 0, 0, time.UTC)
	page.kind = "page"
	expander, err := NewPermalinkExpander(urlize, map[string]map[string]string{
		"page": {"posts": "/:year/:isoyear/:month/:isoweek/"},
	})
	c.Assert(err, qt.IsNil)
	got, err := expander.Expand("posts", page)
	c.Assert(err, qt.IsNil)
	c.Assert(got, qt.Equals, "/2021/2020/01/53/")
}
