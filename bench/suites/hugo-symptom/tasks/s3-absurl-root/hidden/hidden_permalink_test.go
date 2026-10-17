package paths

import "testing"

func TestHiddenMakePermalinkEmptyLinkKeepsBaseSlash(t *testing.T) {
	for _, test := range []struct{ host, link, want string }{
		{"https://example.org/docs/", "", "https://example.org/docs/"},
		{"https://example.org/", "", "https://example.org/"},
		{"https://example.org/docs", "", "https://example.org/docs"},
		{"https://example.org/docs/", "guide/", "https://example.org/docs/guide/"},
	} {
		if got := MakePermalink(test.host, test.link).String(); got != test.want {
			t.Errorf("MakePermalink(%q, %q) = %q, want %q", test.host, test.link, got, test.want)
		}
	}
}
