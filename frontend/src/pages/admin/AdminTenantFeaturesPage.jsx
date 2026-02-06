import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Search, Save, RotateCcw, Building2, Shield, Loader2, Copy, Check, RefreshCw, AlertTriangle, CreditCard, Calendar } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Checkbox } from "../../components/ui/checkbox";
import { Badge } from "../../components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { toast } from "sonner";
import { FEATURE_CATALOG } from "../../config/featureCatalog";
import { api, apiErrorMessage } from "../../lib/api";
import { fetchTenantList } from "../../lib/tenantFeaturesAdmin";

const STATUS_MAP = {
  active: { label: "Active", color: "bg-emerald-500/10 text-emerald-700 border-emerald-500/20" },
  trialing: { label: "Trial", color: "bg-blue-500/10 text-blue-700 border-blue-500/20" },
  past_due: { label: "Payment Issue", color: "bg-amber-500/10 text-amber-700 border-amber-500/20" },
  incomplete: { label: "Payment Issue", color: "bg-amber-500/10 text-amber-700 border-amber-500/20" },
  unpaid: { label: "Payment Issue", color: "bg-amber-500/10 text-amber-700 border-amber-500/20" },
  canceled: { label: "Canceled", color: "bg-muted text-muted-foreground border-border" },
};

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
          <Badge className={`${displayStatus?.color} text-[10px] px-1.5 py-0`} data-testid="sub-status-badge">
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
            <p className="text-[10px] text-muted-foreground">{renewalDays} gün kaldı</p>
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
    </div>
  );
}

function TenantListItem({ tenant, selected, onSelect }) {
  const [copied, setCopied] = useState(false);
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
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          <Badge variant={tenant.status === "active" ? "default" : "secondary"} className="text-[10px] px-1.5 py-0">
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
            <Badge variant="outline" className="text-[9px] px-1 py-0 text-muted-foreground">Plan</Badge>
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
  const [loadingTenants, setLoadingTenants] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedTenant, setSelectedTenant] = useState(null);

  // New: plan + add-ons model
  const [currentPlan, setCurrentPlan] = useState("starter");
  const [addOns, setAddOns] = useState([]);
  const [initialPlan, setInitialPlan] = useState("starter");
  const [initialAddOns, setInitialAddOns] = useState([]);
  const [planMatrix, setPlanMatrix] = useState({});
  const [availablePlans, setAvailablePlans] = useState([]);

  const [loadingFeatures, setLoadingFeatures] = useState(false);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    setLoadingTenants(true);
    fetchTenantList().then((d) => setTenants(d.items || [])).catch(() => setTenants([])).finally(() => setLoadingTenants(false));
  }, []);

  const filteredTenants = useMemo(() => {
    if (!searchQuery.trim()) return tenants;
    const q = searchQuery.toLowerCase();
    return tenants.filter((t) => (t.name || "").toLowerCase().includes(q) || (t.slug || "").toLowerCase().includes(q));
  }, [tenants, searchQuery]);

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
    } catch {
      setCurrentPlan("starter");
      setAddOns([]);
      setInitialPlan("starter");
      setInitialAddOns([]);
      toast.error("Feature bilgisi yüklenemedi.");
    } finally {
      setLoadingFeatures(false);
    }
  }, []);

  const planFeatures = useMemo(() => new Set(planMatrix[currentPlan] || []), [planMatrix, currentPlan]);

  const effectiveFeatures = useMemo(() => {
    const all = new Set([...(planMatrix[currentPlan] || []), ...addOns]);
    return [...all].sort();
  }, [planMatrix, currentPlan, addOns]);

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

  const handleSave = async () => {
    if (!selectedTenant) return;
    setSaving(true);
    try {
      // Save plan
      if (currentPlan !== initialPlan) {
        await api.patch(`/admin/tenants/${selectedTenant.id}/plan`, { plan: currentPlan });
      }
      // Save add-ons
      const res = await api.patch(`/admin/tenants/${selectedTenant.id}/add-ons`, { add_ons: addOns });
      const data = res.data;
      setCurrentPlan(data.plan || currentPlan);
      setAddOns([...(data.add_ons || [])]);
      setInitialPlan(data.plan || currentPlan);
      setInitialAddOns([...(data.add_ons || [])]);
      toast.success("Özellikler güncellendi.");
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="admin-tenant-features-page">
      <div>
        <h1 className="text-2xl font-semibold text-foreground tracking-tight" data-testid="page-title">Tenant Özellikleri</h1>
        <p className="text-sm text-muted-foreground mt-1">Plan ve add-on modülleri ile tenant yeteneklerini yönetin.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Tenant List */}
        <div className="lg:col-span-4 border rounded-lg bg-card overflow-hidden">
          <div className="p-3 border-b bg-muted/30">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input placeholder="Tenant ara..." value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-9 h-9" data-testid="tenant-search-input" />
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
          <div className="px-3 py-2 border-t bg-muted/20 text-xs text-muted-foreground">{filteredTenants.length} tenant</div>
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
                            {p.charAt(0).toUpperCase() + p.slice(1)} ({(planMatrix[p] || []).length} modül)
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                    <p className="text-[11px] text-muted-foreground mt-1">
                      Plan ile gelen: {(planMatrix[currentPlan] || []).length} modül
                    </p>
                  </div>

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
    </div>
  );
}
