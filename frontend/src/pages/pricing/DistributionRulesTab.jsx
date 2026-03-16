import React, { useState, useCallback, useEffect } from "react";
import { Plus, Trash2, RefreshCw, Layers, Loader2 } from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "../../components/ui/select";
import { Table, TableHeader, TableBody, TableRow, TableHead, TableCell } from "../../components/ui/table";
import { toast } from "sonner";
import { pricingApi } from "./lib/pricingApi";

export function DistributionRulesTab() {
  const [rules, setRules] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ name: "", rule_category: "base_markup", value: 10, scope: {}, priority: 10 });
  const [scopeStr, setScopeStr] = useState("");

  const load = useCallback(async () => {
    setLoading(true);
    const data = await pricingApi("/distribution-rules");
    setRules(Array.isArray(data) ? data : []);
    setLoading(false);
  }, []);

  useEffect(() => { load(); }, [load]);

  const create = async () => {
    let scope = {};
    try { scope = scopeStr ? JSON.parse(scopeStr) : {}; } catch { toast.error("Scope JSON hatali"); return; }
    await pricingApi("/distribution-rules", { method: "POST", body: JSON.stringify({ ...form, scope, value: parseFloat(form.value), priority: parseInt(form.priority) }) });
    toast.success("Kural eklendi");
    setShowAdd(false);
    load();
  };

  const remove = async (ruleId) => {
    await pricingApi(`/distribution-rules/${ruleId}`, { method: "DELETE" });
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
