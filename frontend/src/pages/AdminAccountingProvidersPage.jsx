import React, { useEffect, useState, useCallback } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Badge } from "../components/ui/badge";
import {
  Settings, CheckCircle, XCircle, RefreshCw, Trash2,
  Shield, Activity, Server, Key, TestTube, Link2,
  ChevronRight, AlertTriangle, Clock, Zap, Lock,
  RotateCcw, Eye, EyeOff
} from "lucide-react";
import { cn } from "../lib/utils";
import { toast } from "sonner";

const STATUS_MAP = {
  active: { label: "Aktif", color: "bg-emerald-100 text-emerald-800 border-emerald-200", icon: CheckCircle },
  configured: { label: "Yapilandirildi", color: "bg-blue-100 text-blue-800 border-blue-200", icon: Settings },
  error: { label: "Hata", color: "bg-red-100 text-red-800 border-red-200", icon: XCircle },
};

function StatusBadge({ status }) {
  const s = STATUS_MAP[status] || { label: status, color: "bg-slate-100 text-slate-600", icon: Settings };
  const Icon = s.icon;
  return (
    <Badge variant="outline" className={cn("gap-1 font-medium text-xs", s.color)} data-testid={`status-badge-${status}`}>
      <Icon className="h-3 w-3" /> {s.label}
    </Badge>
  );
}

function CapabilityDot({ supported, label }) {
  return (
    <div className="flex items-center gap-1.5 text-xs" data-testid={`cap-${label}`}>
      <div className={cn("h-2 w-2 rounded-full", supported ? "bg-emerald-500" : "bg-slate-300")} />
      <span className={supported ? "text-slate-700" : "text-slate-400"}>{label}</span>
    </div>
  );
}

// ── Provider Card ────────────────────────────────────────────────────

function ProviderCard({ provider, isSelected, onSelect }) {
  const caps = provider.capabilities || {};
  return (
    <div
      className={cn(
        "rounded-xl border p-4 cursor-pointer transition-all duration-200",
        isSelected
          ? "border-blue-500 bg-blue-50/50 ring-1 ring-blue-200"
          : provider.is_active
            ? "border-slate-200 hover:border-slate-300 bg-white hover:shadow-sm"
            : "border-slate-100 bg-slate-50/50 opacity-70"
      )}
      onClick={() => provider.is_active && onSelect(provider)}
      data-testid={`provider-card-${provider.code}`}
    >
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="flex items-center gap-2">
            <h3 className="font-semibold text-slate-900 text-sm">{provider.name}</h3>
            {provider.is_active ? (
              <Badge variant="outline" className="text-[10px] bg-emerald-50 text-emerald-700 border-emerald-200">Aktif</Badge>
            ) : (
              <Badge variant="outline" className="text-[10px] bg-slate-100 text-slate-500 border-slate-200">Yakin Zamanda</Badge>
            )}
          </div>
          <p className="text-xs text-slate-500 mt-1">{provider.description}</p>
        </div>
        {isSelected && <CheckCircle className="h-5 w-5 text-blue-500 flex-shrink-0" />}
      </div>

      <div className="grid grid-cols-3 gap-1.5 mt-3">
        <CapabilityDot supported={caps.customer_management} label="Cari" />
        <CapabilityDot supported={caps.invoice_creation} label="Fatura" />
        <CapabilityDot supported={caps.invoice_cancel} label="Iptal" />
        <CapabilityDot supported={caps.status_polling} label="Durum" />
        <CapabilityDot supported={caps.pdf_download} label="PDF" />
        <CapabilityDot supported={caps.webhook_support} label="Webhook" />
      </div>

      {provider.rate_limit_rpm > 0 && (
        <div className="flex items-center gap-1 mt-2 text-[10px] text-slate-400">
          <Zap className="h-3 w-3" /> {provider.rate_limit_rpm} istek/dk
        </div>
      )}
    </div>
  );
}

// ── Credential Form ──────────────────────────────────────────────────

function CredentialForm({ provider, onSave, saving }) {
  const [fields, setFields] = useState({});
  const [showPasswords, setShowPasswords] = useState({});

  useEffect(() => {
    const init = {};
    (provider.credential_fields || []).forEach(f => { init[f.key] = ""; });
    setFields(init);
    setShowPasswords({});
  }, [provider.code]);

  const handleChange = (key, val) => setFields(prev => ({ ...prev, [key]: val }));
  const toggleShow = (key) => setShowPasswords(prev => ({ ...prev, [key]: !prev[key] }));

  return (
    <div className="space-y-3" data-testid="credential-form">
      {(provider.credential_fields || []).map(f => (
        <div key={f.key}>
          <label className="text-xs font-medium text-slate-600 mb-1 block">
            {f.label} {f.required && <span className="text-red-400">*</span>}
          </label>
          <div className="relative">
            <input
              type={f.type === "password" && !showPasswords[f.key] ? "password" : "text"}
              className="w-full rounded-lg border border-slate-200 px-3 py-2 text-sm focus:ring-2 focus:ring-blue-200 focus:border-blue-400 outline-none"
              placeholder={f.placeholder || ""}
              value={fields[f.key] || ""}
              onChange={e => handleChange(f.key, e.target.value)}
              data-testid={`cred-field-${f.key}`}
            />
            {f.type === "password" && (
              <button
                type="button"
                className="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                onClick={() => toggleShow(f.key)}
              >
                {showPasswords[f.key] ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            )}
          </div>
        </div>
      ))}
      <Button
        onClick={() => onSave(fields)}
        disabled={saving || !(provider.credential_fields || []).filter(f => f.required).every(f => fields[f.key])}
        className="w-full mt-2"
        data-testid="save-credentials-btn"
      >
        {saving ? <RefreshCw className="h-4 w-4 animate-spin mr-2" /> : <Key className="h-4 w-4 mr-2" />}
        Kaydet
      </Button>
    </div>
  );
}

// ── Health Card ───────────────────────────────────────────────────────

function HealthCard({ config }) {
  if (!config) return null;
  const health = config.health || {};
  const total = health.total_requests || 0;
  const failures = health.total_failures || 0;
  const successRate = total > 0 ? ((total - failures) / total * 100).toFixed(1) : "—";

  return (
    <div className="rounded-xl border border-slate-200 p-4 bg-white" data-testid="health-card">
      <h4 className="text-sm font-semibold text-slate-800 mb-3 flex items-center gap-2">
        <Activity className="h-4 w-4 text-blue-500" /> Saglik Durumu
      </h4>
      <div className="grid grid-cols-2 gap-3">
        <div className="text-center p-2 bg-slate-50 rounded-lg">
          <div className="text-lg font-bold text-slate-900">{total}</div>
          <div className="text-[10px] text-slate-500">Toplam Istek</div>
        </div>
        <div className="text-center p-2 bg-slate-50 rounded-lg">
          <div className={cn("text-lg font-bold", failures > 0 ? "text-red-600" : "text-emerald-600")}>{failures}</div>
          <div className="text-[10px] text-slate-500">Basarisiz</div>
        </div>
        <div className="text-center p-2 bg-slate-50 rounded-lg">
          <div className="text-lg font-bold text-blue-600">{successRate}%</div>
          <div className="text-[10px] text-slate-500">Basari Orani</div>
        </div>
        <div className="text-center p-2 bg-slate-50 rounded-lg">
          <div className="text-lg font-bold text-slate-900">
            {config.last_test_result || "—"}
          </div>
          <div className="text-[10px] text-slate-500">Son Test</div>
        </div>
      </div>
      {health.last_error && (
        <div className="mt-3 p-2 bg-red-50 rounded-lg border border-red-100">
          <div className="text-[10px] text-red-600 font-medium">Son Hata</div>
          <div className="text-xs text-red-700 mt-0.5 break-all">{health.last_error}</div>
        </div>
      )}
    </div>
  );
}

// ── Main Page ────────────────────────────────────────────────────────

export default function AdminAccountingProvidersPage() {
  const [providers, setProviders] = useState([]);
  const [selectedProvider, setSelectedProvider] = useState(null);
  const [currentConfig, setCurrentConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [catalogRes, configRes] = await Promise.all([
        api.get("/accounting/providers/catalog"),
        api.get("/accounting/providers/config"),
      ]);
      setProviders(catalogRes.data.providers || []);
      if (configRes.data.configured) {
        setCurrentConfig(configRes.data.provider);
        const match = (catalogRes.data.providers || []).find(p => p.code === configRes.data.provider.provider_code);
        if (match) setSelectedProvider(match);
      }
    } catch (err) {
      toast.error("Veri yuklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadData(); }, [loadData]);

  const handleSave = async (credentials) => {
    if (!selectedProvider) return;
    setSaving(true);
    try {
      await api.post("/accounting/providers/config", {
        provider_code: selectedProvider.code,
        credentials,
      });
      toast.success(`${selectedProvider.name} yapilandirildi`);
      await loadData();
    } catch (err) {
      toast.error(err?.response?.data?.error?.message || "Kaydetme hatasi");
    } finally {
      setSaving(false);
    }
  };

  const handleTest = async () => {
    setTesting(true);
    try {
      const res = await api.post("/accounting/providers/test-connection");
      if (res.data.success) {
        toast.success(`Baglanti basarili (${res.data.status})`);
      } else {
        toast.error(res.data.error_message || "Baglanti basarisiz");
      }
      await loadData();
    } catch (err) {
      toast.error("Test hatasi");
    } finally {
      setTesting(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Provider yapilandirmasi silinecek. Emin misiniz?")) return;
    setDeleting(true);
    try {
      await api.delete("/accounting/providers/config");
      toast.success("Provider kaldirildi");
      setCurrentConfig(null);
      setSelectedProvider(null);
      await loadData();
    } catch (err) {
      toast.error("Silme hatasi");
    } finally {
      setDeleting(false);
    }
  };

  const handleRotate = async (credentials) => {
    setSaving(true);
    try {
      await api.post("/accounting/providers/rotate-credentials", { credentials });
      toast.success("Kimlik bilgileri guncellendi");
      await loadData();
    } catch (err) {
      toast.error("Guncelleme hatasi");
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20" data-testid="loading">
        <RefreshCw className="h-6 w-6 animate-spin text-blue-500" />
      </div>
    );
  }

  return (
    <div className="space-y-6 max-w-6xl" data-testid="accounting-providers-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold text-slate-900" data-testid="page-title">Muhasebe Provider Yonetimi</h1>
          <p className="text-sm text-slate-500 mt-0.5">Muhasebe sistemi entegrasyonu yapilandirma ve izleme</p>
        </div>
        <Button variant="outline" size="sm" onClick={loadData} data-testid="refresh-btn">
          <RefreshCw className="h-4 w-4 mr-1" /> Yenile
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left: Provider Selection */}
        <div className="lg:col-span-2 space-y-4">
          <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
            <Server className="h-4 w-4 text-slate-500" /> Muhasebe Sistemleri
          </h2>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {providers.map(p => (
              <ProviderCard
                key={p.code}
                provider={p}
                isSelected={selectedProvider?.code === p.code}
                onSelect={setSelectedProvider}
              />
            ))}
          </div>

          {/* Current Config Info */}
          {currentConfig && (
            <div className="rounded-xl border border-slate-200 p-4 bg-white" data-testid="current-config">
              <div className="flex items-center justify-between mb-3">
                <h3 className="text-sm font-semibold text-slate-800 flex items-center gap-2">
                  <Link2 className="h-4 w-4 text-blue-500" /> Aktif Yapilandirma
                </h3>
                <StatusBadge status={currentConfig.status} />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs">
                <div>
                  <span className="text-slate-500">Provider</span>
                  <div className="font-medium text-slate-900">{currentConfig.provider_name}</div>
                </div>
                <div>
                  <span className="text-slate-500">Son Test</span>
                  <div className="font-medium text-slate-900">
                    {currentConfig.last_test_at
                      ? new Date(currentConfig.last_test_at).toLocaleString("tr-TR")
                      : "—"}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500">Guncelleme</span>
                  <div className="font-medium text-slate-900">
                    {currentConfig.updated_at
                      ? new Date(currentConfig.updated_at).toLocaleString("tr-TR")
                      : "—"}
                  </div>
                </div>
                <div>
                  <span className="text-slate-500">Guncelleyen</span>
                  <div className="font-medium text-slate-900">{currentConfig.updated_by || "—"}</div>
                </div>
              </div>

              {/* Masked Credentials */}
              {currentConfig.masked_credentials && (
                <div className="mt-3 p-3 bg-slate-50 rounded-lg">
                  <div className="text-[10px] text-slate-500 font-medium mb-1.5 flex items-center gap-1">
                    <Lock className="h-3 w-3" /> Kayitli Kimlik Bilgileri (maskeli)
                  </div>
                  <div className="grid grid-cols-2 gap-2 text-xs">
                    {Object.entries(currentConfig.masked_credentials).map(([k, v]) => (
                      <div key={k}>
                        <span className="text-slate-400">{k}:</span>{" "}
                        <span className="text-slate-700 font-mono">{v}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Action buttons */}
              <div className="flex gap-2 mt-3">
                <Button
                  variant="outline" size="sm"
                  onClick={handleTest}
                  disabled={testing}
                  data-testid="test-connection-btn"
                >
                  {testing ? <RefreshCw className="h-3 w-3 animate-spin mr-1" /> : <TestTube className="h-3 w-3 mr-1" />}
                  Baglanti Testi
                </Button>
                <Button
                  variant="outline" size="sm"
                  className="text-red-600 hover:bg-red-50 border-red-200"
                  onClick={handleDelete}
                  disabled={deleting}
                  data-testid="delete-config-btn"
                >
                  <Trash2 className="h-3 w-3 mr-1" /> Kaldir
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Right: Config Panel */}
        <div className="space-y-4">
          {selectedProvider ? (
            <>
              <h2 className="text-sm font-semibold text-slate-700 flex items-center gap-2">
                <Key className="h-4 w-4 text-slate-500" />
                {currentConfig?.provider_code === selectedProvider.code
                  ? "Kimlik Bilgilerini Guncelle"
                  : `${selectedProvider.name} Yapilandirma`}
              </h2>
              <div className="rounded-xl border border-slate-200 p-4 bg-white">
                <CredentialForm
                  provider={selectedProvider}
                  onSave={
                    currentConfig?.provider_code === selectedProvider.code
                      ? handleRotate
                      : handleSave
                  }
                  saving={saving}
                />
              </div>
              {/* Health Card */}
              {currentConfig?.provider_code === selectedProvider.code && (
                <HealthCard config={currentConfig} />
              )}
            </>
          ) : (
            <div className="rounded-xl border border-dashed border-slate-300 p-8 text-center">
              <Server className="h-8 w-8 text-slate-300 mx-auto mb-2" />
              <p className="text-sm text-slate-500">Yapilandirmak icin bir provider secin</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
