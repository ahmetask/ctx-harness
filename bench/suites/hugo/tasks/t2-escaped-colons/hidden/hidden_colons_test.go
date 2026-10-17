package page

import (
	"testing"
	"time"

	qt "github.com/frankban/quicktest"
)

func TestHiddenEscapedColons(t *testing.T) {
	c := qt.New(t)

	page := newTestPageWithFile("/test-page/index.md")
	page.title = "Spf13 Vim 3.0 Release and new website"
	page.date = time.Date(2012, 4, 6, 3, 1, 59, 0, time.UTC)
	page.section = "blue"
	page.slug = "The Slug"
	page.kind = "page"

	for _, test := range []struct{ spec, expect string }{
		{`/docs\:v2\:beta/:slug/`, "/docs:v2:beta/the-slug/"},
		{`/a\:b\:c\:d/:section/`, "/a:b:c:d/blue/"},
		{`/a\:b\:c/`, "/a:b:c/"},
		{`/special\::slug/`, "/special:the-slug/"},
	} {
		expander, err := NewPermalinkExpander(urlize, map[string]map[string]string{"page": {"posts": test.spec}})
		c.Assert(err, qt.IsNil)
		got, err := expander.Expand("posts", page)
		c.Assert(err, qt.IsNil)
		c.Assert(got, qt.Equals, test.expect, qt.Commentf("spec %q", test.spec))
		got, err = expander.ExpandPattern(test.spec, page)
		c.Assert(err, qt.IsNil)
		c.Assert(got, qt.Equals, test.expect, qt.Commentf("spec %q via ExpandPattern", test.spec))
	}
}
