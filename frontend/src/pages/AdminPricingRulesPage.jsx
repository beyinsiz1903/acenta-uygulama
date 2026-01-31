import React, { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Label } from "../components/ui/label";
import { Badge } from "../components/ui/badge";
import { Switch } from "../components/ui/switch";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { AlertCircle, Loader2, Trash2, Pencil } from "lucide-react";

function FieldError({ text }) {
  if (!text) return null;
  return (
    <div className="mt-2 flex items-start gap-2 rounded-md border border-destructive/30 bg-destructive/5 p-2 text-[11px] text-destructive">
      <AlertCircle className="h-4 w-4 mt-0.5" />
      <div>{text}</div>
    </div>
  );
}

const RULE_TYPES = [
  { value: "markup_pct", label: "Markup %" },
  { value: "markup_fixed", label: "Markup Sabit" },
  { value: "commission_pct", label: "Komisyon %" },
  { value: "commission_fixed", label: "Komisyon Sabit" },
];

function formatDate(value) {
  if (!value) return "-";
  try {
    const d = new Date(value);
    if (Number.isNaN(d.getTime())) return String(value);
    return d.toLocaleString("tr-TR");
  } catch {
    return String(value);
  }
}

function ValidityCell({ from, to }) {
  if (!from && !to) return <span className="text-xs text-muted-foreground">Sonsuz</span>;
  return (
    <div className="flex flex-col text-[11px]">
      <span>{from ? formatDate(from) : "-"}</span>
      <span className="text-muted-foreground">{to ? formatDate(to) : "-"}</span>
    </div>
  );
}

function StackableBadge({ stackable }) {
  if (!stackable) {
    return <Badge variant="outline">Hayır</Badge>;
  }
  return <Badge variant="secondary">Evet</Badge>;
}

function usePricingRules(initialFilters) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState(initialFilters);

  const load = async () => {
    setLoading(true);
    setError("");
    try {
      const params = {};
      if (filters.active_only) params.active_only = true;
      if (filters.supplier) params.supplier = filters.supplier.trim();
      if (filters.rule_type) params.rule_type = filters.rule_type;
      const res = await api.get("/pricing/rules", { params });
      setItems(res.data || []);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters.active_only, filters.supplier, filters.rule_type]);

  return {
    items,
    loading,
    error,
    filters,
    setFilters,
    reload: load,
  };
}

function RuleFormDialog({ open, onOpenChange, mode, initial, onSaved }) {
  const isEdit = mode === "edit";
  const [ruleType, setRuleType] = useState(initial?.rule_type || "markup_pct");
  const [value, setValue] = useState(initial?.value || "10.00");
  const [priority, setPriority] = useState(initial?.priority ?? 100);
  const [supplier, setSupplier] = useState(initial?.supplier || "");
  const [stackable, setStackable] = useState(initial?.stackable ?? true);
  const [validFrom, setValidFrom] = useState(initial?.valid_from || "");
  const [validTo, setValidTo] = useState(initial?.valid_to || "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (open) {
      setRuleType(initial?.rule_type || "markup_pct");
      setValue(initial?.value || "10.00");
      setPriority(initial?.priority ?? 100);
      setSupplier(initial?.supplier || "");
      setStackable(initial?.stackable ?? true);
      setValidFrom(initial?.valid_from || "");
      setValidTo(initial?.valid_to || "");
      setError("");
    }
  }, [open, initial]);

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (saving) return;

    setSaving(true);
    setError("");
    try {
      const payload = {
        rule_type: ruleType,
        value: String(value || "0").trim(),
        priority: Number(priority || 0),
        supplier: supplier.trim() || null,
        stackable,
        valid_from: validFrom || null,
        valid_to: validTo || null,
      };

      if (isEdit && initial?.id) {
        await api.patch(`/pricing/rules/${initial.id}`, payload);
      } else {
        await api.post("/pricing/rules", payload);
      }
      if (onSaved) onSaved();
      onOpenChange(false);
    } catch (err) {
      setError(apiErrorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-base">
            {isEdit ? "Fiyat Kuralını Düzenle" : "Yeni Fiyat Kuralı"}
          </DialogTitle>
        </DialogHeader>
        <form onSubmit={handleSubmit} className="space-y-3 text-[11px]">
          <FieldError text={error} />
          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label className="text-[11px]">Rule Type</Label>
              <select
                className="h-8 w-full rounded-md border bg-background px-2 text-xs"
                value={ruleType}
                onChange={(e) => setRuleType(e.target.value)}
              >
                {RULE_TYPES.map((rt) => (
                  <option key={rt.value} value={rt.value}>
                    {rt.label}
                  </option>
                ))}
              </select>
            </div>
            <div className="space-y-1">
              <Label className="text-[11px]">Değer</Label>
              <Input
                className="h-8 text-xs"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                placeholder="10.00"
              />
            </div>
          </div>

          <div className="grid grid-cols-3 gap-2">
            <div className="space-y-1">
              <Label className="text-[11px]">Öncelik (priority)</Label>
              <Input
                type="number"
                className="h-8 text-xs"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-[11px]">Supplier</Label>
              <Input
                className="h-8 text-xs"
                value={supplier}
                onChange={(e) => setSupplier(e.target.value)}
                placeholder="mock_v1"
              />
            </div>
            <div className="flex items-center gap-2 mt-5">
              <Switch
                id="stackable"
                checked={!!stackable}
                onCheckedChange={(val) => setStackable(val)}
              />
              <Label htmlFor="stackable" className="text-[11px]">
                Stackable
              </Label>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-2">
            <div className="space-y-1">
              <Label className="text-[11px]">Valid From</Label>
              <Input
                type="datetime-local"
                className="h-8 text-xs"
                value={validFrom || ""}
                onChange={(e) => setValidFrom(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <Label className="text-[11px]">Valid To</Label>
              <Input
                type="datetime-local"
                className="h-8 text-xs"
                value={validTo || ""}
                onChange={(e) => setValidTo(e.target.value)}
              />
            </div>
          </div>

          <DialogFooter className="mt-2 flex justify-end gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              className="h-8 text-xs"
              onClick={() => onOpenChange(false)}
            >
              Vazgeç
            </Button>
            <Button type="submit" size="sm" className="h-8 text-xs" disabled={saving}>
              {saving && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
              {isEdit ? "Kaydet" : "Oluştur"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}

export default function AdminPricingRulesPage() {
  const [activeOnly, setActiveOnly] = useState(true);
  const [supplierFilter, setSupplierFilter] = useState("");
  const [ruleTypeFilter, setRuleTypeFilter] = useState("");
  const [createOpen, setCreateOpen] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [selectedRule, setSelectedRule] = useState(null);
  const [deleteLoadingId, setDeleteLoadingId] = useState(null);

  const { items, loading, error, filters, setFilters, reload } = usePricingRules({
    active_only: activeOnly,
    supplier: supplierFilter,
    rule_type: ruleTypeFilter,
  });

  useEffect(() => {
    setFilters({ active_only: activeOnly, supplier: supplierFilter, rule_type: ruleTypeFilter });
  }, [activeOnly, supplierFilter, ruleTypeFilter, setFilters]);

  const handleDelete = async (rule) => {
    if (!window.confirm("Kural silinsin mi? Bu işlem geri alınamaz.")) return;
    setDeleteLoadingId(rule.id);
    try {
      await api.delete(`/pricing/rules/${rule.id}`);
      await reload();
    } catch (err) {
      // eslint-disable-next-line no-alert
      // Not: v1 için basit alert yeterli, ileride FriendlyError bileşeni ile değiştirilebilir.
      alert(apiErrorMessage(err));
    } finally {
      setDeleteLoadingId(null);
    }
  };

  const ruleTypeOptions = useMemo(() => [{ value: "", label: "Hepsi" }, ...RULE_TYPES], []);

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <div className="text-lg font-semibold">Pricing Kuralları</div>
          <div className="text-[11px] text-muted-foreground max-w-xl">
            Agentis tarzı B2B fiyatlandırma için kullanılan basit markup/komisyon kuralları. Priorite yüksekten düşüğe
            doğru uygulanır.
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Button
            size="sm"
            variant="outline"
            className="h-8 text-xs"
            onClick={() => reload()}
            disabled={loading}
          >
            {loading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
            Yenile
          </Button>
          <Button
            size="sm"
            className="h-8 text-xs"
            onClick={() => {
              setSelectedRule(null);
              setCreateOpen(true);
            }}
          >
            Yeni Kural
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/30 bg-destructive/5 px-3 py-2 text-[11px] text-destructive flex items-center gap-2">
          <AlertCircle className="h-4 w-4" />
          <span>{error}</span>
        </div>
      )}

      <div className="rounded-md border p-3 text-[11px] space-y-2">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-2">
            <Switch
              id="active_only"
              checked={activeOnly}
              onCheckedChange={(val) => setActiveOnly(val)}
            />
            <Label htmlFor="active_only" className="text-[11px]">
              Sadece aktif kurallar (validity penceresi içinde)
            </Label>
          </div>
          <div className="flex items-center gap-2">
            <Label className="text-[11px]">Rule Type</Label>
            <select
              className="h-8 rounded-md border bg-background px-2 text-xs"
              value={ruleTypeFilter}
              onChange={(e) => setRuleTypeFilter(e.target.value)}
            >
              {ruleTypeOptions.map((rt) => (
                <option key={rt.value} value={rt.value}>
                  {rt.label}
                </option>
              ))}
            </select>
          </div>
          <div className="flex items-center gap-2">
            <Label className="text-[11px]">Supplier</Label>
            <Input
              className="h-8 text-xs w-[160px]"
              placeholder="mock_v1"
              value={supplierFilter}
              onChange={(e) => setSupplierFilter(e.target.value)}
            />
          </div>
        </div>
      </div>

      <div className="rounded-md border overflow-hidden">
        <Table className="text-[11px]">
          <TableHeader>
            <TableRow className="bg-muted/40">
              <TableHead className="w-[110px]">Rule Type</TableHead>
              <TableHead>Değer</TableHead>
              <TableHead>Priority</TableHead>
              <TableHead>Supplier</TableHead>
              <TableHead>Tenant</TableHead>
              <TableHead>Validity</TableHead>
              <TableHead>Stackable</TableHead>
              <TableHead>Updated At</TableHead>
              <TableHead className="text-right">Actions</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {loading && (
              <TableRow>
                <TableCell colSpan={9} className="py-6 text-center text-muted-foreground">
                  <Loader2 className="h-4 w-4 mr-2 inline-block animate-spin" /> Yükleniyor...
                </TableCell>
              </TableRow>
            )}
            {!loading && items.length === 0 && (
              <TableRow>
                <TableCell colSpan={9} className="py-6 text-center text-muted-foreground">
                  Henüz fiyat kuralı tanımlı değil.
                </TableCell>
              </TableRow>
            )}
            {!loading &&
              items.map((r) => (
                <TableRow key={r.id}>
                  <TableCell className="font-mono">{r.rule_type}</TableCell>
                  <TableCell>
                    <span className="font-mono">{r.value}</span>
                  </TableCell>
                  <TableCell>{r.priority}</TableCell>
                  <TableCell>{r.supplier || <span className="text-muted-foreground">-</span>}</TableCell>
                  <TableCell>{r.tenant_id || <span className="text-muted-foreground">(org-genel)</span>}</TableCell>
                  <TableCell>
                    <ValidityCell from={r.valid_from} to={r.valid_to} />
                  </TableCell>
                  <TableCell>
                    <StackableBadge stackable={r.stackable} />
                  </TableCell>
                  <TableCell>{formatDate(r.updated_at)}</TableCell>
                  <TableCell className="text-right">
                    <div className="flex justify-end gap-1">
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="h-7 w-7"
                        onClick={() => {
                          setSelectedRule(r);
                          setEditOpen(true);
                        }}
                      >
                        <Pencil className="h-3 w-3" />
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="icon"
                        className="h-7 w-7 text-destructive border-destructive/40"
                        onClick={() => handleDelete(r)}
                        disabled={deleteLoadingId === r.id}
                      >
                        {deleteLoadingId === r.id ? (
                          <Loader2 className="h-3 w-3 animate-spin" />
                        ) : (
                          <Trash2 className="h-3 w-3" />
                        )}
                      </Button>
                    </div>
                  </TableCell>
                </TableRow>
              ))}
          </TableBody>
        </Table>
      </div>

      <RuleFormDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        mode="create"
        initial={null}
        onSaved={reload}
      />
      <RuleFormDialog
        open={editOpen}
        onOpenChange={setEditOpen}
        mode="edit"
        initial={selectedRule}
        onSaved={reload}
      />
    </div>
  );
}
