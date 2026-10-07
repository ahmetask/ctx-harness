package shipping

import "strings"

// Carrier is a shipping provider.
type Carrier string

const (
	Post    Carrier = "POST"
	Courier Carrier = "COURIER"
	Freight Carrier = "FREIGHT"
)

// CarrierFor picks a carrier by parcel weight in grams.
func CarrierFor(weightG int) Carrier {
	switch {
	case weightG <= 2000:
		return Post
	case weightG <= 30000:
		return Courier
	default:
		return Freight
	}
}

// TrackingNumber builds the tracking reference printed on the label.
func TrackingNumber(c Carrier, orderID string) string {
	return string(c) + "-" + strings.ToUpper(orderID)
}
