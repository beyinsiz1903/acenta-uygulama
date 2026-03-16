import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Truck,
  AlertTriangle,
  CheckCircle2,
  Clock,
  Filter,
} from "lucide-react";
import { Card, CardContent } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "../../components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../../components/ui/select";
import { fetchSupplierPayables } from "./lib/financeApi";

const fmt = (v) => new Intl.NumberFormat("tr-TR", { style: "currency", currency: "EUR" }).format(v || 0);

const STATUS_MAP = {
  current: { label: "Güncel", icon: CheckCircle2, color: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300" },
  overdue: { label: "Gecikmiş", icon: AlertTriangle, color: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300" },
  paid: { label: "Ödenmiş", icon: CheckCircle2, color: "bg-teal-100 text-teal-800 dark:bg-teal-900/40 dark:text-teal-300" },
  pending: { label: "Bekliyor", icon: Clock, color: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300" },
};

export default function SupplierPayablesPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState("all");

  const { data, isLoading } = useQuery({
    queryKey: ["supplier-payables", statusFilter],
    queryFn: () => fetchSupplierPayables({ status: statusFilter === "all" ? undefined : statusFilter }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  const payables = data?.payables || [];

  const totalPayable = payables.reduce((s, p) => s + (p.total_payable || 0), 0);
  const totalOutstanding = payables.reduce((s, p) => s + (p.outstanding_amount || 0), 0);
  const totalOverdue = payables.reduce((s, p) => s + (p.overdue_amount || 0), 0);
  const totalPaid = payables.reduce((s, p) => s + (p.total_paid || 0), 0);

  return (
    <div className="space-y-6" data-testid="supplier-payables-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" data-testid="supplier-payables-title">Tedarikçi Borçları</h1>
          <p className="text-sm text-muted-foreground mt-1">Tedarikçi bazlı borç ve ödeme durumları</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => navigate("/app/admin/finance/overview-v2")} data-testid="back-to-overview-btn">
          Genel Bakış
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="supplier-summary-cards">
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Toplam Borç</div>
            <div className="text-xl font-bold">{fmt(totalPayable)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Ödenen</div>
            <div className="text-xl font-bold text-emerald-600">{fmt(totalPaid)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Açık Borç</div>
            <div className="text-xl font-bold">{fmt(totalOutstanding)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Gecikmiş</div>
            <div className="text-xl font-bold text-red-600">{fmt(totalOverdue)}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3" data-testid="supplier-filters">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px] h-9 text-sm" data-testid="supplier-status-filter">
            <SelectValue placeholder="Durum" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">Tüm Durumlar</SelectItem>
            {Object.entries(STATUS_MAP).map(([key, cfg]) => (
              <SelectItem key={key} value={key}>{cfg.label}</SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {/* Payables Table */}
      <Card>
        <CardContent className="p-0" data-testid="supplier-payables-table">
          <div className="overflow-auto border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Tedarikçi</TableHead>
                  <TableHead className="text-xs text-right">Toplam Borç</TableHead>
                  <TableHead className="text-xs text-right">Ödenen</TableHead>
                  <TableHead className="text-xs text-right">Açık Borç</TableHead>
                  <TableHead className="text-xs text-right">Gecikmiş</TableHead>
                  <TableHead className="text-xs text-center">Vade (Gün)</TableHead>
                  <TableHead className="text-xs">Sonraki Vade</TableHead>
                  <TableHead className="text-xs text-center">Rez. Sayısı</TableHead>
                  <TableHead className="text-xs">Durum</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {payables.map((p) => {
                  const cfg = STATUS_MAP[p.status] || STATUS_MAP.current;
                  const paidPct = p.total_payable ? ((p.total_paid / p.total_payable) * 100).toFixed(0) : 0;
                  return (
                    <TableRow key={p.supplier_id} data-testid={`supplier-row-${p.supplier_id}`}>
                      <TableCell>
                        <div className="flex items-center gap-2">
                          <div className="p-1.5 rounded-md bg-muted">
                            <Truck className="h-3.5 w-3.5" />
                          </div>
                          <div>
                            <div className="font-medium text-sm">{p.supplier_name}</div>
                            <div className="text-xs text-muted-foreground font-mono">{p.supplier_id}</div>
                          </div>
                        </div>
                      </TableCell>
                      <TableCell className="text-right font-medium text-sm">{fmt(p.total_payable)}</TableCell>
                      <TableCell className="text-right text-sm">
                        <div>{fmt(p.total_paid)}</div>
                        <div className="text-xs text-muted-foreground">%{paidPct}</div>
                      </TableCell>
                      <TableCell className="text-right font-medium text-sm">{fmt(p.outstanding_amount)}</TableCell>
                      <TableCell className="text-right text-sm">
                        <span className={p.overdue_amount > 0 ? "text-red-600 font-medium" : ""}>
                          {fmt(p.overdue_amount)}
                        </span>
                      </TableCell>
                      <TableCell className="text-center text-sm">{p.payment_terms_days}</TableCell>
                      <TableCell className="text-xs text-muted-foreground">
                        {p.next_due_date || "-"}
                      </TableCell>
                      <TableCell className="text-center text-sm">{p.booking_count}</TableCell>
                      <TableCell>
                        <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
                          <cfg.icon className="h-3 w-3" />
                          {cfg.label}
                        </span>
                      </TableCell>
                    </TableRow>
                  );
                })}
                {payables.length === 0 && (
                  <TableRow>
                    <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                      Tedarikçi borç kaydı bulunamadı
                    </TableCell>
                  </TableRow>
                )}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>

      {/* Payment Progress */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4" data-testid="supplier-progress-cards">
        {payables.map((p) => {
          const paidPct = p.total_payable ? (p.total_paid / p.total_payable) * 100 : 0;
          return (
            <Card key={p.supplier_id}>
              <CardContent className="p-4">
                <div className="flex items-center gap-2 mb-3">
                  <Truck className="h-4 w-4 text-muted-foreground" />
                  <span className="text-sm font-medium">{p.supplier_name}</span>
                </div>
                <div className="w-full bg-muted rounded-full h-2 mb-2">
                  <div
                    className="h-2 rounded-full transition-all duration-500 bg-teal-600"
                    style={{ width: `${Math.min(paidPct, 100)}%` }}
                  />
                </div>
                <div className="flex justify-between text-xs text-muted-foreground">
                  <span>{fmt(p.total_paid)} ödendi</span>
                  <span>%{paidPct.toFixed(0)}</span>
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
