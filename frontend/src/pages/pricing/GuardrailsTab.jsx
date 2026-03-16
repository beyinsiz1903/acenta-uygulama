import React, { useState, useCallback, useEffect } from "react";
import { Plus, Trash2, Shield, Loader2 } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "../../components/ui/select";
import { toast } from "sonner";
import { pricingApi } from "./lib/pricingApi";
import { GUARDRAIL_LABELS, GUARDRAIL_ICONS, fmtCurrency } from "./lib/pricingConstants";

export function GuardrailsTab() {
  const [guardrails, setGuardrails] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", guardrail_type: "min_margin_pct", value: 5, scope: {} });
  const [scopeStr, setScopeStr] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await pricingApi("/guardrails");
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
    await pricingApi("/guardrails", { method: "POST", body: JSON.stringify({ ...form, value: parseFloat(form.value), scope }) });
    toast.success("Guardrail eklendi");
    setShowAdd(false);
    setScopeStr("");
    load();
  };

  const remove = async (guardrailId) => {
    await pricingApi(`/guardrails/${guardrailId}`, { method: "DELETE" });
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
