package strings

import (
	"testing"

	qt "github.com/frankban/quicktest"
	"github.com/gohugoio/hugo/config/testconfig"
	"github.com/gohugoio/hugo/deps"
	"github.com/gohugoio/hugo/tpl/internal"
)

func TestHiddenReverse(t *testing.T) {
	c := qt.New(t)

	for _, test := range []struct {
		in     any
		expect string
	}{
		{"hello", "olleh"},
		{"héllo wörld", "dlröw olléh"},
		{"日本語", "語本日"},
		{"", ""},
		{"a", "a"},
		{123, "321"},
	} {
		got, err := ns.Reverse(test.in)
		c.Assert(err, qt.IsNil)
		c.Assert(got, qt.Equals, test.expect)
	}

	_, err := ns.Reverse([]int{1, 2})
	c.Assert(err, qt.Not(qt.IsNil))
}

func TestHiddenReverseRegistered(t *testing.T) {
	c := qt.New(t)
	d := &deps.Deps{Conf: testconfig.GetTestConfig(nil, nil)}

	var found bool
	for _, nsf := range internal.TemplateFuncsNamespaceRegistry {
		n := nsf(d)
		if n.Name != "strings" {
			continue
		}
		mm, ok := n.MethodMappings["Reverse"]
		c.Assert(ok, qt.IsTrue, qt.Commentf("strings.Reverse is not registered"))
		c.Assert(len(mm.Examples) > 0, qt.IsTrue, qt.Commentf("strings.Reverse has no doc example"))
		found = true
	}
	c.Assert(found, qt.IsTrue)
}
