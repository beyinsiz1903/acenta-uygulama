import React, { useEffect, useMemo, useState } from "react";

import PageHeader from "../../components/PageHeader";
import EmptyState from "../../components/EmptyState";
import ErrorState from "../../components/ErrorState";
import { api, apiErrorMessage } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "../../components/ui/select";
import { Badge } from "../../components/ui/badge";
import { Tooltip, TooltipContent, TooltipTrigger, TooltipProvider } from "../../components/ui/tooltip";
import { X, Loader2, AlertTriangle } from "lucide-react";

function formatDateTime(value) {
  if (!value) return "-";
  try {
    const d = new Date(value);
    return d.toLocaleString();
  } catch {
    return String(value);
  }
}

function SeverityBadge({ severity }) {
  if (!severity) return <span className="text-[11px] text-muted-foreground">—</span>;
  
  const variants = {
    critical: "destructive",
    high: "destructive", 
    medium: "default",
    low: "secondary"
  };
  
  return (
    <Badge variant={variants[severity] || "outline"} className="text-[10px] capitalize">
      {severity}
    </Badge>
  );
}

function StatusBadge({ status }) {
  if (!status) return <span className="text-[11px] text-muted-foreground">—</span>;
  
  const variants = {
    open: "destructive",
    resolved: "default"
  };
  
  return (
    <Badge variant={variants[status] || "outline"} className="text-[10px] capitalize">
      {status}
    </Badge>
  );
}

function SupplierHealthBadge({ badge }) {
  if (!badge) {
    return <span className="text-[11px] text-muted-foreground">—</span>;
  }

  const notes = badge.notes || [];

  if (notes.includes("health_not_found")) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge
              variant="outline"
              className="text-[10px] bg-slate-50 text-slate-700 border-slate-200"
              data-testid="ops-incidents-health-no-health"
            >
              NO HEALTH
            </Badge>
          </TooltipTrigger>
          <TooltipContent side="top" className="text-[11px]">
            Health snapshot not found (fail-open).
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  if (badge.circuit_state === "open") {
    return (
      <Badge
        variant="destructive"
        className="text-[10px]"
        data-testid="ops-incidents-health-open"
      >
        Circuit: OPEN
      </Badge>
    );
  }

  if (badge.circuit_state === "closed" || (!badge.circuit_state && (!notes || notes.length === 0))) {
    return (
      <TooltipProvider>
        <Tooltip>
          <TooltipTrigger asChild>
            <Badge
              variant="outline"
              className="text-[10px] bg-emerald-50 text-emerald-900 border-emerald-200"
              data-testid="ops-incidents-health-closed"
            >
              Circuit: CLOSED
            </Badge>
          </TooltipTrigger>
          <TooltipContent side="top" className="text-[11px]">
            Circuit is closed; supplier is allowed for routing.
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  }

  return (
    <Badge variant="outline" className="text-[10px]" data-testid="ops-incidents-health-unknown">
      —
    </Badge>
  );
function SeverityBadge({ severity }) {
  const s = String(severity || "").toLowerCase();
  if (!s) return <span className="text-[11px] text-muted-foreground">-</span>;

  if (s === "critical") {
    return (
      <Badge variant="destructive" className="text-[10px] px-1.5 py-0.5">
        CRITICAL
      </Badge>
    );
  }
  if (s === "high") {
    return (
      <Badge
        variant="outline"
        className="text-[10px] px-1.5 py-0.5 border-red-300 text-red-900 bg-red-50"
      >
        HIGH
      </Badge>
    );
  }
  if (s === "medium") {
    return (
      <Badge
        variant="outline"
        className="text-[10px] px-1.5 py-0.5 border-amber-300 text-amber-900 bg-amber-50"
      >
        MEDIUM
      </Badge>
    );
  }
  return (
    <Badge
      variant="outline"
      className="text-[10px] px-1.5 py-0.5 border-slate-300 text-slate-800 bg-slate-50"
    >
      LOW
    </Badge>
  );
}

function StatusBadge({ status }) {
  const s = String(status || "").toLowerCase();
  if (s === "open") {
    return (
      <Badge
        variant="outline"
        className="text-[10px] px-1.5 py-0.5 border-red-300 text-red-900 bg-red-50"
      >
        OPEN
      </Badge>
    );
  }
  if (s === "resolved") {
    return (
      <Badge
        variant="outline"
        className="text-[10px] px-1.5 py-0.5 border-slate-200 text-slate-700 bg-slate-50"
      >
        RESOLVED
      </Badge>
    );
  }
  return <span className="text-[11px] text-muted-foreground">{status || "-"}</span>;
}


}

export default function AdminOpsIncidentsPage() {
  const [filters, setFilters] = useState({
    type: undefined,
    severity: undefined,
    status: "open",
  });
  const [limit] = useState(50);
  const [offset, setOffset] = useState(0);

  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [selectedIncidentId, setSelectedIncidentId] = useState(null);
  const [drawerOpen, setDrawerOpen] = useState(false);
  const [detail, setDetail] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState("");

  const pageCount = useMemo(() => {
    if (!total || !limit) return 1;
    return Math.max(1, Math.ceil(total / limit));
  }, [total, limit]);

  const currentPage = useMemo(() => {
    if (!limit) return 1;
    return Math.floor(offset / limit) + 1;
  }, [offset, limit]);

  const loadIncidents = async () => {
    setLoading(true);
    setError("");
    try {
      const params = {
        limit,
        offset,
        include_supplier_health: true,
      };
      if (filters.type) params.type = filters.type;
      if (filters.severity) params.severity = filters.severity;
      if (filters.status) params.status = filters.status;

      const resp = await api.get("/admin/ops/incidents", { params });
      const body = resp.data || {};
      setItems(body.items || []);
      setTotal(body.total ?? 0);
    } catch (e) {
      setError(apiErrorMessage(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadIncidents();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters, offset]);

  useEffect(() => {
    if (!drawerOpen || !selectedIncidentId) return;

    const loadDetail = async () => {
      setDetailLoading(true);
      setDetailError("");
      try {
        const resp = await api.get(`/admin/ops/incidents/${selectedIncidentId}`);
        setDetail(resp.data || null);
      } catch (e) {
        setDetailError(apiErrorMessage(e));
        setDetail(null);
      } finally {
        setDetailLoading(false);
      }
    };

    loadDetail();
  }, [drawerOpen, selectedIncidentId]);

  const onChangeFilter = (key, value) => {
    setFilters((prev) => ({
      ...prev,
      [key]: value || undefined,
    }));
    setOffset(0);
  };

  const clearFilters = () => {
    setFilters({
      type: undefined,
      severity: undefined,
      status: undefined,
    });
    setOffset(0);
  };

  const onRowClick = (incident) => {
    if (incident.incident_id === selectedIncidentId && drawerOpen) return;
    setSelectedIncidentId(incident.incident_id);
    setDrawerOpen(true);
  };

  const closeDrawer = () => {
    setDrawerOpen(false);
  };

  const hasRows = items && items.length > 0;

  const canPrev = currentPage > 1;
  const canNext = currentPage < pageCount;

  const goPrev = () => {
    if (!canPrev) return;
    setOffset((prev) => Math.max(0, prev - limit));
  };

  const goNext = () => {
    if (!canNext) return;
    setOffset((prev) => prev + limit);
  };

  return (
    <div className="space-y-4">
      <PageHeader
        title="Ops Incidents"
        subtitle="Risk review ve supplier kaynakl1 ops olaylar1n1 tek ekranda g6rntleyin."
      />

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle className="text-sm">Filters</CardTitle>
        </CardHeader>
        <CardContent className="flex flex-wrap gap-3 text-xs items-end">
          <div className="space-y-1">
            <div className="text-[11px] text-muted-foreground">Status</div>
            <Select
              value={filters.status ?? "all"}
              onValueChange={(v) => onChangeFilter("status", v === "all" ? undefined : v)}
            >
              <SelectTrigger className="h-8 w-40 text-xs" data-testid="ops-incidents-filter-status">
                <SelectValue placeholder="All" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="open">Open</SelectItem>
                <SelectItem value="resolved">Resolved</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <div className="text-[11px] text-muted-foreground">Type</div>
            <Select
              value={filters.type ?? "all"}
              onValueChange={(v) => onChangeFilter("type", v === "all" ? undefined : v)}
            >
              <SelectTrigger className="h-8 w-48 text-xs" data-testid="ops-incidents-filter-type">
                <SelectValue placeholder="All" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="risk_review">risk_review</SelectItem>
                <SelectItem value="supplier_partial_failure">supplier_partial_failure</SelectItem>
                <SelectItem value="supplier_all_failed">supplier_all_failed</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1">
            <div className="text-[11px] text-muted-foreground">Severity</div>
            <Select
              value={filters.severity ?? "all"}
              onValueChange={(v) => onChangeFilter("severity", v === "all" ? undefined : v)}
            >
              <SelectTrigger className="h-8 w-40 text-xs" data-testid="ops-incidents-filter-severity">
                <SelectValue placeholder="All" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All</SelectItem>
                <SelectItem value="critical">critical</SelectItem>
                <SelectItem value="high">high</SelectItem>
                <SelectItem value="medium">medium</SelectItem>
                <SelectItem value="low">low</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="ml-auto flex items-center gap-2 text-[11px] text-muted-foreground">
            <span>
              Page {currentPage} / {pageCount}
            </span>
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-[11px]"
              onClick={goPrev}
              disabled={!canPrev}
            >
              Prev
            </Button>
            <Button
              size="sm"
              variant="outline"
              className="h-7 px-2 text-[11px]"
              onClick={goNext}
              disabled={!canNext}
            >
              Next
            </Button>
          </div>
        </CardContent>
      </Card>

      <Card data-testid="ops-incidents-table">
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <CardTitle className="text-sm flex items-center gap-2">
            Incidents
            {loading && <Loader2 className="h-3 w-3 animate-spin text-muted-foreground" />}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-xs">
          {error && <ErrorState description={error} compact />}

          {!loading && !error && !hasRows && (
            <EmptyState
              title="No incidents"
              description="There are no ops incidents for the selected filters."
              action={
                (filters.type || filters.severity || filters.status) && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={clearFilters}
                    className="text-xs"
                  >
                    Clear filters
                  </Button>
                )
              }
            />
          )}

          {hasRows && (
            <div className="border rounded-md overflow-hidden" data-testid="ops-incidents-rows">
              <div className="grid grid-cols-8 gap-2 bg-muted px-2 py-1 text-[11px] font-semibold text-muted-foreground">
                <div>Created At</div>
                <div>Severity</div>
                <div>Status</div>
                <div>Type</div>
                <div>Summary</div>
                <div>Source</div>
                <div>Supplier Health</div>
                <div>ID</div>
              </div>
              {items.map((inc) => {
                const src = inc.source_ref || {};
                const sourceLabel =
                  src.booking_id || src.session_id || src.offer_token || src.supplier_code || "-";

                return (
                  <button
                    key={inc.incident_id}
                    type="button"
                    onClick={() => onRowClick(inc)}
                    className="grid grid-cols-8 gap-2 border-t px-2 py-1 items-center text-[11px] w-full text-left hover:bg-accent/60 focus:outline-none focus:ring-1 focus:ring-primary/40"
                    data-testid="ops-incidents-row"
                    data-row-id={inc.incident_id}
                  >
                    <div>{formatDateTime(inc.created_at)}</div>
                    <div>
                      <SeverityBadge severity={inc.severity} />
                    </div>
                    <div>
                      <StatusBadge status={inc.status} />
                    </div>
                    <div>{inc.type}</div>
                    <div className="truncate" title={inc.summary}>
                      {inc.summary}
                    </div>
                    <div className="truncate" title={sourceLabel}>
                      {sourceLabel}
                    </div>
                    <div>
                      <SupplierHealthBadge badge={inc.supplier_health} />
                    </div>
                    <div className="font-mono truncate" title={inc.incident_id}>
                      {inc.incident_id}
                    </div>
                  </button>
                );
              })}
            </div>
          )}

          {loading && !hasRows && (
            <div className="border rounded-md overflow-hidden">
              <div className="grid grid-cols-8 gap-2 bg-muted px-2 py-1 text-[11px] font-semibold text-muted-foreground">
                <div>ID</div>
                <div>Type</div>
                <div>Severity</div>
                <div>Status</div>
                <div>Summary</div>
                <div>Source</div>
                <div>Created At</div>
                <div>Supplier Health</div>
              </div>
              {Array.from({ length: 5 }).map((_, i) => (
                <div
                  key={i}
                  className="grid grid-cols-8 gap-2 border-t px-2 py-1 items-center text-[11px] animate-pulse"
                >
                  <div className="h-3 bg-muted rounded w-20"></div>
                  <div className="h-3 bg-muted rounded w-16"></div>
                  <div className="h-3 bg-muted rounded w-12"></div>
                  <div className="h-3 bg-muted rounded w-12"></div>
                  <div className="h-3 bg-muted rounded w-32"></div>
                  <div className="h-3 bg-muted rounded w-16"></div>
                  <div className="h-3 bg-muted rounded w-24"></div>
                  <div className="h-3 bg-muted rounded w-16"></div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {drawerOpen && (
        <div className="fixed inset-0 z-40" data-testid="ops-incident-drawer-root">
          <div
            className="absolute inset-0 bg-black/30 transition-opacity"
            onClick={detailLoading ? undefined : closeDrawer}
          />

          <div
            className="absolute inset-y-0 right-0 w-full max-w-xl bg-background border-l shadow-xl flex flex-col"
            data-testid="ops-incident-drawer"
          >
            <div className="flex items-center justify-between px-4 py-3 border-b">
              <div className="flex flex-col gap-0.5">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                  Ops Incident
                </span>
                <span className="text-sm font-semibold">
                  {detail?.incident_id || selectedIncidentId || "Incident"}
                </span>
              </div>
              <Button
                variant="ghost"
                size="icon"
                onClick={closeDrawer}
                className="h-8 w-8"
                disabled={detailLoading}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4 text-xs">
              {detailLoading ? (
                <div className="flex items-center justify-center py-10 text-sm text-muted-foreground">
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" /> Loading incident...
                </div>
              ) : detailError ? (
                <ErrorState description={detailError} compact />
              ) : !detail ? (
                <div className="text-sm text-muted-foreground py-6">
                  Incident detail not found.
                </div>
              ) : (
                <>
                  <div className="grid gap-3 md:grid-cols-2">
                    <div className="space-y-1">
                      <div className="text-[11px] font-semibold text-muted-foreground">
                        Meta
                      </div>
                      <div className="space-y-0.5">
                        <div>
                          <span className="font-semibold">Type:</span> {detail.type}
                        </div>
                        <div>
                          <span className="font-semibold">Severity:</span> {detail.severity}
                        </div>
                        <div>
                          <span className="font-semibold">Status:</span> {detail.status}
                        </div>
                        <div>
                          <span className="font-semibold">Created:</span> {formatDateTime(detail.created_at)}
                        </div>
                        <div>
                          <span className="font-semibold">Updated:</span> {formatDateTime(detail.updated_at)}
                        </div>
                        <div>
                          <span className="font-semibold">Resolved At:</span> {formatDateTime(detail.resolved_at)}
                        </div>
                      </div>
                    </div>

                    <div className="space-y-1">
                      <div className="text-[11px] font-semibold text-muted-foreground">
                        Source
                      </div>
                      <div className="space-y-0.5">
                        <div>
                          <span className="font-semibold">Booking:</span> {detail.source_ref?.booking_id || "-"}
                        </div>
                        <div>
                          <span className="font-semibold">Session:</span> {detail.source_ref?.session_id || "-"}
                        </div>
                        <div>
                          <span className="font-semibold">Offer token:</span> {detail.source_ref?.offer_token || "-"}
                        </div>
                        <div>
                          <span className="font-semibold">Supplier code:</span> {detail.source_ref?.supplier_code || "-"}
                        </div>
                        <div>
                          <span className="font-semibold">Risk decision:</span> {detail.source_ref?.risk_decision || "-"}
                        </div>
                      </div>
                    </div>
                  </div>

                  <div className="space-y-1">
                    <div className="text-[11px] font-semibold text-muted-foreground">Summary</div>
                    <div className="text-xs text-foreground whitespace-pre-wrap">
                      {detail.summary || "-"}
                    </div>
                  </div>

                  {detail.supplier_health && (
                    <div className="space-y-2" data-testid="ops-incident-drawer-health">
                      <div className="text-[11px] font-semibold text-muted-foreground">
                        Supplier Health
                      </div>
                      <div className="flex flex-wrap items-center gap-2">
                        <SupplierHealthBadge badge={detail.supplier_health} />
                        <span className="text-[11px] text-muted-foreground">
                          Supplier: {detail.supplier_health.supplier_code}
                        </span>
                      </div>

                      <div className="mt-1 grid gap-1 md:grid-cols-2 text-[11px] text-muted-foreground">
                        <div>
                          <span className="font-semibold">Success rate:</span>{" "}
                          {detail.supplier_health.success_rate != null
                            ? `${Math.round(detail.supplier_health.success_rate * 100)}%`
                            : "-"}
                        </div>
                        <div>
                          <span className="font-semibold">Error rate:</span>{" "}
                          {detail.supplier_health.error_rate != null
                            ? `${Math.round(detail.supplier_health.error_rate * 100)}%`
                            : "-"}
                        </div>
                        <div>
                          <span className="font-semibold">Avg latency:</span>{" "}
                          {detail.supplier_health.avg_latency_ms != null
                            ? `${detail.supplier_health.avg_latency_ms} ms`
                            : "-"}
                        </div>
                        <div>
                          <span className="font-semibold">p95 latency:</span>{" "}
                          {detail.supplier_health.p95_latency_ms != null
                            ? `${detail.supplier_health.p95_latency_ms} ms`
                            : "-"}
                        </div>
                        <div className="md:col-span-2">
                          <span className="font-semibold">Last error codes:</span>{" "}
                          {(detail.supplier_health.last_error_codes || []).join(", ") || "-"}
                        </div>
                      </div>

                      {detail.supplier_health.notes && detail.supplier_health.notes.length > 0 && (
                        <div className="mt-1 text-[11px] text-muted-foreground">
                          <span className="font-semibold">Notes:</span>{" "}
                          {detail.supplier_health.notes.join(", ")}
                        </div>
                      )}
                    </div>
                  )}

                  {detail.meta && Object.keys(detail.meta || {}).length > 0 && (
                    <div className="space-y-1">
                      <div className="text-[11px] font-semibold text-muted-foreground">Meta</div>
                      <pre className="bg-muted/40 rounded p-2 text-[10px] overflow-x-auto max-h-60">
                        {JSON.stringify(detail.meta, null, 2)}
                      </pre>
                    </div>
                  )}
                </>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
