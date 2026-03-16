import React, { useState } from "react";
import { Calculator, TrendingUp, Loader2 } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "../../components/ui/select";
import { toast } from "sonner";
import { pricingApi } from "./lib/pricingApi";
import { fmtCurrency } from "./lib/pricingConstants";
import { PipelineExplainer } from "./PipelineExplainer";
import { TraceBar } from "./TraceBar";
import { GuardrailWarnings } from "./GuardrailWarnings";
import { RulePrecedenceViewer } from "./RulePrecedenceViewer";

export function PricingSimulatorTab({ metadata, onSimulated }) {
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
      const data = await pricingApi("/simulate", {
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
            <TraceBar result={result} />
            <GuardrailWarnings warnings={result.guardrail_warnings} passed={result.guardrails_passed} />
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
            <RulePrecedenceViewer evaluatedRules={result.evaluated_rules} />
          </>
        )}
      </div>
    </div>
  );
}
