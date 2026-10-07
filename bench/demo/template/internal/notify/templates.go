package notify

// Template is a message with {{placeholders}}.
type Template struct {
	Subject string
	Body    string
}

// templates maps an event name to its message.
var templates = map[string]Template{
	"paid": {
		Subject: "Payment received for {{order}}",
		Body:    "Hi {{name}}, we received {{total}} for order {{order}}.",
	},
	"shipped": {
		Subject: "Order {{order}} shipped",
		Body:    "Hi {{name}}, order {{order}} is on its way. Tracking: {{tracking}}.",
	},
	"delivered": {
		Subject: "Order {{order}} delivered",
		Body:    "Hi {{name}}, order {{order}} was delivered.",
	},
	"cancelled": {
		Subject: "Order {{order}} cancelled",
		Body:    "Hi {{name}}, order {{order}} was cancelled.",
	},
}
