import React, { useState, useEffect, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import {
  CheckCircle2, XCircle, RefreshCw, Plug, Trash2, TestTube, Eye, EyeOff,
  Globe, Key, User, Lock, Building2, Shield, Clock, ArrowLeft,
  Hotel, Plane, Map, Bus, Activity, FileText
} from "lucide-react";
import { api } from "../../lib/api";

const SUPPLIER_CONFIG = {
  ratehawk: {
    name: "RateHawk",
    description: "Worldwide hotel inventory with competitive rates",
    color: "from-orange-600 to-red-600",
    fields: [
      { key: "base_url", label: "API Base URL", icon: Globe, placeholder: "https://api.worldota.net", sensitive: false },
      { key: "key_id", label: "Key ID", icon: Key, placeholder: "Your RateHawk Key ID", sensitive: false },
      { key: "api_key", label: "API Key", icon: Lock, placeholder: "Your RateHawk API Key", sensitive: true },
    ],
  },
  tbo: {
    name: "TBO Holidays",
    description: "Multi-product: hotel, flight & tour inventory",
    color: "from-sky-600 to-blue-700",
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
    color: "from-emerald-600 to-teal-700",
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
    color: "from-blue-600 to-indigo-700",
    fields: [
      { key: "base_url", label: "API Base URL", icon: Globe, placeholder: "https://b2b-api.wtatil.com", sensitive: false },
      { key: "application_secret_key", label: "Secret Key", icon: Key, placeholder: "Application secret key", sensitive: true },
      { key: "username", label: "Username", icon: User, placeholder: "API username", sensitive: false },
      { key: "password", label: "Password", icon: Lock, placeholder: "API password", sensitive: true },
      { key: "agency_id", label: "Agency ID", icon: Building2, placeholder: "12345", sensitive: false },
    ],
  },
};

const STATUS_MAP = {
  connected: { label: "Connected", cls: "bg-emerald-500/20 text-emerald-300 border-emerald-500/30" },
  draft: { label: "Draft", cls: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
  saved: { label: "Saved", cls: "bg-amber-500/20 text-amber-300 border-amber-500/30" },
  auth_failed: { label: "Failed", cls: "bg-red-500/20 text-red-300 border-red-500/30" },
  disabled: { label: "Disabled", cls: "bg-zinc-600/30 text-zinc-400 border-zinc-600/30" },
};

function AdminCredentialCard({ code, config, savedCred, orgId, onRefresh }) {
  const [editing, setEditing] = useState(false);
  const [fields, setFields] = useState({});
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
      await api.post(`/supplier-credentials/admin/agency/${orgId}/save`, { supplier: code, fields });
      setEditing(false);
      onRefresh();
    } catch (e) { console.error(e); }
    setSaving(false);
  };

  const test = async () => {
    setTesting(true);
    setTestResult(null);
    try {
      const r = await api.post(`/supplier-credentials/admin/agency/${orgId}/test/${code}`);
      setTestResult(r.data);
      onRefresh();
    } catch (e) { setTestResult({ verdict: "FAIL", error: e.message }); }
    setTesting(false);
  };

  const del = async () => {
    setDeleting(true);
    try {
      await api.delete(`/supplier-credentials/admin/agency/${orgId}/${code}`);
      onRefresh();
      setFields({});
    } catch (e) { console.error(e); }
    setDeleting(false);
  };

  const toggle = async (enabled) => {
    setToggling(true);
    try {
      const r = await api.put(`/supplier-credentials/admin/agency/${orgId}/toggle/${code}`, { enabled });
      if (r.data?.error) {
        setTestResult({ verdict: "FAIL", error: r.data.error });
      } else { onRefresh(); }
    } catch (e) { console.error(e); }
    setToggling(false);
  };

  const status = savedCred?.status;
  const sc = STATUS_MAP[status] || { label: "Not Connected", cls: "bg-zinc-700/30 text-zinc-400 border-zinc-600/30" };

  return (
    <Card data-testid={`admin-supplier-card-${code}`} className="bg-zinc-900/80 border-zinc-800 hover:border-zinc-700 transition-colors">
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
          <Badge data-testid={`admin-status-${code}`} variant="outline" className={`text-[10px] ${sc.cls}`}>{sc.label}</Badge>
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
                    data-testid={`admin-input-${code}-${f.key}`}
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
              <Button data-testid={`admin-save-${code}`} size="sm" className="text-xs h-7" disabled={saving} onClick={save}>
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
            {savedCred.last_tested && <p className="text-zinc-600 text-[10px]">Last Test: {new Date(savedCred.last_tested).toLocaleString("tr-TR")}</p>}
          </div>
        )}

        {savedCred && !editing && (
          <div className="flex flex-wrap gap-2 pt-1 border-t border-zinc-800">
            <Button data-testid={`admin-test-${code}`} size="sm" variant="outline" className="text-xs h-7 mt-2" disabled={testing} onClick={test}>
              <TestTube className="w-3 h-3 mr-1" />{testing ? "Testing..." : "Test"}
            </Button>
            <Button data-testid={`admin-edit-${code}`} size="sm" variant="outline" className="text-xs h-7 mt-2" onClick={() => setEditing(true)}>
              <Plug className="w-3 h-3 mr-1" />Edit
            </Button>
            {status === "connected" && (
              <Button data-testid={`admin-disable-${code}`} size="sm" variant="outline" className="text-xs h-7 mt-2 text-amber-400 border-amber-900/30" disabled={toggling} onClick={() => toggle(false)}>
                <XCircle className="w-3 h-3 mr-1" />{toggling ? "..." : "Disable"}
              </Button>
            )}
            {status === "disabled" && (
              <Button data-testid={`admin-enable-${code}`} size="sm" variant="outline" className="text-xs h-7 mt-2 text-emerald-400 border-emerald-900/30" disabled={toggling} onClick={() => toggle(true)}>
                <CheckCircle2 className="w-3 h-3 mr-1" />{toggling ? "..." : "Enable"}
              </Button>
            )}
            <Button data-testid={`admin-delete-${code}`} size="sm" variant="outline" className="text-xs h-7 mt-2 text-red-400 border-red-900/30" disabled={deleting} onClick={del}>
              <Trash2 className="w-3 h-3 mr-1" />{deleting ? "..." : "Remove"}
            </Button>
          </div>
        )}

        {testResult && (
          <div data-testid={`admin-test-result-${code}`} className={`p-3 rounded-lg border ${testResult.verdict === "PASS" ? "bg-emerald-950/40 border-emerald-800/50" : "bg-red-950/40 border-red-800/50"}`}>
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

function AgencyDetail({ orgId, companyName, onBack }) {
  const queryClient = useQueryClient();

  const { data: credentials = [], isLoading: loading, refetch } = useQuery({
    queryKey: ["supplier-credentials", "agency", orgId],
    queryFn: async () => {
      const r = await api.get(`/supplier-credentials/admin/agency/${orgId}`);
      return r.data.credentials || [];
    },
    enabled: !!orgId,
  });

  const getCredForSupplier = (code) => credentials.find(c => c.supplier === code);

  return (
    <div data-testid="agency-detail-view" className="space-y-5">
      <div className="flex items-center gap-3">
        <Button data-testid="back-to-list" size="sm" variant="outline" className="text-xs h-8" onClick={onBack}>
          <ArrowLeft className="w-3.5 h-3.5 mr-1" />Back
        </Button>
        <div>
          <h3 className="text-sm font-semibold text-zinc-200">{companyName || orgId}</h3>
          <p className="text-[11px] text-zinc-500 font-mono">{orgId}</p>
        </div>
        <Button size="sm" variant="outline" className="text-xs h-7 ml-auto" onClick={() => refetch()}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {Object.entries(SUPPLIER_CONFIG).map(([code, config]) => (
          <AdminCredentialCard key={code} code={code} config={config} savedCred={getCredForSupplier(code)} orgId={orgId} onRefresh={() => refetch()} />
        ))}
      </div>
    </div>
  );
}

function AuditLogTab() {
  const [filter, setFilter] = useState("");

  const { data: logs = [], isLoading: loading, refetch } = useQuery({
    queryKey: ["supplier-credentials", "audit-log", filter],
    queryFn: async () => {
      const params = filter ? `?organization_id=${filter}&limit=100` : "?limit=100";
      const r = await api.get(`/supplier-credentials/admin/audit-log${params}`);
      return r.data.logs || [];
    },
  });

  const ACTION_COLORS = {
    save: "text-blue-400",
    test: "text-amber-400",
    enable: "text-emerald-400",
    disable: "text-zinc-400",
    delete: "text-red-400",
  };

  return (
    <div data-testid="audit-log-tab" className="space-y-4">
      <div className="flex items-center gap-3">
        <Input data-testid="audit-filter-input" placeholder="Filter by Organization ID..." value={filter} onChange={e => setFilter(e.target.value)} className="h-8 text-xs bg-zinc-800/80 border-zinc-700 max-w-xs" />
        <Button size="sm" variant="outline" className="text-xs h-8" onClick={() => refetch()}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </Button>
        <span className="text-[11px] text-zinc-500 ml-auto">{logs.length} kayit</span>
      </div>
      <div className="space-y-1 max-h-[500px] overflow-y-auto">
        {logs.map((log, i) => (
          <div key={i} className="flex items-center gap-3 text-[11px] py-1.5 px-3 bg-zinc-900/50 rounded border border-zinc-800/50">
            <span className="text-zinc-600 w-36 shrink-0">{new Date(log.timestamp).toLocaleString("tr-TR")}</span>
            <Badge variant="outline" className={`text-[9px] w-14 justify-center ${ACTION_COLORS[log.action] || "text-zinc-400"}`}>{log.action}</Badge>
            <span className="text-zinc-300 font-medium w-20 shrink-0">{SUPPLIER_CONFIG[log.supplier]?.name || log.supplier}</span>
            <span className="text-zinc-500 font-mono w-28 shrink-0 truncate">{log.organization_id}</span>
            <span className="text-zinc-500 truncate">{log.actor}</span>
            <span className="text-zinc-600 ml-auto truncate max-w-[200px]">{log.details}</span>
          </div>
        ))}
        {logs.length === 0 && !loading && <p className="text-zinc-500 text-xs text-center py-6">Henuz audit kaydı yok</p>}
      </div>
    </div>
  );
}

export default function AdminSupplierCredentialsPage() {
  const [selectedAgency, setSelectedAgency] = useState(null);

  const { data: agencyData, isLoading: loading, refetch: fetchAgencies } = useQuery({
    queryKey: ["supplier-credentials", "agencies-all"],
    queryFn: async () => {
      const [credsRes, orgsRes] = await Promise.all([
        api.get("/supplier-credentials/admin/agencies"),
        api.get("/admin/agencies").catch(() => ({ data: { agencies: [] } })),
      ]);
      return {
        agencies: credsRes.data.agencies || [],
        allOrgs: orgsRes.data?.agencies || orgsRes.data?.items || [],
      };
    },
  });

  const agencies = agencyData?.agencies || [];
  const allOrgs = agencyData?.allOrgs || [];

  if (selectedAgency) {
    return (
      <div data-testid="admin-supplier-credentials-page" className="p-6 space-y-4">
        <AgencyDetail
          orgId={selectedAgency.organization_id || selectedAgency.org_id}
          companyName={selectedAgency.company_name || selectedAgency.name}
          onBack={() => { setSelectedAgency(null); fetchAgencies(); }}
        />
      </div>
    );
  }

  const totalConnected = agencies.reduce((s, a) => s + (a.connected_count || 0), 0);
  const totalDisabled = agencies.reduce((s, a) => s + (a.disabled_count || 0), 0);

  return (
    <div data-testid="admin-supplier-credentials-page" className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
            <Shield className="w-5 h-5 text-amber-400" />
            Acente Supplier Credential Yonetimi
          </h2>
          <p className="text-xs text-zinc-500 mt-1">Tum acentelerin supplier API bilgilerini bu sayfadan yonetin</p>
        </div>
        <Button data-testid="refresh-agencies" size="sm" variant="outline" className="text-xs h-8" onClick={fetchAgencies}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {/* Stats */}
      <div className="flex gap-3 text-xs">
        <div className="bg-zinc-800/50 rounded-lg px-4 py-2.5 border border-zinc-800 flex items-center gap-2">
          <Building2 className="w-3.5 h-3.5 text-zinc-500" />
          <span className="text-zinc-500">Acenteler:</span>
          <span className="text-zinc-200 font-mono font-medium" data-testid="total-agencies">{agencies.length}</span>
        </div>
        <div className="bg-zinc-800/50 rounded-lg px-4 py-2.5 border border-zinc-800 flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          <span className="text-zinc-500">Connected:</span>
          <span className="text-emerald-400 font-mono font-medium" data-testid="total-connected">{totalConnected}</span>
        </div>
        <div className="bg-zinc-800/50 rounded-lg px-4 py-2.5 border border-zinc-800 flex items-center gap-2">
          <XCircle className="w-3.5 h-3.5 text-zinc-500" />
          <span className="text-zinc-500">Disabled:</span>
          <span className="text-zinc-400 font-mono font-medium">{totalDisabled}</span>
        </div>
      </div>

      <Tabs defaultValue="agencies" className="w-full">
        <TabsList className="bg-zinc-800/50 border border-zinc-700">
          <TabsTrigger value="agencies" className="text-xs">Acenteler</TabsTrigger>
          <TabsTrigger value="audit" className="text-xs">Audit Log</TabsTrigger>
        </TabsList>

        <TabsContent value="agencies" className="mt-4">
          {/* Agencies with credentials */}
          {agencies.length > 0 && (
            <div className="space-y-2 mb-6">
              <h4 className="text-xs font-medium text-zinc-400 mb-2">Credential Tanimli Acenteler</h4>
              {agencies.map(a => (
                <div
                  key={a.organization_id}
                  data-testid={`agency-row-${a.organization_id}`}
                  className="flex items-center gap-4 bg-zinc-900/60 rounded-lg px-4 py-3 border border-zinc-800 hover:border-zinc-700 cursor-pointer transition-colors"
                  onClick={() => setSelectedAgency(a)}
                >
                  <Building2 className="w-4 h-4 text-zinc-500" />
                  <div className="flex-1">
                    <span className="text-sm font-medium text-zinc-200">{a.company_name}</span>
                    <span className="text-[11px] text-zinc-600 font-mono ml-2">{a.organization_id}</span>
                  </div>
                  <div className="flex gap-2">
                    {(a.suppliers || []).map(s => {
                      const sc = STATUS_MAP[s.status] || STATUS_MAP.draft;
                      return (
                        <Badge key={s.supplier} variant="outline" className={`text-[9px] ${sc.cls}`}>
                          {SUPPLIER_CONFIG[s.supplier]?.name || s.supplier}: {sc.label}
                        </Badge>
                      );
                    })}
                  </div>
                  <span className="text-zinc-600 text-xs">&rarr;</span>
                </div>
              ))}
            </div>
          )}

          {/* Agencies without credentials */}
          {allOrgs.length > 0 && (
            <div className="space-y-2">
              <h4 className="text-xs font-medium text-zinc-500 mb-2">Diger Acenteler (Henuz Credential Yok)</h4>
              {allOrgs
                .filter(o => !agencies.some(a => a.organization_id === (o.org_id || o.organization_id)))
                .slice(0, 20)
                .map(o => (
                  <div
                    key={o.org_id || o.organization_id}
                    data-testid={`agency-row-${o.org_id || o.organization_id}`}
                    className="flex items-center gap-4 bg-zinc-900/30 rounded-lg px-4 py-3 border border-zinc-800/50 hover:border-zinc-700 cursor-pointer transition-colors"
                    onClick={() => setSelectedAgency({ organization_id: o.org_id || o.organization_id, company_name: o.name || o.company_name })}
                  >
                    <Building2 className="w-4 h-4 text-zinc-600" />
                    <span className="text-sm text-zinc-400">{o.name || o.company_name || o.org_id}</span>
                    <span className="text-[11px] text-zinc-600 font-mono">{o.org_id || o.organization_id}</span>
                    <span className="text-zinc-700 text-xs ml-auto">No credentials &rarr;</span>
                  </div>
                ))}
            </div>
          )}

          {agencies.length === 0 && allOrgs.length === 0 && !loading && (
            <p className="text-zinc-500 text-sm text-center py-8">Henuz acente bulunmadi</p>
          )}
        </TabsContent>

        <TabsContent value="audit" className="mt-4">
          <AuditLogTab />
        </TabsContent>
      </Tabs>
    </div>
  );
}
