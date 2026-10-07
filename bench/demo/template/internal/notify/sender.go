package notify

import "sync"

// MemorySender keeps sent messages in memory instead of emailing them.
type MemorySender struct {
	mu   sync.Mutex
	Sent []Message
}

// Send records msg.
func (m *MemorySender) Send(msg Message) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.Sent = append(m.Sent, msg)
	return nil
}

// Last returns the most recent message, or a zero Message.
func (m *MemorySender) Last() Message {
	m.mu.Lock()
	defer m.mu.Unlock()
	if len(m.Sent) == 0 {
		return Message{}
	}
	return m.Sent[len(m.Sent)-1]
}
