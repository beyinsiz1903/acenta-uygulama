import React, { useEffect, useState, useCallback, useRef } from "react";
import { api, apiErrorMessage, getUser } from "../lib/api";
import { toast } from "../components/ui/sonner";
import PageHeader from "../components/PageHeader";
import ErrorState from "../components/ErrorState";
import { Loader2 } from "lucide-react";

/* ─── Feature Components ─── */
import { RefundQueueList } from "../features/refunds/components/RefundQueueList";
import { RefundDetailPanel } from "../features/refunds/components/RefundDetailPanel";
import { RefundApproveDialog, RefundApproveStep2Dialog, RefundRejectDialog, RefundMarkPaidDialog } from "../features/refunds/components/RefundDialogs";
import { BulkOperationsCard } from "../features/refunds/components/BulkOperationsCard";
import { FilterPresetsBar } from "../features/refunds/components/FilterPresetsBar";
import { exportRefundsCsv } from "../features/refunds/utils";
import { refundsApi } from "../features/refunds/api";

export default function AdminFinanceRefundsPage() {
  const user = getUser();
  const orgId = user?.organization_id || "";
  const myEmail = user?.email || "";

  /* ─── State ─── */
  const [list, setList] = useState([]);
  const [statusFilter, setStatusFilter] = useState("open");
  const [limit, setLimit] = useState(50);
  const [loadingList, setLoadingList] = useState(true);
  const [listError, setListError] = useState("");

  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [selectedCaseIds, setSelectedCaseIds] = useState([]);
  const [caseData, setCaseData] = useState(null);
  const [bookingFinancials, setBookingFinancials] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);

  /* Dialog states */
  const [approveStep1Open, setApproveStep1Open] = useState(false);
  const [approveStep2Open, setApproveStep2Open] = useState(false);
  const [rejectOpen, setRejectOpen] = useState(false);
  const [markPaidOpen, setMarkPaidOpen] = useState(false);

  /* Bulk state */
  const [bulkAction, setBulkAction] = useState("");
  const [bulkRunning, setBulkRunning] = useState(false);
  const [bulkProcessed, setBulkProcessed] = useState(0);
  const [bulkTotal, setBulkTotal] = useState(0);
  const [bulkErrorSummary, setBulkErrorSummary] = useState("");
  const [bulkCancelRequested, setBulkCancelRequested] = useState(false);
  const cancelRef = useRef(false);

  /* Presets */
  const [presets, setPresets] = useState([]);
  const [selectedPresetId, setSelectedPresetId] = useState("");

  const PRESET_STORAGE_KEY = orgId && myEmail
    ? `refunds.filter_presets.v1.${orgId}.${myEmail}` : null;

  useEffect(() => {
    if (!PRESET_STORAGE_KEY) return;
    try {
      const raw = localStorage.getItem(PRESET_STORAGE_KEY);
      if (raw) { const p = JSON.parse(raw); if (Array.isArray(p)) setPresets(p); }
    } catch { /* ignore */ }
  }, [PRESET_STORAGE_KEY]);

  const savePresetsToStorage = (next) => {
    setPresets(next);
    if (PRESET_STORAGE_KEY) try { localStorage.setItem(PRESET_STORAGE_KEY, JSON.stringify(next)); } catch { /* ignore */ }
  };

  const handleSavePreset = (name) => {
    const id = `preset_${Date.now()}`;
    const next = [...presets, { id, name, values: { statusFilter, limit } }];
    savePresetsToStorage(next);
    setSelectedPresetId(id);
  };

  const handleSelectPreset = (presetId) => {
    setSelectedPresetId(presetId);
    const p = presets.find((x) => x.id === presetId);
    if (!p) return;
    const v = p.values || {};
    if (typeof v.statusFilter === "string") setStatusFilter(v.statusFilter);
    if (typeof v.limit === "number") setLimit(v.limit);
  };

  const handleDeletePreset = (presetId) => {
    savePresetsToStorage(presets.filter((p) => p.id !== presetId));
    if (selectedPresetId === presetId) setSelectedPresetId("");
  };

  /* ─── Data Loading ─── */
  const loadList = useCallback(async () => {
    try {
      setLoadingList(true); setListError("");
      const resp = await refundsApi.list({ status: statusFilter, limit });
      setList(resp?.items || []);
    } catch (e) {
      setListError(apiErrorMessage(e));
    } finally {
      setLoadingList(false);
    }
  }, [limit, statusFilter]);

  const loadDetail = useCallback(async (caseId) => {
    if (!caseId) return;
    try {
      setDetailLoading(true); setCaseData(null); setBookingFinancials(null);
      const resp = await refundsApi.detail(caseId);
      setCaseData(resp);
      if (resp?.booking_id) {
        try {
          const fin = await refundsApi.bookingFinancials(resp.booking_id);
          setBookingFinancials(fin);
        } catch { setBookingFinancials(null); }
      }
    } catch { setCaseData(null); setBookingFinancials(null); }
    finally { setDetailLoading(false); }
  }, []);

  useEffect(() => { loadList(); }, [statusFilter, limit, loadList]);

  useEffect(() => {
    if (list?.length > 0) {
      setSelectedCaseId(list[0].case_id);
      loadDetail(list[0].case_id);
      const validIds = new Set(list.map((it) => it.case_id));
      setSelectedCaseIds((prev) => prev.filter((id) => validIds.has(id)));
    } else {
      setSelectedCaseId(null); setCaseData(null); setBookingFinancials(null); setSelectedCaseIds([]);
    }
  }, [list]);

  /* ─── Handlers ─── */
  const onSelectCase = (caseId) => { setSelectedCaseId(caseId); loadDetail(caseId); };

  const onToggleCase = (caseId, checked) => {
    setSelectedCaseIds((prev) => checked
      ? prev.includes(caseId) ? prev : [...prev, caseId]
      : prev.filter((id) => id !== caseId));
  };

  const onToggleAllOnPage = (checked) => {
    if (!list.length) return;
    if (checked) {
      const idsOnPage = list.map((it) => it.case_id);
      setSelectedCaseIds((prev) => { const set = new Set(prev); idsOnPage.forEach((id) => set.add(id)); return Array.from(set); });
    } else {
      const idsOnPage = new Set(list.map((it) => it.case_id));
      setSelectedCaseIds((prev) => prev.filter((id) => !idsOnPage.has(id)));
    }
  };

  const onAfterDecision = async () => {
    await loadList();
    if (selectedCaseId) await loadDetail(selectedCaseId);
  };

  const onCloseCase = async () => {
    if (!caseData?.case_id) return;
    try {
      await refundsApi.close(caseData.case_id, null);
      toast({ title: "Case kapatildi" });
      await onAfterDecision();
    } catch (e) {
      toast({ title: "Kapatma basarisiz", description: apiErrorMessage(e), variant: "destructive" });
    }
  };

  const onExportCsv = (mode) => {
    let rows = mode === "selected"
      ? list.filter((it) => new Set(selectedCaseIds).has(it.case_id))
      : list;
    if (!exportRefundsCsv(rows, mode)) {
      toast({ title: "Export edilecek kayit yok", variant: "destructive" });
    }
  };

  /* ─── Bulk Operations ─── */
  const runBulk = async (runner) => {
    const ids = selectedCaseIds;
    if (!ids.length) return;
    setBulkRunning(true); setBulkProcessed(0); setBulkTotal(ids.length);
    setBulkErrorSummary(""); setBulkCancelRequested(false); cancelRef.current = false;
    const errors = [];
    const concurrency = 3;
    let idx = 0;

    const runNext = async () => {
      if (cancelRef.current || idx >= ids.length) return;
      const caseId = ids[idx++];
      try { await runner(caseId); }
      catch (e) { errors.push({ caseId, message: apiErrorMessage(e) || "Bilinmeyen hata" }); }
      finally { setBulkProcessed((p) => p + 1); if (idx < ids.length) await runNext(); }
    };

    await Promise.all(Array.from({ length: Math.min(concurrency, ids.length) }, () => runNext()));

    if (errors.length) {
      const firstFive = errors.slice(0, 5).map((e) => `${e.caseId}: ${e.message}`).join("; ");
      setBulkErrorSummary(`Hatali: ${errors.length} case. Ilk hatalar: ${firstFive}`);
    } else { setBulkErrorSummary(""); }
    setBulkRunning(false);
  };

  const onRunBulk = async () => {
    if (!bulkAction || !selectedCaseIds.length) return;
    if (!window.confirm(`Secili ${selectedCaseIds.length} case icin '${bulkAction}' aksiyonu calistirilacak. Emin misiniz?`)) return;

    if (bulkAction === "approve_step1") {
      await runBulk(async (caseId) => {
        const data = await refundsApi.detail(caseId);
        if (data?.status && !["open", "pending_approval", "pending_approval_1"].includes(data.status))
          throw new Error(`Bu status icin 1. onay uygun degil: ${data.status}`);
        if (typeof data?.computed?.refundable !== "number") throw new Error("Refundable amount bulunamadi");
        await refundsApi.approveStep1(caseId, data.computed.refundable);
      });
    } else if (bulkAction === "approve_step2") {
      await runBulk((caseId) => refundsApi.approveStep2(caseId, null));
    } else if (bulkAction === "reject") {
      await runBulk((caseId) => refundsApi.reject(caseId, null));
    } else if (bulkAction === "close") {
      await runBulk((caseId) => refundsApi.close(caseId, null));
    }

    await loadList();
    if (selectedCaseId) await loadDetail(selectedCaseId);
  };

  /* ─── Render ─── */
  return (
    <div className="space-y-6" data-testid="admin-finance-refunds-page">
      <PageHeader title="Iade Talepleri" subtitle="Iade talepleri ve ilgili rezervasyon finansal ozeti." />

      {listError && !loadingList && <ErrorState title="Liste yuklenemedi" description={listError} />}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6" style={{ minHeight: "60vh" }}>
        {loadingList ? (
          <div className="flex items-center justify-center"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
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
        <RefundDetailPanel
          caseData={caseData}
          bookingFinancials={bookingFinancials}
          loading={detailLoading}
          onRefresh={() => selectedCaseId && loadDetail(selectedCaseId)}
          onOpenApproveStep1={() => setApproveStep1Open(true)}
          onOpenApproveStep2={() => setApproveStep2Open(true)}
          onOpenReject={() => setRejectOpen(true)}
          onOpenMarkPaid={() => setMarkPaidOpen(true)}
          onCloseCase={onCloseCase}
        />
      </div>

      {/* Filter Presets */}
      <FilterPresetsBar
        presets={presets}
        selectedPresetId={selectedPresetId}
        onSelectPreset={handleSelectPreset}
        onSavePreset={handleSavePreset}
        onDeletePreset={handleDeletePreset}
      />

      {/* Dialogs */}
      <RefundApproveDialog open={approveStep1Open} onOpenChange={setApproveStep1Open} caseData={caseData} onApproved={onAfterDecision} />
      <RefundApproveStep2Dialog open={approveStep2Open} onOpenChange={setApproveStep2Open} caseData={caseData} onApproved={onAfterDecision} />
      <RefundRejectDialog open={rejectOpen} onOpenChange={setRejectOpen} caseData={caseData} onRejected={onAfterDecision} />
      <RefundMarkPaidDialog open={markPaidOpen} onOpenChange={setMarkPaidOpen} caseData={caseData} onMarked={onAfterDecision} />

      {/* Bulk Operations */}
      <BulkOperationsCard
        selectedCaseIds={selectedCaseIds}
        bulkAction={bulkAction}
        setBulkAction={setBulkAction}
        bulkRunning={bulkRunning}
        bulkProcessed={bulkProcessed}
        bulkTotal={bulkTotal}
        bulkErrorSummary={bulkErrorSummary}
        bulkCancelRequested={bulkCancelRequested}
        onRunBulk={onRunBulk}
        onCancelBulk={() => { cancelRef.current = true; setBulkCancelRequested(true); }}
        onExportCsv={onExportCsv}
      />
    </div>
  );
}
