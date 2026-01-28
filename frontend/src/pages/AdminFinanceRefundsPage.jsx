import React, { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage, getUser } from "../lib/api";
import { toast } from "../components/ui/sonner";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../components/ui/table";
import { Badge } from "../components/ui/badge";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "../components/ui/dialog";

import { Loader2, AlertCircle, Clipboard, Trash2, Clock } from "lucide-react";

function StatusBadge({ status }) {
  if (!status) return <Badge variant="outline">-</Badge>;

  switch (status) {
    case "open":
      return <Badge variant="outline">Açık</Badge>;
    case "pending_approval_1":
    case "pending_approval":
      return <Badge variant="outline">1. onay bekliyor</Badge>;
    case "pending_approval_2":
      return <Badge variant="outline">2. onay bekliyor</Badge>;
    case "approved":
      return <Badge variant="secondary">Onaylandı</Badge>;
    case "paid":
      return <Badge variant="secondary">Ödendi</Badge>;
    case "rejected":
      return (
        <Badge variant="destructive" className="gap-1">
          Reddedildi
        </Badge>
      );
    case "closed":
      return <Badge variant="secondary">Kapalı</Badge>;
    default:
      return <Badge variant="outline">{status}</Badge>;
  }
}

function statusBadge(status) {
  if (!status) return <Badge variant="outline">-</Badge>;

  switch (status) {
    case "open":
      return <Badge variant="outline" className="text-[10px] px-1 py-0">Açık</Badge>;
    case "in_progress":
      return <Badge variant="default" className="text-[10px] px-1 py-0">Devam ediyor</Badge>;
    case "done":
      return <Badge variant="secondary" className="text-[10px] px-1 py-0">Tamamlandı</Badge>;
    case "cancelled":
      return <Badge variant="destructive" className="text-[10px] px-1 py-0">İptal</Badge>;
    default:
      return <Badge variant="outline" className="text-[10px] px-1 py-0">{status}</Badge>;
  }
}

function priorityBadge(priority) {
  if (!priority) return null;

  switch (priority) {
    case "high":
      return <Badge variant="destructive" className="text-[10px] px-1 py-0">Yüksek</Badge>;
    case "medium":
      return <Badge variant="default" className="text-[10px] px-1 py-0">Orta</Badge>;
    case "low":
      return <Badge variant="outline" className="text-[10px] px-1 py-0">Düşük</Badge>;
    default:
      return <Badge variant="outline" className="text-[10px] px-1 py-0">{priority}</Badge>;
  }
}

function RefundQueueList({
  items,
  statusFilter,
  limit,
  onChangeStatus,
  onChangeLimit,
  selectedCaseId,
  onSelectCase,
  selectedCaseIds,
  onToggleCase,
  onToggleAllOnPage,
}) {
  const selectAllRef = React.useRef(null);
  const idsOnPage = React.useMemo(() => items.map((it) => it.case_id), [items]);
  const selectedSet = React.useMemo(() => new Set(selectedCaseIds), [selectedCaseIds]);
  const selectedOnPage = idsOnPage.filter((id) => selectedSet.has(id)).length;

  useEffect(() => {
    if (!selectAllRef.current) return;
    selectAllRef.current.indeterminate =
      selectedOnPage > 0 && selectedOnPage < items.length;
  }, [selectedOnPage, items.length]);

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="text-sm font-medium">İade Kuyruğu</CardTitle>
            <p className="text-[10px] text-muted-foreground mt-0.5">
              Seç kutusu: bu sayfadaki kayıtları seçer (tüm filtrelenmiş kayıtları değil).
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Ops ekibi için açık iade case listesi.
            </p>
          </div>
          <div className="flex items-center gap-3">
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Durum</div>
              <select
                className="h-8 rounded-md border bg-background px-2 text-xs"
                value={statusFilter}
                onChange={(e) => onChangeStatus(e.target.value)}
              >
                <option value="all">Tümü</option>
                <option value="open">Açık / Beklemede</option>
                <option value="closed">Kapalı</option>
              </select>
            </div>
            <div className="space-y-1">
              <div className="text-xs text-muted-foreground">Limit</div>
              <Input
                className="h-8 w-20 text-xs"
                type="number"
                min={1}
                max={200}
                value={limit}
                onChange={(e) => onChangeLimit(Number(e.target.value) || 50)}
              />
            </div>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto">
        {items.length === 0 ? (
          <EmptyState
            title="Henüz refund case yok"
            description="Bu ortamda refund akışı henüz veri üretmemiş olabilir."
          />
        ) : (
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="w-8 text-xs">
                    <input
                      ref={selectAllRef}
                      type="checkbox"
                      className="h-3 w-3 cursor-pointer"
                      aria-label="Sayfadaki tüm case'leri seç"
                      disabled={items.length === 0}
                      checked={items.length > 0 && selectedOnPage === items.length}
                      onChange={(e) => onToggleAllOnPage(e.target.checked)}
                    />
                  </TableHead>
                  <TableHead className="text-xs">Case</TableHead>
                  <TableHead className="text-xs">Agency</TableHead>
                  <TableHead className="text-xs">Booking</TableHead>
                  <TableHead className="text-xs">Booking Status</TableHead>
                  <TableHead className="text-xs text-right">Requested</TableHead>
                  <TableHead className="text-xs text-right">Refundable</TableHead>
                  <TableHead className="text-xs text-right">Penalty</TableHead>
                  <TableHead className="text-xs">Status</TableHead>
                  <TableHead className="text-xs">Decision</TableHead>
                  <TableHead className="text-xs">Updated</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {items.map((it) => {
                  const isSelected = selectedCaseIds.includes(it.case_id);
                  return (
                    <TableRow
                      key={it.case_id}
                      className={
                        "cursor-pointer hover:bg-muted/40 " +
                        (selectedCaseId === it.case_id ? "bg-muted" : "")
                      }
                      onClick={() => onSelectCase(it.case_id)}
                    >
                      <TableCell className="w-8 align-middle">
                        <input
                          type="checkbox"
                          className="h-3 w-3 cursor-pointer"
                          checked={isSelected}
                          onChange={(e) => {
                            e.stopPropagation();
                            onToggleCase(it.case_id, e.target.checked);
                          }}
                          aria-label="Case seç"
                        />
                      </TableCell>
                      <TableCell className="text-xs font-mono truncate max-w-[120px]">
                        {it.case_id}
                      </TableCell>
                      <TableCell className="text-xs truncate max-w-[140px]">
                        {it.agency_name || it.agency_id}
                      </TableCell>
                      <TableCell className="text-xs font-mono truncate max-w-[120px]">
                        {it.booking_id}
                      </TableCell>
                      <TableCell className="text-xs">
                        {it.booking_status ? (
                          <Badge variant="outline">{it.booking_status}</Badge>
                        ) : (
                          <span className="text-muted-foreground">-</span>
                        )}
                      </TableCell>
      {hasSelection && (
        <Card className="border-amber-200 bg-amber-50 mb-2">
          <CardContent className="py-2 flex flex-col gap-2 text-xs">
            <div className="flex items-center gap-3 text-xs text-muted-foreground">
              {bulkRunning ? (
                <>
                  <span>
                    İşlem devam ediyor... {bulkProcessed}/{bulkTotal} case işlendi
                  </span>
                  {bulkCancelRequested && (
                    <span className="text-amber-700">
                      İptal istendi, devam eden istekler tamamlanıyor…
                    </span>
                  )}
                </>
              ) : (
                <span>Seçili case sayısı: {selectedCaseIds.length}</span>
              )}
              {bulkErrorSummary && !bulkRunning && (
                <span className="text-destructive">{bulkErrorSummary}</span>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-2 text-xs">
              <span className="font-medium">Toplu Aksiyon:</span>
              <select
                className="h-8 rounded-md border bg-background px-2 text-xs"
                value={bulkAction}
                onChange={(e) => setBulkAction(e.target.value)}
              >
                <option value="">Seçiniz</option>
                {BULK_ACTIONS.map((opt) => (
                  <option key={opt.value} value={opt.value}>
                    {opt.label}
                  </option>
                ))}
              </select>
              {bulkRunning && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    cancelRef.current = true;
                    setBulkCancelRequested(true);
                  }}
                >
                  İptal et
                </Button>
              )}
              <Button
                size="sm"
                variant="default"
                disabled={!bulkAction || bulkRunning}
                onClick={onRunBulk}
              >
                {bulkRunning && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
                Uygula
              </Button>
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs">
              <span className="font-medium">CSV Export:</span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => exportCsv("filtered")}
              >
                Filtrelenmiş liste (CSV)
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={!selectedCaseIds.length}
                onClick={() => exportCsv("selected")}
              >
                Seçili kayıtlar (CSV)
              </Button>
            </div>
          </CardContent>
        </Card>
      )}


                      <TableCell className="text-xs text-right">
                        {it.requested_amount != null ? it.requested_amount.toFixed(2) : "-"}
                      </TableCell>
                      <TableCell className="text-xs text-right">
                        {it.computed_refundable != null ? it.computed_refundable.toFixed(2) : "-"}
                      </TableCell>
                      <TableCell className="text-xs text-right">
                        {it.computed_penalty != null ? it.computed_penalty.toFixed(2) : "-"}
                      </TableCell>
                      <TableCell className="text-xs">
                        <StatusBadge status={it.status} />
                      </TableCell>
                      <TableCell className="text-xs">
                        {it.decision || "-"}
                      </TableCell>
                      <TableCell className="text-xs">
                        {it.updated_at
                          ? new Date(it.updated_at).toLocaleString()
                          : "-"}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function RefundApproveDialog({ open, onOpenChange, caseData, onApproved }) {
  const [amount, setAmount] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const refundable = caseData?.computed?.refundable ?? 0;

  useEffect(() => {
    if (open && refundable) {
      setAmount(String(refundable));
    }
  }, [open, refundable]);

  const onSubmit = async () => {
    const parsed = parseFloat(amount);
    if (!parsed || parsed <= 0 || parsed > refundable + 1e-6) {
      toast({
        title: "Onaylanan tutar geçersiz",
        description: `Tutar 0'dan büyük ve iade edilebilir tutardan ( ${refundable.toFixed(2)} ) küçük veya eşit olmalıdır.`,
        variant: "destructive",
      });
      return;
    }
    try {
      setSubmitting(true);
      await api.post(`/ops/finance/refunds/${caseData.case_id}/approve-step1`, {
        approved_amount: parsed,
      });
      toast({ title: "1. onay verildi" });
      onApproved();
      onOpenChange(false);
    } catch (e) {
      toast({ title: "Onaylama başarısız", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>1. Onay</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 mt-2 text-sm">
          <div className="text-xs text-muted-foreground">
            Refundable (computed): <strong>{refundable.toFixed(2)}</strong>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Onaylanan tutar</div>
            <Input
              type="number"
              min={0}
              step="0.01"
              value={amount}
              onChange={(e) => setAmount(e.target.value)}
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            İptal
          </Button>
          <Button onClick={onSubmit} disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            1. Onayı Ver
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RefundApproveStep2Dialog({ open, onOpenChange, caseData, onApproved }) {
  const [note, setNote] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) setNote("");
  }, [open]);

  const onSubmit = async () => {
    try {
      setSubmitting(true);
      await api.post(`/ops/finance/refunds/${caseData.case_id}/approve-step2`, {
        note: note || null,
      });
      toast({ title: "2. onay verildi" });
      onApproved();
      onOpenChange(false);
    } catch (e) {
      toast({ title: "Onaylama başarısız", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>2. Onay</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 mt-2 text-sm">
          <div className="text-xs text-muted-foreground">
            Bu adımda ledger kayıtları oluşturulur ve refund case &quot;approved&quot; durumuna alınır.
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Not (opsiyonel)</div>
            <Input
              type="text"
              value={note}
              onChange={(e) => setNote(e.target.value)}
              placeholder="Ops notu (opsiyonel)"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            İptal
          </Button>
          <Button onClick={onSubmit} disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            2. Onayı Ver
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function MiniRefundHistory({ bookingId }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    if (!bookingId) {
      setItems([]);
      setError("");
      return;
    }
    let cancelled = false;
    const run = async () => {
      try {
        setLoading(true);
        setError("");
        const resp = await api.get("/ops/finance/refunds", {
          params: { booking_id: bookingId, status: "closed", limit: 5 },
        });
        if (cancelled) return;
        setItems(resp.data?.items || []);
      } catch (e) {
        if (cancelled) return;
        setError("Liste yfklenemedi");
        setItems([]);
      } finally {
        if (cancelled) return;
        setLoading(false);
      }
    };
    run();
    return () => {
      cancelled = true;
    };
  }, [bookingId]);

  if (!bookingId) {
    return null;
  }

  if (loading) {
    return (
      <div className="flex items-center gap-2 text-xs text-muted-foreground">
        <Loader2 className="h-3 w-3 animate-spin" />
        <span>Yfkleniyor...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center gap-2 text-xs text-destructive">
        <AlertCircle className="h-3 w-3" />
        <span>{error}</span>
      </div>
    );
  }

  if (!items.length) {
    return (
      <div className="text-xs text-muted-foreground">
        Bu booking için kapalı refund yok.
      </div>
    );
  }

  return (
    <div className="space-y-1 text-xs">
      {items.map((it) => (
        <div
          key={it.case_id}
          className="flex flex-wrap items-center justify-between gap-2 border-b last:border-0 py-1"
        >
          <div className="flex flex-col gap-0.5">
            <div className="text-[11px] text-muted-foreground">
              {it.updated_at
                ? new Date(it.updated_at).toLocaleString()
                : "-"}
            </div>
            <div className="flex items-center gap-2">
              <Badge
                variant={
                  it.decision === "approved"
                    ? "default"
                    : it.decision === "rejected"
                    ? "destructive"
                    : "secondary"
                }
                className="text-[10px] px-1 py-0"
              >
                {it.decision || "-"}
              </Badge>
              {(() => {
                const amount =
                  it.approved_amount ?? it.requested_amount ?? null;
                if (amount == null) return null;
                return (
                  <span>
                    {Number(amount).toFixed(2)} {it.currency || ""}
                  </span>
                );
              })()}
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function isPdfDoc(doc) {
  const ct = (doc?.content_type || "").toLowerCase();
  const fn = (doc?.filename || "").toLowerCase();
  return ct === "application/pdf" || fn.endsWith(".pdf");
}

function RefundDocumentsSection({ caseData }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [uploading, setUploading] = useState(false);
  const [file, setFile] = useState(null);
  const [tag, setTag] = useState("dekont");
  const [note, setNote] = useState("");
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewUrl, setPreviewUrl] = useState("");
  const [previewTitle, setPreviewTitle] = useState("");
  const [previewLoading, setPreviewLoading] = useState(false);
  const [previewError, setPreviewError] = useState("");

  const hasCase = !!caseData?.case_id;

  const load = async () => {
    if (!hasCase) return;
    try {
      setLoading(true);
      setError("");
      const resp = await api.get("/ops/documents", {
        params: { entity_type: "refund_case", entity_id: caseData.case_id },
      });
      setItems(resp.data?.items || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (hasCase) {
      load();
    } else {
      setItems([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseData?.case_id]);

  const TAG_OPTIONS = ["dekont", "iptal_yazisi", "musteri_yazismasi", "kimlik", "diger"];

  const onUpload = async () => {
    if (!file) {
      toast({
        title: "Dosya seçilmedi",
        description: "Lütfen yüklenecek bir dosya seçin.",
        variant: "destructive",
      });
      return;
    }
    if (!TAG_OPTIONS.includes(tag)) {
      toast({
        title: "Geçersiz etiket",
        description: "Lütfen geçerli bir etiket seçin.",
        variant: "destructive",
      });
      return;
    }
    try {
      setUploading(true);
      const formData = new FormData();
      formData.append("entity_type", "refund_case");
      formData.append("entity_id", caseData.case_id);
      formData.append("tag", tag);
      if (note) formData.append("note", note);
      formData.append("file", file);
      await api.post("/ops/documents/upload", formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast({ title: "Doküman yüklendi" });
      setFile(null);
      setNote("");
      await load();
    } catch (e) {
      toast({ title: "Doküman yüklenemedi", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setUploading(false);
    }
  };

  const onDelete = async (doc) => {
    try {
      await api.delete(`/ops/documents/${doc.document_id}`, { data: {} });
      toast({ title: "Doküman silindi" });
      await load();
    } catch (e) {
      toast({ title: "Doküman silinemedi", description: apiErrorMessage(e), variant: "destructive" });
    }
  };

  const onDownload = async (doc) => {
    try {
      const resp = await api.get(`/ops/documents/${doc.document_id}/download`, {
        responseType: "blob",
      });
      const blob = new Blob([resp.data], { type: doc.content_type || "application/octet-stream" });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = doc.filename || "document";
      document.body.appendChild(a);
      a.click();
      a.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      toast({ title: "İndirme başarısız", description: apiErrorMessage(e), variant: "destructive" });
    }
  };

  if (!hasCase) return null;

  return (
    <div className="rounded-lg border bg-muted/20 p-3 space-y-3">
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs font-semibold text-muted-foreground">Dokümanlar</div>
      </div>

      {/* Upload form */}
      <div className="flex flex-wrap items-end gap-2 text-xs">
        <div className="flex flex-col gap-1">
          <span className="text-[11px] text-muted-foreground">Etiket</span>
          <select
            className="border rounded px-2 py-1 text-xs bg-background"
            value={tag}
            onChange={(e) => setTag(e.target.value)}
          >
            <option value="dekont">Dekont</option>
            <option value="iptal_yazisi">İptal yazısı</option>
            <option value="musteri_yazismasi">Müşteri yazışması</option>
            <option value="kimlik">Kimlik</option>
            <option value="diger">Diğer</option>
          </select>
        </div>
        <div className="flex flex-col gap-1 min-w-[160px] flex-1">
          <span className="text-[11px] text-muted-foreground">Not (opsiyonel)</span>
          <Input
            type="text"
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Kısa açıklama"
          />
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-[11px] text-muted-foreground">Dosya</span>
          <Input
            type="file"
            onChange={(e) => setFile(e.target.files?.[0] || null)}
          />
        </div>
        <Button size="sm" onClick={onUpload} disabled={uploading || !file} className="mt-4">
          {uploading && <Loader2 className="h-3 w-3 mr-1 animate-spin" />}
          Yükle
        </Button>
      </div>

      {loading ? (
        <div className="text-xs text-muted-foreground">Dokümanlar yükleniyor...</div>
      ) : error ? (
        <div className="text-xs text-destructive">{error}</div>
      ) : !items.length ? (
        <div className="text-xs text-muted-foreground">Bu refund için doküman yok.</div>
      ) : (
        <div className="mt-2 space-y-1 text-xs">
          {items.map((doc) => {
            const tagValue = doc.tag || "diger";
            const tagLabelMap = {
              dekont: "Dekont",
              iptal_yazisi: "İptal yazısı",
              musteri_yazismasi: "Müşteri yazışması",
              kimlik: "Kimlik",
              diger: "Diğer",
            };
            const isKnownTag = TAG_OPTIONS.includes(tagValue);
            const badgeText = isKnownTag ? tagLabelMap[tagValue] : `Diğer (${tagValue})`;

            return (
              <div
                key={doc.document_id}
                className="flex items-center justify-between gap-2 rounded border bg-background px-2 py-1"
              >
                <div className="flex items-center gap-2 min-w-0">
                  <Badge variant="outline" className="text-[10px] uppercase">
                    {badgeText}
                  </Badge>
                  <button
                  type="button"
                  className="text-xs text-blue-600 hover:underline truncate max-w-[220px] text-left"
                  onClick={() => onDownload(doc)}
                  title={doc.filename}
                >
                  {doc.filename}
                </button>
                <span className="text-[11px] text-muted-foreground">
                  {doc.size_bytes != null ? `${Math.round(doc.size_bytes / 1024)} KB` : ""}
                </span>
                {isPdfDoc(doc) && (
                  <Button
                    size="xs"
                    variant="outline"
                    disabled={previewLoading}
                    onClick={async () => {
                      try {
                        setPreviewError("");
                        setPreviewTitle(doc.filename || "PDF Önizleme");
                        // Dialog hemen açılsın ve önceki URL temizlensin
                        setPreviewOpen(true);
                        if (previewUrl) {
                          window.URL.revokeObjectURL(previewUrl);
                        }
                        setPreviewUrl("");
                        setPreviewLoading(true);

                        const resp = await api.get(`/ops/documents/${doc.document_id}/download`, {
                          responseType: "blob",
                        });
                        const blob = new Blob([resp.data], { type: "application/pdf" });
                        const url = window.URL.createObjectURL(blob);
                        setPreviewUrl(url);
                      } catch (e) {
                        setPreviewError(apiErrorMessage(e));
                        toast({
                          title: "Önizleme açılamadı",
                          description: apiErrorMessage(e),
                          variant: "destructive",
                        });
                      } finally {
                        setPreviewLoading(false);
                      }
                    }}
                  >
                    Önizle
                  </Button>
                )}
                </div>
                <div className="flex items-center gap-2 text-[11px] text-muted-foreground">
                  <span>{doc.created_by_email}</span>
                  <span>
                    {doc.created_at ? new Date(doc.created_at).toLocaleString() : ""}
                  </span>
                  <Button
                    size="icon"
                    variant="ghost"
                    className="h-6 w-6 text-destructive"
                    onClick={() => onDelete(doc)}
                  >
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              </div>
            );
          })}
        </div>
      )}
      <PDFPreviewDialog 
        previewOpen={previewOpen}
        setPreviewOpen={setPreviewOpen}
        previewUrl={previewUrl}
        setPreviewUrl={setPreviewUrl}
        previewTitle={previewTitle}
        previewLoading={previewLoading}
        previewError={previewError}
      />
    </div>
  );
}

{/* PDF Preview Dialog */}
function PDFPreviewDialog({ previewOpen, setPreviewOpen, previewUrl, setPreviewUrl, previewTitle, previewLoading, previewError }) {
  return (
    <Dialog
      open={previewOpen}
      onOpenChange={(v) => {
        if (!v && previewUrl) {
          window.URL.revokeObjectURL(previewUrl);
        }
        if (!v) {
          setPreviewUrl("");
        }
        setPreviewOpen(v);
      }}
    >
      <DialogContent className="max-w-4xl">
        <DialogHeader>
          <DialogTitle className="text-sm">{previewTitle || "PDF Önizleme"}</DialogTitle>
        </DialogHeader>
        {previewLoading ? (
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <Loader2 className="h-3 w-3 animate-spin" />
            <span>Yükleniyor...</span>
          </div>
        ) : previewError ? (
          <div className="text-xs text-destructive">{previewError}</div>
        ) : previewUrl ? (
          <iframe
            src={previewUrl}
            title="PDF Preview"
            className="w-full h-[70vh] rounded border"
          />
        ) : (
          <div className="text-xs text-muted-foreground">Önizleme için bir PDF seçin.</div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function RefundTasksSection({ caseData }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [busyTaskId, setBusyTaskId] = useState("");

  const hasCase = !!caseData?.case_id;

  const load = async () => {
    if (!hasCase) return;
    try {
      setLoading(true);
      setError("");
      const resp = await api.get(`/ops/refunds/${caseData.case_id}/tasks`);
      setItems(resp.data?.items || []);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (hasCase) {
      load();
    } else {
      setItems([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [caseData?.case_id]);

  const onQuickStatus = async (task, status) => {
    try {
      await api.patch(`/ops/tasks/${task.task_id}`, { status });
      await load();
    } catch (e) {
      toast({ title: "Görev güncellenemedi", description: apiErrorMessage(e), variant: "destructive" });
    }
  };

  const onAssign = async (task, assigneeEmail) => {
    if (!task?.task_id) return;
    try {
      setBusyTaskId(task.task_id);
      await api.patch(`/ops/tasks/${task.task_id}`, { assignee_email: assigneeEmail || null });
      await load();
      toast({
        title: assigneeEmail ? "Görev üstlenildi" : "Görev bırakıldı",
      });
    } catch (e) {
      toast({
        title: "İşlem başarısız",
        description: apiErrorMessage(e),
        variant: "destructive",
      });
    } finally {
      setBusyTaskId("");
    }
  };

  if (!hasCase) return null;

  return (
    <div className="rounded-lg border bg-muted/20 p-3 space-y-2">
      <div className="flex items-center justify-between gap-2">
        <div className="text-xs font-semibold text-muted-foreground">Görevler</div>
        <RefundTaskCreateDialogButton caseData={caseData} onCreated={load} />
      </div>
      {loading ? (
        <div className="text-xs text-muted-foreground">Görevler yükleniyor...</div>
      ) : error ? (
        <div className="text-xs text-destructive">{error}</div>
      ) : !items.length ? (
        <div className="text-xs text-muted-foreground">Bu refund için görev yok.</div>
      ) : (
        <div className="space-y-1 text-xs">
          {items.map((t) => {
            const overdue = t.is_overdue && ["open", "in_progress"].includes(t.status);
            return (
              <div
                key={t.task_id}
                className="flex items-center justify-between gap-2 rounded border bg-background px-2 py-1"
              >
                <div className="flex flex-col gap-0.5 min-w-0">
                  <div className="flex items-center gap-2">
                    {statusBadge(t.status)}
                    {priorityBadge(t.priority)}
                    {overdue && (
                      <span className="text-[10px] text-destructive flex items-center gap-1">
                        <Clock className="h-3 w-3" /> SLA aşıldı
                      </span>
                    )}
                  </div>
                  <div className="truncate font-medium" title={t.title}>
                    {t.title}
                  </div>
                  <div className="text-[11px] text-muted-foreground flex flex-wrap gap-2">
                    <span>Tip: {t.task_type}</span>
                    {t.due_at && <span>Due: {new Date(t.due_at).toLocaleString()}</span>}
                    {t.assignee_email && <span>Atanan: {t.assignee_email}</span>}
                  </div>
                </div>
                <div className="flex items-center gap-1">
                  {/* Üstlen / Bırak */}
                  {!t.assignee_email && myEmail && (
                    <Button
                      size="xs"
                      variant="outline"
                      disabled={busyTaskId === t.task_id}
                      onClick={() => onAssign(t, myEmail)}
                    >
                      Üstlen
                    </Button>
                  )}
                  {t.assignee_email && t.assignee_email === myEmail && (
                    <Button
                      size="xs"
                      variant="ghost"
                      disabled={busyTaskId === t.task_id}
                      onClick={() => onAssign(t, null)}
                    >
                      Bırak
                    </Button>
                  )}

                  {t.status === "open" && (
                    <Button
                      size="xs"
                      variant="outline"
                      onClick={() => onQuickStatus(t, "in_progress")}
                    >
                      Başlat
                    </Button>
                  )}
                  {t.status === "in_progress" && (
                    <Button size="xs" onClick={() => onQuickStatus(t, "done")}>
                      Tamamla
                    </Button>
                  )}
                  {t.status !== "done" && t.status !== "cancelled" && (
                    <Button
                      size="xs"
                      variant="ghost"
                      onClick={() => onQuickStatus(t, "cancelled")}
                    >
                      İptal
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function RefundTaskCreateDialogButton({ caseData, onCreated }) {
  const [open, setOpen] = useState(false);
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [priority, setPriority] = useState("normal");
  const [dueAt, setDueAt] = useState("");
  const [slaHours, setSlaHours] = useState("");
  const [assigneeEmail, setAssigneeEmail] = useState("");
  const [tags, setTags] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = !!caseData?.case_id && title && !submitting;

  const onSubmit = async () => {
    if (!canSubmit) return;
    try {
      setSubmitting(true);
      const body = {
        entity_type: "refund_case",
        entity_id: caseData.case_id,
        task_type: "custom",
        title,
        description: description || null,
        priority,
        due_at: dueAt || null,
        sla_hours: slaHours ? Number(slaHours) : null,
        assignee_email: assigneeEmail || null,
        tags: tags
          ? tags
              .split(",")
              .map((t) => t.trim())
              .filter(Boolean)
          : [],
        meta: { source: "refund_detail", case_id: caseData.case_id },
      };
      await api.post("/ops/tasks", body);
      toast({ title: "Görev oluşturuldu" });
      setTitle("");
      setDescription("");
      setDueAt("");
      setSlaHours("");
      setAssigneeEmail("");
      setTags("");
      setOpen(false);
      if (onCreated) onCreated();
    } catch (e) {
      toast({ title: "Görev oluşturulamadı", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <Button size="xs" variant="outline" onClick={() => setOpen(true)}>
        Yeni görev
      </Button>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Yeni görev oluştur</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 mt-2 text-sm">
          <div className="text-xs text-muted-foreground">
            case: <span className="font-mono text-[11px]">{caseData?.case_id}</span>
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Başlık *</div>
            <Input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Görev başlığı"
            />
          </div>
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Açıklama</div>
            <Input
              type="text"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Ops notu (opsiyonel)"
            />
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="space-y-1">
              <div className="text-[11px] text-muted-foreground">Öncelik</div>
              <select
                className="h-8 rounded-md border bg-background px-2 text-xs"
                value={priority}
                onChange={(e) => setPriority(e.target.value)}
              >
                <option value="low">Düşük</option>
                <option value="normal">Normal</option>
                <option value="high">Yüksek</option>
                <option value="urgent">Acil</option>
              </select>
            </div>
            <div className="space-y-1">
              <div className="text-[11px] text-muted-foreground">Atanan e-posta</div>
              <Input
                type="email"
                value={assigneeEmail}
                onChange={(e) => setAssigneeEmail(e.target.value)}
                placeholder="ops@acenta.test"
              />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-2 text-xs">
            <div className="space-y-1">
              <div className="text-[11px] text-muted-foreground">Son tarih (due_at)</div>
              <Input
                type="datetime-local"
                value={dueAt}
                onChange={(e) => setDueAt(e.target.value)}
              />
            </div>
            <div className="space-y-1">
              <div className="text-[11px] text-muted-foreground">SLA (saat)</div>
              <Input
                type="number"
                min={0}
                value={slaHours}
                onChange={(e) => setSlaHours(e.target.value)}
              />
            </div>
          </div>
          <div className="space-y-1 text-xs">
            <div className="text-[11px] text-muted-foreground">Etiketler (virgülle ayırın)</div>
            <Input
              type="text"
              value={tags}
              onChange={(e) => setTags(e.target.value)}
              placeholder="refund, followup"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => setOpen(false)}
            disabled={submitting}
          >
            İptal
          </Button>
          <Button onClick={onSubmit} disabled={!canSubmit}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Oluştur
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RefundMarkPaidDialog({ open, onOpenChange, caseData, onMarked }) {
  const [paymentRef, setPaymentRef] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) setPaymentRef("");
  }, [open]);

  const onSubmit = async () => {
    if (!paymentRef.trim()) {
      toast({
        title: "Ödeme referansı gerekli",
        description: "Lütfen bir ödeme referansı girin.",
        variant: "destructive",
      });
      return;
    }
    try {
      setSubmitting(true);
      await api.post(`/ops/finance/refunds/${caseData.case_id}/mark-paid`, {
        payment_reference: paymentRef.trim(),
      });
      toast({ title: "Refund ödendi olarak işaretlendi" });
      onMarked();
      onOpenChange(false);
    } catch (e) {
      toast({ title: "İşlem başarısız", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Ödendi olarak işaretle</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 mt-2 text-sm">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Ödeme referansı</div>
            <Input
              type="text"
              value={paymentRef}
              onChange={(e) => setPaymentRef(e.target.value)}
              placeholder="Ödeme dekont/ref no"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            İptal
          </Button>
          <Button onClick={onSubmit} disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Ödendi
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RefundRejectDialog({ open, onOpenChange, caseData, onRejected }) {
  const [reason, setReason] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (open) setReason("");
  }, [open]);

  const onSubmit = async () => {
    try {
      setSubmitting(true);
      await api.post(`/ops/finance/refunds/${caseData.case_id}/reject`, {
        reason: reason || null,
      });
      toast({ title: "Refund reddedildi" });
      onRejected();
      onOpenChange(false);
    } catch (e) {
      toast({ title: "Red başarısız", description: apiErrorMessage(e), variant: "destructive" });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Refund Reddet</DialogTitle>
        </DialogHeader>
        <div className="space-y-3 mt-2 text-sm">
          <div className="space-y-1">
            <div className="text-xs text-muted-foreground">Red sebebi</div>
            <Input
              type="text"
              value={reason}
              onChange={(e) => setReason(e.target.value)}
              placeholder="Ops notu (opsiyonel)"
            />
          </div>
        </div>
        <DialogFooter>
          <Button
            variant="outline"
            onClick={() => onOpenChange(false)}
            disabled={submitting}
          >
            İptal
          </Button>
          <Button onClick={onSubmit} disabled={submitting}>
            {submitting && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
            Reddet
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function RefundDetailPanel({
  caseData,
  bookingFinancials,
  loading,
  onRefresh,
  onOpenApproveStep1,
  onOpenApproveStep2,
  onOpenReject,
  onOpenMarkPaid,
  onCloseCase,
}) {
  if (loading) {
    return (
      <Card className="h-full flex items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </Card>
    );
  }

  if (!caseData) {
    return (
      <Card className="h-full flex items-center justify-center">
        <p className="text-sm text-muted-foreground">
          Soldan bir refund case se1n.
        </p>
      </Card>
    );
  }

  const status = caseData.status;
  const isOpen = status === "open" || status === "pending_approval" || status === "pending_approval_1";
  const isPendingStep2 = status === "pending_approval_2";
  const isApproved = status === "approved";
  const isPaid = status === "paid";
  const isRejected = status === "rejected";
  const isClosed = status === "closed";
  const computed = caseData.computed || {};
  const requested = caseData.requested || {};

  return (
    <Card className="h-full flex flex-col">
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="space-y-1">
          <CardTitle className="text-sm font-medium">Refund Detail</CardTitle>
          <p className="text-xs text-muted-foreground">
            Case ID: <span className="font-mono">{caseData.case_id}</span>
          </p>
          <p className="text-xs text-muted-foreground">
            Booking: <span className="font-mono">{caseData.booking_id}</span>  b7 Agency: <span className="font-mono">{caseData.agency_id}</span>
          </p>
          <p className="text-xs text-muted-foreground">
            Status: <StatusBadge status={caseData.status} />
          </p>
        </div>
        <div className="flex flex-col items-end gap-2">
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              variant="outline"
              onClick={onRefresh}
            >
              Yenile
            </Button>
          </div>
          <div className="flex flex-wrap items-center gap-2 mt-2 text-xs">
            {/* Step 1 approve */}
            <Button
              size="sm"
              onClick={onOpenApproveStep1}
              disabled={!isOpen || isClosed}
            >
              1. Onay
            </Button>
            {/* Step 2 approve */}
            <Button
              size="sm"
              variant="outline"
              onClick={onOpenApproveStep2}
              disabled={!isPendingStep2 || isClosed}
            >
              2. Onay
            </Button>
            {/* Mark paid */}
            <Button
              size="sm"
              variant="secondary"
              onClick={onOpenMarkPaid}
              disabled={!isApproved || isClosed}
            >
              Ödendi
            </Button>
            {/* Reject */}
            <Button
              size="sm"
              variant="outline"
              onClick={onOpenReject}
              disabled={isClosed}
            >
              Reddet
            </Button>
            {/* Close */}
            <Button
              size="sm"
              variant="ghost"
              onClick={onCloseCase}
              disabled={!(isPaid || isRejected) || isClosed}
            >
              Kapat
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto space-y-4 text-sm">
        <div className="rounded-lg border bg-muted/40 p-3 space-y-1">
          <div className="text-xs font-semibold text-muted-foreground">Request</div>
          <div className="flex flex-wrap gap-4 text-xs">
            <div>
              <div className="text-muted-foreground">Requested</div>
              <div>{requested.amount != null ? requested.amount.toFixed(2) : "-"}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Currency</div>
              <div>{caseData.currency}</div>
            </div>
            <div className="min-w-[200px]">
              <div className="text-muted-foreground">Message</div>
              <div className="truncate" title={requested.message || "-"}>
                {requested.message || "-"}
              </div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-muted/40 p-3 space-y-1">
          <div className="text-xs font-semibold text-muted-foreground">Computed</div>
          <div className="flex flex-wrap gap-4 text-xs">
            <div>
              <div className="text-muted-foreground">Refundable</div>
              <div>{computed.refundable != null ? computed.refundable.toFixed(2) : "-"}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Penalty</div>
              <div>{computed.penalty != null ? computed.penalty.toFixed(2) : "-"}</div>
            </div>
            <div>
              <div className="text-muted-foreground">Basis</div>
              <div>{computed.basis || "-"}</div>
            </div>
          </div>
        </div>

        <div className="rounded-lg border bg-muted/40 p-3 space-y-1">
          <div className="text-xs font-semibold text-muted-foreground">Booking financials</div>
          {bookingFinancials ? (
            <div className="flex flex-wrap gap-4 text-xs">
              <div>
                <div className="text-muted-foreground">Sell total</div>
                <div>{bookingFinancials.sell_total != null ? bookingFinancials.sell_total.toFixed(2) : "-"}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Refunded total</div>
                <div>{bookingFinancials.refunded_total != null ? bookingFinancials.refunded_total.toFixed(2) : "-"}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Penalty total</div>
                <div>{bookingFinancials.penalty_total != null ? bookingFinancials.penalty_total.toFixed(2) : "-"}</div>
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 text-xs text-muted-foreground">
              <AlertCircle className="h-3 w-3" />
              <span>Financials bulunamad1.</span>
            </div>
          )}
        </div>

        {caseData.status === "closed" && (
          <div className="rounded-lg border bg-muted/20 p-3 space-y-1">
            <div className="text-xs font-semibold text-muted-foreground">Decision</div>
            <div className="flex flex-wrap gap-4 text-xs">
              <div>
                <div className="text-muted-foreground">Decision</div>
                <div>{caseData.decision || "-"}</div>
              </div>
              <div>
                <div className="text-muted-foreground">Approved amount</div>
                <div>
                  {caseData.approved?.amount != null
                    ? caseData.approved.amount.toFixed(2)
                    : "-"}
                </div>
              </div>
              <div>
                <div className="text-muted-foreground">By</div>
                <div>{caseData.decision_by_email || "-"}</div>
              </div>
              <div>
                <div className="text-muted-foreground">At</div>
                <div>
                  {caseData.decision_at
                    ? new Date(caseData.decision_at).toLocaleString()
                    : "-"}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* Documents section */}
        <RefundDocumentsSection caseData={caseData} />

        {/* Tasks for this refund */}
        <RefundTasksSection caseData={caseData} />

        {/* Last 5 closed refunds for this booking */}
        <div className="rounded-lg border bg-muted/10 p-3 space-y-2">
          <div className="text-xs font-semibold text-muted-foreground">
            Bu booking için son 5 kapalı refund
          </div>
          <MiniRefundHistory bookingId={caseData.booking_id} />
        </div>
      </CardContent>
    </Card>
  );
}

export default function AdminFinanceRefundsPage() {
  const user = getUser();
  const orgId = user?.organization_id || "";
  const myEmail = user?.email || "";

  const [list, setList] = useState([]);
  const [bulkAction, setBulkAction] = useState("");
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkProcessed, setBulkProcessed] = useState(0);
  const [bulkTotal, setBulkTotal] = useState(0);
  const [bulkErrorSummary, setBulkErrorSummary] = useState("");
  const [bulkCancelRequested, setBulkCancelRequested] = useState(false);

  const [statusFilter, setStatusFilter] = useState("open");
  const [limit, setLimit] = useState(50);
  const [selectedCaseIds, setSelectedCaseIds] = useState([]);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState("");
  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [caseData, setCaseData] = useState(null);
  const [bookingFinancials, setBookingFinancials] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [approveStep1Open, setApproveStep1Open] = useState(false);
  const [approveStep2Open, setApproveStep2Open] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [markPaidOpen, setMarkPaidOpen] = useState(false);
  const [presets, setPresets] = useState([]);
  const [selectedPresetId, setSelectedPresetId] = useState("");

  const PRESET_STORAGE_KEY = orgId && myEmail
    ? `refunds.filter_presets.v1.${orgId}.${myEmail}`
    : null;

  const cancelRef = React.useRef(false);

  const hasSelection = selectedCaseIds.length > 0;

  const BULK_ACTIONS = [
    { value: "approve_step1", label: "1. Onay (approve_step1)" },
    { value: "approve_step2", label: "2. Onay (approve_step2)" },
    { value: "reject", label: "Reddet" },
    { value: "close", label: "Kapat" },
  ];

  // Helper functions
  const buildCsvRows = (rows) => {
    return rows.map((it) => {
      const approvedAmount = it.approved?.amount;
      const amount =
        typeof approvedAmount === "number"
          ? approvedAmount
          : typeof it.computed_refundable === "number"
          ? it.computed_refundable
          : typeof it.requested_amount === "number"
          ? it.requested_amount
          : null;

      return {
        refund_case_id: it.case_id,
        booking_id: it.booking_id,
        status: it.status,
        amount,
        currency: it.currency,
        created_at: it.created_at || "",
        updated_at: it.updated_at || "",
        agency_name: it.agency_name || "",
        agency_id: it.agency_id || "",
        reason: it.reason || "",
      };
    });
  };

  const exportCsv = (mode) => {
    let rows = [];
    if (mode === "selected") {
      const set = new Set(selectedCaseIds);
      rows = list.filter((it) => set.has(it.case_id));
    } else {
      rows = list;
    }

    if (!rows.length) {
      toast({ title: "Export edilecek kayıt yok", variant: "destructive" });
      return;
    }

    const mapped = buildCsvRows(rows);
    const headers = [
      "refund_case_id",
      "booking_id",
      "status",
      "amount",
      "currency",
      "created_at",
      "updated_at",
      "agency_name",
      "agency_id",
      "reason",
    ];

    const csvLines = [];
    csvLines.push(headers.join(","));
    for (const row of mapped) {
      const line = headers
        .map((h) => {
          const v = row[h];
          if (v == null) return "";
          const s = String(v);
          if (s.includes(",") || s.includes("\"") || s.includes("\n")) {
            return `"${s.replace(/"/g, '""')}"`;
          }
          return s;
        })
        .join(",");
      csvLines.push(line);
    }

    const blob = new Blob([csvLines.join("\n")], { type: "text/csv;charset=utf-8;" });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    const ts = new Date().toISOString().replace(/[:.]/g, "-");
    const suffix = mode === "selected" ? "selected" : "filtered";
    a.download = `refunds_${suffix}_${ts}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    window.URL.revokeObjectURL(url);
  };

  const onToggleCase = (caseId, checked) => {
    setSelectedCaseIds((prev) => {
      if (checked) {
        if (prev.includes(caseId)) return prev;
        return [...prev, caseId];
      }
      return prev.filter((id) => id !== caseId);
    });
  };

  const onToggleAllOnPage = (checked) => {
    if (checked) {
      const allCaseIds = list.map(item => item.case_id);
      setSelectedCaseIds(prev => {
        const newIds = [...prev];
        allCaseIds.forEach(id => {
          if (!newIds.includes(id)) {
            newIds.push(id);
          }
        });
        return newIds;
      });
    } else {
      const pageCaseIds = list.map(item => item.case_id);
      setSelectedCaseIds(prev => prev.filter(id => !pageCaseIds.includes(id)));
    }
  };

  const onSelectCase = (caseId) => {
    setSelectedCaseId(caseId);
    loadDetail(caseId);
  };

  const handleToggleCase = (caseId, checked) => {
    setSelectedCaseIds((prev) => {
      if (checked) {
        if (prev.includes(caseId)) return prev;
        return [...prev, caseId];
      }
      return prev.filter((id) => id !== caseId);
    });
  };

  const handleToggleAllOnPage = (checked) => {
    if (!list.length) return;
    if (checked) {
      const idsOnPage = list.map((it) => it.case_id);
      setSelectedCaseIds((prev) => {
        const set = new Set(prev);
        idsOnPage.forEach((id) => set.add(id));
        return Array.from(set);
      });
    } else {
      const idsOnPage = new Set(list.map((it) => it.case_id));
      setSelectedCaseIds((prev) => prev.filter((id) => !idsOnPage.has(id)));
    }
  };

  const runBulk = async (runner) => {
    const ids = selectedCaseIds;
    if (!ids.length) return;
    setBulkRunning(true);
    setBulkProcessed(0);
    setBulkTotal(ids.length);
    setBulkErrorSummary("");
    setBulkCancelRequested(false);
    cancelRef.current = false;
    const errors = [];

    const concurrency = 3;
    let idx = 0;
    let active = 0;

    const runNext = async () => {
      if (cancelRef.current) return;
      if (idx >= ids.length) return;
      const caseId = ids[idx++];
      active += 1;
      try {
        await runner(caseId);
      } catch (e) {
        const msg = apiErrorMessage(e) || "Bilinmeyen hata";
        errors.push({ caseId, message: msg });
      } finally {
        setBulkProcessed((prev) => prev + 1);
        active -= 1;
        if (idx < ids.length) {
          await runNext();
        }
      }
    };

    const starters = [];
    for (let i = 0; i < concurrency && i < ids.length; i += 1) {
      starters.push(runNext());
    }

    await Promise.all(starters);

    if (bulkCancelRequested) {
      setBulkErrorSummary((prev) => prev || "İptal istendi, devam eden istekler tamamlandı.");
    }

    if (errors.length) {
      const firstFive = errors.slice(0, 5)
        .map((e) => `${e.caseId}: ${e.message}`)
        .join("; ");
      setBulkErrorSummary(`Hatalı: ${errors.length} case. İlk hatalar: ${firstFive}`);
      // Detay için console
      // eslint-disable-next-line no-console
      console.error("Bulk refund action errors", errors);
    } else {
      setBulkErrorSummary("");
    }

    setBulkRunning(false);
  };

  const onRunBulk = async () => {
    if (!bulkAction || !selectedCaseIds.length) return;

    if (!window.confirm(`Seçili ${selectedCaseIds.length} case için '${bulkAction}' aksiyonu çalıştırılacak. Emin misiniz?`)) {
      return;
    }

    if (bulkAction === "approve_step1") {
      await runBulk(async (caseId) => {
        // Her case için önce detay çekip refundable ve status kontrolü yap
        const resp = await api.get(`/ops/finance/refunds/${caseId}`);
        const data = resp.data;
        const status = data?.status;
        if (status && !["open", "pending_approval", "pending_approval_1"].includes(status)) {
          throw new Error(`Bu status için 1. onay uygun değil: ${status}`);
        }
        const refundable = data?.computed?.refundable;
        if (typeof refundable !== "number") {
          throw new Error("Refundable amount bulunamadı");
        }
        await api.post(`/ops/finance/refunds/${caseId}/approve-step1`, {
          approved_amount: refundable,
        });
      });
    } else if (bulkAction === "approve_step2") {
      await runBulk(async (caseId) => {
        await api.post(`/ops/finance/refunds/${caseId}/approve-step2`, { note: null });
      });
    } else if (bulkAction === "reject") {
      await runBulk(async (caseId) => {
        await api.post(`/ops/finance/refunds/${caseId}/reject`, { reason: null });
      });
    } else if (bulkAction === "close") {
      await runBulk(async (caseId) => {
        await api.post(`/ops/finance/refunds/${caseId}/close`, { note: null });
      });
    }

    await loadList();
    if (selectedCaseId) {
      await loadDetail(selectedCaseId);
    }
  };

  const loadList = React.useCallback(async () => {
    try {
      setLoadingList(true);
      setListError("");
      const params = {};
      if (statusFilter === "open") {
        // Open bucket = open + pending_approval
        params.status = "open,pending_approval";
      } else if (statusFilter === "closed") {
        params.status = "closed";
      }
      if (limit) params.limit = limit;
      const resp = await api.get("/ops/finance/refunds", { params });
      setList(resp.data?.items || []);
    } catch (e) {
      setListError(apiErrorMessage(e));
    } finally {
      setLoadingList(false);
    }
  }, [limit, statusFilter]);

  const loadDetail = React.useCallback(async (caseId) => {
    if (!caseId) return;
    try {
      setDetailLoading(true);
      setCaseData(null);
      setBookingFinancials(null);
      const resp = await api.get(`/ops/finance/refunds/${caseId}`);
      setCaseData(resp.data);
      
      // Load booking financials if booking_id exists
      if (resp.data?.booking_id) {
        try {
          const finResp = await api.get(`/ops/bookings/${resp.data.booking_id}/financials`);
          setBookingFinancials(finResp.data);
        } catch (e) {
          // Ignore financials error
          setBookingFinancials(null);
        }
      }
    } catch (e) {
      setCaseData(null);
      setBookingFinancials(null);
    } finally {
      setDetailLoading(false);
    }
  }, []);

  useEffect(() => {
    // load list when filters change
    loadList();
  }, [statusFilter, limit, loadList]);

  useEffect(() => {
    if (list && list.length > 0) {
      const first = list[0];
      setSelectedCaseId(first.case_id);
      loadDetail(first.case_id);
      // Sayfa yenilendiğinde, listede olmayan caseId'leri temizle
      const validIds = new Set(list.map((it) => it.case_id));
      setSelectedCaseIds((prev) => prev.filter((id) => validIds.has(id)));
    } else {
      setSelectedCaseId(null);
      setCaseData(null);
      setBookingFinancials(null);
      setSelectedCaseIds([]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [list]);

  const onAfterDecision = async () => {
    await loadList();
    if (selectedCaseId) {
      await loadDetail(selectedCaseId);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader
        title="Refund Kuyruğu"
        subtitle="Refund case kuyruğu ve ilgili booking finansal özeti."
      />

      {listError && !loadingList && (
        <ErrorState
          title="Refund listesi yüklenemedi"
          description={listError}
          onRetry={loadList}
          className="max-w-xl"
        />
      )}

      <div className="grid grid-cols-1 lg:grid-cols-[minmax(0,1.2fr)_minmax(0,1.8fr)] gap-4 h-[560px]">
        <div className="min-h-0">
          {loadingList ? (
            <Card className="h-full flex items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </Card>
          ) : (
            <RefundQueueList
              items={list}
              statusFilter={statusFilter}
              limit={limit}
              onChangeStatus={setStatusFilter}
              onChangeLimit={setLimit}
              selectedCaseId={selectedCaseId}
              onSelectCase={onSelectCase}
              selectedCaseIds={selectedCaseIds}
              onToggleCase={onToggleCase}
              onToggleAllOnPage={onToggleAllOnPage}
            />
          )}
        </div>
        <div className="min-h-0">
          <RefundDetailPanel
            caseData={caseData}
            bookingFinancials={bookingFinancials}
            loading={detailLoading}
            onRefresh={() => {
              if (selectedCaseId) loadDetail(selectedCaseId);
            }}
            onOpenApproveStep1={() => setApproveStep1Open(true)}
            onOpenApproveStep2={() => setApproveStep2Open(true)}
            onOpenReject={() => setRejectOpen(true)}
            onOpenMarkPaid={() => setMarkPaidOpen(true)}
            onCloseCase={async () => {
              if (!caseData) return;
              try {
                await api.post(`/ops/finance/refunds/${caseData.case_id}/close`, { note: null });
                toast({ title: "Refund case kapatıldı" });
                await onAfterDecision();
              } catch (e) {
                toast({ title: "Kapatma başarısız", description: apiErrorMessage(e), variant: "destructive" });
              }
            }}
          />
        </div>
      </div>

      <RefundApproveDialog
        open={approveStep1Open}
        onOpenChange={setApproveStep1Open}
        caseData={caseData}
        onApproved={onAfterDecision}
      />

      <RefundApproveStep2Dialog
        open={approveStep2Open}
        onOpenChange={setApproveStep2Open}
        caseData={caseData}
        onApproved={onAfterDecision}
      />

      <RefundMarkPaidDialog
        open={markPaidOpen}
        onOpenChange={setMarkPaidOpen}
        caseData={caseData}
        onMarked={onAfterDecision}
      />

      <RefundRejectDialog
        open={rejectOpen}
        onOpenChange={setRejectOpen}
        caseData={caseData}
        onRejected={onAfterDecision}
      />

      {/* Bulk Operations Section */}
      {hasSelection && (
        <Card className="border-dashed">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Bulk Operations</CardTitle>
            <p className="text-xs text-muted-foreground">
              {selectedCaseIds.length} case seçili
            </p>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex flex-wrap items-center gap-3 text-xs">
              <span className="font-medium">Aksiyon:</span>
              <select
                className="h-8 rounded-md border bg-background px-2 text-xs"
                value={bulkAction}
                onChange={(e) => setBulkAction(e.target.value)}
              >
                <option value="">Seçin</option>
                {BULK_ACTIONS.map((action) => (
                  <option key={action.value} value={action.value}>
                    {action.label}
                  </option>
                ))}
              </select>
              <Button
                size="sm"
                onClick={onRunBulk}
                disabled={!bulkAction || bulkRunning}
              >
                {bulkRunning && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}
                Çalıştır
              </Button>
              {bulkRunning && (
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => {
                    cancelRef.current = true;
                    setBulkCancelRequested(true);
                  }}
                >
                  İptal et
                </Button>
              )}
            </div>

            <div className="flex flex-wrap items-center gap-3 text-xs">
              <span className="font-medium">CSV Export:</span>
              <Button
                size="sm"
                variant="outline"
                onClick={() => exportCsv("filtered")}
              >
                Filtrelenmiş liste (CSV)
              </Button>
              <Button
                size="sm"
                variant="outline"
                disabled={!selectedCaseIds.length}
                onClick={() => exportCsv("selected")}
              >
                Seçili kayıtlar (CSV)
              </Button>
            </div>

            {bulkRunning && (
              <div className="space-y-2 text-xs">
                <div className="flex items-center gap-2">
                  <div className="text-muted-foreground">İlerleme:</div>
                  <div>
                    {bulkProcessed} / {bulkTotal}
                  </div>
                  <div className="flex-1 bg-muted rounded-full h-2">
                    <div
                      className="bg-primary h-2 rounded-full transition-all"
                      style={{
                        width: `${bulkTotal > 0 ? (bulkProcessed / bulkTotal) * 100 : 0}%`,
                      }}
                    />
                  </div>
                </div>
                {bulkCancelRequested && (
                  <div className="text-orange-600">İptal istendi, devam eden istekler tamamlanıyor...</div>
                )}
              </div>
            )}

            {bulkErrorSummary && (
              <div className="text-xs text-destructive bg-destructive/10 p-2 rounded">
                {bulkErrorSummary}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
