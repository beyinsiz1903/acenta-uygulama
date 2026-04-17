import React, { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  FileText, Plus, Trash2, Loader2, AlertTriangle, CheckCircle2, X, Clock, Ban, RefreshCw,
} from "lucide-react";
import { api, apiErrorMessage } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Input } from "../../components/ui/input";
import { Label } from "../../components/ui/label";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from "../../components/ui/select";

const PAYMENT_TERMS = [
  { value: "prepaid", label: "Ön Ödemeli" },
  { value: "on_arrival", label: "Girişte Tahsilat" },
  { value: "net_7", label: "Net 7 gün" },
  { value: "net_15", label: "Net 15 gün" },
  { value: "net_30", label: "Net 30 gün" },
];

const CURRENCIES = ["TRY", "EUR", "USD"];

const STATUS_LABELS = {
  pending: { label: "Bekliyor", cls: "bg-amber-100 text-amber-800 border-amber-200", Icon: Clock },
  approved: { label: "Aktif", cls: "bg-emerald-100 text-emerald-800 border-emerald-200", Icon: CheckCircle2 },
  rejected: { label: "Reddedildi", cls: "bg-red-100 text-red-800 border-red-200", Icon: Ban },
  terminated: { label: "Feshedildi", cls: "bg-zinc-100 text-zinc-700 border-zinc-200", Icon: Ban },
  expired: { label: "Süresi Doldu", cls: "bg-zinc-100 text-zinc-700 border-zinc-200", Icon: Clock },
};

function StatusBadge({ status }) {
  const meta = STATUS_LABELS[status] || { label: status || "-", cls: "bg-gray-100 text-gray-700 border-gray-200", Icon: FileText };
  const Icon = meta.Icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-xs font-medium rounded-full border ${meta.cls}`}>
      <Icon className="h-3 w-3" /> {meta.label}
    </span>
  );
}

function Banner({ kind, children, onClose }) {
  const palette = kind === "error"
    ? "bg-red-50 border-red-200 text-red-800"
    : "bg-emerald-50 border-emerald-200 text-emerald-800";
  const Icon = kind === "error" ? AlertTriangle : CheckCircle2;
  return (
    <div className={`flex items-start gap-2 p-3 rounded border ${palette}`}>
      <Icon size={18} className="mt-0.5 shrink-0" />
      <div className="flex-1 text-sm whitespace-pre-line">{children}</div>
      {onClose && <button onClick={onClose} className="opacity-60 hover:opacity-100"><X size={16} /></button>}
    </div>
  );
}

function fmtDate(iso) {
  if (!iso) return "-";
  try { return new Date(iso).toLocaleDateString("tr-TR"); } catch { return iso; }
}

function ContractCard({ contract, onWithdraw, withdrawing }) {
  const cp = contract.cancellation_policy || {};
  const paymentLabel = PAYMENT_TERMS.find(p => p.value === contract.payment_terms)?.label || contract.payment_terms || "-";
  const isPending = contract.status === "pending";
  const isApproved = contract.status === "approved";
  return (
    <Card className={isApproved ? "border-emerald-200" : ""}>
      <CardHeader className="pb-2">
        <div className="flex items-start justify-between gap-2">
          <div>
            <CardTitle className="text-sm font-semibold flex items-center gap-2">
              <FileText className="h-4 w-4 text-muted-foreground" />
              {contract.contract_code || contract.id}
            </CardTitle>
            <div className="text-xs text-muted-foreground mt-0.5">
              {contract.target_hotel_name || contract.hotel_name || `Tenant: ${contract.tenant_id}`}
            </div>
          </div>
          <StatusBadge status={contract.status} />
        </div>
      </CardHeader>
      <CardContent className="text-xs space-y-2">
        <div className="grid grid-cols-2 gap-2">
          <div><span className="text-muted-foreground">Komisyon:</span> <strong>%{contract.commission_pct ?? "-"}</strong></div>
          <div><span className="text-muted-foreground">Ödeme:</span> <strong>{paymentLabel}</strong></div>
          <div><span className="text-muted-foreground">Geçerlilik:</span> <strong>{fmtDate(contract.valid_from)} → {fmtDate(contract.valid_to)}</strong></div>
          <div><span className="text-muted-foreground">Para Birimi:</span> <strong>{contract.currency || "TRY"}</strong></div>
        </div>
        <div className="text-muted-foreground">
          İptal: ücretsiz {cp.free_until_days_before ?? 0}g öncesine kadar, sonrası %{cp.penalty_pct ?? 0} ceza, no-show %{cp.no_show_penalty_pct ?? 100}
        </div>
        {Array.isArray(contract.allowed_room_types) && contract.allowed_room_types.length > 0 && (
          <div><span className="text-muted-foreground">Oda tipleri:</span> {contract.allowed_room_types.join(", ")}</div>
        )}
        {contract.special_terms && (
          <div className="p-2 bg-muted/50 rounded text-xs whitespace-pre-line"><strong>Özel şartlar:</strong> {contract.special_terms}</div>
        )}
        {contract.decision_notes && (
          <div className="p-2 bg-muted/50 rounded text-xs"><strong>Otelci notu:</strong> {contract.decision_notes}</div>
        )}
        <div className="flex items-center justify-between pt-1">
          <div className="text-2xs text-muted-foreground">
            Teklif: {fmtDate(contract.proposed_at)} {contract.decided_at && `• Karar: ${fmtDate(contract.decided_at)}`}
          </div>
          {isPending && (
            <Button
              size="sm" variant="outline"
              onClick={() => onWithdraw(contract)}
              disabled={withdrawing}
              className="h-7 text-xs"
            >
              {withdrawing ? <Loader2 className="h-3 w-3 animate-spin mr-1" /> : <Trash2 className="h-3 w-3 mr-1" />}
              Geri Çek
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
}

const EMPTY_FORM = {
  tenant_id: "",
  commission_pct: 15,
  cancellation_policy: { free_until_days_before: 7, penalty_pct: 50, no_show_penalty_pct: 100 },
  payment_terms: "on_arrival",
  valid_from: "",
  valid_to: "",
  currency: "TRY",
  allowed_room_types: "",
  special_terms: "",
};

function ProposeDialog({ open, onClose, onSubmit, submitting, error, prefillTenantId, prefillHotelName }) {
  const [form, setForm] = useState(EMPTY_FORM);
  const [localErr, setLocalErr] = useState("");

  React.useEffect(() => {
    if (open) {
      const today = new Date().toISOString().slice(0, 10);
      const oneYear = new Date(Date.now() + 365 * 24 * 3600 * 1000).toISOString().slice(0, 10);
      setForm({ ...EMPTY_FORM, tenant_id: prefillTenantId || "", valid_from: today, valid_to: oneYear });
      setLocalErr("");
    }
  }, [open, prefillTenantId]);

  if (!open) return null;

  const setCP = (k, v) => setForm(f => ({ ...f, cancellation_policy: { ...f.cancellation_policy, [k]: v } }));
  const submit = (e) => {
    e.preventDefault();
    setLocalErr("");
    if (!form.valid_from || !form.valid_to || form.valid_to <= form.valid_from) {
      setLocalErr("Geçerlilik bitiş tarihi başlangıçtan büyük olmalı.");
      return;
    }
    const payload = {
      tenant_id: form.tenant_id.trim(),
      commission_pct: Number(form.commission_pct),
      cancellation_policy: {
        free_until_days_before: Number(form.cancellation_policy.free_until_days_before),
        penalty_pct: Number(form.cancellation_policy.penalty_pct),
        no_show_penalty_pct: Number(form.cancellation_policy.no_show_penalty_pct),
      },
      payment_terms: form.payment_terms,
      valid_from: form.valid_from,
      valid_to: form.valid_to,
      currency: form.currency,
      allowed_room_types: form.allowed_room_types
        ? form.allowed_room_types.split(",").map(s => s.trim()).filter(Boolean)
        : [],
      special_terms: form.special_terms.trim() || null,
    };
    onSubmit(payload);
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-50 p-4 overflow-y-auto">
      <div className="bg-background rounded-lg shadow-xl w-full max-w-2xl my-8">
        <div className="flex items-center justify-between p-4 border-b">
          <h3 className="text-base font-semibold flex items-center gap-2">
            <Plus className="h-4 w-4" /> Yeni Sözleşme Teklifi
          </h3>
          <button onClick={onClose} className="opacity-60 hover:opacity-100"><X size={18} /></button>
        </div>
        <form onSubmit={submit} className="p-4 space-y-4">
          {(error || localErr) && <Banner kind="error">{localErr || error}</Banner>}
          {prefillHotelName && (
            <div className="text-sm bg-muted p-2 rounded">
              Hedef otel: <strong>{prefillHotelName}</strong>
            </div>
          )}
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1.5 md:col-span-2">
              <Label className="text-xs">Otel Tenant ID *</Label>
              <Input
                value={form.tenant_id}
                onChange={e => setForm(f => ({ ...f, tenant_id: e.target.value }))}
                placeholder="Otelcinin size verdiği UUID"
                required
                disabled={!!prefillTenantId}
              />
              <p className="text-2xs text-muted-foreground">Bu ID'yi otelden temin edin (Syroce PMS Tenant ID).</p>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Komisyon (%) *</Label>
              <Input type="number" step="0.1" min="0" max="100"
                value={form.commission_pct}
                onChange={e => setForm(f => ({ ...f, commission_pct: e.target.value }))} required />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Ödeme Vadesi *</Label>
              <Select value={form.payment_terms} onValueChange={v => setForm(f => ({ ...f, payment_terms: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {PAYMENT_TERMS.map(p => <SelectItem key={p.value} value={p.value}>{p.label}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Geçerlilik Başlangıç *</Label>
              <Input type="date" value={form.valid_from} onChange={e => setForm(f => ({ ...f, valid_from: e.target.value }))} required />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Geçerlilik Bitiş *</Label>
              <Input type="date" value={form.valid_to} onChange={e => setForm(f => ({ ...f, valid_to: e.target.value }))} required />
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">Para Birimi</Label>
              <Select value={form.currency} onValueChange={v => setForm(f => ({ ...f, currency: v }))}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  {CURRENCIES.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-1.5">
              <Label className="text-xs">İzinli Oda Tipleri</Label>
              <Input
                value={form.allowed_room_types}
                onChange={e => setForm(f => ({ ...f, allowed_room_types: e.target.value }))}
                placeholder="standard, deluxe (boş = hepsi)"
              />
            </div>
          </div>

          <div className="border rounded p-3 space-y-2">
            <div className="text-xs font-semibold">İptal Politikası</div>
            <div className="grid gap-3 md:grid-cols-3">
              <div className="space-y-1.5">
                <Label className="text-xs">Ücretsiz iptal (gün öncesi)</Label>
                <Input type="number" min="0" value={form.cancellation_policy.free_until_days_before}
                  onChange={e => setCP("free_until_days_before", e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">Geç iptal cezası (%)</Label>
                <Input type="number" step="0.1" min="0" max="100" value={form.cancellation_policy.penalty_pct}
                  onChange={e => setCP("penalty_pct", e.target.value)} />
              </div>
              <div className="space-y-1.5">
                <Label className="text-xs">No-show cezası (%)</Label>
                <Input type="number" step="0.1" min="0" max="100" value={form.cancellation_policy.no_show_penalty_pct}
                  onChange={e => setCP("no_show_penalty_pct", e.target.value)} />
              </div>
            </div>
          </div>

          <div className="space-y-1.5">
            <Label className="text-xs">Özel Şartlar (markdown)</Label>
            <textarea
              className="w-full min-h-[80px] rounded border bg-background p-2 text-sm"
              value={form.special_terms}
              onChange={e => setForm(f => ({ ...f, special_terms: e.target.value }))}
              placeholder="Yüksek sezon istisnaları, grup indirimleri vb."
            />
          </div>

          <div className="flex justify-end gap-2 pt-2 border-t">
            <Button type="button" variant="outline" onClick={onClose} disabled={submitting}>Vazgeç</Button>
            <Button type="submit" disabled={submitting || !form.tenant_id || !form.valid_from || !form.valid_to}>
              {submitting ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Plus className="h-4 w-4 mr-1" />}
              Teklif Gönder
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default function MarketplaceContractsPage() {
  const qc = useQueryClient();
  const [searchParams, setSearchParams] = useSearchParams();
  const [tab, setTab] = useState("active");
  const [proposeOpen, setProposeOpen] = useState(false);
  const [proposeError, setProposeError] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [withdrawingId, setWithdrawingId] = useState(null);
  const [prefill, setPrefill] = useState({ tenant_id: "", hotel_name: "" });

  // URL params: ?propose=1&tenant_id=...&hotel_name=...
  useEffect(() => {
    if (searchParams.get("propose") === "1") {
      setPrefill({
        tenant_id: searchParams.get("tenant_id") || "",
        hotel_name: searchParams.get("hotel_name") || "",
      });
      setProposeError("");
      setProposeOpen(true);
      // Clear URL params so dialog doesn't reopen on refetch / back nav
      const next = new URLSearchParams(searchParams);
      next.delete("propose");
      next.delete("tenant_id");
      next.delete("hotel_name");
      setSearchParams(next, { replace: true });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const { data, isLoading, refetch, isFetching } = useQuery({
    queryKey: ["marketplace-contracts"],
    queryFn: () => api.get("/syroce-marketplace/contracts").then(r => r.data),
  });

  const all = useMemo(() => {
    const items = data?.items || data?.contracts || (Array.isArray(data) ? data : []);
    return Array.isArray(items) ? items : [];
  }, [data]);

  const buckets = useMemo(() => ({
    pending: all.filter(c => c.status === "pending"),
    active: all.filter(c => c.status === "approved"),
    history: all.filter(c => ["rejected", "terminated", "expired"].includes(c.status)),
  }), [all]);

  const proposeMut = useMutation({
    mutationFn: (payload) => api.post("/syroce-marketplace/contracts/propose", payload).then(r => r.data),
    onSuccess: () => {
      setSuccess("Sözleşme teklifi gönderildi. Otelci onayı bekleniyor.");
      setProposeOpen(false);
      setProposeError("");
      qc.invalidateQueries({ queryKey: ["marketplace-contracts"] });
      setTab("pending");
    },
    onError: (err) => setProposeError(apiErrorMessage(err) || "Teklif gönderilemedi."),
  });

  const withdrawMut = useMutation({
    mutationFn: (id) => api.delete(`/syroce-marketplace/contracts/${id}`).then(r => r.data),
    onMutate: (id) => setWithdrawingId(id),
    onSettled: () => setWithdrawingId(null),
    onSuccess: () => {
      setSuccess("Teklif geri çekildi.");
      qc.invalidateQueries({ queryKey: ["marketplace-contracts"] });
    },
    onError: (err) => setError(apiErrorMessage(err) || "Geri çekme başarısız."),
  });

  const renderList = (list, emptyMsg) => {
    if (list.length === 0) {
      return (
        <div className="text-center py-12 text-sm text-muted-foreground">
          <FileText className="h-8 w-8 mx-auto mb-2 opacity-40" />
          {emptyMsg}
        </div>
      );
    }
    return (
      <div className="grid gap-3 md:grid-cols-2">
        {list.map(c => (
          <ContractCard
            key={c.id || c.contract_code}
            contract={c}
            onWithdraw={(ct) => withdrawMut.mutate(ct.id)}
            withdrawing={withdrawingId === c.id}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="space-y-4 p-4">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-xl font-semibold flex items-center gap-2">
            <FileText className="h-5 w-5" /> Sözleşmelerim
          </h1>
          <p className="text-sm text-muted-foreground">
            Otellerle yaptığınız anlaşmaları yönetin. Arama ve rezervasyon yalnızca onaylı sözleşmelerde mümkündür.
          </p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()} disabled={isFetching}>
            <RefreshCw className={`h-4 w-4 mr-1 ${isFetching ? "animate-spin" : ""}`} /> Yenile
          </Button>
          <Button size="sm" onClick={() => { setProposeError(""); setProposeOpen(true); }}>
            <Plus className="h-4 w-4 mr-1" /> Yeni Teklif
          </Button>
        </div>
      </div>

      {error && <Banner kind="error" onClose={() => setError("")}>{error}</Banner>}
      {success && <Banner kind="success" onClose={() => setSuccess("")}>{success}</Banner>}

      {isLoading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" /></div>
      ) : (
        <Tabs value={tab} onValueChange={setTab}>
          <TabsList>
            <TabsTrigger value="active">Aktif Anlaşmalar ({buckets.active.length})</TabsTrigger>
            <TabsTrigger value="pending">Bekleyen Tekliflerim ({buckets.pending.length})</TabsTrigger>
            <TabsTrigger value="history">Geçmiş ({buckets.history.length})</TabsTrigger>
          </TabsList>
          <TabsContent value="active" className="mt-4">
            {renderList(buckets.active, "Aktif anlaşmanız yok. Yeni teklif göndererek başlayın.")}
          </TabsContent>
          <TabsContent value="pending" className="mt-4">
            {renderList(buckets.pending, "Bekleyen teklifiniz yok.")}
          </TabsContent>
          <TabsContent value="history" className="mt-4">
            {renderList(buckets.history, "Geçmiş kayıt yok.")}
          </TabsContent>
        </Tabs>
      )}

      <ProposeDialog
        open={proposeOpen}
        onClose={() => { setProposeOpen(false); setPrefill({ tenant_id: "", hotel_name: "" }); }}
        onSubmit={(p) => proposeMut.mutate(p)}
        submitting={proposeMut.isPending}
        error={proposeError}
        prefillTenantId={prefill.tenant_id}
        prefillHotelName={prefill.hotel_name}
      />
    </div>
  );
}
