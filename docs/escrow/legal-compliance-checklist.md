# Escrow Legal Compliance Checklist

> Status: DRAFT — For internal review + external legal counsel briefing
> Owner: Platform Team / Legal
> Last updated: 2026-02-06
> Classification: CONFIDENTIAL

---

## 1. Executive Summary

### What We're Building
A B2B marketplace escrow system where:
- **Buyer** (seller tenant) pays for a service/product via the platform
- **Platform** holds funds until service delivery is confirmed
- **Seller** (provider tenant) receives payout after confirmation
- **Platform** captures a commission fee (1-10%) on each transaction

### Proposed Model
**Stripe Connect — Separate Charges & Transfers**
- Buyer pays via Stripe PaymentIntent to **platform's Stripe account**
- Platform transfers net amount to seller's **connected Stripe account**
- Platform retains `application_fee_amount` as commission
- **Funds are held by Stripe**, not by the platform's bank account

### Core Principle
> **Platform NEVER acts as custodian of user funds.**
> Funds flow through Stripe's regulated infrastructure.
> Platform only instructs transfer timing and fee deduction.

---

## 2. Turkey Regulatory Framework

### Relevant Legislation

| Law/Regulation | Relevance |
|---|---|
| **6493 sayılı Kanun** — Ödeme ve Menkul Kıymet Mutabakat Sistemleri, Ödeme Hizmetleri ve Elektronik Para Kuruluşları Hakkında Kanun | Core payment services regulation |
| **BDDK** (Bankacılık Düzenleme ve Denetleme Kurumu) | Licensing authority for payment institutions |
| **TCMB** (Türkiye Cumhuriyet Merkez Bankası) | Payment systems oversight |
| **5549 sayılı Kanun** — Suç Gelirlerinin Aklanmasının Önlenmesi | AML/CFT obligations |
| **MASAK** (Mali Suçları Araştırma Kurulu) | AML reporting authority |
| **213 sayılı VUK** — Vergi Usul Kanunu | Tax documentation and invoicing |

### Key Regulatory Concepts

**"Ödeme Hizmeti" (Payment Service) — 6493/m.12**
Includes:
- Fon transferi (fund transfer)
- Ödeme işlemi gerçekleştirme (payment execution)
- Fon kabul etme (fund acceptance)

**Critical Question**: Does the platform's escrow model constitute a "payment service" under 6493?

**"Elektronik Para Kuruluşu" (E-Money Institution)**
If the platform issues balance/credits that represent monetary value → may require e-money license.

**"Ödeme Kuruluşu" (Payment Institution)**
If the platform facilitates fund transfers between parties → may require payment institution license.

### Regulatory Risk by Model

| Model | BDDK Risk | Reason |
|---|---|---|
| **Stripe Connect (platform never holds funds)** | LOW | Stripe is the regulated entity; platform is a technology provider |
| **Platform holds funds in bank account** | HIGH | Constitutes fund acceptance → requires ödeme kuruluşu license |
| **Platform issues balance/credits** | HIGH | May constitute e-money issuance → requires lisans |
| **Immediate pass-through (no hold)** | VERY LOW | No fund holding → likely not a payment service |

---

## 3. Stripe Connect Model Analysis

### Model A: Destination Charges
```
Buyer → PaymentIntent → Platform Stripe Account
Platform → automatic transfer → Seller Connected Account
Platform keeps application_fee
```
- **Funds held by**: Stripe (platform account temporarily)
- **Platform custodian?**: No (Stripe holds)
- **Chargeback liability**: Platform (since charge is on platform account)
- **BDDK risk**: LOW-MEDIUM
- **Complexity**: Low
- **Best for**: Simple marketplace, low dispute rate

### Model B: Separate Charges & Transfers ⭐ RECOMMENDED
```
Buyer → PaymentIntent → Platform Stripe Account
Platform → manual Transfer → Seller Connected Account (when ready)
Platform keeps application_fee_amount
```
- **Funds held by**: Stripe (platform account balance)
- **Platform custodian?**: No (Stripe holds; platform instructs timing)
- **Chargeback liability**: Platform
- **BDDK risk**: LOW (Stripe is regulated, platform is technology layer)
- **Complexity**: Medium
- **Best for**: Escrow-like flows, controlled release timing
- **Key advantage**: Platform controls WHEN to transfer (enables service confirmation)

### Model C: Direct Charges
```
Buyer → PaymentIntent → Seller Connected Account directly
Platform → receives application_fee
```
- **Funds held by**: Seller's Stripe account
- **Platform custodian?**: No
- **Chargeback liability**: Seller (connected account)
- **BDDK risk**: VERY LOW
- **Complexity**: Medium-High (seller must have Stripe account)
- **Limitation**: No escrow hold possible

### Recommendation
**Model B (Separate Charges & Transfers)** for V1:
- Enables escrow-like hold (platform controls transfer timing)
- Platform never holds funds in its own bank account
- Stripe handles compliance as regulated entity
- Platform acts as technology/marketplace provider

---

## 4. Risk Checklist (10 Critical Questions)

### For Internal Decision

| # | Question | Current Answer | Risk Level | Action Required |
|---|---|---|---|---|
| 1 | Does the platform hold user funds in its own bank account? | **NO** — Funds in Stripe account | LOW | Maintain Stripe-only model |
| 2 | Does the platform delay transfers to sellers? | **YES** — Until service confirmation | MEDIUM | Define max hold period (e.g., 72h) |
| 3 | Does the platform issue refunds from its own funds? | **NO** — Refund from Stripe balance | LOW | Ensure refund = reverse of original charge |
| 4 | Who bears chargeback liability? | **Platform** (in Model B) | MEDIUM | Budget for chargeback reserve; implement dispute flow |
| 5 | Is KYC required for sellers? | **TBD** — Stripe Connect requires basic KYC | MEDIUM | Stripe handles KYC for connected accounts |
| 6 | Does AML (5549) obligation arise? | **TBD** — Depends on transaction volume | MEDIUM | Consult MASAK guidelines; Stripe handles primary AML |
| 7 | Is there an escrow clause in platform terms of service? | **NO** — Needs to be added | HIGH | Draft escrow terms; define hold period, release conditions, dispute policy |
| 8 | Is refund/cancellation SLA defined? | **NO** — Needs definition | MEDIUM | Define: cancellation window, refund timeline, partial refund rules |
| 9 | Are escrow funds accounted separately from platform revenue? | **YES** — Designed as separate ledger | LOW | Maintain escrow_accounts as separate virtual ledger |
| 10 | Is BDDK approval/notification required? | **TBD** — Legal counsel needed | HIGH | Formal legal opinion required before launch |

---

## 5. Accounting & Tax Impact

### Revenue Recognition

| Event | Accounting Treatment |
|---|---|
| Buyer funds escrow | **NOT revenue** — Liability (escrow holding) |
| Service confirmed + release | Platform fee = **Revenue recognized** |
| Seller payout | Reduction of liability |
| Refund | Reversal of liability; no revenue impact |

### KDV (VAT) Considerations

| Transaction | KDV |
|---|---|
| Platform fee (commission) | KDV applicable — platform issues invoice for commission service |
| Escrow hold amount | No KDV — this is not platform revenue |
| Seller service revenue | Seller's KDV obligation (between seller and buyer) |

### Critical Tax Rule
> Platform fee KDV doğum anı = **release (service confirmed)**, NOT at funding time.
> Escrow hold is a liability, not revenue, until release.

### Required Accounting Entries

```
1. Escrow Funded:
   DR: Escrow Receivable (Stripe)     ₺1,200
   CR: Escrow Liability (Buyer)       ₺1,200

2. Service Confirmed + Release:
   DR: Escrow Liability (Buyer)       ₺1,200
   CR: Seller Payable                 ₺1,068  (net)
   CR: Platform Fee Revenue           ₺12     (commission)
   CR: Provider Commission Payable    ₺120    (provider share)

3. Seller Payout:
   DR: Seller Payable                 ₺1,068
   CR: Bank/Stripe Transfer           ₺1,068

4. Refund:
   DR: Escrow Liability (Buyer)       ₺1,200
   CR: Escrow Receivable (Stripe)     ₺1,200
   (No revenue impact)
```

---

## 6. Open Legal Questions (For External Counsel)

### Priority 1 (Must answer before ANY implementation)

1. **BDDK Scope**: Under 6493, does our proposed Stripe Connect model (platform instructs transfer timing, funds held by Stripe) constitute a "payment service" requiring licensing?

2. **Ödeme Kuruluşu**: Do we need to apply for an ödeme kuruluşu license, or does Stripe's existing license cover our use case as a marketplace technology provider?

3. **Fund Holding Period**: What is the maximum legally permissible holding period before transferring funds to the seller, without triggering regulatory obligations?

4. **Terms of Service**: What escrow-specific clauses must be added to our platform terms of service and user agreements?

### Priority 2 (Before production launch)

5. **MASAK Reporting**: At what transaction volume/threshold do we need to implement AML reporting? Does Stripe's compliance cover this?

6. **Consumer Protection**: What are the buyer's rights regarding refund and dispute under Turkish consumer protection law (6502 sayılı Kanun) in a B2B context?

7. **Cross-Border**: If buyer or seller is outside Turkey, what additional regulatory requirements apply?

8. **Insurance**: Should the platform carry professional indemnity insurance for escrow operations?

### Priority 3 (Operational)

9. **Tax Invoicing**: Should the platform issue a "komisyon faturası" for each transaction's platform fee? What is the KDV treatment?

10. **Dispute Arbitration**: Can the platform act as arbitrator in disputes, or must disputes be referred to an external body?

---

## 7. Recommended Next Steps

### Immediate (Before any code)
- [ ] Engage Turkish fintech legal counsel
- [ ] Present this document as briefing
- [ ] Get formal opinion on BDDK scope (Question 1-2)
- [ ] Define maximum escrow hold period based on legal guidance

### Short-term (After legal clearance)
- [ ] Draft escrow terms of service addendum
- [ ] Define dispute resolution policy
- [ ] Implement Stripe Connect seller onboarding
- [ ] Begin Escrow Phase 1 (MVP) implementation

### Medium-term (Post-launch)
- [ ] Monitor MASAK thresholds
- [ ] Establish chargeback reserve
- [ ] Build dispute evidence collection system
- [ ] Monthly reconciliation reporting

---

## 8. Decision Matrix — GO / NO-GO

| Criterion | Requirement | Status |
|---|---|---|
| Legal opinion on BDDK scope | Written opinion | ⬜ Pending |
| Stripe Connect model approved by counsel | Formal sign-off | ⬜ Pending |
| Escrow terms of service drafted | Legal review complete | ⬜ Pending |
| Dispute policy defined | Internal + legal review | ⬜ Pending |
| Max hold period defined | Legal guidance | ⬜ Pending |
| Technical architecture reviewed | Complete | ✅ Done |
| Domain model designed | Complete | ✅ Done |
| Risk matrix documented | Complete | ✅ Done |
| Accounting entries defined | Complete | ✅ Done |

**GO Decision**: All items must be ✅ before Escrow Phase 1 production launch.

---

> **Note**: This document is for internal planning and legal briefing purposes.
> It does not constitute legal advice. Formal legal counsel is required
> before implementing any escrow or payment holding functionality.
