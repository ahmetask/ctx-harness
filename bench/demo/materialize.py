#!/usr/bin/env python3
"""Create a fresh copy of the shopd demo repo with a scripted git history.

The template directory holds the final state of the code. HISTORY lists the
commits that led there, oldest first; each change says what a file looked
like before and after that commit. To build the repo, the changes are undone
newest-first to get the initial import, which is committed, and then replayed
one commit at a time. The result is deterministic: same files, authors, dates
and commit hashes on every run.

History is what gives ctxh something to mine: fix/revert commits (risk),
files that change together without importing each other (co-change), and
several authors (owners).

  python3 bench/demo/materialize.py <dest> [--no-history]
"""
import os
import shutil
import subprocess
import sys
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "template"

KIM = ("Kim Park", "kim@shopd.example")
SAM = ("Sam Lee", "sam@shopd.example")
DANA = ("Dana Ortiz", "dana@shopd.example")

SHIP_FUNC = (
    "// Ship hands a paid order to a carrier.\n"
    "func (s *Service) Ship(id string) (Order, error) {\n"
    "\to, err := s.Get(id)\n"
    "\tif err != nil {\n"
    "\t\treturn Order{}, err\n"
    "\t}\n"
    "\tweight := 0\n"
    "\tfor _, l := range o.Lines {\n"
    "\t\tif p, err := s.Catalog.Get(l.SKU); err == nil {\n"
    "\t\t\tweight += p.WeightG * int(l.Qty)\n"
    "\t\t}\n"
    "\t}\n"
    "\to.Tracking = shipping.TrackingNumber(shipping.CarrierFor(weight), o.ID)\n"
    "\treturn s.transition(o, StateShipped)\n"
    "}\n\n"
)
DELIVER_FUNC = (
    "// Deliver marks a shipped order as delivered.\n"
    "func (s *Service) Deliver(id string) (Order, error) {\n"
    "\to, err := s.Get(id)\n"
    "\tif err != nil {\n"
    "\t\treturn Order{}, err\n"
    "\t}\n"
    "\treturn s.transition(o, StateDelivered)\n"
    "}\n\n"
)
REQUEST_ID = (
    "var requestSeq atomic.Int64\n\n"
    "// withRequestID echoes X-Request-ID, or assigns one when the client sent none.\n"
    "func withRequestID(next http.Handler) http.Handler {\n"
    "\treturn http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {\n"
    "\t\tid := r.Header.Get(\"X-Request-ID\")\n"
    "\t\tif id == \"\" {\n"
    "\t\t\tid = fmt.Sprintf(\"req-%06d\", requestSeq.Add(1))\n"
    "\t\t}\n"
    "\t\tw.Header().Set(\"X-Request-ID\", id)\n"
    "\t\tnext.ServeHTTP(w, r)\n"
    "\t})\n"
    "}\n\n"
)
TAX_TEST = (
    "func TestTaxIsRoundedPerLine(t *testing.T) {\n"
    "\tq, err := engine().Quote([]Line{{SKU: \"A\", Qty: 1, Unit: usd(333)}, {SKU: \"B\", Qty: 1, Unit: usd(333)}}, \"\")\n"
    "\tif err != nil {\n"
    "\t\tt.Fatal(err)\n"
    "\t}\n"
    "\tif q.Tax.Amount != 134 {\n"
    "\t\tt.Fatalf(\"tax = %d, want 134 (67 per line)\", q.Tax.Amount)\n"
    "\t}\n"
    "}\n\n"
)


def ch(file, before, after):
    return {"file": file, "before": before, "after": after}


def add(file):
    return {"file": file, "add": True}


HISTORY = [
    {"msg": "httpapi: add request id middleware", "author": SAM, "changes": [
        ch("internal/httpapi/middleware.go",
           'import (\n\t"log"\n\t"net/http"\n)\n\n',
           'import (\n\t"fmt"\n\t"log"\n\t"net/http"\n\t"sync/atomic"\n)\n\n' + REQUEST_ID),
        ch("internal/httpapi/server.go", "\treturn withRecover(s.mux)\n", "\treturn withRequestID(withRecover(s.mux))\n"),
    ]},
    {"msg": "orders: add shipped state", "author": DANA, "changes": [
        ch("internal/orders/state.go",
           '\tStatePaid      State = "paid"\n\tStateCancelled',
           '\tStatePaid      State = "paid"\n\tStateShipped   State = "shipped"\n\tStateCancelled'),
        ch("internal/orders/state.go",
           "\tStatePending: {StatePaid, StateCancelled},\n}",
           "\tStatePending: {StatePaid, StateCancelled},\n\tStatePaid:    {StateShipped},\n}"),
        ch("internal/notify/templates.go",
           '\t"cancelled": {',
           '\t"shipped": {\n\t\tSubject: "Order {{order}} shipped",\n'
           '\t\tBody:    "Hi {{name}}, order {{order}} is on its way. Tracking: {{tracking}}.",\n\t},\n\t"cancelled": {'),
        ch("internal/orders/service.go", '\t"shopd/internal/pricing"\n',
           '\t"shopd/internal/pricing"\n\t"shopd/internal/shipping"\n'),
        ch("internal/orders/service.go", "// Cancel cancels", SHIP_FUNC + "// Cancel cancels"),
        ch("internal/httpapi/server.go",
           '\ts.mux.HandleFunc("POST /orders/{id}/cancel"',
           '\ts.mux.HandleFunc("POST /orders/{id}/ship", s.shipOrder)\n\ts.mux.HandleFunc("POST /orders/{id}/cancel"'),
        ch("internal/httpapi/handlers_orders.go",
           "func (s *Server) cancelOrder",
           "func (s *Server) shipOrder(w http.ResponseWriter, r *http.Request)    { s.act(w, r, s.orders.Ship) }\n"
           "func (s *Server) cancelOrder"),
        ch("internal/reports/sales.go",
           "\treturn s == orders.StatePaid\n",
           "\treturn s == orders.StatePaid || s == orders.StateShipped\n"),
    ]},
    {"msg": "pricing: coupon codes are case-insensitive", "author": KIM, "changes": [
        ch("internal/pricing/coupon.go", "\t\tb.coupons[c.Code] = c\n", "\t\tb.coupons[strings.ToUpper(c.Code)] = c\n"),
        ch("internal/pricing/coupon.go", "\tcode = strings.TrimSpace(code)\n",
           "\tcode = strings.ToUpper(strings.TrimSpace(code))\n"),
    ]},
    {"msg": "fix: double charge when a payment retry built a new idempotency key", "author": SAM, "changes": [
        add("internal/payments/idempotency.go"),
        ch("internal/payments/client.go",
           'import (\n\t"fmt"\n\t"time"\n\n\t"shopd/internal/money"\n)\n',
           'import "shopd/internal/money"\n'),
        ch("internal/payments/client.go",
           "// Charge captures amount for an order, retrying transient failures.\n"
           "func (c *Client) Charge(orderID string, amount money.Money) (Charge, error) {\n"
           "\tvar ch Charge\n\terr := c.policy.Do(func() error {\n\t\tvar err error\n"
           '\t\tkey := fmt.Sprintf("%s-%d", orderID, time.Now().UnixNano())\n',
           "// Charge captures amount under key, retrying transient failures.\n"
           "func (c *Client) Charge(key string, amount money.Money) (Charge, error) {\n"
           "\tvar ch Charge\n\terr := c.policy.Do(func() error {\n\t\tvar err error\n"),
        ch("internal/orders/service.go", "s.Payments.Charge(o.ID, o.Quote.Total)",
           "s.Payments.Charge(payments.IdempotencyKey(o.ID), o.Quote.Total)"),
    ]},
    {"msg": "hotfix: round tax per line, not on the order total", "author": KIM, "changes": [
        ch("internal/pricing/tax.go",
           "// perLineTax computes the tax of the order.\n"
           "func perLineTax(amounts []money.Money, bp int64) money.Money {\n"
           "\tsum := money.Zero(amounts[0].Currency)\n\tfor _, a := range amounts {\n"
           "\t\tsum = sum.Add(a)\n\t}\n\treturn sum.Percent(bp)\n}\n",
           "// perLineTax computes the tax of every line, rounds it, and sums the\n// rounded amounts.\n"
           "func perLineTax(amounts []money.Money, bp int64) money.Money {\n"
           "\ttotal := money.Zero(amounts[0].Currency)\n\tfor _, a := range amounts {\n"
           "\t\ttotal = total.Add(a.Percent(bp))\n\t}\n\treturn total\n}\n"),
        ch("internal/pricing/pricing_test.go", "func TestUnknownCoupon", TAX_TEST + "func TestUnknownCoupon"),
    ]},
    {"msg": "catalog: cache search results", "author": SAM, "changes": [
        ch("internal/catalog/search.go", 'import "strings"\n', 'import (\n\t"strings"\n\t"sync"\n)\n'),
        ch("internal/catalog/search.go",
           "\tq = strings.ToLower(strings.TrimSpace(q))\n\tvar out []Product\n",
           "\tq = strings.ToLower(strings.TrimSpace(q))\n\tif v, ok := searchCache.Load(q); ok {\n"
           "\t\treturn v.([]Product)\n\t}\n\tvar out []Product\n"),
        ch("internal/catalog/search.go", "\treturn out\n}\n",
           "\tsearchCache.Store(q, out)\n\treturn out\n}\n\nvar searchCache sync.Map // query -> []Product\n"),
    ]},
    {"msg": "orders: add delivered state", "author": DANA, "changes": [
        ch("internal/orders/state.go",
           '\tStateShipped   State = "shipped"\n\tStateCancelled',
           '\tStateShipped   State = "shipped"\n\tStateDelivered State = "delivered"\n\tStateCancelled'),
        ch("internal/orders/state.go",
           "\tStatePaid:    {StateShipped},\n}",
           "\tStatePaid:    {StateShipped},\n\tStateShipped: {StateDelivered},\n}"),
        ch("internal/notify/templates.go",
           '\t"cancelled": {',
           '\t"delivered": {\n\t\tSubject: "Order {{order}} delivered",\n'
           '\t\tBody:    "Hi {{name}}, order {{order}} was delivered.",\n\t},\n\t"cancelled": {'),
        ch("internal/orders/service.go", "// Cancel cancels", DELIVER_FUNC + "// Cancel cancels"),
        ch("internal/httpapi/server.go",
           '\ts.mux.HandleFunc("POST /orders/{id}/cancel"',
           '\ts.mux.HandleFunc("POST /orders/{id}/deliver", s.deliverOrder)\n\ts.mux.HandleFunc("POST /orders/{id}/cancel"'),
        ch("internal/httpapi/handlers_orders.go",
           "func (s *Server) cancelOrder",
           "func (s *Server) deliverOrder(w http.ResponseWriter, r *http.Request) { s.act(w, r, s.orders.Deliver) }\n"
           "func (s *Server) cancelOrder"),
        ch("internal/reports/sales.go",
           "\treturn s == orders.StatePaid || s == orders.StateShipped\n",
           "\treturn s == orders.StatePaid || s == orders.StateShipped || s == orders.StateDelivered\n"),
    ]},
    {"msg": "revert: search cache served archived products after Put", "author": SAM, "changes": [
        ch("internal/catalog/search.go", 'import (\n\t"strings"\n\t"sync"\n)\n', 'import "strings"\n'),
        ch("internal/catalog/search.go",
           "\tq = strings.ToLower(strings.TrimSpace(q))\n\tif v, ok := searchCache.Load(q); ok {\n"
           "\t\treturn v.([]Product)\n\t}\n\tvar out []Product\n",
           "\tq = strings.ToLower(strings.TrimSpace(q))\n\tvar out []Product\n"),
        ch("internal/catalog/search.go",
           "\tsearchCache.Store(q, out)\n\treturn out\n}\n\nvar searchCache sync.Map // query -> []Product\n",
           "\treturn out\n}\n"),
    ]},
    {"msg": "fix: release reserved stock when a payment fails", "author": DANA, "changes": [
        ch("internal/orders/service.go", "// Pay charges the order total.\n",
           "// Pay charges the order total. A failed payment cancels the order.\n"),
        ch("internal/orders/service.go",
           '\t\ts.Audit.Record(eventPaymentFailed, "order", o.ID, "error", err.Error())\n\t\treturn Order{}, err\n',
           '\t\ts.Inventory.Release(o.ID)\n'
           '\t\ts.Audit.Record(eventPaymentFailed, "order", o.ID, "error", err.Error())\n'
           "\t\tif _, cerr := s.transition(o, StateCancelled); cerr != nil {\n"
           "\t\t\treturn Order{}, errors.Join(err, cerr)\n\t\t}\n\t\treturn Order{}, err\n"),
        ch("internal/inventory/reservation.go",
           "// Release drops the hold of an order.\nfunc",
           "// Release drops the hold of an order. Releasing an order without a hold\n"
           "// is a no-op, so every failure path can call it.\nfunc"),
    ]},
]


def _replace_once(path: Path, old: str, new: str, what: str):
    text = path.read_text()
    n = text.count(old)
    if n != 1:
        raise ValueError(f"{what}: expected 1 match in {path.name}, found {n}: {old[:60]!r}")
    path.write_text(text.replace(old, new))


def _git(dest: Path, *args, author=KIM, day=0):
    date = f"2024-03-{day + 1:02d}T10:00:00+00:00"
    env = {**os.environ, "GIT_AUTHOR_NAME": author[0], "GIT_AUTHOR_EMAIL": author[1],
           "GIT_COMMITTER_NAME": author[0], "GIT_COMMITTER_EMAIL": author[1],
           "GIT_AUTHOR_DATE": date, "GIT_COMMITTER_DATE": date}
    subprocess.run(["git", "-c", "commit.gpgsign=false", "-c", "init.defaultBranch=main", *args],
                   cwd=dest, env=env, check=True, capture_output=True)


def _commit(dest: Path, msg: str, author, day):
    _git(dest, "add", "-A", author=author, day=day)
    _git(dest, "commit", "-q", "-m", msg, author=author, day=day)


def materialize(dest, history=True) -> Path:
    """Copy the template to dest (which must not exist) and build its git history."""
    dest = Path(dest)
    shutil.copytree(TEMPLATE, dest)
    _git(dest, "init", "-q")
    if not history:
        _commit(dest, "initial import", KIM, 0)
        return dest
    added = {}
    for i in range(len(HISTORY) - 1, -1, -1):
        for c in reversed(HISTORY[i]["changes"]):
            p = dest / c["file"]
            if c.get("add"):
                added[(i, c["file"])] = p.read_text()
                p.unlink()
            else:
                _replace_once(p, c["after"], c["before"], f"undo '{HISTORY[i]['msg']}'")
    _commit(dest, "initial import", KIM, 0)
    for i, commit in enumerate(HISTORY):
        for c in commit["changes"]:
            p = dest / c["file"]
            if c.get("add"):
                p.write_text(added[(i, c["file"])])
            else:
                _replace_once(p, c["before"], c["after"], f"replay '{commit['msg']}'")
        _commit(dest, commit["msg"], commit["author"], i + 1)
    return dest


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    out = materialize(sys.argv[1], history="--no-history" not in sys.argv)
    print(f"materialized shopd demo at {out}")
