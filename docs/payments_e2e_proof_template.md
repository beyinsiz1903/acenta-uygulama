# Payments e2e — Proof Pack Template (Stripe test mode + signed webhook)

## Status rule
- **KANITLI DONE** demek için şu 3 kanıt tek mesajda olmalı:
  - **A)** Funnel events JSON (sorted by `created_at`, same `correlation_id`)
  - **B)** Booking JSON ( `payment_status: "paid"` + same `correlation_id` + same `payment_intent_id`)
  - **C)** Consistency check JSON (PASS: correlation + payment_intent triple match + time order)

## Env prerequisites (hard blockers)
- Required:
  - `STRIPE_API_KEY` (test key)
  - `STRIPE_WEBHOOK_SECRET` (signing secret)
- Stripe Dashboard webhook:
  - endpoint: `<BASE>/<YOUR_WEBHOOK_PATH>`
  - events: `payment_intent.succeeded` (minimum), optionally `payment_intent.payment_failed`

If `STRIPE_WEBHOOK_SECRET` is missing, the system is **implement ready, proof pending (env)**.

---

# Runbook (public flow, e2e)

## 0) Variables
```bash
BASE="https://<your-preview-domain>"
API_URL="$BASE"
ADMIN_EMAIL="admin@acenta.test"
ADMIN_PASS="admin123"
ORG_ID="<org_id>"   # if needed by your public quote payload

1) Admin token

ADMIN_TOKEN=$(
  curl -s -X POST "$API_URL/api/auth/login" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$ADMIN_EMAIL\",\"password\":\"$ADMIN_PASS\"}" \
  | python3 -c "import sys,json;print(json.load(sys.stdin).get('access_token',''))"
)
echo "ADMIN_TOKEN=${#ADMIN_TOKEN} chars"

2) Create public quote (capture correlation_id)

QUOTE_RES=$(
  curl -s -X POST "$API_URL/api/public/quote" \
    -H "Content-Type: application/json" \
    -d '{
      "org": "'$ORG_ID'",
      "product_id": "<PRODUCT_ID>",
      "date_from": "2026-02-15",
      "date_to": "2026-02-17",
      "pax": { "adults": 2, "children": 0 },
      "rooms": 1,
      "currency": "EUR"
    }'
)
echo "$QUOTE_RES" | python3 -m json.tool

FC=$(
  echo "$QUOTE_RES" | python3 -c "import sys,json;print(json.load(sys.stdin).get('correlation_id',''))"
)
QID=$(
  echo "$QUOTE_RES" | python3 -c "import sys,json;print(json.load(sys.stdin).get('quote_id',''))"
)

echo "correlation_id=$FC"
echo "quote_id=$QID"

3) Public checkout (propagate correlation_id, capture booking_id, payment_intent if returned)

Not: Eğer checkout response PaymentIntent dönmüyorsa, PI’yi Stripe Dashboard’dan veya booking/payments aggregate’tan alacağız.

CHECKOUT_RES=$(
  curl -s -X POST "$API_URL/api/public/checkout" \
    -H "Content-Type: application/json" \
    -H "X-Correlation-Id: $FC" \
    -d '{
      "quote_id": "'$QID'",
      "guest": {
        "full_name": "E2E Test",
        "email": "e2e@example.com",
        "phone": "+90 555 000 0000"
      },
      "idempotency_key": "e2e-'"$FC"'"
    }'
)
echo "$CHECKOUT_RES" | python3 -m json.tool

BOOKING_ID=$(
  echo "$CHECKOUT_RES" | python3 -c "import sys,json;print(json.load(sys.stdin).get('booking_id',''))"
)
PI_FROM_CHECKOUT=$(
  echo "$CHECKOUT_RES" | python3 -c "import sys,json;print((json.load(sys.stdin).get('payment_intent_id') or ''))"
)

echo "booking_id=$BOOKING_ID"
echo "payment_intent_id(from checkout)=$PI_FROM_CHECKOUT"

4) Pay with Stripe test card (manual step)

Complete payment in the UI / Stripe flow using a test card.
	•	Card: 4242 4242 4242 4242
	•	Any future exp, any CVC

Wait until webhook arrives and is processed (must return 2xx).

⸻

Proof outputs (paste into a single message)

A) Funnel events (sorted by created_at)

Fetch events by correlation_id:

EVENTS_RAW=$(
  curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
    "$API_URL/api/admin/funnel/events?correlation_id=$FC&limit=50"
)
echo "$EVENTS_RAW" | python3 -m json.tool

Sort by created_at:

EVENTS_SORTED=$(
  echo "$EVENTS_RAW" | python3 - <<'PY'
import sys, json
arr = json.load(sys.stdin)
arr = sorted(arr, key=lambda x: x.get("created_at",""))
print(json.dumps(arr, ensure_ascii=False, indent=2))
PY
)
echo "$EVENTS_SORTED"

Must contain (same correlation_id, time-ordered):
	•	public.quote.created
	•	public.checkout.started
	•	public.booking.created (entity_id = booking_id)
	•	public.payment.intent.created (context.payment_intent_id)
	•	public.payment.succeeded (context.payment_intent_id + trace.event_id)

Paste output:

PASTE_EVENTS_JSON_HERE

B) Booking JSON (paid state)

Fetch booking details (use your admin booking detail endpoint OR Mongo read).
If you have an admin endpoint:

curl -s -H "Authorization: Bearer $ADMIN_TOKEN" \
  "$API_URL/api/admin/bookings/$BOOKING_ID" | python3 -m json.tool

Must show
	•	payment_status: "paid"
	•	correlation_id == $FC
	•	payments.payment_intent_id exists and matches events
	•	amounts + applied_rules still present

Paste output:

PASTE_BOOKING_JSON_HERE

C) Consistency check (PASS)

This checks:
	•	same correlation_id across events + booking
	•	payment_intent_id triple match (intent.created, succeeded, booking)
	•	time order: intent.created < succeeded

python3 - <<'PY'
import json, sys, re
from datetime import datetime

events = json.loads("""PASTE_EVENTS_JSON_HERE""")
booking = json.loads("""PASTE_BOOKING_JSON_HERE""")

def parse_dt(s):
  if not s: return None
  # accepts Z or offset
  try:
    return datetime.fromisoformat(s.replace("Z","+00:00"))
  except Exception:
    return None

fc = booking.get("correlation_id")
paid = booking.get("payment_status") == "paid"

# find events by name
def find(name):
  for e in events:
    if e.get("event_name") == name:
      return e
  return None

e_intent = find("public.payment.intent.created")
e_succ = find("public.payment.succeeded")

pi1 = (e_intent or {}).get("context",{}).get("payment_intent_id")
pi2 = (e_succ or {}).get("context",{}).get("payment_intent_id")
pi3 = (booking.get("payments") or {}).get("payment_intent_id")

ok_pi = (pi1 and pi2 and pi3 and (pi1 == pi2 == pi3))

t1 = parse_dt((e_intent or {}).get("created_at"))
t2 = parse_dt((e_succ or {}).get("created_at"))
ok_time = (t1 and t2 and (t1 < t2))

ok_fc = True
for e in events:
  if e.get("correlation_id") != fc:
    ok_fc = False
    break

out = {
  "ok": bool(paid and ok_fc and ok_pi and ok_time),
  "checks": {
    "booking_paid": paid,
    "same_correlation_id": ok_fc,
    "payment_intent_triple_match": ok_pi,
    "time_order_intent_before_succeeded": ok_time
  },
  "values": {
    "correlation_id": fc,
    "payment_intent_id": {"intent_created": pi1, "succeeded": pi2, "booking": pi3},
    "created_at": {"intent_created": (e_intent or {}).get("created_at"), "succeeded": (e_succ or {}).get("created_at")}
  }
}

print(json.dumps(out, ensure_ascii=False, indent=2))
PY

Paste output:

PASTE_CHECK_JSON_HERE


⸻

Closure statement (paste after A/B/C in the final message)

If A/B/C are present and C.ok=true:
	•	Payments e2e — KANITLI DONE ✅
	•	Parite:
	•	Agentis: %82
	•	Agentis Pro: %57 (Δ +2)

If env blocks exist (e.g., missing STRIPE_WEBHOOK_SECRET):
	•	Payments e2e — implement ready, proof pending (env)
	•	Parite: unchanged

İstersen bir sonraki adım olarak “Reporting v1 sayfasına payments e2e proof pending durumunu badge olarak ekleyelim mi?” gibi küçük bir ops görünürlük polish’i de yapabiliriz.
