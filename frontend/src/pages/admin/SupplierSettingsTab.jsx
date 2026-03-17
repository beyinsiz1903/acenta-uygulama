import React, { useState, useEffect, useCallback } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import {
  CheckCircle2, XCircle, RefreshCw, Plug, Trash2, TestTube, Eye, EyeOff,
  Globe, Key, User, Lock, Building2, Search, Layers, Zap, Hotel,
  Plane, Map, Bus, Activity
} from "lucide-react";
import { api } from "../../lib/api";

const PRODUCT_ICONS = {
  hotel: Hotel,
  flight: Plane,
  tour: Map,
  transfer: Bus,
  activity: Activity,
};

const SUPPLIER_CONFIG = {
  ratehawk: {
    name: "RateHawk",
    description: "Worldwide hotel inventory with competitive rates",
    type: "Hotel",
    color: "from-orange-600 to-red-600",
    dotColor: "bg-orange-400",
    capabilities: ["hotel"],
    fields: [
      { key: "base_url", label: "API Base URL", icon: Globe, placeholder: "https://api.worldota.net", sensitive: false },
      { key: "key_id", label: "Key ID", icon: Key, placeholder: "Your RateHawk Key ID", sensitive: false },
      { key: "api_key", label: "API Key", icon: Lock, placeholder: "Your RateHawk API Key", sensitive: true },
    ],
  },
  tbo: {
    name: "TBO Holidays",
    description: "Multi-product: hotel, flight & tour inventory",
    type: "Hotel + Flight + Tour",
    color: "from-sky-600 to-blue-700",
    dotColor: "bg-sky-400",
    capabilities: ["hotel", "flight", "tour"],
    fields: [
      { key: "base_url", label: "API Base URL", icon: Globe, placeholder: "https://api.tbotechnology.in", sensitive: false },
      { key: "username", label: "Username", icon: User, placeholder: "TBO API username", sensitive: false },
      { key: "password", label: "Password", icon: Lock, placeholder: "TBO API password", sensitive: true },
      { key: "client_id", label: "Client ID", icon: Building2, placeholder: "Client ID (optional)", sensitive: false },
    ],
  },
  paximum: {
    name: "Paximum",
    description: "Hotel, transfer & activity B2B supplier",
    type: "Hotel + Transfer + Activity",
    color: "from-emerald-600 to-teal-700",
    dotColor: "bg-emerald-400",
    capabilities: ["hotel", "transfer", "activity"],
    fields: [
      { key: "base_url", label: "API Base URL", icon: Globe, placeholder: "https://api.paximum.com", sensitive: false },
      { key: "username", label: "Username", icon: User, placeholder: "Paximum username", sensitive: false },
      { key: "password", label: "Password", icon: Lock, placeholder: "Paximum password", sensitive: true },
      { key: "agency_code", label: "Agency Code", icon: Building2, placeholder: "Agency code", sensitive: false },
    ],
  },
  wtatil: {
    name: "WTatil",
    description: "Tour packages with booking & post-sale management",
    type: "Tour",
    color: "from-blue-600 to-indigo-700",
    dotColor: "bg-blue-400",
    capabilities: ["tour"],
    fields: [
      { key: "base_url", label: "API Base URL", icon: Globe, placeholder: "https://b2b-api.wtatil.com", sensitive: false },
      { key: "application_secret_key", label: "Secret Key", icon: Key, placeholder: "Application secret key", sensitive: true },
      { key: "username", label: "Username", icon: User, placeholder: "API username", sensitive: false },
      { key: "password", label: "Password", icon: Lock, placeholder: "API password", sensitive: true },
      { key: "agency_id", label: "Agency ID", icon: Building2, placeholder: "12345", sensitive: false },
    ],
  },
};

function SupplierCard({ code, config, savedCred, onRefresh }) {
  const [fields, setFields] = useState({});
  const [editing, setEditing] = useState(false);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [toggling, setToggling] = useState(false);
  const [showSensitive, setShowSensitive] = useState({});

  useEffect(() => {
    if (savedCred) {
      const init = {};
      config.fields.forEach(f => { init[f.key] = savedCred[f.key] || ""; });
      setFields(init);
    }
  }, [savedCred, config.fields]);

  const save = async () => {
    setSaving(true);
    try {
      await api.post("/supplier-credentials/save", { supplier: code, fields });
      setEditing(false);
      onRefresh();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const test = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await api.post(`/supplier-credentials/test/${code}`);
      setTestResult(r.data);
      onRefresh();
    } catch (e) { setTestResult({ verdict: "FAIL", error: e.message }); }
    setTesting(false);
  };

  const del = async () => {
    setDeleting(true);
    try {
      await api.delete(`/supplier-credentials/${code}`);
      onRefresh();
      setFields({});
    } catch (e) { console.error(e); }
    setDeleting(false);
  };

  const toggle = async (enabled) => {
    setToggling(true);
    try {
      const r = await api.put(`/supplier-credentials/toggle/${code}`, { enabled });
      if (r.data?.error) {
        setTestResult({ verdict: "FAIL", error: r.data.error });
      } else {
        onRefresh();
      }
    } catch (e) { console.error(e); }
    setToggling(false);
  };

  const status = savedCred?.status;

  const statusConfig = {
    connected: { label: "Connected", cls: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" },
    draft: { label: "Draft", cls: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
    saved: { label: "Saved", cls: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
    auth_failed: { label: "Auth Failed", cls: "bg-red-500/20 text-red-300 border-red-500/30" },
    disabled: { label: "Disabled", cls: "bg-zinc-600/30 text-zinc-400 border-zinc-600/30" },
  };
  const sc = statusConfig[status] || { label: "Not Connected", cls: "bg-zinc-700/30 text-zinc-400 border-zinc-600/30" };

  return (
    <Card data-testid={`supplier-card-${code}`} className="bg-zinc-900/80 border-zinc-800 hover:border-zinc-700 transition-colors">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-3">
            <div className={`w-10 h-10 rounded-lg bg-gradient-to-br ${config.color} flex items-center justify-center`}>
              <Plug className="w-5 h-5 text-white" />
            </div>
            <div>
              <CardTitle className="text-sm font-semibold text-zinc-100">{config.name}</CardTitle>
              <p className="text-[11px] text-zinc-500 mt-0.5">{config.description}</p>
            </div>
          </div>
          <Badge data-testid={`supplier-status-${code}`} variant="outline" className={`text-[10px] ${sc.cls}`}>{sc.label}</Badge>
        </div>
        <div className="flex gap-1.5 mt-2">
          {config.capabilities.map(cap => {
            const Icon = PRODUCT_ICONS[cap] || Activity;
            return (
              <Badge key={cap} variant="outline" className="text-[9px] gap-1 px-1.5 py-0.5 border-zinc-700 text-zinc-400">
                <Icon className="w-2.5 h-2.5" />{cap}
              </Badge>
            );
          })}
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-xs pt-0">
        {(editing || !savedCred) ? (
          <div className="space-y-2">
            {config.fields.map(f => (
              <div key={f.key} className="flex items-center gap-2">
                <f.icon className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                <label className="text-zinc-400 w-24 shrink-0 text-[11px]">{f.label}</label>
                <div className="flex-1 relative">
                  <Input
                    data-testid={`input-${code}-${f.key}`}
                    type={f.sensitive && !showSensitive[f.key] ? "password" : "text"}
                    value={fields[f.key] || ""}
                    onChange={e => setFields(p => ({ ...p, [f.key]: e.target.value }))}
                    placeholder={f.placeholder}
                    className="h-7 text-xs bg-zinc-800/80 border-zinc-700"
                  />
                  {f.sensitive && (
                    <button className="absolute right-2 top-1/2 -translate-y-1/2 text-zinc-500 hover:text-zinc-300" onClick={() => setShowSensitive(p => ({ ...p, [f.key]: !p[f.key] }))}>
                      {showSensitive[f.key] ? <EyeOff className="w-3 h-3" /> : <Eye className="w-3 h-3" />}
                    </button>
                  )}
                </div>
              </div>
            ))}
            <div className="flex gap-2 pt-1">
              <Button data-testid={`save-${code}`} size="sm" className="text-xs h-7" disabled={saving} onClick={save}>
                {saving ? "Saving..." : "Save Credentials"}
              </Button>
              {savedCred && <Button size="sm" variant="outline" className="text-xs h-7" onClick={() => setEditing(false)}>Cancel</Button>}
            </div>
          </div>
        ) : (
          <div className="space-y-1.5">
            {config.fields.map(f => (
              <div key={f.key} className="flex items-center gap-2">
                <f.icon className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                <span className="text-zinc-500 w-24 shrink-0 text-[11px]">{f.label}</span>
                <span className="text-zinc-300 font-mono text-[11px]">{savedCred[f.key] || "---"}</span>
              </div>
            ))}
            {savedCred.connected_at && <p className="text-zinc-600 text-[10px] mt-1">Connected: {new Date(savedCred.connected_at).toLocaleString("tr-TR")}</p>}
          </div>
        )}

        {savedCred && !editing && (
          <div className="flex flex-wrap gap-2 pt-1 border-t border-zinc-800">
            <Button data-testid={`test-${code}`} size="sm" variant="outline" className="text-xs h-7 mt-2" disabled={testing} onClick={test}>
              <TestTube className="w-3 h-3 mr-1" />{testing ? "Testing..." : "Test Connection"}
            </Button>
            <Button data-testid={`edit-${code}`} size="sm" variant="outline" className="text-xs h-7 mt-2" onClick={() => setEditing(true)}>
              <Plug className="w-3 h-3 mr-1" />Edit
            </Button>
            {status === "connected" && (
              <Button data-testid={`disable-${code}`} size="sm" variant="outline" className="text-xs h-7 mt-2 text-amber-400 hover:text-amber-300 border-amber-900/30" disabled={toggling} onClick={() => toggle(false)}>
                <XCircle className="w-3 h-3 mr-1" />{toggling ? "..." : "Disable"}
              </Button>
            )}
            {status === "disabled" && (
              <Button data-testid={`enable-${code}`} size="sm" variant="outline" className="text-xs h-7 mt-2 text-emerald-400 hover:text-emerald-300 border-emerald-900/30" disabled={toggling} onClick={() => toggle(true)}>
                <CheckCircle2 className="w-3 h-3 mr-1" />{toggling ? "..." : "Enable"}
              </Button>
            )}
            <Button data-testid={`delete-${code}`} size="sm" variant="outline" className="text-xs h-7 mt-2 text-red-400 hover:text-red-300 border-red-900/30" disabled={deleting} onClick={del}>
              <Trash2 className="w-3 h-3 mr-1" />{deleting ? "..." : "Remove"}
            </Button>
          </div>
        )}

        {testResult && (
          <div data-testid={`test-result-${code}`} className={`p-3 rounded-lg border ${testResult.verdict === "PASS" ? "bg-emerald-950/40 border-emerald-800/50" : "bg-red-950/40 border-red-800/50"}`}>
            <div className="flex items-center gap-2 mb-1">
              {testResult.verdict === "PASS" ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
              <span className="font-mono font-bold text-[11px]">{testResult.verdict}</span>
              {testResult.latency_ms && <span className="text-zinc-500 ml-auto text-[10px]">{testResult.latency_ms}ms</span>}
            </div>
            {testResult.message && <p className="text-zinc-400 text-[11px]">{testResult.message}</p>}
            {testResult.error && <p className="text-red-400 text-[11px]">{testResult.error}</p>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function CapabilityMatrix({ capabilities }) {
  if (!capabilities) return null;

  const productTypes = ["hotel", "flight", "tour", "transfer", "activity"];

  return (
    <Card data-testid="capability-matrix" className="bg-zinc-900/80 border-zinc-800">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <Layers className="w-4 h-4 text-zinc-400" />
          Supplier Aggregator — Capability Matrix
        </CardTitle>
        <p className="text-[11px] text-zinc-500">Search across all connected suppliers simultaneously for price comparison and inventory merge</p>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="border-b border-zinc-800">
                <th className="text-left py-2 text-zinc-500 font-medium">Supplier</th>
                {productTypes.map(pt => {
                  const Icon = PRODUCT_ICONS[pt] || Activity;
                  return <th key={pt} className="text-center py-2 text-zinc-500 font-medium"><div className="flex items-center justify-center gap-1"><Icon className="w-3 h-3" />{pt}</div></th>;
                })}
                <th className="text-center py-2 text-zinc-500 font-medium">Status</th>
              </tr>
            </thead>
            <tbody>
              {(capabilities.suppliers || []).map(s => (
                <tr key={s.supplier} className="border-b border-zinc-800/50">
                  <td className="py-2 font-medium text-zinc-300">{SUPPLIER_CONFIG[s.supplier]?.name || s.supplier}</td>
                  {productTypes.map(pt => (
                    <td key={pt} className="text-center py-2">
                      {s.capabilities.includes(pt) ? (
                        <span className={`inline-block w-5 h-5 rounded-full ${s.connected ? "bg-emerald-500/20" : "bg-zinc-700/40"} flex items-center justify-center mx-auto`}>
                          <CheckCircle2 className={`w-3 h-3 ${s.connected ? "text-emerald-400" : "text-zinc-600"}`} />
                        </span>
                      ) : (
                        <span className="text-zinc-700">—</span>
                      )}
                    </td>
                  ))}
                  <td className="text-center py-2">
                    <Badge variant="outline" className={`text-[9px] ${s.connected ? "text-emerald-400 border-emerald-800" : "text-zinc-500 border-zinc-700"}`}>
                      {s.connected ? "Active" : "Inactive"}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Product coverage summary */}
        <div className="mt-4 flex flex-wrap gap-2">
          {Object.entries(capabilities.product_coverage || {}).map(([pt, info]) => {
            const Icon = PRODUCT_ICONS[pt] || Activity;
            return (
              <div key={pt} className="flex items-center gap-2 bg-zinc-800/50 rounded-lg px-3 py-1.5">
                <Icon className="w-3.5 h-3.5 text-zinc-400" />
                <span className="text-zinc-400 capitalize">{pt}</span>
                <span className="text-emerald-400 font-mono">{info.connected}</span>
                <span className="text-zinc-600">/</span>
                <span className="text-zinc-500 font-mono">{info.total}</span>
              </div>
            );
          })}
        </div>
      </CardContent>
    </Card>
  );
}

export default function SupplierSettingsTab() {
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(false);
  const [capabilities, setCapabilities] = useState(null);

  const fetchCreds = useCallback(async () => {
    setLoading(true);
    try {
      const [credsRes, capsRes] = await Promise.all([
        api.get("/supplier-credentials/my"),
        api.get("/supplier-aggregator/capabilities").catch(() => ({ data: null })),
      ]);
      setCredentials(credsRes.data.credentials || []);
      if (capsRes.data) setCapabilities(capsRes.data);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchCreds(); }, [fetchCreds]);

  const getCredForSupplier = (code) => credentials.find(c => c.supplier === code);
  const connectedCount = credentials.filter(c => c.status === "connected").length;
  const savedCount = credentials.filter(c => c.status === "saved").length;
  const totalSuppliers = Object.keys(SUPPLIER_CONFIG).length;

  return (
    <div data-testid="supplier-settings-tab" className="space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-zinc-200 flex items-center gap-2">
            <Zap className="w-4 h-4 text-amber-400" />
            Supplier Integrations
          </h3>
          <p className="text-xs text-zinc-500 mt-0.5">Her acenta kendi supplier API bilgilerini yonetir. Tum credential'lar AES-256 ile sifrelenir.</p>
        </div>
        <Button data-testid="refresh-creds" size="sm" variant="outline" className="text-xs h-7" onClick={fetchCreds}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {/* Stats bar */}
      <div className="flex gap-3 text-xs">
        <div className="bg-zinc-800/50 rounded-lg px-3 py-2 flex items-center gap-2 border border-zinc-800">
          <Plug className="w-3.5 h-3.5 text-zinc-500" />
          <span className="text-zinc-500">Total:</span>
          <span className="text-zinc-200 font-mono font-medium" data-testid="total-suppliers">{totalSuppliers}</span>
        </div>
        <div className="bg-zinc-800/50 rounded-lg px-3 py-2 flex items-center gap-2 border border-zinc-800">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          <span className="text-zinc-500">Connected:</span>
          <span className="text-emerald-400 font-mono font-medium" data-testid="connected-count">{connectedCount}</span>
        </div>
        <div className="bg-zinc-800/50 rounded-lg px-3 py-2 flex items-center gap-2 border border-zinc-800">
          <Search className="w-3.5 h-3.5 text-amber-500" />
          <span className="text-zinc-500">Saved:</span>
          <span className="text-amber-400 font-mono font-medium">{savedCount}</span>
        </div>
      </div>

      {/* Aggregator Capability Matrix */}
      <CapabilityMatrix capabilities={capabilities} />

      {/* Supplier Cards */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {Object.entries(SUPPLIER_CONFIG).map(([code, config]) => (
          <SupplierCard key={code} code={code} config={config} savedCred={getCredForSupplier(code)} onRefresh={fetchCreds} />
        ))}
      </div>

      {/* Info box */}
      <Card className="bg-zinc-800/30 border-zinc-700/50">
        <CardContent className="pt-4 text-xs text-zinc-500 space-y-1">
          <p><strong className="text-zinc-400">Aggregator:</strong> Arama istekleri tum bagli supplier'lara paralel gonderilir. Fiyat karsilastirma ve envanter birlestirme otomatik yapilir.</p>
          <p><strong className="text-zinc-400">Guvenlik:</strong> Tum credential'lar AES-256 ile sifrelenerek saklanir. Her acenta sadece kendi bilgilerine erisir.</p>
          <p><strong className="text-zinc-400">Fallback:</strong> Bir supplier hata verirse diger supplier'lardan sonuclar gosterilir. Sistem dayanikliligi arttirilir.</p>
        </CardContent>
      </Card>
    </div>
  );
}
