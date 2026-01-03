import React from "react";
import { Card, CardHeader, CardTitle, CardContent, CardFooter } from "./ui/card";
import { Badge } from "./ui/badge";
import { Separator } from "./ui/separator";
import { Button } from "./ui/button";
import { Select, SelectTrigger, SelectValue, SelectContent, SelectItem } from "./ui/select";
import { FileText, Percent, Ticket, Send } from "lucide-react";
import { formatMoney } from "../lib/format";

export function FinanceSummaryCard({
  gross,
  commissionPercent,
  commissionAmount,
  netToHotel,
  paymentStatus,
  onStatusChange,
  onSave,
  onDownloadPdf,
}) {
  const prettyStatus = (paymentStatus || "-").replace("_", " ");

  return (
    <Card data-testid="finance-summary-card" className="bg-card/80 backdrop-blur-sm">
      <CardHeader className="pb-2">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base md:text-lg">Finansal Özet</CardTitle>
          <Badge variant="secondary" className="uppercase tracking-wide text-[10px]">
            Snapshot
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Brüt</span>
          <span className="font-semibold tabular-nums">
            {formatMoney(gross || 0, "TRY")}
          </span>
        </div>
        <div className="flex items-start justify-between">
          <div className="flex items-center gap-2">
            <span className="text-muted-foreground">Komisyon</span>
            <Percent className="h-3.5 w-3.5 text-muted-foreground" />
          </div>
          <div className="text-right">
            <div className="font-semibold tabular-nums">
              {formatMoney(commissionAmount || 0, "TRY")}
            </div>
            <div className="text-xs text-muted-foreground">
              %{commissionPercent ?? 0}
            </div>
          </div>
        </div>
        <Separator />
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Otele Net</span>
          <span className="font-semibold tabular-nums">
            {formatMoney(netToHotel || 0, "TRY")}
          </span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-muted-foreground">Ödeme Durumu</span>
          <Badge variant="outline" className="capitalize">
            {prettyStatus}
          </Badge>
        </div>
      </CardContent>
      <CardFooter className="flex flex-col sm:flex-row gap-2 justify-between">
        <div className="flex-1">
          <Select value={paymentStatus} onValueChange={onStatusChange}>
            <SelectTrigger data-testid="payment-status-select" className="w-full">
              <SelectValue placeholder="Ödeme durumu seçin" />
            </SelectTrigger>
            <SelectContent align="end">
              <SelectItem value="unpaid">Unpaid</SelectItem>
              <SelectItem value="partially_paid">Partially paid</SelectItem>
              <SelectItem value="paid">Paid</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="flex gap-2 justify-end">
          <Button
            data-testid="payment-status-save-button"
            onClick={onSave}
            disabled={!paymentStatus}
          >
            Kaydet
          </Button>
          <Button
            data-testid="self-billing-download-button"
            variant="outline"
            onClick={onDownloadPdf}
          >
            <FileText className="h-4 w-4 mr-2" /> PDF
          </Button>
        </div>
      </CardFooter>
    </Card>
  );
}
