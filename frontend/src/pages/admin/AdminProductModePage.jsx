import React, { useEffect, useState, useCallback } from "react";
import { api, getUser } from "../../lib/api";
import { useProductMode } from "../../contexts/ProductModeContext";
import { getActiveTenantId } from "../../lib/tenantContext";
import {
  Settings, ChevronRight, Check, AlertTriangle, Shield, Zap,
  Building2, Eye, EyeOff, ArrowUpRight, ArrowDownRight,
} from "lucide-react";

const MODE_META = {
  lite: {
    label: "Lite", tagline: "Küçük Acenta",
    description: "Rezervasyon ve tahsilatı tek panelde yönetin.",
    color: "bg-emerald-500", bgLight: "bg-emerald-50 dark:bg-emerald-950/30",
    borderColor: "border-emerald-200 dark:border-emerald-800", icon: Zap,
  },
  pro: {
    label: "Pro", tagline: "Büyüyen Acenta",
    description: "Alt acenta ve finans kontrolünü netleştirin.",
    color: "bg-blue-500", bgLight: "bg-blue-50 dark:bg-blue-950/30",
    borderColor: "border-blue-200 dark:border-blue-800", icon: Building2,
  },
  enterprise: {
    label: "Enterprise", tagline: "DMC / Büyük Operatör",
    description: "Finansal risk ve operasyonel kaosu bitirin.",
    color: "bg-purple-500", bgLight: "bg-purple-50 dark:bg-purple-950/30",
    borderColor: "border-purple-200 dark:border-purple-800", icon: Shield,
  },
};

const MODES_LIST = ["lite", "pro", "enterprise"];

export default function AdminProductModePage() {
  const { refresh: refreshMode } = useProductMode();
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [tenantMode, setTenantMode] = useState("enterprise");
  const [preview, setPreview] = useState(null);
  const [confirmOpen, setConfirmOpen] = useState(false);
  const [pendingMode, setPendingMode] = useState(null);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const tenantId = getActiveTenantId() || getUser()?.organization_id;

  const fetchCurrentMode = useCallback(async () => {
    try {
      const res = await api.get("/system/product-mode");
      setTenantMode(res.data.product_mode || "enterprise");
    } catch { setTenantMode("enterprise"); }
    setLoading(false);
  }, []);

  useEffect(() => { fetchCurrentMode(); }, [fetchCurrentMode]);

  const loadPreview = useCallback(async (targetMode) => {
    if (!tenantId) return;
    try {
      const res = await api.get(`/admin/tenants/${tenantId}/product-mode-preview?target_mode=${targetMode}`);
      setPreview(res.data);
    } catch { setPreview(null); }
  }, [tenantId]);

  const handleModeSelect = (mode) => {
    if (mode === tenantMode) return;
    setPendingMode(mode);
    loadPreview(mode);
    setConfirmOpen(true);
    setError(null);
    setSuccess(null);
  };

  const confirmModeChange = async () => {
    if (!pendingMode || !tenantId) return;
    setSaving(true);
    setError(null);
    try {
      await api.patch(`/admin/tenants/${tenantId}/product-mode`, { product_mode: pendingMode });
      setTenantMode(pendingMode);
      setSuccess(`Mod "${MODE_META[pendingMode]?.label}" olarak değiştirildi.`);
      refreshMode();
      setConfirmOpen(false);
      setPendingMode(null);
      setPreview(null);
    } catch (err) {
      setError(err.response?.data?.error?.message || "Mod değiştirilirken hata oluştu.");
    }
    setSaving(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin h-8 w-8 border-2 border-primary border-t-transparent rounded-full" />
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
          <Settings className="h-6 w-6 text-muted-foreground" />
          Ürün Modu Ayarları
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Aynı motor — farklı kontrol seviyeleri. Mod değişikliği yalnızca UI görünürlüğünü etkiler.
        </p>
      </div>

      {/* Current Mode */}
      <div className={`rounded-xl border p-4 ${MODE_META[tenantMode]?.bgLight} ${MODE_META[tenantMode]?.borderColor}`}>
        <div className="flex items-center gap-3">
          <div className={`h-10 w-10 rounded-lg ${MODE_META[tenantMode]?.color} flex items-center justify-center`}>
            {React.createElement(MODE_META[tenantMode]?.icon || Settings, { className: "h-5 w-5 text-white" })}
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-lg font-semibold">{MODE_META[tenantMode]?.label} Mod</span>
              <span className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium bg-primary/10 text-primary">Aktif</span>
            </div>
            <p className="text-sm text-muted-foreground">{MODE_META[tenantMode]?.description}</p>
          </div>
        </div>
      </div>

      {success && (
        <div className="rounded-lg border border-emerald-200 dark:border-emerald-800 bg-emerald-50 dark:bg-emerald-950/30 p-3 flex items-center gap-2 text-sm text-emerald-700 dark:text-emerald-300">
          <Check className="h-4 w-4 shrink-0" />{success}
        </div>
      )}
      {error && (
        <div className="rounded-lg border border-destructive/30 bg-destructive/5 p-3 flex items-center gap-2 text-sm text-destructive">
          <AlertTriangle className="h-4 w-4 shrink-0" />{error}
        </div>
      )}

      {/* Mode Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {MODES_LIST.map((mk) => {
          const meta = MODE_META[mk];
          const isCurrent = mk === tenantMode;
          const Icon = meta.icon;
          return (
            <button key={mk} onClick={() => handleModeSelect(mk)} disabled={isCurrent}
              className={`relative rounded-xl border-2 p-5 text-left transition-all hover:shadow-md ${isCurrent ? `${meta.borderColor} ${meta.bgLight} ring-2 ring-primary/20 cursor-default` : "border-border hover:border-muted-foreground/30 bg-card cursor-pointer"}`}>
              {isCurrent && (
                <div className="absolute top-3 right-3">
                  <span className="inline-flex items-center px-2 py-0.5 rounded-full text-2xs font-medium bg-primary text-primary-foreground">
                    <Check className="h-3 w-3 mr-0.5" /> Aktif
                  </span>
                </div>
              )}
              <div className={`h-10 w-10 rounded-lg ${meta.color} flex items-center justify-center mb-3`}>
                <Icon className="h-5 w-5 text-white" />
              </div>
              <h3 className="text-lg font-semibold">{meta.label}</h3>
              <p className="text-xs text-muted-foreground mt-0.5">{meta.tagline}</p>
              <p className="text-sm text-muted-foreground mt-2">{meta.description}</p>
              {!isCurrent && (
                <div className="mt-3 flex items-center gap-1 text-xs font-medium text-primary">
                  Geçiş yap <ChevronRight className="h-3 w-3" />
                </div>
              )}
            </button>
          );
        })}
      </div>

      {/* Confirm Modal */}
      {confirmOpen && pendingMode && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-card rounded-2xl border shadow-2xl max-w-lg w-full mx-4 overflow-hidden">
            <div className="px-6 pt-6 pb-4">
              <h2 className="text-lg font-semibold flex items-center gap-2">
                <Settings className="h-5 w-5 text-muted-foreground" />
                Mod Değişikliği Onayla
              </h2>
              <p className="text-sm text-muted-foreground mt-1">
                <span className="font-medium">{MODE_META[tenantMode]?.label}</span>
                {" → "}
                <span className="font-medium">{MODE_META[pendingMode]?.label}</span>
              </p>
            </div>

            {preview && (
              <div className="px-6 pb-4 space-y-3">
                {preview.is_upgrade ? (
                  <div className="flex items-center gap-2 text-sm text-emerald-600 dark:text-emerald-400">
                    <ArrowUpRight className="h-4 w-4" /> Bu bir yükseltme (upgrade)
                  </div>
                ) : (
                  <div className="flex items-center gap-2 text-sm text-amber-600 dark:text-amber-400">
                    <ArrowDownRight className="h-4 w-4" /> Bu bir düşürme (downgrade)
                  </div>
                )}

                {preview.newly_hidden?.length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
                      <EyeOff className="h-3 w-3" /> Gizlenecek ({preview.newly_hidden.length})
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {preview.newly_hidden.map((item) => (
                        <span key={item} className="inline-flex items-center px-2 py-0.5 rounded text-2xs bg-destructive/10 text-destructive border border-destructive/20">
                          {item.replace(/_/g, " ")}
                        </span>
                      ))}
                    </div>
                  </div>
                )}

                {preview.newly_visible?.length > 0 && (
                  <div>
                    <div className="text-xs font-medium text-muted-foreground mb-1 flex items-center gap-1">
                      <Eye className="h-3 w-3" /> Görünür olacak ({preview.newly_visible.length})
                    </div>
                    <div className="flex flex-wrap gap-1">
                      {preview.newly_visible.map((item) => (
                        <span key={item} className="inline-flex items-center px-2 py-0.5 rounded text-2xs bg-emerald-500/10 text-emerald-600 border border-emerald-500/20">
                          {item.replace(/_/g, " ")}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            <div className="px-6 py-4 border-t bg-muted/30 flex items-center justify-end gap-2">
              <button onClick={() => { setConfirmOpen(false); setPendingMode(null); setPreview(null); }}
                className="px-4 py-2 text-sm rounded-lg border border-border hover:bg-muted transition-colors">
                İptal
              </button>
              <button onClick={confirmModeChange} disabled={saving}
                className="px-4 py-2 text-sm rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 transition-colors disabled:opacity-50 flex items-center gap-1.5">
                {saving && <div className="animate-spin h-3 w-3 border-2 border-primary-foreground border-t-transparent rounded-full" />}
                {saving ? "Uygulanıyor..." : "Onayla ve Uygula"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Info */}
      <div className="rounded-xl border border-border bg-muted/20 p-4 text-sm text-muted-foreground">
        <h3 className="font-semibold text-foreground mb-2">Nasıl Çalışır?</h3>
        <ul className="space-y-1 text-xs">
          <li className="flex items-start gap-1.5"><Check className="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" /><span><strong>Capabilities korunur.</strong> Backend yetenekleri kapanmaz.</span></li>
          <li className="flex items-start gap-1.5"><Check className="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" /><span><strong>Sadece UI yüzeyi değişir.</strong> Sidebar ve component görünürlüğü kontrol edilir.</span></li>
          <li className="flex items-start gap-1.5"><Check className="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" /><span><strong>Audit log tutulur.</strong> Her mod değişikliği kayıt altına alınır.</span></li>
          <li className="flex items-start gap-1.5"><Check className="h-3.5 w-3.5 text-emerald-500 mt-0.5 shrink-0" /><span><strong>Anlık geçiş.</strong> Değişiklik anında uygulanır.</span></li>
        </ul>
      </div>
    </div>
  );
}
