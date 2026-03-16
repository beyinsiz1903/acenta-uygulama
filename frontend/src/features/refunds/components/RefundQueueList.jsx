import React, { useEffect, useMemo, useRef } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "../../../components/ui/table";
import { Badge } from "../../../components/ui/badge";
import { Input } from "../../../components/ui/input";
import EmptyState from "../../../components/EmptyState";
import { RefundStatusBadge } from "./RefundBadges";

export function RefundQueueList({
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
  const selectAllRef = useRef(null);
  const idsOnPage = useMemo(() => items.map((it) => it.case_id), [items]);
  const selectedSet = useMemo(() => new Set(selectedCaseIds), [selectedCaseIds]);
  const selectedOnPage = idsOnPage.filter((id) => selectedSet.has(id)).length;

  useEffect(() => {
    if (!selectAllRef.current) return;
    selectAllRef.current.indeterminate =
      selectedOnPage > 0 && selectedOnPage < items.length;
  }, [selectedOnPage, items.length]);

  return (
    <Card className="h-full flex flex-col" data-testid="refund-queue-list">
      <CardHeader className="space-y-3">
        <div className="flex items-center justify-between gap-3">
          <div>
            <CardTitle className="text-sm font-medium">Iade Kuyrugu</CardTitle>
            <p className="text-2xs text-muted-foreground mt-0.5">
              Sec kutusu: bu sayfadaki kayitlari secer (tum filtrelenmis kayitlari degil).
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Ops ekibi icin acik iade case listesi.
            </p>
          </div>
          <div className="flex flex-col gap-1 items-end">
            <div className="space-y-1 flex items-center gap-2">
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Durum</div>
                <select
                  data-testid="refund-status-filter"
                  className="h-8 rounded-md border bg-background px-2 text-xs"
                  value={statusFilter}
                  onChange={(e) => onChangeStatus(e.target.value)}
                >
                  <option value="all">Tumu</option>
                  <option value="open">Acik / Beklemede</option>
                  <option value="closed">Kapali</option>
                </select>
              </div>
              <div className="space-y-1">
                <div className="text-xs text-muted-foreground">Limit</div>
                <Input
                  data-testid="refund-limit-input"
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
        </div>
      </CardHeader>
      <CardContent className="flex-1 overflow-y-auto">
        {items.length === 0 ? (
          <EmptyState
            title="Henuz iade talebi yok"
            description="Henuz bir iade talebi olusturulmamis."
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
                      aria-label="Sayfadaki tum case'leri sec"
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
                  <TableHead className="text-xs text-right">Iade Edilebilir</TableHead>
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
                      data-testid={`refund-row-${it.case_id}`}
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
                          aria-label="Case sec"
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
                        <RefundStatusBadge status={it.status} />
                      </TableCell>
                      <TableCell className="text-xs">
                        {it.decision || "-"}
                      </TableCell>
                      <TableCell className="text-xs">
                        {it.updated_at ? new Date(it.updated_at).toLocaleString() : "-"}
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
