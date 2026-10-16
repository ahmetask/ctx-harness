package hugolib

import "testing"

func TestHiddenIsoWeekSite(t *testing.T) {
	t.Parallel()

	files := `
-- hugo.toml --
baseURL = "https://example.org/"
[permalinks.page]
posts = "/:isoyear/w:isoweek/:slug/"
-- content/posts/p1.md --
---
title: P1
date: 2021-01-03
slug: s1
---
-- content/posts/p2.md --
---
title: P2
date: 2019-02-05
slug: s2
---
-- layouts/_default/single.html --
{{ .Permalink }}
`

	b := Test(t, files)
	b.AssertFileContent("public/2020/w53/s1/index.html", "https://example.org/2020/w53/s1/")
	b.AssertFileContent("public/2019/w06/s2/index.html", "https://example.org/2019/w06/s2/")
}
