# shopd

A small order service: catalog, inventory, pricing, payments, notifications and a JSON HTTP API. Everything is in memory, using only the Go standard library.

```bash
go test ./...
go run ./cmd/shopd     # serves :8080 with demo data
```

Endpoints: `GET /products?q=`, `GET /products/{sku}`, `POST /orders`, `GET /orders/{id}`, `POST /orders/{id}/pay|ship|deliver|cancel`.
