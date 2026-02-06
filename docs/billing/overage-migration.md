# Active Overage Pricing — Migration Plan

> Status: DRAFT — Awaiting 1 shadow billing cycle data
> Owner: Platform Team
> Last updated: 2026-02-06

---

## 1. Decision Framework

### Metrics to Evaluate (from Revenue Analytics)

Before activating overage pricing, collect these metrics for at least 1 full billing cycle:

| Metric | Source | Threshold for GO |
|---|---|---|
| Pro tenants with usage ≥80% quota | `/api/admin/analytics/usage-overview` → over_80_count | ≥ 30% of Pro tenants |
| Pro tenants with usage ≥100% quota | usage-overview → exceeded_count | ≥ 10% of Pro tenants |
| Average Pro usage (b2b.match_request/mo) | usage_ledger aggregate | > 50 (meaningful activity) |
| p95 Pro usage | usage_ledger percentile | > 80 (close to quota) |
| Enterprise candidate count | usage-overview → enterprise_candidates_count | > 0 |
| Finalize pending_after | billing_period_jobs | Must be 0 (clean reconciliation) |
| Push error rate | usage_ledger error_records / total | < 1% |

### Decision Rules

```
IF pro_exceeded_rate >= 10% AND avg_usage > 50 AND push_error_rate < 1%:
    → ACTIVATE overage pricing
    
IF pro_exceeded_rate >= 30%:
    → Consider raising free tier OR aggressive Enterprise upsell first

IF finalize pending_after > 0:
    → DO NOT activate until reconciliation is clean
```

---

## 2. Pricing Strategy

### Current Plan Structure

| Plan | Monthly Price | Free Quota (b2b.match_request) |
|---|---|---|
| Starter | ₺499 | N/A (no B2B access) |
| Pro | ₺999 | 100 / month |
| Enterprise | ₺2,499 | 1,000 / month |

### Overage Pricing Model

```
Pro:       100 free → ₺X per additional match_request
Enterprise: 1000 free → ₺Y per additional match_request
```

### How to Calculate X and Y

**Method: Revenue-anchored pricing**

```
X = (Pro monthly price * target_overage_revenue_ratio) / avg_monthly_overage

Example:
- Pro price: ₺999
- Target: overage = 20% of MRR
- Avg overage per tenant: ~30 requests/month above quota
- X = (999 * 0.20) / 30 = ₺6.66 → round to ₺7/request
```

**Recommended ranges:**
- Pro (X): ₺5–10 per match_request
- Enterprise (Y): ₺3–7 per match_request (volume discount)

**Constraints:**
- X must be low enough that Pro doesn't churn
- X must be high enough that Enterprise upsell makes sense
- Break-even: tenant doing 100 + 150 overage at ₺7 = ₺999 + ₺1,050 = ₺2,049
  → Still cheaper than Enterprise (₺2,499), so upgrade incentive preserved

### Anti-patterns to Avoid
- Don't set X so high that Pro tenants stop using B2B
- Don't set Y = 0 (Enterprise should still have soft cost awareness)
- Don't charge retroactively for shadow period usage

---

## 3. Technical Migration Steps

### Phase 0: Preparation (before activation)

1. **Create new Stripe metered price** (real, non-zero)
   ```
   stripe.Price.create(
     product=existing_metered_product_id,
     currency="try",
     recurring={"interval": "month", "usage_type": "metered"},
     unit_amount=700,  # ₺7.00 in kuruş
     metadata={"type": "overage", "plan": "pro"}
   )
   ```

2. **Store new price ID in billing_plan_catalog**
   ```
   billing_plan_catalog: {
     plan: "pro",
     interval: "monthly",
     currency: "TRY",
     overage_price_id: "price_xxx",  // NEW field
     overage_unit_amount: 700,
     free_quota: 100
   }
   ```

3. **Update UsagePushService** to use overage price
   - Only push usage ABOVE free quota
   - quantity = max(0, total_used - free_quota)

### Phase 1: New subscriptions only

4. **New tenants** subscribing to Pro/Enterprise get real metered item
   - `setup-metered-item` uses real price instead of shadow (₺0)
   - Existing tenants keep shadow item

5. **Feature flag**: `OVERAGE_BILLING_ENABLED=new_only`

### Phase 2: Opt-in migration

6. **Admin UI**: "Activate overage billing" toggle per tenant
   - Detach shadow metered item
   - Attach real metered item
   - Notify tenant (in-app + email)

7. **Feature flag**: `OVERAGE_BILLING_ENABLED=opt_in`

### Phase 3: Full rollout

8. **Migrate all remaining shadow items** to real pricing
   - Batch script with dry_run
   - Audit log per migration

9. **Feature flag**: `OVERAGE_BILLING_ENABLED=all`

10. **Remove shadow price** from Stripe (cleanup)

---

## 4. Rollout Strategy

| Phase | Scope | Duration | Success Criteria |
|---|---|---|---|
| Shadow | All tenants | 1-2 cycles | push_error=0, pending_after=0 |
| Phase 1 | New subs only | 1 cycle | No billing complaints, reconciliation clean |
| Phase 2 | Opt-in (top 10%) | 1 cycle | Churn rate stable, revenue increase visible |
| Phase 3 | Full rollout | - | All tenants on real pricing |

### Rollback Plan

At each phase, if issues arise:
1. Set `OVERAGE_BILLING_ENABLED=off`
2. Stripe metered items stay but report 0 usage
3. No charges generated
4. Revert to shadow mode
5. Post-mortem + fix + retry

---

## 5. Risk Matrix

| Risk | Probability | Impact | Mitigation |
|---|---|---|---|
| Double-charge (push idempotency failure) | Low | High | source_event_id unique constraint + Stripe idempotency key |
| Overcharge (wrong quota calculation) | Medium | High | Shadow validation: compare expected vs actual Stripe invoice |
| Churn spike (price shock) | Medium | Medium | Phase rollout + 1-month grace notification |
| Enterprise downgrade (overage cheaper than Enterprise) | Low | Medium | Price X calibrated: 100+150 overage < Enterprise price |
| Stripe API failure during push | Low | Medium | Retry logic + partial failure handling + Slack alert |
| Reconciliation mismatch | Low | High | Finalize lock + pending_after=0 check + audit trail |

---

## 6. Communication Plan

### Before Activation
- [ ] Email to all Pro/Enterprise tenants: "Usage-based billing starting [date]"
- [ ] In-app banner: "Starting [date], usage above your plan quota will be billed"
- [ ] Documentation update: pricing page, FAQ

### At Activation
- [ ] In-app notification: "Overage billing is now active"
- [ ] First invoice preview (before charge)

### Ongoing
- [ ] Monthly usage email: total usage, quota, overage amount
- [ ] >80% quota in-app warning (already implemented)
- [ ] >100% quota alert + upgrade CTA

---

## 7. Success Metrics (Post-Activation)

| Metric | Target |
|---|---|
| MRR increase from overage | +15-25% within 3 months |
| Enterprise upgrade rate | +10% from Pro segment |
| Churn rate | No increase vs pre-overage baseline |
| Support tickets (billing) | < 5% of active tenants |
| Push error rate | < 0.1% |

---

## Appendix: Current System Readiness

- [x] Usage ledger with idempotency
- [x] Shadow metered push
- [x] Finalize cron with lock
- [x] Slack alerting
- [x] Revenue analytics dashboard
- [x] Quota nudging (in-app >80% warning)
- [x] Plan catalog in DB (not hardcoded)
- [x] Audit trail for all billing actions
- [ ] Real metered price created in Stripe
- [ ] UsagePushService updated for quota-aware push
- [ ] Feature flag for rollout phases
- [ ] Tenant communication templates
