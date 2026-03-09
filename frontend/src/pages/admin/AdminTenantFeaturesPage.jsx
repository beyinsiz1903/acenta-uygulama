import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Search, Save, RotateCcw, Building2, Shield, Loader2, Copy, Check, RefreshCw, AlertTriangle, CreditCard, Calendar } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Checkbox } from "../../components/ui/checkbox";
import { Badge } from "../../components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../../components/ui/alert-dialog";
import { toast } from "sonner";
import { FEATURE_CATALOG } from "../../config/featureCatalog";
import { api, apiErrorMessage } from "../../lib/api";
import { fetchTenantList } from "../../lib/tenantFeaturesAdmin";
import { AdminTenantUsageOverview } from "../../components/admin/AdminTenantUsageOverview";
import { TenantEntitlementOverview } from "../../components/admin/TenantEntitlementOverview";

const STATUS_MAP = {
  active: { label: "Active", color: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20" },
  trialing: { label: "Trial", color: "bg-blue-500/10 text-blue-700 border-blue-500/20" },
  past_due: { label: "Payment Issue", color: "bg-amber-500/10 text-amber-700 border-amber-500/20" },
  incomplete: { label: "Payment Issue", color: "bg-amber-500/10 text-amber-700 border-amber-500/20" },
  unpaid: { label: "Payment Issue", color: "bg-amber-500/10 text-amber-700 border-amber-500/20" },
  canceled: { label: "Canceled", color: "bg-muted text-muted-foreground border-border" },
};

const LIST_STAGE_MAP = {
  active: { label: "Aktif", color: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20" },
  trialing: { label: "Trial", color: "bg-blue-500/10 text-blue-700 border-blue-500/20" },
  payment_issue: { label: "Ödeme sorunu", color: "bg-amber-500/10 text-amber-700 border-amber-500/20" },
  canceling: { label: "İptal sırada", color: "bg-orange-500/10 text-orange-700 border-orange-500/20" },
  canceled: { label: "İptal", color: "bg-muted text-muted-foreground border-border" },
  inactive: { label: "Pasif", color: "bg-muted text-muted-foreground border-border" },
};

const PLAN_BADGE_MAP = {
  trial: "bg-sky-500/10 text-sky-700 border-sky-500/20",
  starter: "bg-slate-500/10 text-slate-700 border-slate-500/20",
  pro: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20",
  enterprise: "bg-violet-500/10 text-violet-700 border-violet-500/20",
};

const FILTER_OPTIONS = [
  { key: "all", label: "Tümü" },
  { key: "payment_issue", label: "Ödeme sorunu" },
  { key: "trialing", label: "Trial" },
  { key: "canceling", label: "İptal sırada" },
  { key: "active", label: "Aktif" },
];

const TENANT_STAGE_PRIORITY = {
  payment_issue: 0,
  canceling: 1,
  trialing: 2,
  active: 3,
  canceled: 4,
  inactive: 5,
};

function resolveTenantStage(tenant) {
  if (tenant?.lifecycle_stage) return tenant.lifecycle_stage;
  if (tenant?.has_payment_issue) return "payment_issue";
  if (tenant?.cancel_at_period_end && ["active", "trialing"].includes(tenant?.subscription_status)) return "canceling";
  if (["past_due", "unpaid", "incomplete", "incomplete_expired"].includes(tenant?.subscription_status)) return "payment_issue";
  if (tenant?.subscription_status === "trialing" || tenant?.plan === "trial") return "trialing";
  if (tenant?.subscription_status === "canceled") return "canceled";
  return tenant?.status === "active" ? "active" : (tenant?.status || "inactive");
}

function getTenantStageMeta(tenant) {
  return LIST_STAGE_MAP[resolveTenantStage(tenant)] || { label: resolveTenantStage(tenant), color: "bg-muted text-muted-foreground border-border" };
}

function TenantSummaryCard({ title, value, subtitle, icon: Icon, tone = "default", testId }) {
  const toneClasses = {
    default: "border-border/70 bg-card",
    warning: "border-amber-500/30 bg-amber-500/5",
    success: "border-emerald-500/30 bg-emerald-500/5",
    info: "border-sky-500/30 bg-sky-500/5",
  };

  return (
    <div className={`rounded-2xl border p-4 shadow-sm ${toneClasses[tone] || toneClasses.default}`} data-testid={testId}>
      <div className="flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">{title}</p>
          <p className="mt-2 text-3xl font-semibold tracking-tight text-foreground">{value}</p>
          <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
        </div>
        <div className="rounded-2xl border border-white/60 bg-background/70 p-2.5 text-muted-foreground">
          <Icon className="h-4 w-4" />
        </div>
      </div>
    </div>
  );
}

function TenantFilterButton({ option, count, active, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-xs font-medium transition-colors ${active ? "border-primary bg-primary text-primary-foreground" : "border-border bg-background text-muted-foreground hover:border-primary/30 hover:text-foreground"}`}
      data-testid={`tenant-filter-${option.key}`}
    >
      <span>{option.label}</span>
      <span className={`rounded-full px-1.5 py-0.5 text-[11px] ${active ? "bg-white/20 text-primary-foreground" : "bg-muted text-foreground"}`}>{count}</span>
    </button>
  );
}

function getDisplayStatus(sub) {
  if (!sub) return null;
  if (sub.cancel_at_period_end && sub.status === "active") {
    return { label: "Canceling", color: "bg-orange-500/10 text-orange-700 border-orange-500/20" };
  }
  return STATUS_MAP[sub.status] || { label: sub.status, color: "bg-muted text-muted-foreground border-border" };
}

function daysUntil(isoDate) {
  if (!isoDate) return null;
  const target = typeof isoDate === "string" ? new Date(isoDate.includes("T") ? isoDate : isoDate + "T00:00:00Z") : new Date(Number(isoDate) * 1000);
  if (isNaN(target.getTime())) return null;
  const now = new Date();
  const diff = Math.ceil((target - now) / (1000 * 60 * 60 * 24));
  return diff;
}

function formatTRDate(isoDate) {
  if (!isoDate) return "—";
  try {
    const d = typeof isoDate === "string" ? new Date(isoDate.includes("T") ? isoDate : isoDate + "T00:00:00Z") : new Date(Number(isoDate) * 1000);
    if (isNaN(d.getTime())) return "—";
    return d.toLocaleDateString("tr-TR", { day: "2-digit", month: "2-digit", year: "numeric" });
  } catch { return "—"; }
}

function SubscriptionPanel({ tenantId }) {
  const [sub, setSub] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  const [cancelDialogOpen, setCancelDialogOpen] = useState(false);
  const [canceling, setCanceling] = useState(false);

  const fetchSub = useCallback(async () => {
    if (!tenantId) return;
    setLoading(true);
    setError(false);
    try {
      const res = await api.get(`/admin/billing/tenants/${tenantId}/subscription`);
      setSub(res.data?.subscription || null);
    } catch {
      setError(true);
      setSub(null);
    } finally {
      setLoading(false);
    }
  }, [tenantId]);

  useEffect(() => { fetchSub(); }, [fetchSub]);

  if (loading) {
    return (
      <div className="rounded-lg border bg-muted/20 p-3 flex items-center gap-2 text-xs text-muted-foreground" data-testid="sub-panel-loading">
        <Loader2 className="h-3.5 w-3.5 animate-spin" /> Subscription yükleniyor...
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 flex items-center justify-between" data-testid="sub-panel-error">
        <span className="text-xs text-destructive">Billing verisi alınamadı.</span>
        <Button variant="ghost" size="sm" onClick={fetchSub} className="h-6 px-2"><RefreshCw className="h-3 w-3" /></Button>
      </div>
    );
  }

  if (!sub) {
    return (
      <div className="rounded-lg border border-dashed bg-muted/10 p-3 flex items-center gap-2" data-testid="sub-panel-empty">
        <CreditCard className="h-4 w-4 text-muted-foreground/50" />
        <span className="text-xs text-muted-foreground">Bu tenant için aktif subscription bulunamadı.</span>
      </div>
    );
  }

  const displayStatus = getDisplayStatus(sub);
  const renewalDays = daysUntil(sub.current_period_end);
  const graceDays = sub.grace_period_until ? daysUntil(sub.grace_period_until) : null;
  const showGrace = graceDays !== null && graceDays > 0;
  const isPastDue = sub.status === "past_due" || sub.status === "unpaid" || sub.status === "incomplete";

  const handleCancelSubscription = async () => {
    setCanceling(true);
    try {
      await api.post(`/admin/billing/tenants/${tenantId}/cancel-subscription`, { at_period_end: true });
      toast.success("Abonelik period sonunda iptal edilecek.");
      setCancelDialogOpen(false);
      fetchSub();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setCanceling(false);
    }
  };

  return (
    <div className="rounded-lg border bg-card p-3 space-y-2" data-testid="sub-panel">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <CreditCard className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs font-medium uppercase tracking-wide text-muted-foreground">Subscription</span>
        </div>
        <Button variant="ghost" size="sm" onClick={fetchSub} className="h-6 px-2" title="Yenile" data-testid="sub-refresh-btn">
          <RefreshCw className="h-3 w-3" />
        </Button>
      </div>

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
        <div>
          <p className="text-muted-foreground mb-0.5">Plan</p>
          <p className="font-medium capitalize">{sub.plan || "—"}</p>
        </div>
        <div>
          <p className="text-muted-foreground mb-0.5">Durum</p>
          <Badge className={`${displayStatus?.color} text-2xs px-1.5 py-0`} data-testid="sub-status-badge">
            {displayStatus?.label}
          </Badge>
        </div>
        <div>
          <p className="text-muted-foreground mb-0.5">Yenileme</p>
          <div className="flex items-center gap-1">
            <Calendar className="h-3 w-3 text-muted-foreground" />
            <span>{formatTRDate(sub.current_period_end)}</span>
          </div>
          {renewalDays !== null && renewalDays > 0 && (
            <p className="text-2xs text-muted-foreground">{renewalDays} gün kaldı</p>
          )}
        </div>
        <div>
          <p className="text-muted-foreground mb-0.5">Mode</p>
          <p className="font-medium">{sub.mode || "test"}</p>
        </div>
      </div>

      {/* Cancel at period end badge */}
      {sub.cancel_at_period_end && sub.status === "active" && (
        <div className="rounded border border-orange-500/30 bg-orange-500/5 px-2.5 py-1.5 text-xs text-orange-700 flex items-center gap-1.5" data-testid="sub-cancel-badge">
          <AlertTriangle className="h-3.5 w-3.5" />
          Period sonunda iptal edilecek.
        </div>
      )}

      {/* Past due / grace warning */}
      {isPastDue && (
        <div className="rounded border border-amber-500/30 bg-amber-500/5 px-2.5 py-1.5 text-xs text-amber-700 flex items-center gap-1.5" data-testid="sub-past-due-banner">
          <AlertTriangle className="h-3.5 w-3.5" />
          Ödeme başarısız.
          {showGrace && <span className="font-medium">Grace: {graceDays} gün kaldı.</span>}
          {!showGrace && <span>Tenant kısıtlanabilir.</span>}
        </div>
      )}

      {/* Cancel button (super_admin) */}
      {sub.status === "active" && !sub.cancel_at_period_end && (
        <div className="flex justify-end">
          <Button
            variant="outline"
            size="sm"
            className="text-xs text-destructive border-destructive/30 hover:bg-destructive/5"
            data-testid="cancel-sub-btn"
            onClick={() => setCancelDialogOpen(true)}
          >
            Period Sonunda İptal Et
          </Button>
        </div>
      )}

      <AlertDialog open={cancelDialogOpen} onOpenChange={setCancelDialogOpen}>
        <AlertDialogContent data-testid="subscription-cancel-confirm-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Aboneliği period sonunda iptal et</AlertDialogTitle>
            <AlertDialogDescription>
              Tenant için plan hemen kapanmaz; mevcut dönem sonuna kadar aktif kalır. Bu aksiyon retention tarafında geri dönüş fırsatı yaratır.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={canceling} data-testid="subscription-cancel-confirm-cancel">Vazgeç</AlertDialogCancel>
            <AlertDialogAction
              onClick={(event) => {
                event.preventDefault();
                handleCancelSubscription();
              }}
              disabled={canceling}
              data-testid="subscription-cancel-confirm-accept"
            >
              {canceling ? "İşleniyor..." : "İptali onayla"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}

function PlanChangeImpactCard({ currentPlanLabel, nextPlanLabel, impactItems }) {
  if (!impactItems.length) return null;

  return (
    <div className="rounded-2xl border border-primary/20 bg-primary/5 p-4" data-testid="plan-change-impact-card">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Plan değişim özeti</p>
          <p className="mt-1 text-sm text-foreground">
            <strong>{currentPlanLabel}</strong> → <strong>{nextPlanLabel}</strong>
          </p>
        </div>
        <Badge variant="outline" data-testid="plan-change-impact-badge">Onay gerekli</Badge>
      </div>
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {impactItems.map((item) => (
          <div key={item.key} className="rounded-xl border bg-background/80 px-3 py-3" data-testid={`plan-impact-${item.key.replace(/\./g, "-")}`}>
            <p className="text-xs text-muted-foreground">{item.label}</p>
            <p className="mt-2 text-sm font-semibold text-foreground">{item.from} → {item.to}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

function TenantListItem({ tenant, selected, onSelect }) {
  const [copied, setCopied] = useState(false);
  const stageMeta = getTenantStageMeta(tenant);
  const planClass = PLAN_BADGE_MAP[tenant.plan] || "bg-muted text-muted-foreground border-border";

  const handleCopy = (e) => {
    e.stopPropagation();
    navigator.clipboard.writeText(tenant.id);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };

  return (
    <div
      role="button"
      tabIndex={0}
      data-testid={`tenant-row-${tenant.id}`}
      onClick={() => onSelect(tenant)}
      onKeyDown={(e) => e.key === "Enter" && onSelect(tenant)}
      className={`w-full text-left px-3 py-2.5 border-b border-border transition-colors cursor-pointer ${
        selected ? "bg-primary/10 border-l-2 border-l-primary" : "hover:bg-muted/50"
      }`}
    >
      <div className="flex items-center justify-between gap-2">
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-foreground truncate">{tenant.name || "(isimsiz)"}</p>
          <p className="text-xs text-muted-foreground truncate">{tenant.slug}</p>
          <div className="mt-2 flex flex-wrap items-center gap-1.5">
            <Badge className={`${planClass} text-2xs px-1.5 py-0`} data-testid={`tenant-plan-badge-${tenant.id}`}>
              {tenant.plan_label || tenant.plan || "Starter"}
            </Badge>
            <Badge className={`${stageMeta.color} text-2xs px-1.5 py-0`} data-testid={`tenant-lifecycle-badge-${tenant.id}`}>
              {stageMeta.label}
            </Badge>
            {tenant.grace_period_until ? (
              <span className="text-[11px] font-medium text-amber-700" data-testid={`tenant-grace-period-${tenant.id}`}>
                Grace: {formatTRDate(tenant.grace_period_until)}
              </span>
            ) : null}
          </div>
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <Badge variant={tenant.status === "active" ? "default" : "secondary"} className="text-2xs px-1.5 py-0">
            {tenant.status}
          </Badge>
          <button type="button" onClick={handleCopy} className="p-1 rounded hover:bg-muted text-muted-foreground" title="ID kopyala">
            {copied ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
          </button>
        </div>
      </div>
    </div>
  );
}

function FeatureCheckboxRow({ feature, checked, isFromPlan, onChange, disabled }) {
  return (
    <label
      className={`flex items-start gap-3 p-3 rounded-lg border transition-colors cursor-pointer ${
        checked ? "border-primary/40 bg-primary/5" : "border-border hover:border-muted-foreground/30"
      } ${disabled ? "opacity-50 pointer-events-none" : ""}`}
      data-testid={`feature-checkbox-${feature.key}`}
    >
      <Checkbox checked={checked} onCheckedChange={onChange} disabled={disabled} className="mt-0.5" />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-1.5">
          <span className="text-sm font-medium text-foreground">{feature.label}</span>
          {isFromPlan && checked && (
            <Badge variant="outline" className="text-2xs px-1 py-0 text-muted-foreground">Plan</Badge>
          )}
        </div>
        {feature.description && (
          <p className="text-xs text-muted-foreground mt-0.5">{feature.description}</p>
        )}
      </div>
    </label>
  );
}

export default function AdminTenantFeaturesPage() {
  const [tenants, setTenants] = useState([]);
  const [tenantSummary, setTenantSummary] = useState(null);
  const [loadingTenants, setLoadingTenants] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");
  const [selectedTenant, setSelectedTenant] = useState(null);

  // New: plan + add-ons model
  const [currentPlan, setCurrentPlan] = useState("starter");
  const [addOns, setAddOns] = useState([]);
  const [initialPlan, setInitialPlan] = useState("starter");
  const [initialAddOns, setInitialAddOns] = useState([]);
  const [planMatrix, setPlanMatrix] = useState({});
  const [availablePlans, setAvailablePlans] = useState([]);
  const [planCatalog, setPlanCatalog] = useState([]);
  const [entitlementSource, setEntitlementSource] = useState("capabilities");

  const [loadingFeatures, setLoadingFeatures] = useState(false);
  const [saving, setSaving] = useState(false);
  const [planConfirmOpen, setPlanConfirmOpen] = useState(false);

  const syncTenantSnapshot = useCallback((tenantId, patch) => {
    setTenants((prev) => prev.map((item) => (item.id === tenantId ? { ...item, ...patch } : item)));
    setSelectedTenant((prev) => (prev?.id === tenantId ? { ...prev, ...patch } : prev));
  }, []);

  const loadTenantDirectory = useCallback(async () => {
    setLoadingTenants(true);
    try {
      const data = await fetchTenantList();
      setTenants(data.items || []);
      setTenantSummary(data.summary || null);
    } catch {
      setTenants([]);
      setTenantSummary(null);
    } finally {
      setLoadingTenants(false);
    }
  }, []);

  useEffect(() => {
    loadTenantDirectory();
  }, [loadTenantDirectory]);

  const computedSummary = useMemo(() => {
    if (tenantSummary) return tenantSummary;
    const base = {
      total: tenants.length,
      payment_issue_count: 0,
      trial_count: 0,
      canceling_count: 0,
      active_count: 0,
      by_plan: {},
      lifecycle: {},
    };
    tenants.forEach((tenant) => {
      const stage = resolveTenantStage(tenant);
      base.by_plan[tenant.plan || "starter"] = (base.by_plan[tenant.plan || "starter"] || 0) + 1;
      base.lifecycle[stage] = (base.lifecycle[stage] || 0) + 1;
      if (stage === "payment_issue") base.payment_issue_count += 1;
      if (stage === "trialing") base.trial_count += 1;
      if (stage === "canceling") base.canceling_count += 1;
      if (stage === "active") base.active_count += 1;
    });
    return base;
  }, [tenantSummary, tenants]);

  const filterCounts = useMemo(() => ({
    all: tenants.length,
    payment_issue: computedSummary?.lifecycle?.payment_issue || 0,
    trialing: computedSummary?.lifecycle?.trialing || 0,
    canceling: computedSummary?.lifecycle?.canceling || 0,
    active: computedSummary?.lifecycle?.active || 0,
  }), [computedSummary, tenants.length]);

  const filteredTenants = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    return [...tenants]
      .filter((tenant) => {
        const matchesSearch = !q || (tenant.name || "").toLowerCase().includes(q) || (tenant.slug || "").toLowerCase().includes(q);
        const matchesFilter = statusFilter === "all" || resolveTenantStage(tenant) === statusFilter;
        return matchesSearch && matchesFilter;
      })
      .sort((a, b) => {
        const stageDelta = (TENANT_STAGE_PRIORITY[resolveTenantStage(a)] ?? 99) - (TENANT_STAGE_PRIORITY[resolveTenantStage(b)] ?? 99);
        if (stageDelta !== 0) return stageDelta;
        return String(a.name || a.slug || "").localeCompare(String(b.name || b.slug || ""), "tr");
      });
  }, [searchQuery, statusFilter, tenants]);

  const loadFeatures = useCallback(async (tenant) => {
    setSelectedTenant(tenant);
    setLoadingFeatures(true);
    try {
      const res = await api.get(`/admin/tenants/${tenant.id}/features`);
      const data = res.data;
      const plan = data.plan || "starter";
      const ao = data.add_ons || [];
      setCurrentPlan(plan);
      setAddOns([...ao]);
      setInitialPlan(plan);
      setInitialAddOns([...ao]);
      setPlanMatrix(data.plan_matrix || {});
      setAvailablePlans(data.plans || ["starter", "pro", "enterprise"]);
      setPlanCatalog(data.plan_catalog || []);
      setEntitlementSource(data.source || "capabilities");
      syncTenantSnapshot(tenant.id, {
        plan: data.plan || tenant.plan,
        plan_label: data.plan_label || tenant.plan_label,
      });
    } catch {
      setCurrentPlan("starter");
      setAddOns([]);
      setInitialPlan("starter");
      setInitialAddOns([]);
      setPlanCatalog([]);
      toast.error("Feature bilgisi yüklenemedi.");
    } finally {
      setLoadingFeatures(false);
    }
  }, [syncTenantSnapshot]);

  const planFeatures = useMemo(() => new Set(planMatrix[currentPlan] || []), [planMatrix, currentPlan]);

  const effectiveFeatures = useMemo(() => {
    const all = new Set([...(planMatrix[currentPlan] || []), ...addOns]);
    return [...all].sort();
  }, [planMatrix, currentPlan, addOns]);

  const currentPlanDefinition = useMemo(
    () => planCatalog.find((item) => item.key === currentPlan || item.name === currentPlan) || null,
    [planCatalog, currentPlan]
  );
  const initialPlanDefinition = useMemo(
    () => planCatalog.find((item) => item.key === initialPlan || item.name === initialPlan) || null,
    [planCatalog, initialPlan]
  );

  const planImpactItems = useMemo(() => {
    if (currentPlan === initialPlan) return [];

    const currentLimits = initialPlanDefinition?.limits || {};
    const nextLimits = currentPlanDefinition?.limits || {};
    const currentUsageAllowances = initialPlanDefinition?.usage_allowances || initialPlanDefinition?.quotas || {};
    const nextUsageAllowances = currentPlanDefinition?.usage_allowances || currentPlanDefinition?.quotas || {};
    const items = [
      {
        key: "users.active",
        label: "Aktif kullanıcı limiti",
        from: currentLimits["users.active"] ?? "—",
        to: nextLimits["users.active"] ?? "—",
      },
      {
        key: "reservations.monthly",
        label: "Aylık rezervasyon limiti",
        from: currentLimits["reservations.monthly"] ?? currentUsageAllowances["reservation.created"] ?? "—",
        to: nextLimits["reservations.monthly"] ?? nextUsageAllowances["reservation.created"] ?? "—",
      },
      {
        key: "reports.monthly",
        label: "Aylık rapor kotası",
        from: currentUsageAllowances["report.generated"] ?? "—",
        to: nextUsageAllowances["report.generated"] ?? "—",
      },
    ];
    return items;
  }, [currentPlan, currentPlanDefinition, initialPlan, initialPlanDefinition]);

  const isDirty = useMemo(() => {
    if (currentPlan !== initialPlan) return true;
    const sorted1 = [...addOns].sort();
    const sorted2 = [...initialAddOns].sort();
    if (sorted1.length !== sorted2.length) return true;
    return sorted1.some((v, i) => v !== sorted2[i]);
  }, [currentPlan, addOns, initialPlan, initialAddOns]);

  const handleToggleAddOn = (key, checked) => {
    setAddOns((prev) => checked ? [...prev, key] : prev.filter((k) => k !== key));
  };

  const handleReset = () => {
    setCurrentPlan(initialPlan);
    setAddOns([...initialAddOns]);
  };

  const performSave = useCallback(async () => {
    if (!selectedTenant) return;
    setSaving(true);
    try {
      if (currentPlan !== initialPlan) {
        await api.patch(`/admin/tenants/${selectedTenant.id}/plan`, { plan: currentPlan });
      }
      const res = await api.patch(`/admin/tenants/${selectedTenant.id}/add-ons`, { add_ons: addOns });
      const data = res.data;
      setCurrentPlan(data.plan || currentPlan);
      setAddOns([...(data.add_ons || [])]);
      setInitialPlan(data.plan || currentPlan);
      setInitialAddOns([...(data.add_ons || [])]);
      setEntitlementSource(data.source || entitlementSource);
      syncTenantSnapshot(selectedTenant.id, {
        plan: data.plan || currentPlan,
        plan_label: data.plan_label || currentPlanDefinition?.label || currentPlan,
      });
      await loadTenantDirectory();
      toast.success("Özellikler güncellendi.");
      setPlanConfirmOpen(false);
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }, [
    addOns,
    currentPlan,
    currentPlanDefinition?.label,
    entitlementSource,
    initialPlan,
    loadTenantDirectory,
    selectedTenant,
    syncTenantSnapshot,
  ]);

  const handleSave = () => {
    if (!selectedTenant) return;
    if (currentPlan !== initialPlan) {
      setPlanConfirmOpen(true);
      return;
    }
    performSave();
  };

  return (
    <div className="space-y-6" data-testid="admin-tenant-features-page">
      <div className="space-y-2">
        <h1 className="text-2xl font-semibold text-foreground tracking-tight" data-testid="page-title">Tenant Paket Merkezi</h1>
        <p className="text-sm text-muted-foreground mt-1">Plan, faturalama riski ve modül dağılımını tek ekranda görün; ödeme sorunu yaşayan tenant’ları hızla aksiyona alın.</p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-4">
        <TenantSummaryCard
          title="Toplam tenant"
          value={computedSummary?.total || 0}
          subtitle={`${computedSummary?.active_count || 0} aktif tenant izleniyor`}
          icon={Building2}
          tone="default"
          testId="tenant-summary-total"
        />
        <TenantSummaryCard
          title="Ödeme sorunu"
          value={computedSummary?.payment_issue_count || 0}
          subtitle="Billing aksiyonu bekleyen tenant sayısı"
          icon={AlertTriangle}
          tone="warning"
          testId="tenant-summary-payment-issue"
        />
        <TenantSummaryCard
          title="Trial"
          value={computedSummary?.trial_count || 0}
          subtitle="Yakın takip edilmesi gereken deneme tenant’ları"
          icon={Calendar}
          tone="info"
          testId="tenant-summary-trial"
        />
        <TenantSummaryCard
          title="İptal sırada"
          value={computedSummary?.canceling_count || 0}
          subtitle="Retention için geri kazanım fırsatı"
          icon={CreditCard}
          tone="success"
          testId="tenant-summary-canceling"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Tenant List */}
        <div className="lg:col-span-4 overflow-hidden rounded-[1.5rem] border bg-card shadow-sm">
          <div className="space-y-3 border-b bg-muted/20 p-3">
            <div className="flex items-center justify-between gap-3">
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.18em] text-muted-foreground">Tenant dizini</p>
                <p className="text-sm text-muted-foreground">Önce riskli tenant’lar gösterilir.</p>
              </div>
              <Button variant="outline" size="sm" onClick={loadTenantDirectory} data-testid="tenant-list-refresh-button">
                <RefreshCw className="mr-1.5 h-3.5 w-3.5" /> Yenile
              </Button>
            </div>

            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Tenant ara..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-9 h-9" data-testid="tenant-search-input" />
            </div>

            <div className="flex flex-wrap gap-2" data-testid="tenant-filter-bar">
              {FILTER_OPTIONS.map((option) => (
                <TenantFilterButton
                  key={option.key}
                  option={option}
                  count={filterCounts[option.key] || 0}
                  active={statusFilter === option.key}
                  onClick={() => setStatusFilter(option.key)}
                />
              ))}
            </div>
          </div>

          <div className="max-h-[520px] overflow-y-auto">
            {loadingTenants ? (
              <div className="flex items-center justify-center py-12 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin mr-2" /><span className="text-sm">Yükleniyor...</span>
              </div>
            ) : filteredTenants.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center" data-testid="no-tenants">
                <Building2 className="h-8 w-8 text-muted-foreground/50 mb-2" />
                <p className="text-sm text-muted-foreground">{searchQuery ? "Aramayla eşleşen tenant bulunamadı." : "Henüz tenant yok."}</p>
              </div>
            ) : filteredTenants.map((t) => (
              <TenantListItem key={t.id} tenant={t} selected={selectedTenant?.id === t.id} onSelect={loadFeatures} />
            ))}
          </div>
          <div className="border-t bg-muted/20 px-3 py-2 text-xs text-muted-foreground" data-testid="tenant-list-count">
            {filteredTenants.length} sonuç · toplam {tenants.length} tenant
          </div>
        </div>

        {/* Right: Plan + Add-on Management */}
        <div className="lg:col-span-8 border rounded-lg bg-card overflow-hidden">
          {!selectedTenant ? (
            <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center px-4" data-testid="no-tenant-selected">
              <Shield className="h-10 w-10 text-muted-foreground/30 mb-3" />
              <p className="text-sm text-muted-foreground">Özellik yönetimi için sol panelden bir tenant seçin.</p>
            </div>
          ) : (
            <div>
              {/* Header */}
              <div className="px-4 py-3 border-b bg-muted/30 flex items-center justify-between gap-3">
                <div className="min-w-0">
                  <h2 className="text-base font-medium text-foreground truncate" data-testid="selected-tenant-name">{selectedTenant.name}</h2>
                  <p className="text-xs text-muted-foreground">{selectedTenant.slug} — {selectedTenant.id}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button variant="outline" size="sm" onClick={handleReset} disabled={!isDirty || saving} data-testid="reset-btn">
                    <RotateCcw className="h-3.5 w-3.5 mr-1.5" />Geri Al
                  </Button>
                  <Button size="sm" onClick={handleSave} disabled={!isDirty || saving} data-testid="save-features-btn">
                    {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Save className="h-3.5 w-3.5 mr-1.5" />}
                    Kaydet
                  </Button>
                </div>
              </div>

              {/* Subscription Status Panel */}
              <div className="px-4 pt-3 space-y-3">
                <SubscriptionPanel tenantId={selectedTenant.id} />
                <AdminTenantUsageOverview tenantId={selectedTenant.id} />
                <TenantEntitlementOverview
                  planLabel={currentPlanDefinition?.label || currentPlan}
                  source={entitlementSource}
                  limits={currentPlanDefinition?.limits || {}}
                  usageAllowances={currentPlanDefinition?.usage_allowances || currentPlanDefinition?.quotas || {}}
                  activeFeatureCount={effectiveFeatures.length}
                  addOnCount={addOns.length}
                />
              </div>

              {loadingFeatures ? (
                <div className="flex items-center justify-center py-16 text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin mr-2" /><span className="text-sm">Yükleniyor...</span>
                </div>
              ) : (
                <div className="p-4 space-y-5">
                  {/* Plan Selection */}
                  <div>
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5 block">Plan</label>
                    <Select value={currentPlan} onValueChange={setCurrentPlan}>
                      <SelectTrigger className="w-56 h-9" data-testid="plan-select">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        {availablePlans.map((p) => (
                          <SelectItem key={p} value={p}>
                            {(planCatalog.find((item) => item.key === p || item.name === p)?.label) || (p.charAt(0).toUpperCase() + p.slice(1))} ({(planMatrix[p] || []).length} modül)
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-xs text-muted-foreground mt-1">
                      Plan ile gelen: {(planMatrix[currentPlan] || []).length} modül
                    </p>
                  </div>

                  <PlanChangeImpactCard
                    currentPlanLabel={initialPlanDefinition?.label || initialPlan}
                    nextPlanLabel={currentPlanDefinition?.label || currentPlan}
                    impactItems={planImpactItems}
                  />

                  {/* Add-on Modules */}
                  <div>
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 block">
                      Modüller ({effectiveFeatures.length} aktif)
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {FEATURE_CATALOG.map((f) => {
                        const fromPlan = planFeatures.has(f.key);
                        const fromAddOn = addOns.includes(f.key);
                        const isActive = fromPlan || fromAddOn;

                        return (
                          <FeatureCheckboxRow
                            key={f.key}
                            feature={f}
                            checked={isActive}
                            isFromPlan={fromPlan}
                            onChange={(checked) => {
                              if (fromPlan && !checked) return; // Can't uncheck plan feature
                              handleToggleAddOn(f.key, checked);
                            }}
                            disabled={saving || (fromPlan && isActive)}
                          />
                        );
                      })}
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      <AlertDialog open={planConfirmOpen} onOpenChange={setPlanConfirmOpen}>
        <AlertDialogContent data-testid="plan-change-confirm-dialog">
          <AlertDialogHeader>
            <AlertDialogTitle>Plan değişikliğini onayla</AlertDialogTitle>
            <AlertDialogDescription>
              {selectedTenant?.name} tenant’ı için plan değişikliği anında entitlement çıktısını günceller. Kaydetmeden önce limit farklarını gözden geçirin.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <div className="space-y-3 rounded-xl border bg-muted/20 p-3 text-sm" data-testid="plan-change-confirm-summary">
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Geçiş</span>
              <span className="font-medium text-foreground">{initialPlanDefinition?.label || initialPlan} → {currentPlanDefinition?.label || currentPlan}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Toplam modül</span>
              <span className="font-medium text-foreground">{effectiveFeatures.length}</span>
            </div>
            <div className="flex items-center justify-between gap-3">
              <span className="text-muted-foreground">Add-on sayısı</span>
              <span className="font-medium text-foreground">{addOns.length}</span>
            </div>
          </div>
          <AlertDialogFooter>
            <AlertDialogCancel disabled={saving} data-testid="plan-change-confirm-cancel">Vazgeç</AlertDialogCancel>
            <AlertDialogAction
              disabled={saving}
              onClick={(event) => {
                event.preventDefault();
                performSave();
              }}
              data-testid="plan-change-confirm-accept"
            >
              {saving ? "Kaydediliyor..." : "Değişikliği uygula"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
