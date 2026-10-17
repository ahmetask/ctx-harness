package security

import (
	"testing"

	qt "github.com/frankban/quicktest"
)

func TestHiddenGetenvPolicy(t *testing.T) {
	c := qt.New(t)

	c.Assert(DefaultConfig.CheckAllowedGetEnv("HUGO_ENV"), qt.IsNil)
	c.Assert(DefaultConfig.CheckAllowedGetEnv("CI"), qt.IsNil)
	c.Assert(DefaultConfig.CheckAllowedGetEnv("HOME"), qt.Not(qt.IsNil))

	w, err := NewWhitelist("^HUGO_", "^MYAPP_")
	c.Assert(err, qt.IsNil)
	c.Assert(w.Accept("HUGO_X"), qt.IsTrue)
	c.Assert(w.Accept("MYAPP_X"), qt.IsTrue)
	c.Assert(w.Accept("OTHER"), qt.IsFalse)
}
