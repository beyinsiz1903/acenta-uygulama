import React, { useState, useEffect, useCallback, useMemo } from "react";
import { Search, Save, RotateCcw, Building2, Shield, Loader2, Copy, Check } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Checkbox } from "../../components/ui/checkbox";
import { Badge } from "../../components/ui/badge";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { toast } from "sonner";
import { FEATURE_CATALOG } from "../../config/featureCatalog";
import { FEATURE_PLANS } from "../../config/featurePlans";
import { fetchTenantList, fetchTenantFeaturesAdmin, updateTenantFeaturesAdmin } from "../../lib/tenantFeaturesAdmin";
import { apiErrorMessage } from "../../lib/api";

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
          <button
            type="button"
            onClick={handleCopy}
            className="p-1 rounded hover:bg-muted text-muted-foreground"
            title="ID kopyala"
          >
            {copied ? <Check className="h-3 w-3 text-green-500" /> : <Copy className="h-3 w-3" />}
          </button>
        </div>
      </div>
    </div>({ feature, checked, onChange, disabled }) {
  return (
    <label
      className={`flex items-start gap-3 p-3 rounded-lg border transition-colors cursor-pointer ${
        checked ? "border-primary/40 bg-primary/5" : "border-border hover:border-muted-foreground/30"
      } ${disabled ? "opacity-50 pointer-events-none" : ""}`}
      data-testid={`feature-checkbox-${feature.key}`}
    >
      <Checkbox
        checked={checked}
        onCheckedChange={onChange}
        disabled={disabled}
        className="mt-0.5"
      />
      <div className="min-w-0">
        <span className="text-sm font-medium text-foreground">{feature.label}</span>
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
  const [enabledFeatures, setEnabledFeatures] = useState([]);
  const [initialFeatures, setInitialFeatures] = useState([]);
  const [loadingFeatures, setLoadingFeatures] = useState(false);
  const [saving, setSaving] = useState(false);
  const [planValue, setPlanValue] = useState("");

  // Load tenants
  useEffect(() => {
    let active = true;
    setLoadingTenants(true);
    fetchTenantList()
      .then((data) => {
        if (active) setTenants(data.items || []);
      })
      .catch(() => {
        if (active) setTenants([]);
      })
      .finally(() => {
        if (active) setLoadingTenants(false);
      });
    return () => { active = false; };
  }, []);

  // Filter tenants client-side
  const filteredTenants = useMemo(() => {
    if (!searchQuery.trim()) return tenants;
    const q = searchQuery.toLowerCase();
    return tenants.filter(
      (t) => (t.name || "").toLowerCase().includes(q) || (t.slug || "").toLowerCase().includes(q)
    );
  }, [tenants, searchQuery]);

  // Load features when tenant selected
  const loadFeatures = useCallback(async (tenant) => {
    setSelectedTenant(tenant);
    setLoadingFeatures(true);
    setPlanValue("");
    try {
      const data = await fetchTenantFeaturesAdmin(tenant.id);
      const feats = data.features || [];
      setEnabledFeatures([...feats]);
      setInitialFeatures([...feats]);
    } catch {
      setEnabledFeatures([]);
      setInitialFeatures([]);
      toast.error("Feature bilgisi yüklenemedi.");
    } finally {
      setLoadingFeatures(false);
    }
  }, []);

  const isDirty = useMemo(() => {
    if (enabledFeatures.length !== initialFeatures.length) return true;
    const sorted1 = [...enabledFeatures].sort();
    const sorted2 = [...initialFeatures].sort();
    return sorted1.some((v, i) => v !== sorted2[i]);
  }, [enabledFeatures, initialFeatures]);

  const handleToggleFeature = (key, checked) => {
    setEnabledFeatures((prev) =>
      checked ? [...prev, key] : prev.filter((k) => k !== key)
    );
  };

  const handlePlanChange = (planKey) => {
    setPlanValue(planKey);
    const plan = FEATURE_PLANS[planKey];
    if (plan) {
      setEnabledFeatures([...plan.features]);
    }
  };

  const handleReset = () => {
    setEnabledFeatures([...initialFeatures]);
    setPlanValue("");
  };

  const handleSave = async () => {
    if (!selectedTenant) return;
    setSaving(true);
    try {
      const data = await updateTenantFeaturesAdmin(selectedTenant.id, enabledFeatures);
      const feats = data.features || [];
      setEnabledFeatures([...feats]);
      setInitialFeatures([...feats]);
      toast.success("Özellikler güncellendi.");
    } catch (err) {
      const msg = err?.raw ? apiErrorMessage(err.raw) : (err?.message || "Kaydetme hatası");
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="space-y-6" data-testid="admin-tenant-features-page">
      <div>
        <h1 className="text-2xl font-semibold text-foreground tracking-tight" data-testid="page-title">
          Tenant Özellikleri
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Seçilen tenant için modülleri aç/kapatabilirsiniz.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left: Tenant List */}
        <div className="lg:col-span-4 border rounded-lg bg-card overflow-hidden">
          <div className="p-3 border-b bg-muted/30">
            <div className="relative">
              <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Tenant ara..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9 h-9"
                data-testid="tenant-search-input"
              />
            </div>
          </div>

          <div className="max-h-[520px] overflow-y-auto">
            {loadingTenants ? (
              <div className="flex items-center justify-center py-12 text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin mr-2" />
                <span className="text-sm">Yükleniyor...</span>
              </div>
            ) : filteredTenants.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center" data-testid="no-tenants">
                <Building2 className="h-8 w-8 text-muted-foreground/50 mb-2" />
                <p className="text-sm text-muted-foreground">
                  {searchQuery ? "Aramayla eşleşen tenant bulunamadı." : "Henüz tenant yok."}
                </p>
              </div>
            ) : (
              filteredTenants.map((t) => (
                <TenantListItem
                  key={t.id}
                  tenant={t}
                  selected={selectedTenant?.id === t.id}
                  onSelect={loadFeatures}
                />
              ))
            )}
          </div>

          <div className="px-3 py-2 border-t bg-muted/20 text-xs text-muted-foreground">
            {filteredTenants.length} tenant
          </div>
        </div>

        {/* Right: Feature Management */}
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
                  <h2 className="text-base font-medium text-foreground truncate" data-testid="selected-tenant-name">
                    {selectedTenant.name}
                  </h2>
                  <p className="text-xs text-muted-foreground">{selectedTenant.slug} — {selectedTenant.id}</p>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleReset}
                    disabled={!isDirty || saving}
                    data-testid="reset-btn"
                  >
                    <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                    Geri Al
                  </Button>
                  <Button
                    size="sm"
                    onClick={handleSave}
                    disabled={!isDirty || saving}
                    data-testid="save-features-btn"
                  >
                    {saving ? <Loader2 className="h-3.5 w-3.5 animate-spin mr-1.5" /> : <Save className="h-3.5 w-3.5 mr-1.5" />}
                    Kaydet
                  </Button>
                </div>
              </div>

              {loadingFeatures ? (
                <div className="flex items-center justify-center py-16 text-muted-foreground">
                  <Loader2 className="h-5 w-5 animate-spin mr-2" />
                  <span className="text-sm">Özellikler yükleniyor...</span>
                </div>
              ) : (
                <div className="p-4 space-y-5">
                  {/* Plan Templates */}
                  <div>
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-1.5 block">
                      Plan Şablonu
                    </label>
                    <Select value={planValue} onValueChange={handlePlanChange}>
                      <SelectTrigger className="w-48 h-9" data-testid="plan-select">
                        <SelectValue placeholder="Şablon seç..." />
                      </SelectTrigger>
                      <SelectContent>
                        {Object.entries(FEATURE_PLANS).map(([key, plan]) => (
                          <SelectItem key={key} value={key}>
                            {plan.label} ({plan.features.length} modül)
                          </SelectItem>
                        ))}
                      </SelectContent>
                    </Select>
                  </div>

                  {/* Feature Checkboxes */}
                  <div>
                    <label className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2 block">
                      Modüller ({enabledFeatures.length}/{FEATURE_CATALOG.length})
                    </label>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                      {FEATURE_CATALOG.map((f) => (
                        <FeatureCheckboxRow
                          key={f.key}
                          feature={f}
                          checked={enabledFeatures.includes(f.key)}
                          onChange={(checked) => handleToggleFeature(f.key, checked)}
                          disabled={saving}
                        />
                      ))}
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
