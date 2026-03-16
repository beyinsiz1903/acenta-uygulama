import React, { useState, useCallback, useEffect } from "react";
import {
  Calculator, Layers, Tag, Zap, Plus, Trash2, ToggleLeft,
  ToggleRight, RefreshCw, Loader2, ArrowRight, TrendingUp,
  DollarSign, Percent, Globe, Building2, Store, Users,
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

const CHANNEL_ICONS = {
  b2b: Building2,
  b2c: Store,
  corporate: Globe,
  whitelabel: Users,
};

const CHANNEL_COLORS = {
  b2b: "bg-blue-50 text-blue-700 border-blue-200",
  b2c: "bg-emerald-50 text-emerald-700 border-emerald-200",
  corporate: "bg-violet-50 text-violet-700 border-violet-200",
  whitelabel: "bg-amber-50 text-amber-700 border-amber-200",
};

// ═══════════════════ STAT CARDS ═══════════════════

function StatCards({ stats }) {
  const cards = [
    { label: "Toplam Kural", value: stats.total_rules || 0, icon: Layers, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Aktif Kural", value: stats.active_rules || 0, icon: Zap, color: "text-emerald-600", bg: "bg-emerald-50" },
    { label: "Kanal", value: stats.channel_count || 0, icon: Globe, color: "text-violet-600", bg: "bg-violet-50" },
    { label: "Aktif Promosyon", value: stats.active_promotions || 0, icon: Tag, color: "text-amber-600", bg: "bg-amber-50" },
  ];
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4" data-testid="pricing-stat-cards">
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

// ═══════════════════ PRICE SIMULATOR ═══════════════════

function PriceSimulator({ metadata }) {
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
    } catch (e) {
      toast.error("Simülasyon hatası");
    }
    setLoading(false);
  };

  const set = (k, v) => setForm(prev => ({ ...prev, [k]: v }));

  return (
    <div className="grid lg:grid-cols-2 gap-6" data-testid="price-simulator">
      {/* Input */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2"><Calculator className="w-4 h-4" /> Fiyat Girdileri</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
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
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2"><TrendingUp className="w-4 h-4" /> Fiyat Sonucu</CardTitle>
        </CardHeader>
        <CardContent>
          {!result ? (
            <div className="flex flex-col items-center justify-center h-48 text-muted-foreground">
              <Calculator className="w-10 h-10 mb-2 opacity-30" />
              <p className="text-sm">Simülasyon için parametreleri girin</p>
            </div>
          ) : (
            <div className="space-y-3" data-testid="sim-result">
              {/* Pipeline visualization */}
              <div className="space-y-2">
                <PipelineRow label="Supplier Fiyat" amount={result.supplier_price} currency={result.supplier_currency} type="base" />
                <PipelineArrow />
                <PipelineRow label={`Baz Markup (%${result.base_markup_pct})`} amount={result.base_markup_amount} sign="+" type="markup" />
                <PipelineArrow />
                <PipelineRow label={`Kanal (${form.channel.toUpperCase()}) %${result.channel_adjustment_pct}`} amount={result.channel_adjustment_amount} sign={result.channel_adjustment_pct >= 0 ? "+" : ""} type="channel" />
                <PipelineArrow />
                {result.promotion_discount_pct > 0 && (
                  <>
                    <PipelineRow label={`Promosyon (-%${result.promotion_discount_pct})`} amount={-result.promotion_discount_amount} sign="-" type="promo" />
                    <PipelineArrow />
                  </>
                )}
                <PipelineRow label={`Vergi (%${result.tax_rate})`} amount={result.tax_amount} sign="+" type="tax" />
                <PipelineArrow />
                {result.fx_rate !== 1 && (
                  <>
                    <PipelineRow label={`Kur (${result.fx_rate})`} amount={null} type="fx" />
                    <PipelineArrow />
                  </>
                )}
                <div className="bg-slate-900 text-white rounded-lg p-3 flex justify-between items-center">
                  <span className="font-semibold">Satis Fiyati</span>
                  <span className="text-lg font-bold" data-testid="sim-sell-price">{fmtCurrency(result.sell_price, result.sell_currency)}</span>
                </div>
              </div>
              {/* Margin */}
              <div className="grid grid-cols-3 gap-2 pt-2">
                <div className="text-center p-2 bg-emerald-50 rounded-lg">
                  <p className="text-xs text-emerald-600">Marj</p>
                  <p className="font-bold text-emerald-700">{fmtCurrency(result.margin, result.sell_currency)}</p>
                </div>
                <div className="text-center p-2 bg-blue-50 rounded-lg">
                  <p className="text-xs text-blue-600">Marj %</p>
                  <p className="font-bold text-blue-700">%{result.margin_pct}</p>
                </div>
                <div className="text-center p-2 bg-violet-50 rounded-lg">
                  <p className="text-xs text-violet-600">Gece Basina</p>
                  <p className="font-bold text-violet-700">{fmtCurrency(result.per_night, result.sell_currency)}</p>
                </div>
              </div>
              {/* Applied rules */}
              {result.applied_rules?.length > 0 && (
                <div className="pt-2">
                  <p className="text-xs font-medium text-muted-foreground mb-1">Uygulanan Kurallar</p>
                  <div className="space-y-1">
                    {result.applied_rules.map((r, i) => (
                      <div key={i} className="flex items-center gap-2 text-xs">
                        <Badge variant="outline" className="text-[10px]">{r.stage}</Badge>
                        <span className="text-muted-foreground">{r.rule_id}</span>
                        <span className="ml-auto font-mono">%{r.value}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function PipelineRow({ label, amount, sign = "", type }) {
  const colors = {
    base: "bg-slate-50 border-slate-200",
    markup: "bg-blue-50 border-blue-200",
    channel: "bg-violet-50 border-violet-200",
    promo: "bg-amber-50 border-amber-200",
    tax: "bg-gray-50 border-gray-200",
    fx: "bg-teal-50 border-teal-200",
  };
  return (
    <div className={`rounded-lg border p-2.5 flex justify-between items-center ${colors[type] || ""}`}>
      <span className="text-sm">{label}</span>
      {amount != null && <span className="font-mono text-sm font-medium">{sign}{amount >= 0 ? "+" : ""}{amount?.toFixed?.(2)}</span>}
    </div>
  );
}

function PipelineArrow() {
  return <div className="flex justify-center"><ArrowRight className="w-3 h-3 text-muted-foreground rotate-90" /></div>;
}

// ═══════════════════ DISTRIBUTION RULES ═══════════════════

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

// ═══════════════════ CHANNEL CONFIGS ═══════════════════

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

// ═══════════════════ PROMOTIONS ═══════════════════

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

// ═══════════════════ MAIN PAGE ═══════════════════

export default function PricingEnginePage() {
  const [stats, setStats] = useState({});
  const [metadata, setMetadata] = useState(null);
  const [activeTab, setActiveTab] = useState("simulator");

  useEffect(() => {
    api("/dashboard").then(setStats).catch(() => {});
    api("/metadata").then(setMetadata).catch(() => {});
  }, []);

  return (
    <div className="space-y-6" data-testid="pricing-engine-page">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">Pricing & Distribution Engine</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Supplier fiyatlarini kanal, acente ve promosyon kurallariyla donusturun
        </p>
      </div>

      <StatCards stats={stats} />

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
        </TabsList>

        <TabsContent value="simulator" className="mt-4">
          <PriceSimulator metadata={metadata} />
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
      </Tabs>
    </div>
  );
}
