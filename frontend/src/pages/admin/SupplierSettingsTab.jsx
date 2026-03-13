import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import {
  CheckCircle2, XCircle, RefreshCw, Plug, Trash2, TestTube, Eye, EyeOff,
  Globe, Key, User, Lock, Building2
} from "lucide-react";
import { api } from "../../lib/api";

const SUPPLIER_CONFIG = {
  wwtatil: {
    name: "WWTatil Tour API",
    type: "Tur",
    color: "bg-blue-600",
    fields: [
      { key: "base_url", label: "API Base URL", icon: Globe, placeholder: "https://b2b-api.wwtatil.com", sensitive: false },
      { key: "application_secret_key", label: "Application Secret Key", icon: Key, placeholder: "Application secret key", sensitive: true },
      { key: "username", label: "Username", icon: User, placeholder: "API username", sensitive: false },
      { key: "password", label: "Password", icon: Lock, placeholder: "API password", sensitive: true },
      { key: "agency_id", label: "Agency ID", icon: Building2, placeholder: "12345", sensitive: false },
    ],
  },
  paximum: {
    name: "Paximum Travel API",
    type: "Otel",
    color: "bg-emerald-600",
    fields: [
      { key: "base_url", label: "API Base URL", icon: Globe, placeholder: "https://api.paximum.com", sensitive: false },
      { key: "api_key", label: "API Key", icon: Key, placeholder: "Paximum API key", sensitive: true },
    ],
  },
  aviationstack: {
    name: "AviationStack Flight API",
    type: "Ucus",
    color: "bg-violet-600",
    fields: [
      { key: "base_url", label: "API Base URL", icon: Globe, placeholder: "https://api.aviationstack.com/v1", sensitive: false },
      { key: "api_key", label: "API Key", icon: Key, placeholder: "AviationStack API key", sensitive: true },
    ],
  },
};

function SupplierCard({ code, config, savedCred, onRefresh }) {
  const [editing, setEditing] = useState(false);
  const [fields, setFields] = useState({});
  const [saving, setSaving] = useState(false);
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [deleting, setDeleting] = useState(false);
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

  const status = savedCred?.status;
  const statusBadge = status === "connected"
    ? <Badge data-testid={`supplier-status-${code}`} className="bg-emerald-600 text-white">Connected</Badge>
    : status === "saved"
      ? <Badge data-testid={`supplier-status-${code}`} className="bg-amber-600 text-white">Saved</Badge>
      : status === "auth_failed"
        ? <Badge data-testid={`supplier-status-${code}`} className="bg-red-600 text-white">Auth Failed</Badge>
        : <Badge data-testid={`supplier-status-${code}`} className="bg-zinc-600 text-white">Not Connected</Badge>;

  return (
    <Card data-testid={`supplier-card-${code}`} className="bg-zinc-900 border-zinc-800">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <span className={`w-2 h-2 rounded-full ${status === "connected" ? "bg-emerald-400" : status ? "bg-amber-400" : "bg-zinc-600"}`} />
          <span className="flex-1">{config.name}</span>
          <Badge variant="outline" className="text-[10px]">{config.type}</Badge>
          {statusBadge}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-xs">
        {/* Credential Fields */}
        {(editing || !savedCred) ? (
          <div className="space-y-2">
            {config.fields.map(f => (
              <div key={f.key} className="flex items-center gap-2">
                <f.icon className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                <label className="text-zinc-400 w-28 shrink-0">{f.label}</label>
                <div className="flex-1 relative">
                  <Input
                    data-testid={`input-${code}-${f.key}`}
                    type={f.sensitive && !showSensitive[f.key] ? "password" : "text"}
                    value={fields[f.key] || ""}
                    onChange={e => setFields(p => ({ ...p, [f.key]: e.target.value }))}
                    placeholder={f.placeholder}
                    className="h-7 text-xs bg-zinc-800 border-zinc-700"
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
              <Button data-testid={`save-${code}`} size="sm" className="text-xs" disabled={saving} onClick={save}>
                {saving ? "Saving..." : "Save Credentials"}
              </Button>
              {savedCred && <Button size="sm" variant="outline" className="text-xs" onClick={() => setEditing(false)}>Cancel</Button>}
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {config.fields.map(f => (
              <div key={f.key} className="flex items-center gap-2">
                <f.icon className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
                <span className="text-zinc-400 w-28 shrink-0">{f.label}</span>
                <span className="text-zinc-300 font-mono">{savedCred[f.key] || "---"}</span>
              </div>
            ))}
            {savedCred.connected_at && <p className="text-zinc-500">Connected: {new Date(savedCred.connected_at).toLocaleString()}</p>}
          </div>
        )}

        {/* Action Buttons */}
        {savedCred && !editing && (
          <div className="flex gap-2 pt-1">
            <Button data-testid={`test-${code}`} size="sm" variant="outline" className="text-xs" disabled={testing} onClick={test}>
              <TestTube className="w-3 h-3 mr-1" />{testing ? "Testing..." : "Test Connection"}
            </Button>
            <Button data-testid={`edit-${code}`} size="sm" variant="outline" className="text-xs" onClick={() => setEditing(true)}>
              <Plug className="w-3 h-3 mr-1" />Edit
            </Button>
            <Button data-testid={`delete-${code}`} size="sm" variant="outline" className="text-xs text-red-400 hover:text-red-300" disabled={deleting} onClick={del}>
              <Trash2 className="w-3 h-3 mr-1" />{deleting ? "..." : "Remove"}
            </Button>
          </div>
        )}

        {/* Test Result */}
        {testResult && (
          <div data-testid={`test-result-${code}`} className={`p-3 rounded border ${testResult.verdict === "PASS" ? "bg-emerald-900/30 border-emerald-800" : "bg-red-900/30 border-red-800"}`}>
            <div className="flex items-center gap-2 mb-1">
              {testResult.verdict === "PASS" ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
              <span className="font-mono font-bold">{testResult.verdict}</span>
              {testResult.latency_ms && <span className="text-zinc-500 ml-auto">{testResult.latency_ms}ms</span>}
            </div>
            {testResult.message && <p className="text-zinc-400">{testResult.message}</p>}
            {testResult.error && <p className="text-red-400">{testResult.error}</p>}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

export default function SupplierSettingsTab() {
  const [credentials, setCredentials] = useState([]);
  const [loading, setLoading] = useState(true);

  const fetchCreds = useCallback(async () => {
    setLoading(true);
    try {
      const r = await api.get("/supplier-credentials/my");
      setCredentials(r.data.credentials || []);
    } catch {}
    setLoading(false);
  }, []);

  useEffect(() => { fetchCreds(); }, [fetchCreds]);

  const getCredForSupplier = (code) => credentials.find(c => c.supplier === code);

  return (
    <div data-testid="supplier-settings-tab" className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-zinc-200">Supplier Integrations</h3>
          <p className="text-xs text-zinc-500 mt-0.5">Acentenize ait supplier API bilgilerini girin. Her acenta kendi credential'larini yonetir.</p>
        </div>
        <Button data-testid="refresh-creds" size="sm" variant="outline" className="text-xs" onClick={fetchCreds}>
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
        </Button>
      </div>

      {/* Stats bar */}
      <div className="flex gap-3 text-xs">
        <div className="bg-zinc-800/50 rounded px-3 py-1.5 flex items-center gap-2">
          <span className="text-zinc-500">Total:</span>
          <span className="text-zinc-200 font-mono">{Object.keys(SUPPLIER_CONFIG).length}</span>
        </div>
        <div className="bg-zinc-800/50 rounded px-3 py-1.5 flex items-center gap-2">
          <span className="text-zinc-500">Connected:</span>
          <span className="text-emerald-400 font-mono" data-testid="connected-count">{credentials.filter(c => c.status === "connected").length}</span>
        </div>
        <div className="bg-zinc-800/50 rounded px-3 py-1.5 flex items-center gap-2">
          <span className="text-zinc-500">Saved:</span>
          <span className="text-amber-400 font-mono">{credentials.filter(c => c.status === "saved").length}</span>
        </div>
      </div>

      {/* Supplier Cards */}
      <div className="grid grid-cols-1 gap-4">
        {Object.entries(SUPPLIER_CONFIG).map(([code, config]) => (
          <SupplierCard key={code} code={code} config={config} savedCred={getCredForSupplier(code)} onRefresh={fetchCreds} />
        ))}
      </div>

      {/* Info box */}
      <Card className="bg-zinc-800/30 border-zinc-700/50">
        <CardContent className="pt-4 text-xs text-zinc-500 space-y-1">
          <p><strong className="text-zinc-400">Guvenlik:</strong> Tum credential'lar AES-256 ile sifrelenerek saklanir.</p>
          <p><strong className="text-zinc-400">Multi-tenant:</strong> Her acenta kendi supplier bilgilerini yonetir. Diger acenteler erisemez.</p>
          <p><strong className="text-zinc-400">Token Cache:</strong> WWTatil tokenları 24 saat cache'lenir. Otomatik yenileme aktif.</p>
        </CardContent>
      </Card>
    </div>
  );
}
