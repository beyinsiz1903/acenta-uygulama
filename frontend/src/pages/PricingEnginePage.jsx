import React, { useState, useCallback, useEffect } from "react";
import {
  Calculator, Layers, Tag, Zap, Plus, Trash2, ToggleLeft,
  ToggleRight, RefreshCw, Loader2, TrendingUp,
  Globe, Building2, Store, Users, Shield, ShieldAlert,
  ShieldCheck, ChevronDown, ChevronUp, Trophy, XCircle,
  CheckCircle2, AlertTriangle, Info, Eye, Copy, Fingerprint,
  Clock, Database, BarChart3, Activity,
} from "lucide-react";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../components/ui/select";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "../components/ui/table";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../components/ui/tabs";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "../components/ui/tooltip";
import { toast } from "sonner";

import { api as axiosApi } from "../lib/api";

async function api(path, opts = {}) {
  try {
    const method = opts.method?.toLowerCase() || "get";
    const body = opts.body ? JSON.parse(opts.body) : undefined;
    const res = await axiosApi.request({
      method,
      url: `/pricing-engine${path}`,
      data: body,
    });
    return res.data;
  } catch (err) {
    console.error(`API error on ${path}:`, err?.response?.status, err?.response?.data || err.message);
    throw err;
  }
}

function fmtCurrency(amt, cur = "EUR") {
  if (amt == null) return "-";
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: cur }).format(amt);
}

const CHANNEL_ICONS = { b2b: Building2, b2c: Store, corporate: Globe, whitelabel: Users };
const CHANNEL_COLORS = {
  b2b: "bg-blue-50 text-blue-700 border-blue-200",
  b2c: "bg-emerald-50 text-emerald-700 border-emerald-200",
  corporate: "bg-violet-50 text-violet-700 border-violet-200",
  whitelabel: "bg-amber-50 text-amber-700 border-amber-200",
};

const GUARDRAIL_LABELS = {
  min_margin_pct: "Minimum Marj %",
  max_discount_pct: "Maksimum Indirim %",
  channel_floor_price: "Kanal Taban Fiyat",
  supplier_max_markup_pct: "Supplier Maks Markup %",
};

const GUARDRAIL_ICONS = {
  min_margin_pct: TrendingUp,
  max_discount_pct: Tag,
  channel_floor_price: Shield,
  supplier_max_markup_pct: Layers,
};

// ============== STAT CARDS ==============

function StatCards({ stats }) {
  const cards = [
    { label: "Toplam Kural", value: stats.total_rules || 0, icon: Layers, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Aktif Kural", value: stats.active_rules || 0, icon: Zap, color: "text-emerald-600", bg: "bg-emerald-50" },
    { label: "Kanal", value: stats.channel_count || 0, icon: Globe, color: "text-violet-600", bg: "bg-violet-50" },
    { label: "Aktif Promosyon", value: stats.active_promotions || 0, icon: Tag, color: "text-amber-600", bg: "bg-amber-50" },
    { label: "Guardrail", value: stats.active_guardrails || 0, icon: Shield, color: "text-rose-600", bg: "bg-rose-50" },
  ];
  return (
    <div className="grid grid-cols-2 lg:grid-cols-5 gap-4" data-testid="pricing-stat-cards">
      {cards.map((c, i) => {
        const Icon = c.icon;
        return (
          <Card key={i} className="border">
            <CardContent className="p-4 flex items-center gap-3">
              <div className={`${c.bg} p-2.5 rounded-lg`}><Icon className={`w-5 h-5 ${c.color}`} /></div>
              <div>
                <p className="text-xs text-muted-foreground">{c.label}</p>
                <p className="text-xl font-bold">{c.value}</p>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}

// ============== PIPELINE EXPLAINER ==============

const STEP_COLORS = {
  supplier_price: { bg: "bg-slate-100", border: "border-slate-300", text: "text-slate-700", accent: "bg-slate-600" },
  base_markup: { bg: "bg-blue-50", border: "border-blue-200", text: "text-blue-700", accent: "bg-blue-600" },
  channel_rule: { bg: "bg-violet-50", border: "border-violet-200", text: "text-violet-700", accent: "bg-violet-600" },
  agency_rule: { bg: "bg-indigo-50", border: "border-indigo-200", text: "text-indigo-700", accent: "bg-indigo-600" },
  promotion: { bg: "bg-amber-50", border: "border-amber-200", text: "text-amber-700", accent: "bg-amber-600" },
  tax: { bg: "bg-gray-50", border: "border-gray-200", text: "text-gray-600", accent: "bg-gray-500" },
  currency_conversion: { bg: "bg-teal-50", border: "border-teal-200", text: "text-teal-700", accent: "bg-teal-600" },
};

function PipelineExplainer({ steps, sellPrice, sellCurrency, supplierPrice }) {
  if (!steps?.length) return null;
  return (
    <div className="space-y-1" data-testid="pipeline-explainer">
      {steps.map((s, i) => {
        const colors = STEP_COLORS[s.step] || STEP_COLORS.supplier_price;
        const isLast = i === steps.length - 1;
        const showAdjustment = s.step !== "supplier_price" && s.step !== "currency_conversion";
        return (
          <React.Fragment key={i}>
            <div className={`rounded-lg border ${colors.border} ${colors.bg} p-3 transition-all duration-200 hover:shadow-sm`}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <div className={`w-1.5 h-8 rounded-full ${colors.accent}`} />
                  <div>
                    <p className={`text-sm font-medium ${colors.text}`}>{s.label}</p>
                    {s.rule_name && <p className="text-[10px] text-muted-foreground">Kural: {s.rule_name} ({s.rule_id})</p>}
                    {!s.rule_name && s.detail && <p className="text-[10px] text-muted-foreground">{s.detail}</p>}
                  </div>
                </div>
                <div className="text-right">
                  {showAdjustment && s.adjustment_amount !== 0 && (
                    <p className={`text-xs font-mono ${s.adjustment_amount > 0 ? "text-emerald-600" : s.adjustment_amount < 0 ? "text-red-500" : "text-muted-foreground"}`}>
                      {s.adjustment_amount > 0 ? "+" : ""}{s.adjustment_amount.toFixed(2)}
                      {s.adjustment_pct !== 0 && ` (%${s.adjustment_pct > 0 ? "+" : ""}${s.adjustment_pct})`}
                    </p>
                  )}
                  <p className={`text-sm font-bold font-mono ${colors.text}`}>{s.output_price.toFixed(2)}</p>
                </div>
              </div>
            </div>
            {!isLast && (
              <div className="flex justify-center">
                <div className="w-px h-3 bg-slate-300" />
              </div>
            )}
          </React.Fragment>
        );
      })}
      {/* Final sell price */}
      <div className="bg-slate-900 text-white rounded-lg p-4 flex justify-between items-center mt-2">
        <div>
          <span className="font-semibold text-sm">Satis Fiyati</span>
          <p className="text-[10px] text-slate-400">supplier_price: {supplierPrice} -&gt; final: {sellPrice}</p>
        </div>
        <span className="text-xl font-bold font-mono" data-testid="sim-sell-price">{fmtCurrency(sellPrice, sellCurrency)}</span>
      </div>
    </div>
  );
}

// ============== EVALUATED RULES PANEL ==============

function EvaluatedRulesPanel({ evaluatedRules }) {
  const [expanded, setExpanded] = useState(false);
  if (!evaluatedRules?.length) return null;

  const winners = evaluatedRules.filter(r => r.won);
  const losers = evaluatedRules.filter(r => !r.won);

  return (
    <div className="border rounded-lg overflow-hidden" data-testid="evaluated-rules-panel">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-3 bg-slate-50 hover:bg-slate-100 transition-colors duration-150"
        data-testid="toggle-evaluated-rules"
      >
        <div className="flex items-center gap-2">
          <Eye className="w-4 h-4 text-slate-500" />
          <span className="text-sm font-medium">Kural Precedence ({evaluatedRules.length} kural degerlendirildi)</span>
        </div>
        {expanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
      </button>
      {expanded && (
        <div className="p-3 space-y-3">
          {/* Winners */}
          {winners.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-emerald-700 mb-1.5 flex items-center gap-1"><Trophy className="w-3 h-3" /> Kazanan Kurallar</p>
              <div className="space-y-1.5">
                {winners.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 p-2 rounded-md bg-emerald-50 border border-emerald-200">
                    <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs font-medium text-emerald-800 truncate">{r.name || r.rule_id}</p>
                      <p className="text-[10px] text-emerald-600">{r.category} | Skor: {r.match_score} | Oncelik: {r.priority} | Deger: %{r.value}</p>
                    </div>
                    <Badge variant="outline" className="text-[9px] border-emerald-300 text-emerald-700 shrink-0">KAZANDI</Badge>
                  </div>
                ))}
              </div>
            </div>
          )}
          {/* Losers */}
          {losers.length > 0 && (
            <div>
              <p className="text-xs font-semibold text-slate-500 mb-1.5 flex items-center gap-1"><XCircle className="w-3 h-3" /> Diger Kurallar</p>
              <div className="space-y-1">
                {losers.map((r, i) => (
                  <div key={i} className="flex items-center gap-2 p-2 rounded-md bg-slate-50 border border-slate-200">
                    <XCircle className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <div className="flex-1 min-w-0">
                      <p className="text-xs text-slate-600 truncate">{r.name || r.rule_id}</p>
                      <p className="text-[10px] text-slate-400">{r.category} | Skor: {r.match_score} | Deger: %{r.value}</p>
                    </div>
                    {r.reject_reason && <Badge variant="secondary" className="text-[9px] shrink-0">{r.reject_reason}</Badge>}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============== GUARDRAIL WARNINGS ==============

function GuardrailWarnings({ warnings, passed }) {
  if (!warnings?.length) return null;
  return (
    <div className={`rounded-lg border p-3 space-y-2 ${passed ? "border-emerald-200 bg-emerald-50" : "border-red-200 bg-red-50"}`} data-testid="guardrail-warnings">
      <div className="flex items-center gap-2">
        {passed
          ? <ShieldCheck className="w-4 h-4 text-emerald-600" />
          : <ShieldAlert className="w-4 h-4 text-red-600" />
        }
        <span className={`text-sm font-semibold ${passed ? "text-emerald-700" : "text-red-700"}`}>
          {passed ? "Tum guardrail'lar gecti" : "Guardrail ihlali tespit edildi"}
        </span>
      </div>
      {warnings.map((w, i) => (
        <div key={i} className={`flex items-start gap-2 text-xs p-2 rounded ${w.severity === "error" ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800"}`}>
          {w.severity === "error" ? <AlertTriangle className="w-3.5 h-3.5 shrink-0 mt-0.5" /> : <Info className="w-3.5 h-3.5 shrink-0 mt-0.5" />}
          <div>
            <p className="font-medium">{GUARDRAIL_LABELS[w.guardrail] || w.guardrail}</p>
            <p>{w.message}</p>
            <p className="text-[10px] opacity-75">Beklenen: {w.expected} | Gercek: {w.actual}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ============== TRACE & CACHE INFO BAR ==============

function TraceBar({ result }) {
  if (!result) return null;
  const traceId = result.pricing_trace_id || "";
  const cacheHit = result.cache_hit || false;
  const latency = result.latency_ms || 0;
  const cacheKey = result.cache_key || "";

  const copyTrace = () => {
    navigator.clipboard.writeText(traceId);
    toast.success("Trace ID kopyalandi");
  };

  return (
    <div className="flex flex-wrap items-center gap-3 px-3 py-2 rounded-lg bg-slate-900 text-white text-xs font-mono" data-testid="pricing-trace-bar">
      <div className="flex items-center gap-1.5">
        <Fingerprint className="w-3.5 h-3.5 text-amber-400" />
        <span className="text-slate-400">trace:</span>
        <span className="text-amber-300 font-semibold" data-testid="trace-id-value">{traceId}</span>
        <button onClick={copyTrace} className="hover:text-amber-200 transition-colors" data-testid="copy-trace-btn" title="Kopyala">
          <Copy className="w-3 h-3" />
        </button>
      </div>
      <div className="w-px h-4 bg-slate-700" />
      <div className="flex items-center gap-1.5">
        <Database className="w-3.5 h-3.5 text-teal-400" />
        <span className="text-slate-400">cache:</span>
        <span className={`font-semibold ${cacheHit ? "text-emerald-400" : "text-slate-500"}`} data-testid="cache-status">
          {cacheHit ? "HIT" : "MISS"}
        </span>
      </div>
      <div className="w-px h-4 bg-slate-700" />
      <div className="flex items-center gap-1.5">
        <Clock className="w-3.5 h-3.5 text-blue-400" />
        <span className="text-slate-400">latency:</span>
        <span className="text-blue-300" data-testid="latency-value">{latency}ms</span>
      </div>
      {cacheKey && (
        <>
          <div className="w-px h-4 bg-slate-700" />
          <div className="flex items-center gap-1.5">
            <span className="text-slate-500">key:</span>
            <span className="text-slate-400">{cacheKey}</span>
          </div>
        </>
      )}
    </div>
  );
}

// ============== PRICE SIMULATOR ==============

function PriceSimulator({ metadata, onSimulated }) {
  const [form, setForm] = useState({
    supplier_code: "ratehawk",
    supplier_price: 100,
    supplier_currency: "EUR",
    destination: "TR",
    channel: "b2b",
    agency_tier: "standard",
    season: "mid",
    product_type: "hotel",
    nights: 3,
    sell_currency: "EUR",
    promo_code: "",
  });
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const simulate = async () => {
    setLoading(true);
    try {
      const data = await api("/simulate", {
        method: "POST",
        body: JSON.stringify({ ...form, supplier_price: parseFloat(form.supplier_price), nights: parseInt(form.nights) }),
      });
      setResult(data);
      if (onSimulated) onSimulated();
    } catch {
      toast.error("Simulasyon hatasi");
    }
    setLoading(false);
  };

  const set = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

  return (
    <div className="grid lg:grid-cols-[380px_1fr] gap-6" data-testid="price-simulator">
      {/* Input */}
      <Card className="h-fit">
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2"><Calculator className="w-4 h-4" /> Fiyat Girdileri</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Supplier</Label>
              <Input data-testid="sim-supplier" value={form.supplier_code} onChange={e => set("supplier_code", e.target.value)} placeholder="ratehawk" />
            </div>
            <div>
              <Label className="text-xs">Supplier Fiyat</Label>
              <Input data-testid="sim-price" type="number" value={form.supplier_price} onChange={e => set("supplier_price", e.target.value)} />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Supplier Para Birimi</Label>
              <Select value={form.supplier_currency} onValueChange={v => set("supplier_currency", v)}>
                <SelectTrigger data-testid="sim-supplier-ccy"><SelectValue /></SelectTrigger>
                <SelectContent>{["EUR","USD","TRY","GBP"].map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Satis Para Birimi</Label>
              <Select value={form.sell_currency} onValueChange={v => set("sell_currency", v)}>
                <SelectTrigger data-testid="sim-sell-ccy"><SelectValue /></SelectTrigger>
                <SelectContent>{["EUR","USD","TRY","GBP"].map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <Label className="text-xs">Destinasyon</Label>
              <Input data-testid="sim-dest" value={form.destination} onChange={e => set("destination", e.target.value)} placeholder="TR" />
            </div>
            <div>
              <Label className="text-xs">Kanal</Label>
              <Select value={form.channel} onValueChange={v => set("channel", v)}>
                <SelectTrigger data-testid="sim-channel"><SelectValue /></SelectTrigger>
                <SelectContent>{(metadata?.channels || []).map(c => <SelectItem key={c} value={c}>{c.toUpperCase()}</SelectItem>)}</SelectContent>
              </Select>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-3">
            <div>
              <Label className="text-xs">Agency Tier</Label>
              <Select value={form.agency_tier} onValueChange={v => set("agency_tier", v)}>
                <SelectTrigger data-testid="sim-tier"><SelectValue /></SelectTrigger>
                <SelectContent>{(metadata?.agency_tiers || []).map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Sezon</Label>
              <Select value={form.season} onValueChange={v => set("season", v)}>
                <SelectTrigger data-testid="sim-season"><SelectValue /></SelectTrigger>
                <SelectContent>{(metadata?.seasons || []).map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Gece</Label>
              <Input data-testid="sim-nights" type="number" value={form.nights} onChange={e => set("nights", e.target.value)} min={1} />
            </div>
          </div>
          <div>
            <Label className="text-xs">Promosyon Kodu</Label>
            <Input data-testid="sim-promo" value={form.promo_code} onChange={e => set("promo_code", e.target.value)} placeholder="Opsiyonel" />
          </div>
          <Button data-testid="sim-calculate-btn" onClick={simulate} disabled={loading} className="w-full">
            {loading ? <Loader2 className="w-4 h-4 animate-spin mr-2" /> : <Calculator className="w-4 h-4 mr-2" />}
            Fiyat Hesapla
          </Button>
        </CardContent>
      </Card>

      {/* Result */}
      <div className="space-y-4">
        {!result ? (
          <Card>
            <CardContent className="flex flex-col items-center justify-center h-64 text-muted-foreground">
              <Calculator className="w-12 h-12 mb-3 opacity-20" />
              <p className="text-sm">Simulasyon icin parametreleri girin ve hesaplayin</p>
              <p className="text-xs mt-1 text-muted-foreground">Pipeline her adimi detayli gosterecektir</p>
            </CardContent>
          </Card>
        ) : (
          <>
            {/* Trace & Cache Info */}
            <TraceBar result={result} />

            {/* Guardrail Warnings */}
            <GuardrailWarnings warnings={result.guardrail_warnings} passed={result.guardrails_passed} />

            {/* Pipeline Explainer */}
            <Card>
              <CardHeader className="pb-2">
                <CardTitle className="text-base flex items-center gap-2">
                  <TrendingUp className="w-4 h-4" /> Fiyat Pipeline
                </CardTitle>
              </CardHeader>
              <CardContent>
                <PipelineExplainer
                  steps={result.pipeline_steps}
                  sellPrice={result.sell_price}
                  sellCurrency={result.sell_currency}
                  supplierPrice={result.supplier_price}
                />
              </CardContent>
            </Card>

            {/* Metrics */}
            <div className="grid grid-cols-4 gap-3" data-testid="sim-metrics">
              <div className={`text-center p-3 rounded-lg border ${result.margin >= 0 ? "bg-emerald-50 border-emerald-200" : "bg-red-50 border-red-200"}`}>
                <p className="text-[10px] font-medium text-muted-foreground">Marj</p>
                <p className={`text-lg font-bold font-mono ${result.margin >= 0 ? "text-emerald-700" : "text-red-600"}`}>{fmtCurrency(result.margin, result.sell_currency)}</p>
              </div>
              <div className={`text-center p-3 rounded-lg border ${result.margin_pct >= 0 ? "bg-blue-50 border-blue-200" : "bg-red-50 border-red-200"}`}>
                <p className="text-[10px] font-medium text-muted-foreground">Marj %</p>
                <p className={`text-lg font-bold font-mono ${result.margin_pct >= 0 ? "text-blue-700" : "text-red-600"}`}>%{result.margin_pct}</p>
              </div>
              <div className="text-center p-3 bg-violet-50 rounded-lg border border-violet-200">
                <p className="text-[10px] font-medium text-muted-foreground">Gece Basina</p>
                <p className="text-lg font-bold font-mono text-violet-700">{fmtCurrency(result.per_night, result.sell_currency)}</p>
              </div>
              <div className="text-center p-3 bg-teal-50 rounded-lg border border-teal-200">
                <p className="text-[10px] font-medium text-muted-foreground">Komisyon</p>
                <p className="text-lg font-bold font-mono text-teal-700">{fmtCurrency(result.commission, result.sell_currency)}</p>
              </div>
            </div>

            {/* Evaluated Rules Panel */}
            <EvaluatedRulesPanel evaluatedRules={result.evaluated_rules} />
          </>
        )}
      </div>
    </div>
  );
}

// ============== DISTRIBUTION RULES ==============

function DistributionRulesTab() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", rule_category: "base_markup", value: 10, scope: {}, priority: 10 });
  const [scopeStr, setScopeStr] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const data = await api("/distribution-rules");
    setRules(Array.isArray(data) ? data : []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    let scope = {};
    try { scope = scopeStr ? JSON.parse(scopeStr) : {}; } catch { toast.error("Scope JSON hatali"); return; }
    await api("/distribution-rules", { method: "POST", body: JSON.stringify({ ...form, scope, value: parseFloat(form.value), priority: parseInt(form.priority) }) });
    toast.success("Kural eklendi");
    setShowAdd(false);
    load();
  };

  const remove = async (ruleId) => {
    await api(`/distribution-rules/${ruleId}`, { method: "DELETE" });
    toast.success("Kural silindi");
    load();
  };

  return (
    <div className="space-y-4" data-testid="distribution-rules-tab">
      <div className="flex justify-between items-center">
        <h3 className="text-sm font-medium">Dagitim Kurallari</h3>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCw className="w-3 h-3 mr-1" /> Yenile</Button>
          <Button size="sm" onClick={() => setShowAdd(!showAdd)} data-testid="add-rule-btn"><Plus className="w-3 h-3 mr-1" /> Kural Ekle</Button>
        </div>
      </div>

      {showAdd && (
        <Card className="border-dashed">
          <CardContent className="p-4 space-y-3">
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Kural Adi</Label>
                <Input data-testid="rule-name" value={form.name} onChange={e => setForm(p => ({...p, name: e.target.value}))} />
              </div>
              <div>
                <Label className="text-xs">Kategori</Label>
                <Select value={form.rule_category} onValueChange={v => setForm(p => ({...p, rule_category: v}))}>
                  <SelectTrigger data-testid="rule-category"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {["base_markup","agency_tier","commission","tax"].map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Deger (%)</Label>
                <Input data-testid="rule-value" type="number" value={form.value} onChange={e => setForm(p => ({...p, value: e.target.value}))} />
              </div>
              <div>
                <Label className="text-xs">Oncelik</Label>
                <Input data-testid="rule-priority" type="number" value={form.priority} onChange={e => setForm(p => ({...p, priority: e.target.value}))} />
              </div>
            </div>
            <div>
              <Label className="text-xs">Scope (JSON)</Label>
              <Input data-testid="rule-scope" value={scopeStr} onChange={e => setScopeStr(e.target.value)} placeholder='{"supplier":"ratehawk","destination":"TR"}' />
            </div>
            <Button data-testid="save-rule-btn" onClick={create} size="sm">Kaydet</Button>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin" /></div>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Kural Adi</TableHead>
                <TableHead>Kategori</TableHead>
                <TableHead>Deger</TableHead>
                <TableHead>Scope</TableHead>
                <TableHead>Oncelik</TableHead>
                <TableHead>Durum</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {rules.map((r) => (
                <TableRow key={r.rule_id} data-testid={`rule-row-${r.rule_id}`}>
                  <TableCell className="font-medium text-sm">{r.name}</TableCell>
                  <TableCell><Badge variant="outline" className="text-xs">{r.rule_category}</Badge></TableCell>
                  <TableCell className="font-mono text-sm">%{r.value}</TableCell>
                  <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate">{JSON.stringify(r.scope)}</TableCell>
                  <TableCell>{r.priority}</TableCell>
                  <TableCell><Badge variant={r.active ? "default" : "secondary"}>{r.active ? "Aktif" : "Pasif"}</Badge></TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" onClick={() => remove(r.rule_id)} data-testid={`delete-rule-${r.rule_id}`}>
                      <Trash2 className="w-3.5 h-3.5 text-red-500" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {rules.length === 0 && (
                <TableRow><TableCell colSpan={7} className="text-center text-sm text-muted-foreground py-8">Henuz kural yok</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}

// ============== CHANNEL CONFIGS ==============

function ChannelsTab() {
  const [channels, setChannels] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ channel: "b2b", label: "", adjustment_pct: 0, commission_pct: 0 });

  const load = useCallback(async () => {
    setLoading(true);
    const data = await api("/channels");
    setChannels(Array.isArray(data) ? data : []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    await api("/channels", { method: "POST", body: JSON.stringify({ ...form, adjustment_pct: parseFloat(form.adjustment_pct), commission_pct: parseFloat(form.commission_pct) }) });
    toast.success("Kanal eklendi");
    setShowAdd(false);
    load();
  };

  const remove = async (ruleId) => {
    await api(`/channels/${ruleId}`, { method: "DELETE" });
    toast.success("Kanal silindi");
    load();
  };

  return (
    <div className="space-y-4" data-testid="channels-tab">
      <div className="flex justify-between items-center">
        <h3 className="text-sm font-medium">Kanal Fiyatlandirmasi</h3>
        <Button size="sm" onClick={() => setShowAdd(!showAdd)} data-testid="add-channel-btn"><Plus className="w-3 h-3 mr-1" /> Kanal Ekle</Button>
      </div>

      {showAdd && (
        <Card className="border-dashed">
          <CardContent className="p-4 grid grid-cols-4 gap-3">
            <div>
              <Label className="text-xs">Kanal</Label>
              <Select value={form.channel} onValueChange={v => setForm(p => ({...p, channel: v}))}>
                <SelectTrigger data-testid="ch-type"><SelectValue /></SelectTrigger>
                <SelectContent>{["b2b","b2c","corporate","whitelabel"].map(c => <SelectItem key={c} value={c}>{c.toUpperCase()}</SelectItem>)}</SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs">Etiket</Label>
              <Input value={form.label} onChange={e => setForm(p => ({...p, label: e.target.value}))} placeholder="B2B Agency" />
            </div>
            <div>
              <Label className="text-xs">Fiyat Ayarlama %</Label>
              <Input type="number" value={form.adjustment_pct} onChange={e => setForm(p => ({...p, adjustment_pct: e.target.value}))} />
            </div>
            <div className="flex items-end">
              <Button data-testid="save-channel-btn" onClick={create} size="sm">Kaydet</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin" /></div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {channels.map((ch) => {
            const Icon = CHANNEL_ICONS[ch.channel] || Globe;
            const colorClass = CHANNEL_COLORS[ch.channel] || "bg-gray-50 text-gray-700 border-gray-200";
            return (
              <Card key={ch.rule_id} className={`border ${colorClass.split(" ").pop()}`} data-testid={`channel-card-${ch.channel}`}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className={`p-2 rounded-lg ${colorClass.split(" ").slice(0, 2).join(" ")}`}>
                      <Icon className="w-5 h-5" />
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => remove(ch.rule_id)}>
                      <Trash2 className="w-3.5 h-3.5 text-red-400" />
                    </Button>
                  </div>
                  <h4 className="font-semibold text-sm">{ch.label || ch.channel.toUpperCase()}</h4>
                  <p className="text-xs text-muted-foreground mt-1">{ch.channel}</p>
                  <div className="mt-3 flex gap-3">
                    <div>
                      <p className="text-[10px] text-muted-foreground">Fiyat Ayarlama</p>
                      <p className="font-mono text-sm font-bold">{ch.adjustment_pct >= 0 ? "+" : ""}{ch.adjustment_pct}%</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-muted-foreground">Komisyon</p>
                      <p className="font-mono text-sm font-bold">{ch.commission_pct}%</p>
                    </div>
                  </div>
                  <Badge variant={ch.active ? "default" : "secondary"} className="mt-2 text-[10px]">
                    {ch.active ? "Aktif" : "Pasif"}
                  </Badge>
                </CardContent>
              </Card>
            );
          })}
          {channels.length === 0 && (
            <div className="col-span-4 text-center py-8 text-sm text-muted-foreground">Henuz kanal yok</div>
          )}
        </div>
      )}
    </div>
  );
}

// ============== PROMOTIONS ==============

function PromotionsTab() {
  const [promos, setPromos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", promo_type: "campaign_discount", discount_pct: 10, promo_code: "", scope: {} });
  const [scopeStr, setScopeStr] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const data = await api("/promotions");
    setPromos(Array.isArray(data) ? data : []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    let scope = {};
    try { scope = scopeStr ? JSON.parse(scopeStr) : {}; } catch { toast.error("Scope JSON hatali"); return; }
    await api("/promotions", { method: "POST", body: JSON.stringify({ ...form, discount_pct: parseFloat(form.discount_pct), scope }) });
    toast.success("Promosyon eklendi");
    setShowAdd(false);
    load();
  };

  const remove = async (ruleId) => {
    await api(`/promotions/${ruleId}`, { method: "DELETE" });
    toast.success("Promosyon silindi");
    load();
  };

  const toggle = async (ruleId, active) => {
    await api(`/promotions/${ruleId}/toggle?active=${!active}`, { method: "POST" });
    load();
  };

  const PROMO_LABELS = {
    early_booking: "Erken Rezervasyon",
    flash_sale: "Flash Sale",
    campaign_discount: "Kampanya",
    fixed_price_override: "Sabit Fiyat",
  };

  return (
    <div className="space-y-4" data-testid="promotions-tab">
      <div className="flex justify-between items-center">
        <h3 className="text-sm font-medium">Promosyonlar</h3>
        <Button size="sm" onClick={() => setShowAdd(!showAdd)} data-testid="add-promo-btn"><Plus className="w-3 h-3 mr-1" /> Promosyon Ekle</Button>
      </div>

      {showAdd && (
        <Card className="border-dashed">
          <CardContent className="p-4 space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">Promosyon Adi</Label>
                <Input data-testid="promo-name" value={form.name} onChange={e => setForm(p => ({...p, name: e.target.value}))} />
              </div>
              <div>
                <Label className="text-xs">Tip</Label>
                <Select value={form.promo_type} onValueChange={v => setForm(p => ({...p, promo_type: v}))}>
                  <SelectTrigger data-testid="promo-type"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(PROMO_LABELS).map(([k,v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Indirim %</Label>
                <Input data-testid="promo-discount" type="number" value={form.discount_pct} onChange={e => setForm(p => ({...p, discount_pct: e.target.value}))} />
              </div>
            </div>
            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Promo Kodu</Label>
                <Input value={form.promo_code} onChange={e => setForm(p => ({...p, promo_code: e.target.value}))} placeholder="Opsiyonel" />
              </div>
              <div>
                <Label className="text-xs">Scope (JSON)</Label>
                <Input value={scopeStr} onChange={e => setScopeStr(e.target.value)} placeholder='{"destination":"TR"}' />
              </div>
            </div>
            <Button data-testid="save-promo-btn" onClick={create} size="sm">Kaydet</Button>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin" /></div>
      ) : (
        <Card>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Promosyon</TableHead>
                <TableHead>Tip</TableHead>
                <TableHead>Indirim</TableHead>
                <TableHead>Kod</TableHead>
                <TableHead>Scope</TableHead>
                <TableHead>Durum</TableHead>
                <TableHead></TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {promos.map((p) => (
                <TableRow key={p.rule_id} data-testid={`promo-row-${p.rule_id}`}>
                  <TableCell className="font-medium text-sm">{p.name}</TableCell>
                  <TableCell><Badge variant="outline" className="text-xs">{PROMO_LABELS[p.promo_type] || p.promo_type}</Badge></TableCell>
                  <TableCell className="font-mono text-sm">%{p.discount_pct}</TableCell>
                  <TableCell className="text-xs">{p.promo_code || "-"}</TableCell>
                  <TableCell className="text-xs text-muted-foreground max-w-[150px] truncate">{JSON.stringify(p.scope)}</TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" onClick={() => toggle(p.rule_id, p.active)} data-testid={`toggle-promo-${p.rule_id}`}>
                      {p.active ? <ToggleRight className="w-5 h-5 text-emerald-500" /> : <ToggleLeft className="w-5 h-5 text-gray-400" />}
                    </Button>
                  </TableCell>
                  <TableCell>
                    <Button variant="ghost" size="sm" onClick={() => remove(p.rule_id)}>
                      <Trash2 className="w-3.5 h-3.5 text-red-500" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {promos.length === 0 && (
                <TableRow><TableCell colSpan={7} className="text-center text-sm text-muted-foreground py-8">Henuz promosyon yok</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </Card>
      )}
    </div>
  );
}

// ============== GUARDRAILS ==============

function GuardrailsTab() {
  const [guardrails, setGuardrails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", guardrail_type: "min_margin_pct", value: 5, scope: {} });
  const [scopeStr, setScopeStr] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await api("/guardrails");
      setGuardrails(Array.isArray(data) ? data : []);
    } catch {
      setGuardrails([]);
    }
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    let scope = {};
    try { scope = scopeStr ? JSON.parse(scopeStr) : {}; } catch { toast.error("Scope JSON hatali"); return; }
    await api("/guardrails", { method: "POST", body: JSON.stringify({ ...form, value: parseFloat(form.value), scope }) });
    toast.success("Guardrail eklendi");
    setShowAdd(false);
    setScopeStr("");
    load();
  };

  const remove = async (guardrailId) => {
    await api(`/guardrails/${guardrailId}`, { method: "DELETE" });
    toast.success("Guardrail silindi");
    load();
  };

  return (
    <div className="space-y-4" data-testid="guardrails-tab">
      <div className="flex justify-between items-center">
        <div>
          <h3 className="text-sm font-medium">Marj Guardrail'lari</h3>
          <p className="text-xs text-muted-foreground mt-0.5">Yanlis kampanya veya kural yuzunden zarar yazmayi onleyin</p>
        </div>
        <Button size="sm" onClick={() => setShowAdd(!showAdd)} data-testid="add-guardrail-btn">
          <Plus className="w-3 h-3 mr-1" /> Guardrail Ekle
        </Button>
      </div>

      {showAdd && (
        <Card className="border-dashed border-rose-200">
          <CardContent className="p-4 space-y-3">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label className="text-xs">Guardrail Adi</Label>
                <Input data-testid="guard-name" value={form.name} onChange={e => setForm(p => ({...p, name: e.target.value}))} placeholder="Min Marj Korumasi" />
              </div>
              <div>
                <Label className="text-xs">Tip</Label>
                <Select value={form.guardrail_type} onValueChange={v => setForm(p => ({...p, guardrail_type: v}))}>
                  <SelectTrigger data-testid="guard-type"><SelectValue /></SelectTrigger>
                  <SelectContent>
                    {Object.entries(GUARDRAIL_LABELS).map(([k,v]) => <SelectItem key={k} value={k}>{v}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs">Deger</Label>
                <Input data-testid="guard-value" type="number" value={form.value} onChange={e => setForm(p => ({...p, value: e.target.value}))} />
              </div>
            </div>
            <div>
              <Label className="text-xs">Scope (JSON) - Opsiyonel</Label>
              <Input data-testid="guard-scope" value={scopeStr} onChange={e => setScopeStr(e.target.value)} placeholder='{"supplier":"ratehawk","channel":"b2b"}' />
            </div>
            <Button data-testid="save-guardrail-btn" onClick={create} size="sm">Kaydet</Button>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="flex justify-center p-8"><Loader2 className="w-6 h-6 animate-spin" /></div>
      ) : (
        <div className="grid sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {guardrails.map((g) => {
            const Icon = GUARDRAIL_ICONS[g.guardrail_type] || Shield;
            return (
              <Card key={g.guardrail_id} className="border border-rose-100" data-testid={`guardrail-card-${g.guardrail_id}`}>
                <CardContent className="p-4">
                  <div className="flex items-center justify-between mb-3">
                    <div className="bg-rose-50 p-2 rounded-lg">
                      <Icon className="w-5 h-5 text-rose-600" />
                    </div>
                    <Button variant="ghost" size="sm" onClick={() => remove(g.guardrail_id)} data-testid={`delete-guardrail-${g.guardrail_id}`}>
                      <Trash2 className="w-3.5 h-3.5 text-red-400" />
                    </Button>
                  </div>
                  <h4 className="font-semibold text-sm">{g.name}</h4>
                  <p className="text-xs text-muted-foreground mt-0.5">{GUARDRAIL_LABELS[g.guardrail_type] || g.guardrail_type}</p>
                  <div className="mt-3">
                    <p className="text-[10px] text-muted-foreground">Deger</p>
                    <p className="font-mono text-lg font-bold text-rose-700">
                      {g.guardrail_type.includes("price") ? fmtCurrency(g.value) : `%${g.value}`}
                    </p>
                  </div>
                  {Object.keys(g.scope || {}).length > 0 && (
                    <div className="mt-2">
                      <p className="text-[10px] text-muted-foreground">Scope</p>
                      <p className="text-xs font-mono bg-slate-50 rounded p-1 mt-0.5">{JSON.stringify(g.scope)}</p>
                    </div>
                  )}
                  <Badge variant={g.active ? "default" : "secondary"} className="mt-2 text-[10px]">
                    {g.active ? "Aktif" : "Pasif"}
                  </Badge>
                </CardContent>
              </Card>
            );
          })}
          {guardrails.length === 0 && (
            <div className="col-span-3 text-center py-12">
              <Shield className="w-10 h-10 mx-auto mb-2 text-slate-200" />
              <p className="text-sm text-muted-foreground">Henuz guardrail yok</p>
              <p className="text-xs text-muted-foreground mt-1">Minimum marj, maksimum indirim gibi korumalar ekleyin</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ============== MAIN PAGE ==============

export default function PricingEnginePage() {
  const [stats, setStats] = useState({});
  const [metadata, setMetadata] = useState(null);
  const [activeTab, setActiveTab] = useState("simulator");
  const [cacheStats, setCacheStats] = useState(null);
  const [telemetry, setTelemetry] = useState(null);
  const [showTelemetry, setShowTelemetry] = useState(false);

  const loadCacheStats = useCallback(() => {
    api("/cache/stats").then(setCacheStats).catch(() => {});
  }, []);

  const loadTelemetry = useCallback(() => {
    api("/cache/telemetry").then(setTelemetry).catch(() => {});
  }, []);

  useEffect(() => {
    api("/dashboard").then(setStats).catch(() => {});
    api("/metadata").then(setMetadata).catch(() => {});
    loadCacheStats();
  }, [loadCacheStats]);

  const clearCache = async () => {
    await api("/cache/clear", { method: "POST" });
    toast.success("Pricing cache temizlendi");
    loadCacheStats();
    if (showTelemetry) loadTelemetry();
  };

  const invalidateSupplier = async (supplier) => {
    try {
      const res = await api(`/cache/invalidate/${supplier}`, { method: "POST" });
      toast.success(`${supplier} cache temizlendi (${res.cleared} entry)`);
      loadCacheStats();
      if (showTelemetry) loadTelemetry();
    } catch {
      toast.error("Invalidation basarisiz");
    }
  };

  const toggleTelemetry = () => {
    const next = !showTelemetry;
    setShowTelemetry(next);
    if (next) loadTelemetry();
  };

  return (
    <TooltipProvider>
      <div className="space-y-6" data-testid="pricing-engine-page">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Pricing & Distribution Engine</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Supplier fiyatlarini kanal, acente ve promosyon kurallariyla donusturun
          </p>
        </div>

        <StatCards stats={stats} />

        {/* Cache Stats Bar */}
        {cacheStats && (
          <div className="rounded-lg border bg-slate-50 overflow-hidden" data-testid="cache-stats-bar">
            <div className="flex items-center gap-4 px-4 py-2.5 text-xs">
              <div className="flex items-center gap-1.5 text-slate-600">
                <Database className="w-3.5 h-3.5 text-teal-600" />
                <span className="font-medium">Pricing Cache</span>
              </div>
              <div className="flex items-center gap-3 text-slate-500 font-mono">
                <span>Entries: <strong className="text-slate-700">{cacheStats.active_entries}</strong></span>
                <span>Hits: <strong className="text-emerald-600">{cacheStats.hits}</strong></span>
                <span>Misses: <strong className="text-amber-600">{cacheStats.misses}</strong></span>
                <span>Hit Rate: <strong className={cacheStats.hit_rate_pct >= 50 ? "text-emerald-600" : "text-amber-600"}>{cacheStats.hit_rate_pct}%</strong></span>
                <span>TTL: {cacheStats.ttl_seconds}s</span>
              </div>
              <div className="ml-auto flex items-center gap-2">
                <Button variant="ghost" size="sm" onClick={toggleTelemetry} className="h-6 px-2 text-xs" data-testid="toggle-telemetry-btn">
                  <BarChart3 className="w-3 h-3 mr-1" /> {showTelemetry ? "Gizle" : "Telemetry"}
                </Button>
                <Button variant="ghost" size="sm" onClick={loadCacheStats} className="h-6 px-2 text-xs" data-testid="refresh-cache-btn">
                  <RefreshCw className="w-3 h-3 mr-1" /> Yenile
                </Button>
                <Button variant="ghost" size="sm" onClick={clearCache} className="h-6 px-2 text-xs text-red-500 hover:text-red-600" data-testid="clear-cache-btn">
                  <Trash2 className="w-3 h-3 mr-1" /> Temizle
                </Button>
              </div>
            </div>

            {/* Telemetry Detail Panel */}
            {showTelemetry && telemetry && (
              <div className="border-t bg-white px-4 py-3 space-y-3" data-testid="telemetry-panel">
                {/* Summary Row */}
                <div className="flex items-center gap-6 text-xs">
                  <div className="flex items-center gap-1.5">
                    <Activity className="w-3.5 h-3.5 text-blue-500" />
                    <span className="text-slate-500">Toplam Istek:</span>
                    <strong className="text-slate-700">{telemetry.total_requests}</strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Ort. HIT Latency:</span>
                    <strong className="text-emerald-600 ml-1">{telemetry.avg_hit_latency_ms}ms</strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Ort. MISS Latency:</span>
                    <strong className="text-amber-600 ml-1">{telemetry.avg_miss_latency_ms}ms</strong>
                  </div>
                  <div>
                    <span className="text-slate-500">Uptime:</span>
                    <strong className="text-slate-700 ml-1">{Math.floor(telemetry.uptime_seconds / 60)}dk</strong>
                  </div>
                </div>

                {/* Per-Supplier Breakdown */}
                {telemetry.supplier_breakdown && Object.keys(telemetry.supplier_breakdown).length > 0 && (
                  <div>
                    <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider mb-1.5">Supplier Bazli</div>
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                      {Object.entries(telemetry.supplier_breakdown).map(([supplier, data]) => (
                        <div key={supplier} className="flex items-center justify-between rounded-md border px-2.5 py-1.5 text-xs bg-slate-50" data-testid={`supplier-telemetry-${supplier}`}>
                          <div>
                            <div className="font-medium text-slate-700">{supplier}</div>
                            <div className="text-[10px] text-slate-400 font-mono">
                              {data.hits}H / {data.misses}M / {data.hit_rate_pct}%
                            </div>
                          </div>
                          <div className="flex items-center gap-1.5">
                            <Badge variant="outline" className="text-[10px] h-4 px-1">
                              {data.active_entries}
                            </Badge>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-5 w-5 p-0 text-red-400 hover:text-red-600"
                              onClick={() => invalidateSupplier(supplier)}
                              data-testid={`invalidate-${supplier}-btn`}
                            >
                              <Trash2 className="w-3 h-3" />
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {/* Recent Invalidations */}
                {telemetry.recent_invalidations && telemetry.recent_invalidations.length > 0 && (
                  <div>
                    <div className="text-[11px] font-medium text-slate-500 uppercase tracking-wider mb-1.5">Son Invalidation'lar</div>
                    <div className="space-y-1">
                      {telemetry.recent_invalidations.slice(-5).reverse().map((inv, i) => (
                        <div key={i} className="flex items-center gap-2 text-[11px] text-slate-500 font-mono" data-testid={`invalidation-log-${i}`}>
                          <span className="text-slate-400">{inv.timestamp?.split("T")[1]?.split(".")[0]}</span>
                          <Badge variant="outline" className="text-[10px] h-4 px-1.5">{inv.reason}</Badge>
                          <span className="text-red-500">{inv.cleared} temizlendi</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}

        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList>
            <TabsTrigger value="simulator" data-testid="tab-simulator">
              <Calculator className="w-3.5 h-3.5 mr-1.5" /> Simulasyon
            </TabsTrigger>
            <TabsTrigger value="rules" data-testid="tab-rules">
              <Layers className="w-3.5 h-3.5 mr-1.5" /> Kurallar
            </TabsTrigger>
            <TabsTrigger value="channels" data-testid="tab-channels">
              <Globe className="w-3.5 h-3.5 mr-1.5" /> Kanallar
            </TabsTrigger>
            <TabsTrigger value="promotions" data-testid="tab-promotions">
              <Tag className="w-3.5 h-3.5 mr-1.5" /> Promosyonlar
            </TabsTrigger>
            <TabsTrigger value="guardrails" data-testid="tab-guardrails">
              <Shield className="w-3.5 h-3.5 mr-1.5" /> Guardrails
            </TabsTrigger>
          </TabsList>

          <TabsContent value="simulator" className="mt-4">
            <PriceSimulator metadata={metadata} onSimulated={() => { loadCacheStats(); if (showTelemetry) loadTelemetry(); }} />
          </TabsContent>
          <TabsContent value="rules" className="mt-4">
            <DistributionRulesTab />
          </TabsContent>
          <TabsContent value="channels" className="mt-4">
            <ChannelsTab />
          </TabsContent>
          <TabsContent value="promotions" className="mt-4">
            <PromotionsTab />
          </TabsContent>
          <TabsContent value="guardrails" className="mt-4">
            <GuardrailsTab />
          </TabsContent>
        </Tabs>
      </div>
    </TooltipProvider>
  );
}
