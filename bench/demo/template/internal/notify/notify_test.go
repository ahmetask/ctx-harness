package notify

import "testing"

func TestNotifyRendersTemplate(t *testing.T) {
	s := &MemorySender{}
	err := New(s).Notify("a@example.com", "shipped", map[string]string{
		"order": "ord-0001", "name": "Ada", "tracking": "POST-ORD-0001",
	})
	if err != nil {
		t.Fatal(err)
	}
	m := s.Last()
	if m.To != "a@example.com" || m.Subject != "Order ord-0001 shipped" {
		t.Fatalf("message = %+v", m)
	}
	if want := "Hi Ada, order ord-0001 is on its way. Tracking: POST-ORD-0001."; m.Body != want {
		t.Fatalf("body = %q, want %q", m.Body, want)
	}
}

func TestUnknownEvent(t *testing.T) {
	if err := New(&MemorySender{}).Notify("a@example.com", "teleported", nil); err == nil {
		t.Fatal("expected error for event without template")
	}
}
