import React, { useEffect, useState } from "react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { Filter, RefreshCw } from "lucide-react";

import PageHeader from "../components/PageHeader";
import EmptyState from "../components/EmptyState";
import ErrorState from "../components/ErrorState";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../components/ui/select";
import { listOpsGuestCases, apiErrorMessage } from "../lib/opsCases";
import OpsGuestCaseDrawer from "../components/OpsGuestCaseDrawer";

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
      const res = await listOpsGuestCases(params);
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

  return (
    <div className="p-4 md:p-6 max-w-6xl mx-auto space-y-4">
      <PageHeader
        title="Guest Cases"
        subtitle="Misafir portal1ndan gelen iptal ve defifiklik taleplerini y1netin."
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
              <SelectItem value="open">Af1k</SelectItem>
              <SelectItem value="closed">Kapal1</SelectItem>
              <SelectItem value="all">T1m1</SelectItem>
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
              <SelectItem value="all">T1m1</SelectItem>
              <SelectItem value="cancel">0ptal talebi</SelectItem>
              <SelectItem value="amend">Defifiklik talebi</SelectItem>
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
              <SelectItem value="">T1m1</SelectItem>
              <SelectItem value="guest_portal">Guest portal</SelectItem>
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
        ) : loading && !hasAny ? (
          <div className="p-6 text-sm text-muted-foreground">Y1kleniyor...</div>
        ) : !hasAny ? (
          <EmptyState
            title="G1sterilecek case yok"
            description="Se15ftirdifiniz filtrelere uyan bir misafir talebi bulunamad1."
          />
        ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full text-sm">
              <thead className="bg-muted/40 border-b">
                <tr>
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
                {items.map((c) => {
                  const created = c.created_at ? new Date(c.created_at) : null;
                  return (
                    <tr
                      key={c.case_id}
                      className="cursor-pointer hover:bg-muted/40"
                      onClick={() => setSelectedCaseId(c.case_id)}
                    >
                      <td className="px-3 py-2 font-mono text-xs text-primary-foreground/90 bg-primary/5">
                        {c.case_id}
                      </td>
                      <td className="px-3 py-2 text-xs">{c.booking_code || "-"}</td>
                      <td className="px-3 py-2 text-xs">
                        {c.type === "cancel" ? "0ptal talebi" : c.type === "amend" ? "Defifiklik" : c.type}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {c.status === "open" ? (
                          <span className="inline-flex items-center rounded-full bg-emerald-50 text-emerald-700 px-2 py-0.5 text-[11px]">
                            Af1k
                          </span>
                        ) : (
                          <span className="inline-flex items-center rounded-full bg-muted text-muted-foreground px-2 py-0.5 text-[11px]">
                            Kapal1
                          </span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-xs">
                        {c.source === "guest_portal" ? "Guest portal" : c.source || "-"}
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
