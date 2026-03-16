import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../../components/ui/card";
import { Button } from "../../../components/ui/button";
import { Loader2 } from "lucide-react";

const BULK_ACTIONS = [
  { value: "approve_step1", label: "1. Onay (approve_step1)" },
  { value: "approve_step2", label: "2. Onay (approve_step2)" },
  { value: "reject", label: "Reddet" },
  { value: "close", label: "Kapat" },
];

export function BulkOperationsCard({
  selectedCaseIds,
  bulkAction,
  setBulkAction,
  bulkRunning,
  bulkProcessed,
  bulkTotal,
  bulkErrorSummary,
  bulkCancelRequested,
  onRunBulk,
  onCancelBulk,
  onExportCsv,
}) {
  if (!selectedCaseIds.length) return null;

  return (
    <Card className="border-dashed" data-testid="bulk-operations-card">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm font-medium">Bulk Operations</CardTitle>
        <p className="text-xs text-muted-foreground">{selectedCaseIds.length} case secili</p>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="flex flex-wrap items-center gap-3 text-xs">
          <span className="font-medium">Aksiyon:</span>
          <select
            data-testid="bulk-action-select"
            className="h-8 rounded-md border bg-background px-2 text-xs"
            value={bulkAction}
            onChange={(e) => setBulkAction(e.target.value)}
          >
            <option value="">Secin</option>
            {BULK_ACTIONS.map((action) => (
              <option key={action.value} value={action.value}>{action.label}</option>
            ))}
          </select>
          <Button size="sm" onClick={onRunBulk} disabled={!bulkAction || bulkRunning} data-testid="bulk-run-btn">
            {bulkRunning && <Loader2 className="h-4 w-4 mr-2 animate-spin" />}Calistir
          </Button>
          {bulkRunning && (
            <Button size="sm" variant="outline" onClick={onCancelBulk} data-testid="bulk-cancel-btn">Iptal et</Button>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-3 text-xs">
          <span className="font-medium">CSV Export:</span>
          <Button size="sm" variant="outline" onClick={() => onExportCsv("filtered")} data-testid="export-filtered-btn">Filtrelenmis liste (CSV)</Button>
          <Button size="sm" variant="outline" disabled={!selectedCaseIds.length} onClick={() => onExportCsv("selected")} data-testid="export-selected-btn">Secili kayitlar (CSV)</Button>
        </div>

        {bulkRunning && (
          <div className="space-y-2 text-xs">
            <div className="flex items-center gap-2">
              <div className="text-muted-foreground">Ilerleme:</div>
              <div>{bulkProcessed} / {bulkTotal}</div>
              <div className="flex-1 bg-muted rounded-full h-2">
                <div className="bg-primary h-2 rounded-full transition-all" style={{ width: `${bulkTotal > 0 ? (bulkProcessed / bulkTotal) * 100 : 0}%` }} />
              </div>
            </div>
            {bulkCancelRequested && (
              <div className="text-orange-600">Iptal istendi, devam eden istekler tamamlaniyor...</div>
            )}
          </div>
        )}

        {bulkErrorSummary && (
          <div className="text-xs text-destructive bg-destructive/10 p-2 rounded" data-testid="bulk-error-summary">{bulkErrorSummary}</div>
        )}
      </CardContent>
    </Card>
  );
}
