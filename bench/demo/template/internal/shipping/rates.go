package shipping

import "shopd/internal/money"

// Rate quotes the shipping price for a parcel: a base fee per carrier plus
// a per-kilogram charge, with partial kilograms rounded up.
func Rate(weightG int, c money.Currency) money.Money {
	kg := int64((weightG + 999) / 1000)
	base := map[Carrier]int64{Post: 400, Courier: 900, Freight: 4500}[CarrierFor(weightG)]
	return money.New(base+kg*120, c)
}
