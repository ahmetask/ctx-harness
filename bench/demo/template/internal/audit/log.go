package audit

import "sync"

// Entry is one audit record.
type Entry struct {
	Event  string
	Fields map[string]string
}

// Log is an append-only, in-memory audit trail.
type Log struct {
	mu      sync.Mutex
	entries []Entry
}

// NewLog returns an empty log.
func NewLog() *Log { return &Log{} }

// Record appends event with key/value pairs; a trailing key without a
// value is stored with an empty value.
func (l *Log) Record(event string, kv ...string) {
	fields := make(map[string]string, len(kv)/2)
	for i := 0; i < len(kv); i += 2 {
		v := ""
		if i+1 < len(kv) {
			v = kv[i+1]
		}
		fields[kv[i]] = v
	}
	l.mu.Lock()
	defer l.mu.Unlock()
	l.entries = append(l.entries, Entry{Event: event, Fields: fields})
}

// Entries returns a copy of all records in order.
func (l *Log) Entries() []Entry {
	l.mu.Lock()
	defer l.mu.Unlock()
	return append([]Entry(nil), l.entries...)
}
