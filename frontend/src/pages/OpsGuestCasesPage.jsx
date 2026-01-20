import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Filter, RefreshCw, CheckSquare } from "lucide-react";

import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import SlaTooltip from "../components/ops/SlaTooltip";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { listOpsCases, bulkUpdateOpsCases, apiErrorMessage } from "../lib/opsCases";
import OpsGuestCaseDrawer from "../components/OpsGuestCaseDrawer";

function parseDateSafe(value) {
  if (!value) return null;
  try {
    const s = String(value).slice(0, 10);
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(s);
    let d;
    if (m) {
      const y = Number(m[1]);
      const mo = Number(m[2]) - 1;
      const da = Number(m[3]);
      d = new Date(y, mo, da);
    } else {
      d = new Date(value);
    }
    if (Number.isNaN(d.getTime())) return null;
    return d;
  } catch {
    return null;
  }
}

function daysBetween(a, b) {
  const ms = b.getTime() - a.getTime();
  return Math.floor(ms / (1000 * 60 * 60 * 24));
}

function classifyRisk(caseItem, now) {
  const status = String(caseItem?.status || "").toLowerCase();
  if (!["open", "waiting", "in_progress"].includes(status)) return "na";

  const created = parseDateSafe(caseItem?.created_at);
  if (!created) return "no_date";

  const ageDays = daysBetween(created, now);
  if (ageDays <= 1) return "fresh";
  if (ageDays <= 6) return "active_risk";
  return "sla_breach";
}

const SLA_DAYS = 7;

function normalizeWaitingOn(v) {
  const s = String(v || "").toLowerCase().trim();
  if (!s) return "none";
  if (s.includes("cust")) return "customer";
  if (s.includes("sup")) return "supplier";
  if (s.includes("ops")) return "ops";
  return "other";
}

function RiskBadge({ kind }) {
  if (!kind || kind === "na") return null;
  let label = "";
  let cls = "border text-[9px] px-1.5 py-0.5 rounded-full inline-flex";

  if (kind === "sla_breach") {
    label = "SLA BREACH";
    cls += " bg-red-100 text-red-900 border-red-200";
  } else if (kind === "active_risk") {
    label = "ACTIVE RISK";
    cls += " bg-amber-100 text-amber-900 border-amber-200";
  } else if (kind === "fresh") {
    label = "FRESH";
    cls += " bg-emerald-100 text-emerald-900 border-emerald-200";
  } else if (kind === "no_date") {
    label = "NO DATE";
    cls += " bg-slate-100 text-slate-700 border-slate-200";
  } else {
    label = "N/A";
    cls += " bg-slate-100 text-slate-700 border-slate-200";
  }

  return <span className={cls}>{label}</span>;
}

function WaitingBadge({ waitingOn }) {
  const w = normalizeWaitingOn(waitingOn);
  let label = "";
  let cls = "border text-[9px] px-1.5 py-0.5 rounded-full inline-flex";

  if (w === "customer") {
    label = "WAITING: CUSTOMER";
    cls += " bg-sky-100 text-sky-900 border-sky-200";
  } else if (w === "supplier") {
    label = "WAITING: SUPPLIER";
    cls += " bg-violet-100 text-violet-900 border-violet-200";
  } else if (w === "ops") {
    label = "WAITING: OPS";
    cls += " bg-slate-100 text-slate-900 border-slate-200";
  } else if (w === "other") {
    label = "WAITING: OTHER";
    cls += " bg-slate-100 text-slate-900 border-slate-200";
  } else {
    return null;
  }

  return <span className={cls}>{label}</span>;
}


function OpsGuestCasesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const navigate = useNavigate();

  const [items, setItems] = useState([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [status, setStatus] = useState(searchParams.get("status") || "open");
  const [type, setType] = useState(searchParams.get("type") || "");
  const [source, setSource] = useState(searchParams.get("source") || "");
  const [q, setQ] = useState(searchParams.get("q") || "");

  const [selectedCaseId, setSelectedCaseId] = useState(null);
  const [selectedIds, setSelectedIds] = useState([]);
  const [bulkStatus, setBulkStatus] = useState("no_change");
  const [bulkWaitingOn, setBulkWaitingOn] = useState("no_change");
  const [bulkNote, setBulkNote] = useState("");
  const [bulkLoading, setBulkLoading] = useState(false);
  const [bulkResult, setBulkResult] = useState(null);
  const [bulkError, setBulkError] = useState(null);
  const [bulkApplying, setBulkApplying] = useState(false);
  const [slaFilter, setSlaFilter] = useState("all");

  const loadCases = async (opts = {}) => {
    setLoading(true);
    setError("");
    try {
      const params = {
        status: status === "all" ? undefined : status,
        type: type || undefined,
        source: source || undefined,
        q: q || undefined,
        page,
        page_size: pageSize,
        ...opts,
      };
      const res = await listOpsCases(params);
      setItems(res.items || []);
      setPage(res.page || 1);
      setPageSize(res.page_size || 20);
      setTotal(res.total || 0);

      // URL'yi filtrelerle güncelle (UX için güzel olur)
      const next = new URLSearchParams();
      if (status && status !== "open") next.set("status", status);
      if (type) next.set("type", type);
      if (source) next.set("source", source);
      if (q) next.set("q", q);
      if (page !== 1) next.set("page", String(page));
      setSearchParams(next);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    // page param'ını URL'den oku (ilk yüklemede)
    const pageFromUrl = Number(searchParams.get("page") || "1");
    if (!Number.isNaN(pageFromUrl) && pageFromUrl > 0) {
      setPage(pageFromUrl);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    loadCases();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [status, type, source, page, pageSize]);

  const onRefetch = () => {
    // Özellikle close sonrası listeyi tazelemek için
    loadCases();
  };

  const hasAny = items.length > 0;

  const visibleItems = items.filter((c) => {
    if (!slaFilter || slaFilter === "all") return true;
    const now = new Date();
    const risk = classifyRisk(c, now);
    const waiting = normalizeWaitingOn(c.waiting_on);

    switch (slaFilter) {
      case "sla_breach":
        return risk === "sla_breach";
      case "active_risk":
        return risk === "active_risk";
      case "fresh":
        return risk === "fresh";
      case "waiting_customer":
        return waiting === "customer";
      case "waiting_supplier":
        return waiting === "supplier";
      case "waiting_ops":
        return waiting === "ops";
      default:
        return true;
    }
  });

  const hasVisible = visibleItems.length > 0;

  const toggleSelectAllVisible = () => {
    if (!hasVisible) return;
    const visibleIds = visibleItems.map((c) => c.case_id);
    const allSelected = visibleIds.every((id) => selectedIds.includes(id));
    if (allSelected) {
      setSelectedIds((prev) => prev.filter((id) => !visibleIds.includes(id)));
    } else {
      const next = new Set(selectedIds);
      visibleIds.forEach((id) => next.add(id));
      setSelectedIds(Array.from(next));
    }
  };

  const toggleSingle = (caseId) => {
    setSelectedIds((prev) =>
      prev.includes(caseId) ? prev.filter((id) => id !== caseId) : [...prev, caseId]
    );
  };

  const visibleIdSet = new Set(visibleItems.map((c) => c.case_id));

  const anySelected = selectedIds.length > 0;

  const effectiveSelectedIds = selectedIds.filter((id) => visibleIdSet.has(id));

  const normalizedBulkWaiting = normalizeWaitingOn(
    bulkWaitingOn === "no_change" ? null : bulkWaitingOn,
  );

  const canApplyBulk =
    !bulkApplying &&
    anySelected &&
    ((bulkStatus && bulkStatus !== "no_change") ||
      (bulkWaitingOn && bulkWaitingOn !== "no_change") ||
      String(bulkNote || "").trim().length > 0);

  const applyBulk = async (caseIdsOverride) => {
    const targetIds = (caseIdsOverride && caseIdsOverride.length
      ? caseIdsOverride
      : effectiveSelectedIds);
    if (!targetIds.length || !canApplyBulk) return;

    const patch = {};
    if (bulkStatus && bulkStatus !== "no_change") patch.status = bulkStatus;

    if (bulkWaitingOn && bulkWaitingOn !== "no_change") {
      if (normalizedBulkWaiting === "none") {
        patch.waiting_on = null;
      } else {
        patch.waiting_on = bulkWaitingOn;
      }
    }

    if (String(bulkNote || "").trim().length > 0) patch.note = bulkNote.trim();

    if (!Object.keys(patch).length) {
      return;
    }

    try {
      setBulkApplying(true);
      setBulkError(null);
      const res = await bulkUpdateOpsCases({
        case_ids: targetIds,
        patch,
      });

      setBulkResult(res || null);

      const failedIds = Array.isArray(res?.results)
        ? res.results.filter((r) => r && r.ok === false).map((r) => r.case_id)
        : [];

      if (!failedIds.length) {
        // Tam başarı: seçimi ve inputları sıfırla
        setSelectedIds([]);
        setBulkStatus("no_change");
        setBulkWaitingOn("no_change");
        setBulkNote("");
        // Banner bir süre kalsın, sonra temizlenebilir (opsiyonel)
        if (typeof window !== "undefined") {
          window.setTimeout(() => {
            setBulkResult(null);
          }, 5000);
        }
      } else {
        // Partial success: sadece failed case'ler seçili kalsın
        setSelectedIds(failedIds);
      }

      loadCases();
    } catch (e) {
      setBulkError(apiErrorMessage(e));
    } finally {
      setBulkApplying(false);
    }
  };

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto space-y-4">
      <PageHeader
        title="Case Yönetimi"
        subtitle="Tüm kaynaklardan (guest_portal/ops_panel/system) gelen caseleri tek ekranda yönetin."
        icon={<Filter className="h-6 w-6 text-muted-foreground" />}
        actions={
          <Button
            variant="outline"
            size="sm"
            onClick={() => {
              setPage(1);
              onRefetch();
            }}
            disabled={loading}
          >
            <RefreshCw className="h-4 w-4 mr-1" /> Yenile
          </Button>
        }
      />

      {/* Filter bar */}
      <div className="rounded-2xl border bg-card p-3 md:p-4 flex flex-col md:flex-row gap-3 md:items-end">
        <div className="flex flex-col gap-1 w-full md:w-[180px]">
          <label className="text-xs font-medium text-muted-foreground">Durum</label>
          <Select
            value={status}
            onValueChange={(val) => {
              setStatus(val);
              setPage(1);
            }}
          >
            <SelectTrigger className="h-8 text-sm">
              <SelectValue placeholder="Durum" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="open">A fk</SelectItem>
              <SelectItem value="waiting">Beklemede</SelectItem>
              <SelectItem value="in_progress">Devam ediyor</SelectItem>
              <SelectItem value="closed">Kapal f</SelectItem>
              <SelectItem value="all">Tümü</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1 w-full md:w-[180px]">
          <label className="text-xs font-medium text-muted-foreground">Tip</label>
          <Select
            value={type || "all"}
            onValueChange={(val) => {
              setType(val === "all" ? "" : val);
              setPage(1);
            }}
          >
            <SelectTrigger className="h-8 text-sm">
              <SelectValue placeholder="T1m1" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tümü</SelectItem>
              <SelectItem value="cancel"> İptal talebi</SelectItem>
              <SelectItem value="amend">Değişiklik talebi</SelectItem>
              <SelectItem value="refund">İade</SelectItem>
Ödeme takibi</SelectItem>
              <SelectItem value="voucher_issue">Voucher sorunu</SelectItem>
              <SelectItem value="missing_docs">Eksik evrak</SelectItem>
              <SelectItem value="supplier_approval">Tedarik e7i onay b1</SelectItem>
              <SelectItem value="other">Di f0er</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1 w-full md:w-[180px]">
          <label className="text-xs font-medium text-muted-foreground">Kaynak</label>
          <Select
            value={source || "all"}
            onValueChange={(val) => {
              setSource(val === "all" ? "" : val);
              setPage(1);
            }}
          >
            <SelectTrigger className="h-8 text-sm">
              <SelectValue placeholder="T1m1" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">Tümü</SelectItem>
              <SelectItem value="guest_portal">Guest portal</SelectItem>
              <SelectItem value="ops_panel">Ops panel</SelectItem>
              <SelectItem value="system">Sistem</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="flex flex-col gap-1 flex-1">
          <label className="text-xs font-medium text-muted-foreground">Ara</label>
          <Input
            className="h-8 text-sm"
            placeholder="Case ID veya rezervasyon kodu"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                setPage(1);
                onRefetch();
              }
            }}
          />
        </div>

        <div className="flex gap-2 md:ml-auto">
          <Button
            type="button"
            variant="outline"
            size="sm"
            onClick={() => {
              setStatus("open");
              setType("");
              setSource("");
              setQ("");
              setPage(1);
              onRefetch();
            }}
            disabled={loading}
          >
            Filtreleri s1f1rla
          </Button>
          <Button
            type="button"
            size="sm"
            onClick={() => {
              setPage(1);
              onRefetch();
            }}
            disabled={loading}
          >
            Uygula
          </Button>
        </div>
      </div>

      {/* SLA Queue Filter Bar */}
      <div className="rounded-2xl border bg-card p-3 mb-3 flex flex-wrap items-center gap-2">
        <span className="text-xs font-medium text-muted-foreground mr-2">SLA Queue</span>
        <Button
          type="button"
          size="xs"
          variant={slaFilter === "all" ? "default" : "outline"}
          data-testid="cases-filter-all"
          onClick={() => setSlaFilter("all")}
        >
          All
        </Button>
        <Button
          type="button"
          size="xs"
          variant={slaFilter === "sla_breach" ? "default" : "outline"}
          data-testid="cases-filter-sla-breach"
          onClick={() => setSlaFilter("sla_breach")}
        >
          SLA BREACH
        </Button>
        <Button
          type="button"
          size="xs"
          variant={slaFilter === "active_risk" ? "default" : "outline"}
          data-testid="cases-filter-active-risk"
          onClick={() => setSlaFilter("active_risk")}
        >
          ACTIVE RISK
        </Button>
        <Button
          type="button"
          size="xs"
          variant={slaFilter === "fresh" ? "default" : "outline"}
          data-testid="cases-filter-fresh"
          onClick={() => setSlaFilter("fresh")}
        >
          FRESH
        </Button>
        <Button
          type="button"
          size="xs"
          variant={slaFilter === "waiting_customer" ? "default" : "outline"}
          data-testid="cases-filter-waiting-customer"
          onClick={() => setSlaFilter("waiting_customer")}
        >
          WAITING: CUSTOMER
        </Button>
        <Button
          type="button"
          size="xs"
          variant={slaFilter === "waiting_supplier" ? "default" : "outline"}
          data-testid="cases-filter-waiting-supplier"
          onClick={() => setSlaFilter("waiting_supplier")}
        >
          WAITING: SUPPLIER
        </Button>
        <Button
          type="button"
          size="xs"
          variant={slaFilter === "waiting_ops" ? "default" : "outline"}
          data-testid="cases-filter-waiting-ops"
          onClick={() => setSlaFilter("waiting_ops")}
        >
          WAITING: OPS
        </Button>
      </div>

      {/* Content */}
      <div className="rounded-2xl border bg-card">
        {error ? (
          <div className="p-4">
            <ErrorState
              description={error}
              onRetry={() => {
                setPage(1);
                onRefetch();
              }}
            />
          </div>
        ) : loading && !hasVisible ? (
          <div className="p-6 text-sm text-muted-foreground">Y1kleniyor...</div>
        ) : !hasVisible ? (
          <EmptyState
            title="G1sterilecek case yok"
            description="Se15ftirdifiniz filtrelere uyan bir misafir talebi bulunamad1."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/40 border-b">
                <tr>
                  <th className="px-3 py-2 text-left font-medium text-xs text-muted-foreground w-8">
                    <input
                      type="checkbox"
                      className="h-3 w-3"
                      data-testid="cases-select-all"
                      checked={
                        hasVisible &&
                        visibleItems.every((c) => selectedIds.includes(c.case_id)) &&
                        visibleItems.some((c) => selectedIds.includes(c.case_id))
                      }
                      onChange={toggleSelectAllVisible}
                    />
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-xs text-muted-foreground">Case ID</th>
                  <th className="px-3 py-2 text-left font-medium text-xs text-muted-foreground">
                    Rezervasyon Kodu
                  </th>
                  <th className="px-3 py-2 text-left font-medium text-xs text-muted-foreground">Tip</th>
                  <th className="px-3 py-2 text-left font-medium text-xs text-muted-foreground">Durum</th>
                  <th className="px-3 py-2 text-left font-medium text-xs text-muted-foreground">Kaynak</th>
                  <th className="px-3 py-2 text-left font-medium text-xs text-muted-foreground">
                    Olufturulma
                  </th>
                </tr>
              </thead>
              <tbody>
                {visibleItems.map((c) => {
                  const now = new Date();
                  const risk = classifyRisk(c, now);

                  let rowBg = "";
                  if (risk === "sla_breach") rowBg = "bg-red-50";
                  else if (risk === "active_risk") rowBg = "bg-amber-50";
                  else if (risk === "fresh") rowBg = "bg-emerald-50";
                  else if (risk === "no_date") rowBg = "bg-slate-50";

                  const baseRowClass = [
                    "cursor-pointer hover:bg-muted/40",
                    rowBg,
                  ]
                    .filter(Boolean)
                    .join(" ");

                  const isClosed = String(c.status || "").toLowerCase() === "closed";
                  const dimClass = isClosed ? "opacity-70" : "";

                  const created = c.created_at ? parseDateSafe(c.created_at) : null;

                  return (
                    <tr
                      key={c.case_id}
                      className={baseRowClass}
                      data-testid={`ops-case-row-${c.case_id}`}
                      onClick={() => setSelectedCaseId(c.case_id)}
                    >
                      <td className="px-3 py-2 w-8" onClick={(e) => e.stopPropagation()}>
                        <input
                          type="checkbox"
                          className="h-3 w-3"
                          checked={selectedIds.includes(c.case_id)}
                          onChange={() => toggleSingle(c.case_id)}
                          data-testid={`cases-select-one-${c.case_id}`}
                        />
                      </td>
                      <td className="px-3 py-2 font-mono text-xs text-primary-foreground/90 bg-primary/5">
                        {c.case_id}
                      </td>
                      <td className="px-3 py-2 text-xs">{c.booking_code || "-"}</td>
                      <td className="px-3 py-2 text-xs">
                        {(() => {
                          switch (c.type) {
                            case "cancel":
                              return "30ptal talebi";
                            case "amend":
                              return "Değişiklik talebi";
                            case "refund":
                              return "İade";
                            case "payment_followup":
Ödeme takibi";
                            case "voucher_issue":
                              return "Voucher sorunu";
                            case "missing_docs":
                              return "Eksik evrak";
                            case "supplier_approval":
                              return "Tedarik e7i onay b1";
                            case "other":
                              return "Di f0er";
                            default:
                              return c.type || "-";
                          }
                        })()}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        <div className={`flex flex-col gap-1 ${dimClass}`}>
                          <div>
                            {(() => {
                              switch (c.status) {
                                case "open":
                                  return (
                                    <span className="inline-flex items-center rounded-full bg-emerald-50 text-emerald-700 px-2 py-0.5 text-[11px]">
                                      Af3k
                                    </span>
                                  );
                                case "waiting":
                                  return (
                                    <span className="inline-flex items-center rounded-full bg-amber-50 text-amber-700 px-2 py-0.5 text-[11px]">
                                      Beklemede
                                    </span>
                                  );
                                case "in_progress":
                                  return (
                                    <span className="inline-flex items-center rounded-full bg-blue-50 text-blue-700 px-2 py-0.5 text-[11px]">
                                      Devam ediyor
                                    </span>
                                  );
                                case "closed":
                                default:
                                  return (
                                    <span className="inline-flex items-center rounded-full bg-muted text-muted-foreground px-2 py-0.5 text-[11px]">
                                      Kapalı
                                    </span>
                                  );
                              }
                            })()}
                          </div>
                          <div className="flex flex-wrap gap-1 mt-0.5 items-center">
                            <span data-testid={`risk-badge-${c.case_id}`}>
                              <RiskBadge kind={risk} />
                            </span>
                            <span data-testid={`waiting-badge-${c.case_id}`}>
                              <WaitingBadge waitingOn={c.waiting_on} />
                            </span>
                            <span className="ml-auto">
                              <SlaTooltip
                                slaDays={SLA_DAYS}
                                testId={`sla-tooltip-list-${c.case_id}`}
                              />
                            </span>
                          </div>
                        </div>
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {(() => {
                          switch (c.source) {
                            case "guest_portal":
                              return "Guest portal";
                            case "ops_panel":
                              return "Ops panel";
                            case "system":
                              return "Sistem";
                            default:
                              return c.source || "-";
                          }
                        })()}
                      </td>
                      <td className="px-3 py-2 text-xs text-muted-foreground">
                        {created ? created.toLocaleString("tr-TR") : "-"}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}

        {/* Basit pagination */}
        {hasAny && !error && (
          <div className="flex items-center justify-between px-3 py-2 border-t text-xs text-muted-foreground">
            <span>
              Toplam {total} kay1t
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="sm"
                disabled={page <= 1 || loading}
                onClick={() => {
                  setPage((p) => Math.max(1, p - 1));
                }}
              >
                0nceki
              </Button>
              <span>
                Sayfa {page}
              </span>
              <Button
                variant="outline"
                size="sm"
                disabled={page * pageSize >= total || loading}
                onClick={() => {
                  setPage((p) => p + 1);
                }}
              >
                Sonraki
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Bulk Actions */}
      {anySelected && (
        <div className="rounded-2xl border bg-card p-4">
          <div className="flex items-center gap-4 mb-4">
            <CheckSquare className="h-5 w-5 text-primary" />
            <span className="font-medium text-sm" data-testid="cases-selected-count">
              {selectedIds.length} case seçildi
            </span>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-muted-foreground">Durum Değiştir</label>
              <Select
                value={bulkStatus}
                onValueChange={setBulkStatus}
                disabled={bulkApplying}
              >
                <SelectTrigger className="h-8 text-sm" data-testid="cases-bulk-status">
                  <SelectValue placeholder="Durum seç" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="no_change">Değiştirme</SelectItem>
                  <SelectItem value="open">Açık</SelectItem>
                  <SelectItem value="waiting">Beklemede</SelectItem>
                  <SelectItem value="in_progress">Devam ediyor</SelectItem>
                  <SelectItem value="closed">Kapalı</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-muted-foreground">Bekleme Durumu</label>
              <Select
                value={bulkWaitingOn}
                onValueChange={setBulkWaitingOn}
                disabled={bulkApplying}
              >
                <SelectTrigger className="h-8 text-sm" data-testid="cases-bulk-waiting-on">
                  <SelectValue placeholder="Bekleme durumu seç" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="no_change">Değiştirme</SelectItem>
                  <SelectItem value="customer">Müşteri</SelectItem>
                  <SelectItem value="supplier">Tedarikçi</SelectItem>
                  <SelectItem value="ops">Ops</SelectItem>
                  <SelectItem value="other">Diğer</SelectItem>
                </SelectContent>
              </Select>
            </div>

            <div className="flex flex-col gap-1">
              <label className="text-xs font-medium text-muted-foreground">Not Ekle</label>
              <Input
                className="h-8 text-sm"
                placeholder="Toplu not ekle"
                value={bulkNote}
                onChange={(e) => setBulkNote(e.target.value)}
                disabled={bulkApplying}
                data-testid="cases-bulk-note"
              />
            </div>
          </div>

          {/* Bulk result banner */}
          {(bulkResult || bulkError) && (
            <div
              className="mt-2 rounded-md border bg-muted/40 p-2 text-xs text-muted-foreground space-y-1"
              data-testid="cases-bulk-result"
            >
              {bulkResult && (
                <div>
                  <span data-testid="cases-bulk-result-updated">
                    Updated: {bulkResult.updated || 0}
                  </span>{" "}
                  ·{" "}
                  <span data-testid="cases-bulk-result-failed">
                    Failed: {bulkResult.failed || 0}
                  </span>
                </div>
              )}
              {bulkError && <div className="text-red-700">{bulkError}</div>}
              {Array.isArray(bulkResult?.results) && bulkResult.failed > 0 && (
                <ul
                  className="list-disc pl-4"
                  data-testid="cases-bulk-result-errors"
                >
                  {bulkResult.results
                    .filter((r) => r && r.ok === false)
                    .slice(0, 3)
                    .map((r) => (
                      <li key={r.case_id}>
                        {r.case_id} — {r.error || "Unknown error"}
                      </li>
                    ))}
                </ul>
              )}
            </div>
          )}

          <div
            className="mt-3 flex flex-wrap items-center gap-2"
            aria-busy={bulkApplying ? "true" : "false"}
          >
            <Button
              onClick={() => applyBulk()}
              disabled={!canApplyBulk}
              size="sm"
              data-testid="cases-bulk-apply"
            >
              {bulkApplying ? (
                <span data-testid="cases-bulk-applying">Uygulanıyor...</span>
              ) : (
                "Değişiklikleri Uygula"
              )}
            </Button>
            {bulkResult?.failed > 0 && (
              <Button
                type="button"
                size="sm"
                variant="outline"
                onClick={() => {
                  const failedIds = bulkResult.results
                    .filter((r) => r && r.ok === false)
                    .map((r) => r.case_id);
                  applyBulk(failedIds);
                }}
                disabled={bulkApplying}
                data-testid="cases-bulk-retry-failed"
              >
                Retry failed
              </Button>
            )}
            <Button
              variant="outline"
              onClick={() => setSelectedIds([])}
              size="sm"
              data-testid="cases-bulk-clear"
            >
              Seçimi Temizle
            </Button>
          </div>

          {bulkResult && (
            <div
              className="mt-2 text-[11px] text-muted-foreground"
              data-testid="cases-bulk-last-action"
            >
              Last bulk: updated {bulkResult.updated || 0}, failed {bulkResult.failed || 0}
            </div>
          )}
        </div>
      )}

      <OpsGuestCaseDrawer
        caseId={selectedCaseId}
        open={Boolean(selectedCaseId)}
        onClose={() => setSelectedCaseId(null)}
        onClosed={onRefetch}
      />
    </div>
  );
}

export default OpsGuestCasesPage;
