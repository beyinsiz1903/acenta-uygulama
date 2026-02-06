# Escrow & Payment Orchestration — Domain Design

> Status: PRE-DESIGN — No implementation yet
> Owner: Platform Team
> Last updated: 2026-02-06
> Prerequisite: Billing engine (PROMPT H) complete, shadow metered active

---

## 1. Domain Model

### Core Entities

```
EscrowTransaction
├── id: "esc_" + uuid
├── match_request_id: "mreq_..."
├── listing_id: "lst_..."
├── provider_tenant_id
├── seller_tenant_id
├── buyer_tenant_id (= seller_tenant_id in B2B context)
├── status: pending_funding | funded | service_confirmed | releasing | released | refunded | disputed
├── amounts:
│   ├── gross_amount (buyer pays)
│   ├── platform_fee_amount
│   ├── platform_fee_rate
│   ├── provider_commission_amount
│   ├── provider_commission_rate
│   ├── net_seller_amount (= gross - platform_fee - provider_commission)
│   └── currency: "TRY"
├── funding:
│   ├── method: "stripe_payment_intent" | "balance" | "credit"
│   ├── provider_payment_id
│   ├── funded_at
│   └── funding_deadline (auto-cancel if not funded)
├── release:
│   ├── released_at
│   ├── payout_id
│   └── release_reason: "service_confirmed" | "auto_release" | "admin_override"
├── refund:
│   ├── refunded_at
│   ├── refund_amount
│   ├── refund_reason
│   └── provider_refund_id
├── created_at
├── updated_at
└── status_history: [{status, at, by_user_id, note}]
```

```
EscrowAccount (per tenant — virtual ledger)
├── tenant_id
├── currency
├── balance_held (total in escrow, not yet released)
├── balance_available (released, pending payout)
├── total_earned (lifetime)
├── total_fees_paid (lifetime platform fees)
├── updated_at
```

```
Settlement (payout batch)
├── id: "stl_" + uuid
├── tenant_id
├── status: pending | processing | completed | failed
├── amount
├── currency
├── escrow_transaction_ids: [...]
├── provider_payout_id (Stripe Transfer/Payout)
├── settled_at
├── created_at
```

```
FeeAllocation (platform revenue record)
├── id: "fee_" + uuid
├── escrow_transaction_id
├── fee_type: "platform_fee" | "provider_commission"
├── amount
├── currency
├── status: pending | captured | refunded
├── created_at
```

```
DisputeCase
├── id: "dsp_" + uuid
├── escrow_transaction_id
├── opened_by: "buyer" | "seller" | "system"
├── reason: "service_not_delivered" | "quality_issue" | "wrong_item" | "other"
├── status: open | under_review | resolved_buyer | resolved_seller | escalated
├── resolution:
│   ├── resolved_at
│   ├── resolved_by
│   ├── action: "full_refund" | "partial_refund" | "release_to_seller" | "split"
│   └── refund_amount (if applicable)
├── evidence: [{type, url, uploaded_by, uploaded_at}]
├── created_at
├── updated_at
```

---

## 2. Escrow State Machine

```
                    ┌─────────────────┐
                    │ pending_funding  │
                    └────────┬────────┘
                             │ buyer funds
                             ▼
                    ┌─────────────────┐
           ┌───────│     funded      │───────┐
           │       └────────┬────────┘       │
           │                │                │
     buyer cancels    service confirmed   dispute opened
           │                │                │
           ▼                ▼                ▼
    ┌──────────┐   ┌───────────────┐  ┌──────────┐
    │ refunded │   │service_confirmed│ │ disputed │
    └──────────┘   └───────┬───────┘  └────┬─────┘
                           │               │
                     release funds    resolution
                           │               │
                           ▼               ▼
                    ┌──────────────┐  (refunded OR released)
                    │  releasing   │
                    └──────┬──────┘
                           │
                           ▼
                    ┌──────────────┐
                    │   released   │
                    └──────────────┘
```

### Valid Transitions

| From | To | Trigger | Side Effects |
|---|---|---|---|
| pending_funding | funded | Payment confirmed (webhook/poll) | Hold amount in escrow account |
| pending_funding | refunded | Funding deadline expired | Auto-cancel, no charge |
| funded | service_confirmed | Seller confirms delivery OR auto-confirm (T+N days) | — |
| funded | refunded | Buyer cancels (within cancellation window) | Refund payment, release hold |
| funded | disputed | Buyer/seller opens dispute | Freeze escrow |
| service_confirmed | releasing | System initiates release | Calculate fees, prepare payout |
| releasing | released | Payout completed | Credit seller account, capture platform fee |
| disputed | refunded | Resolution: buyer wins | Refund buyer |
| disputed | released | Resolution: seller wins | Release to seller |
| disputed | refunded (partial) | Resolution: split | Partial refund + partial release |

### Auto-Transitions (Time-based)

| Rule | Trigger | Action |
|---|---|---|
| Funding deadline | T + 24h after escrow created | Cancel → refunded |
| Auto-confirm | T + 72h after funded (configurable) | service_confirmed |
| Auto-release | T + 24h after service_confirmed | releasing → released |

---

## 3. Financial Flow

### Happy Path (B2B Match Request → Escrow → Payout)

```
1. Match request APPROVED (mreq_xxx)
   → EscrowTransaction created (status: pending_funding)
   → amounts calculated from listing + match request

2. Buyer funds escrow
   → Stripe PaymentIntent created (or balance debit)
   → EscrowTransaction → funded
   → EscrowAccount.balance_held += gross_amount

3. Service delivered / confirmed
   → EscrowTransaction → service_confirmed

4. Release initiated
   → Platform fee captured → FeeAllocation created
   → Provider commission calculated → FeeAllocation created
   → Net amount = gross - platform_fee - provider_commission
   → EscrowAccount.balance_held -= gross_amount
   → EscrowAccount.balance_available += net_amount
   → EscrowTransaction → released

5. Settlement (batch payout)
   → Settlement created from balance_available
   → Stripe Transfer to seller's connected account (or bank payout)
   → EscrowAccount.balance_available -= settlement_amount
   → Settlement → completed
```

### Fee Calculation

```python
gross_amount = match_request.requested_price  # e.g., ₺1,200
platform_fee_rate = 0.01  # 1% (from match request)
provider_commission_rate = listing.provider_commission_rate / 100  # e.g., 10%

platform_fee = gross_amount * platform_fee_rate  # ₺12
provider_commission = gross_amount * provider_commission_rate  # ₺120
net_seller = gross_amount - platform_fee - provider_commission  # ₺1,068
```

### Accounting Journal Entries

| Event | Debit | Credit |
|---|---|---|
| Escrow funded | Escrow Holding Account | Buyer Payment |
| Release to seller | Seller Receivable | Escrow Holding Account |
| Platform fee capture | Escrow Holding Account | Platform Revenue |
| Provider commission | Escrow Holding Account | Provider Receivable |
| Refund to buyer | Buyer Refund Payable | Escrow Holding Account |

---

## 4. Failure Paths

### 4.1 Payment Failure
- Stripe PaymentIntent fails
- Escrow stays `pending_funding`
- Retry window: 24h
- After deadline: auto-cancel → `refunded` (no charge)

### 4.2 Buyer Cancellation
- Within cancellation window (configurable, e.g., before service_confirmed)
- Full refund via Stripe
- EscrowTransaction → `refunded`
- EscrowAccount.balance_held reduced

### 4.3 Seller No-Show
- Auto-confirm timer expires without delivery confirmation
- Options:
  a) Auto-release (trust seller) — default for trusted partners
  b) Require explicit confirmation — for new partners
  c) Auto-dispute — if no activity detected

### 4.4 Dispute Flow
- Either party opens dispute
- Escrow frozen (no release, no refund)
- Admin reviews evidence
- Resolution options:
  - Full refund to buyer
  - Full release to seller
  - Split (partial refund + partial release)
- FeeAllocation adjusted based on resolution

### 4.5 Partial Refund
- Service partially delivered
- Admin determines refund_amount
- Remaining amount released to seller
- Platform fee pro-rated

---

## 5. Risk & Compliance Matrix

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| **Funds segregation** | N/A | Critical | Separate Stripe account for escrow OR Stripe Connect with destination charges |
| **Double release** | Low | Critical | State machine + idempotency + audit trail |
| **Refund after release** | Low | High | Release only after service_confirmed + grace period |
| **Chargeback** | Medium | High | Evidence collection + dispute resolution before release |
| **Currency mismatch** | Low | Medium | Single currency (TRY) for V1; multi-currency in V2 |
| **Settlement delay** | Medium | Low | Batch settlements (daily/weekly) with SLA |
| **Accounting reconciliation** | Medium | High | Journal entries per event + monthly reconciliation report |
| **Regulatory (BDDK/SPK)** | Medium | Critical | Legal review required for escrow in Turkey |

### Compliance Notes (Turkey)
- Escrow in Turkey may require BDDK (banking regulation) approval depending on structure
- Alternative: "Platform balance" model (not technically escrow)
- Stripe Connect may simplify regulatory burden (Stripe as payment facilitator)
- Legal counsel required before production launch

---

## 6. Technical Architecture (Preview)

### Collections
- `escrow_transactions` — core escrow lifecycle
- `escrow_accounts` — per-tenant virtual ledger
- `settlements` — payout batches
- `fee_allocations` — platform revenue tracking
- `dispute_cases` — dispute resolution

### Indexes
- escrow_transactions: (match_request_id unique), (provider_tenant_id, status), (seller_tenant_id, status), (status, created_at)
- escrow_accounts: (tenant_id unique)
- settlements: (tenant_id, status), (created_at desc)

### API Endpoints (Draft)
- `POST /api/b2b/escrow` — create escrow from approved match request
- `POST /api/b2b/escrow/{id}/confirm-service` — seller confirms delivery
- `POST /api/b2b/escrow/{id}/dispute` — open dispute
- `GET /api/b2b/escrow/{id}` — escrow status
- `GET /api/b2b/escrow/my` — tenant's escrow transactions
- `POST /api/admin/escrow/{id}/resolve-dispute` — admin dispute resolution
- `POST /api/admin/settlements/run` — trigger settlement batch
- `GET /api/admin/escrow/summary` — escrow analytics

### Integration Points
- Stripe PaymentIntent (funding)
- Stripe Transfer / Payout (settlement)
- Audit log (all state changes)
- B2B event log (escrow events)
- Billing webhook handler (payment confirmations)

---

## 7. Implementation Phases

### Phase 1: Core Escrow (MVP)
- EscrowTransaction state machine
- Funding via Stripe PaymentIntent
- Service confirmation (manual)
- Release + platform fee capture
- Basic settlement (single transaction payout)

### Phase 2: Operations
- Batch settlements
- Dispute flow
- Auto-confirm timer
- Escrow analytics dashboard

### Phase 3: Advanced
- Partial refund
- Multi-currency
- Escrow account balance management
- Payout scheduling (daily/weekly)
- Stripe Connect integration

---

## 8. Success Metrics

| Metric | Target |
|---|---|
| Escrow GMV (monthly) | Track from day 1 |
| Platform fee revenue | 1% of GMV |
| Average escrow duration | < 5 days |
| Dispute rate | < 2% |
| Settlement SLA | < 3 business days |
| Release success rate | > 99% |

---

## Appendix: Decision — Stripe Connect vs Custom Escrow

### Option A: Stripe Connect (Recommended for V1)
- Stripe handles funds segregation
- Destination charges: buyer pays → Stripe splits fee + seller amount
- Platform fee captured automatically
- Payout to seller's connected Stripe account
- **Pro**: Simpler compliance, Stripe as payment facilitator
- **Con**: Seller must have Stripe account, higher per-transaction fees

### Option B: Custom Escrow
- Platform holds funds in own account
- Manual settlement/payout
- Full control over timing and fees
- **Pro**: No seller Stripe requirement, lower fees
- **Con**: Regulatory risk (BDDK), complex reconciliation, liability

### Recommendation
Start with **Stripe Connect (V1)** for:
- Faster time to market
- Reduced regulatory risk
- Built-in dispute handling
- Automatic tax reporting

Migrate to hybrid model in V2 if volume justifies custom handling.
