package notify

import (
	"fmt"
	"sort"
	"strings"
)

// Message is an outgoing email.
type Message struct {
	To      string
	Subject string
	Body    string
}

// Sender delivers messages.
type Sender interface {
	Send(Message) error
}

// Notifier renders templates and sends them.
type Notifier struct {
	sender Sender
}

// New returns a Notifier that sends through s.
func New(s Sender) *Notifier { return &Notifier{sender: s} }

// Notify renders the template for event with data and sends it to to.
// Events without a template are an error.
func (n *Notifier) Notify(to, event string, data map[string]string) error {
	t, ok := templates[event]
	if !ok {
		return fmt.Errorf("notify: no template for event %q", event)
	}
	return n.sender.Send(Message{To: to, Subject: render(t.Subject, data), Body: render(t.Body, data)})
}

// Events lists the events that have a template, sorted.
func Events() []string {
	out := make([]string, 0, len(templates))
	for e := range templates {
		out = append(out, e)
	}
	sort.Strings(out)
	return out
}

func render(s string, data map[string]string) string {
	keys := make([]string, 0, len(data))
	for k := range data {
		keys = append(keys, k)
	}
	sort.Strings(keys)
	pairs := make([]string, 0, 2*len(keys))
	for _, k := range keys {
		pairs = append(pairs, "{{"+k+"}}", data[k])
	}
	return strings.NewReplacer(pairs...).Replace(s)
}
