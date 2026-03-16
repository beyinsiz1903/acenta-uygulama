import React, { useState, useCallback, useEffect } from "react";
import { Plus, Trash2, ToggleLeft, ToggleRight, Loader2 } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "../../components/ui/select";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../../components/ui/table";
import { toast } from "sonner";
import { pricingApi } from "./lib/pricingApi";

const PROMO_LABELS = {
  early_booking: "Erken Rezervasyon",
  flash_sale: "Flash Sale",
  campaign_discount: "Kampanya",
  fixed_price_override: "Sabit Fiyat",
};

export function PromotionsTab() {
  const [promos, setPromos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", promo_type: "campaign_discount", discount_pct: 10, promo_code: "", scope: {} });
  const [scopeStr, setScopeStr] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const data = await pricingApi("/promotions");
    setPromos(Array.isArray(data) ? data : []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    let scope = {};
    try { scope = scopeStr ? JSON.parse(scopeStr) : {}; } catch { toast.error("Scope JSON hatali"); return; }
    await pricingApi("/promotions", { method: "POST", body: JSON.stringify({ ...form, discount_pct: parseFloat(form.discount_pct), scope }) });
    toast.success("Promosyon eklendi");
    setShowAdd(false);
    load();
  };

  const remove = async (ruleId) => {
    await pricingApi(`/promotions/${ruleId}`, { method: "DELETE" });
    toast.success("Promosyon silindi");
    load();
  };

  const toggle = async (ruleId, active) => {
    await pricingApi(`/promotions/${ruleId}/toggle?active=${!active}`, { method: "POST" });
    load();
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
