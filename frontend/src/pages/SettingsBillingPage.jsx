import React, { useCallback, useMemo, useState } from "react";
import { AlertTriangle, CreditCard, RefreshCw } from "lucide-react";
import { toast } from "sonner";

import { Button } from "../components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "../components/ui/card";
import { Tabs, TabsList, TabsTrigger } from "../components/ui/tabs";
import { SettingsSectionNav } from "../components/settings/SettingsSectionNav";
import { BillingCancelDialog } from "../components/settings/BillingCancelDialog";
import { BillingPlanCard } from "../components/settings/BillingPlanCard";
import { BillingSummaryCards } from "../components/settings/BillingSummaryCards";
import { useSeo } from "../hooks/useSeo";
import { getUser } from "../lib/api";
import {
  cancelBillingSubscription,
  changeBillingPlan,
  createCustomerPortalSession,
  getBillingSubscription,
  reactivateBillingSubscription,
} from "../lib/billing";
import {
  BILLING_PLAN_OPTIONS,
  BILLING_PLAN_ORDER,
  formatBillingDate,
  getIntervalText,
} from "../lib/billingCatalog";

function translateStatus(status) {
  const map = {
    active: "Aktif",
    trialing: "Trial",
    past_due: "Ödeme sorunu",
    unpaid: "Ödenmedi",
    canceled: "İptal edildi",
    incomplete: "Eksik ödeme",
    incomplete_expired: "Süresi doldu",
  };
  return map[status] || status || "—";
}

export default function SettingsBillingPage() {
  const currentUser = getUser();
  const canManageUsers = (currentUser?.roles || []).some((role) => ["super_admin", "admin"].includes(role));
  const [overview, setOverview] = useState(null);
  const [loading, setLoading] = useState(true);
  const [billingCycle, setBillingCycle] = useState("monthly");
  const [actionKey, setActionKey] = useState("");
  const [cancelOpen, setCancelOpen] = useState(false);

  useSeo({
    title: "Faturalama",
    description: "Planınızı, yenileme tarihini ve ödeme durumunu yönetin.",
    canonicalPath: "/app/settings/billing",
    type: "website",
  });

  const loadBilling = useCallback(async () => {
    setLoading(true);
    try {
      const data = await getBillingSubscription();
      setOverview(data);
      setBillingCycle(data?.interval || "monthly");
    } catch (err) {
      toast.error(err?.message || "Faturalama bilgileri alınamadı.");
    } finally {
      setLoading(false);
    }
  }, []);

  React.useEffect(() => {
    void loadBilling();
  }, [loadBilling]);

  React.useEffect(() => {
    function handleVisibilityRefresh() {
      if (document.visibilityState === "visible") {
        void loadBilling();
      }
    }

    function handleFocusRefresh() {
      void loadBilling();
    }

    window.addEventListener("focus", handleFocusRefresh);
    document.addEventListener("visibilitychange", handleVisibilityRefresh);
    return () => {
      window.removeEventListener("focus", handleFocusRefresh);
      document.removeEventListener("visibilitychange", handleVisibilityRefresh);
    };
  }, [loadBilling]);

  const currentPlanKey = overview?.plan || "trial";
  const currentPlanLabel = BILLING_PLAN_OPTIONS[currentPlanKey]?.label || (currentPlanKey ? currentPlanKey.toUpperCase() : "Trial");
  const statusLabel = translateStatus(overview?.status);
  const planCards = useMemo(() => BILLING_PLAN_ORDER.map((key) => BILLING_PLAN_OPTIONS[key]), []);

  async function handlePortalOpen() {
    setActionKey("portal");
    try {
      const result = await createCustomerPortalSession({
        origin_url: window.location.origin,
        return_path: "/app/settings/billing",
      });
      window.location.href = result.url;
    } catch (err) {
      toast.error(err?.message || "Ödeme yöntemi güncelleme ekranı açılamadı.");
    } finally {
      setActionKey("");
    }
  }

  async function handlePlanChange(planKey) {
    setActionKey(`plan:${planKey}`);
    try {
      const result = await changeBillingPlan({
        plan: planKey,
        interval: billingCycle,
        origin_url: window.location.origin,
        cancel_path: "/app/settings/billing",
      });

      if (result?.action === "checkout_redirect" && result?.url) {
        window.location.href = result.url;
        return;
      }

      toast.success(result?.message || "Plan değişikliği kaydedildi.");
      await loadBilling();
    } catch (err) {
      toast.error(err?.message || "Plan değişikliği yapılamadı.");
    } finally {
      setActionKey("");
    }
  }

  async function handleCancelConfirm() {
    setActionKey("cancel");
    try {
      const result = await cancelBillingSubscription();
      toast.success(result?.message || "Abonelik iptal talebiniz alındı.");
      setCancelOpen(false);
      await loadBilling();
    } catch (err) {
      toast.error(err?.message || "Abonelik iptal edilemedi.");
    } finally {
      setActionKey("");
    }
  }

  async function handleReactivateSubscription() {
    setActionKey("reactivate");
    try {
      const result = await reactivateBillingSubscription();
      toast.success(result?.message || "Aboneliğiniz yeniden aktif hale getirildi.");
      await loadBilling();
    } catch (err) {
      toast.error(err?.message || "Abonelik yeniden başlatılamadı.");
    } finally {
      setActionKey("");
    }
  }

  if (loading && !overview) {
    return <div className="rounded-3xl border bg-card/85 p-6 text-sm text-muted-foreground" data-testid="billing-page-loading">Faturalama bilgileri yükleniyor...</div>;
  }

  return (
    <div className="space-y-6" data-testid="billing-page">
      <div className="space-y-3">
        <div>
          <h1 className="text-4xl font-semibold tracking-tight text-foreground" data-testid="billing-page-title">Faturalama</h1>
          <p className="mt-2 text-base text-muted-foreground" data-testid="billing-page-subtitle">
            Mevcut planınızı, yenileme tarihinizi ve abonelik yaşam döngünüzü buradan yönetin.
          </p>
        </div>
        <SettingsSectionNav showUsersSection={canManageUsers} />
      </div>

      <BillingSummaryCards
        planLabel={currentPlanLabel}
        renewalDate={formatBillingDate(overview?.next_renewal_at)}
        intervalLabel={overview?.interval_label || getIntervalText(overview?.interval)}
        statusLabel={statusLabel}
      />

      {overview?.payment_issue?.has_issue ? (
        <div className="rounded-3xl border border-amber-300 bg-amber-50 px-5 py-4 text-sm text-amber-900" data-testid="billing-payment-issue-banner">
          <div className="flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
            <div className="flex items-start gap-3">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
              <div>
                <p className="font-semibold" data-testid="billing-payment-issue-text">{overview.payment_issue.message}</p>
              </div>
            </div>
            <Button
              onClick={() => void handlePortalOpen()}
              disabled={actionKey === "portal" || !overview?.portal_available}
              data-testid="billing-payment-issue-cta"
            >
              {actionKey === "portal" ? "Yönlendiriliyor..." : overview?.payment_issue?.cta_label || "Ödeme Yöntemini Güncelle"}
            </Button>
          </div>
        </div>
      ) : null}

      {overview?.cancel_message ? (
        <div className="rounded-3xl border border-blue-200 bg-blue-50 px-5 py-4 text-sm text-blue-900" data-testid="billing-cancel-pending-banner">
          {overview.cancel_message}
        </div>
      ) : null}

      {overview?.scheduled_change?.message ? (
        <div className="rounded-3xl border border-emerald-200 bg-emerald-50 px-5 py-4 text-sm text-emerald-900" data-testid="billing-scheduled-change-banner">
          <p className="font-semibold" data-testid="billing-scheduled-change-text">{overview.scheduled_change.message}</p>
          <p className="mt-1 text-sm" data-testid="billing-scheduled-change-meta">
            Hedef plan: {BILLING_PLAN_OPTIONS[overview.scheduled_change.plan]?.label || overview.scheduled_change.plan} · {overview.scheduled_change.interval_label} · Başlangıç: {formatBillingDate(overview.scheduled_change.effective_at)}
          </p>
        </div>
      ) : null}

      {overview?.legacy_notice ? (
        <div className="rounded-3xl border border-border/60 bg-card/70 px-5 py-4 text-sm text-muted-foreground" data-testid="billing-legacy-notice">
          {overview.legacy_notice}
        </div>
      ) : null}

      <div className="grid gap-4 lg:grid-cols-[0.92fr_1.08fr]">
        <Card className="rounded-[28px] border-border/60 bg-card/85" data-testid="billing-management-card">
          <CardHeader>
            <CardTitle data-testid="billing-management-title">Abonelik yönetimi</CardTitle>
            <CardDescription data-testid="billing-management-description">
              Plan değişikliği, iptal ve ödeme yöntemi güncelleme işlemlerini yönetin.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <Button
              onClick={() => void handlePortalOpen()}
              variant="outline"
              disabled={actionKey === "portal" || !overview?.portal_available}
              className="w-full justify-between rounded-2xl"
              data-testid="billing-update-payment-method-button"
            >
              <span>Ödeme Yöntemini Güncelle</span>
              <CreditCard className="h-4 w-4" />
            </Button>

            <Button
              onClick={() => setCancelOpen(true)}
              variant="outline"
              disabled={Boolean(overview?.cancel_at_period_end) || !overview?.can_cancel || actionKey === "cancel"}
              className="w-full justify-between rounded-2xl"
              data-testid="billing-cancel-subscription-button"
            >
              <span>{overview?.cancel_at_period_end ? "İptal planlandı" : "Aboneliği İptal Et"}</span>
              <AlertTriangle className="h-4 w-4" />
            </Button>

            {overview?.cancel_at_period_end ? (
              <Button
                onClick={() => void handleReactivateSubscription()}
                variant="outline"
                disabled={actionKey === "reactivate"}
                className="w-full justify-between rounded-2xl"
                data-testid="billing-reactivate-subscription-button"
              >
                <span>{actionKey === "reactivate" ? "İşleniyor..." : "Aboneliği Yeniden Başlat"}</span>
                <RefreshCw className="h-4 w-4" />
              </Button>
            ) : null}

            <Button
              onClick={() => void loadBilling()}
              variant="ghost"
              className="w-full justify-between rounded-2xl"
              data-testid="billing-refresh-button"
            >
              <span>Bilgileri Yenile</span>
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
            </Button>

            {!overview?.portal_available ? (
              <p className="text-xs text-muted-foreground" data-testid="billing-portal-unavailable-note">
                Ödeme yöntemi güncelleme bağlantısı ilk Stripe müşteri kaydı tamamlandığında aktif olur.
              </p>
            ) : null}
          </CardContent>
        </Card>

        <Card className="rounded-[28px] border-border/60 bg-card/85" data-testid="billing-plan-change-card">
          <CardHeader>
            <CardTitle data-testid="billing-plan-change-title">Planı Değiştir</CardTitle>
            <CardDescription data-testid="billing-plan-change-description">
              Upgrade hemen uygulanır. Downgrade ise bir sonraki dönem başlar.
            </CardDescription>
            <div className="pt-2" data-testid="billing-cycle-tabs-wrap">
              <Tabs value={billingCycle} onValueChange={setBillingCycle} data-testid="billing-cycle-tabs">
                <TabsList className="h-11 rounded-xl bg-muted/50 p-1" data-testid="billing-cycle-tabs-list">
                  <TabsTrigger value="monthly" className="rounded-lg px-4" data-testid="billing-cycle-monthly">Aylık</TabsTrigger>
                  <TabsTrigger value="yearly" className="rounded-lg px-4" data-testid="billing-cycle-yearly">Yıllık</TabsTrigger>
                </TabsList>
              </Tabs>
            </div>
          </CardHeader>
          <CardContent>
            <div className="grid gap-4 xl:grid-cols-3" data-testid="billing-plan-grid">
              {planCards.map((plan) => (
                <BillingPlanCard
                  key={plan.key}
                  plan={plan}
                  billingCycle={billingCycle}
                  isCurrent={currentPlanKey === plan.key && (overview?.interval || "monthly") === billingCycle}
                  loading={actionKey === `plan:${plan.key}`}
                  disabled={actionKey !== "" && actionKey !== `plan:${plan.key}`}
                  onSelect={() => void handlePlanChange(plan.key)}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <BillingCancelDialog
        open={cancelOpen}
        loading={actionKey === "cancel"}
        onOpenChange={setCancelOpen}
        onConfirm={handleCancelConfirm}
      />
    </div>
  );
}