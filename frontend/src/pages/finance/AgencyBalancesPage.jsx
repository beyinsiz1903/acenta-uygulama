import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  Building2,
  AlertTriangle,
  CheckCircle2,
  TrendingDown,
  Filter,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
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
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "../../components/ui/tooltip";
import { fetchAgencyBalances } from "./lib/financeApi";

const fmt = (v) => new Intl.NumberFormat("tr-TR", { style: "currency", currency: "EUR" }).format(v || 0);

const STATUS_MAP = {
  current: { label: "Güncel", icon: CheckCircle2, color: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300" },
  overdue: { label: "Gecikmiş", icon: AlertTriangle, color: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300" },
  negative: { label: "Negatif Bakiye", icon: TrendingDown, color: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300" },
  credit: { label: "Kredi", icon: CheckCircle2, color: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300" },
};

export default function AgencyBalancesPage() {
  const navigate = useNavigate();
  const [statusFilter, setStatusFilter] = useState("all");

  const { data, isLoading } = useQuery({
    queryKey: ["agency-balances", statusFilter],
    queryFn: () => fetchAgencyBalances({ status: statusFilter === "all" ? undefined : statusFilter }),
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  const balances = data?.balances || [];

  // Summary computations
  const totalReceivable = balances.reduce((s, b) => s + (b.total_receivable || 0), 0);
  const totalOutstanding = balances.reduce((s, b) => s + (b.outstanding_balance || 0), 0);
  const totalOverdue = balances.reduce((s, b) => s + (b.overdue_amount || 0), 0);
  const overdueCount = balances.filter((b) => b.status === "overdue").length;
  const negativeCount = balances.filter((b) => b.status === "negative").length;

  return (
    <div className="space-y-6" data-testid="agency-balances-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" data-testid="agency-balances-title">Acenta Bakiyeleri</h1>
          <p className="text-sm text-muted-foreground mt-1">Acenta bazlı alacak ve bakiye takibi</p>
        </div>
        <Button variant="outline" size="sm" onClick={() => navigate("/app/admin/finance/overview-v2")} data-testid="back-to-overview-btn">
          Genel Bakış
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4" data-testid="agency-summary-cards">
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Toplam Alacak</div>
            <div className="text-xl font-bold">{fmt(totalReceivable)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Açık Bakiye</div>
            <div className="text-xl font-bold">{fmt(totalOutstanding)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Gecikmiş Tutar</div>
            <div className="text-xl font-bold text-red-600">{fmt(totalOverdue)}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Gecikmiş Acenta</div>
            <div className="text-xl font-bold text-red-600">{overdueCount}</div>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="text-xs text-muted-foreground uppercase tracking-wide mb-1">Negatif Bakiye</div>
            <div className="text-xl font-bold text-amber-600">{negativeCount}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3" data-testid="agency-filters">
        <Filter className="h-4 w-4 text-muted-foreground" />
        <Select value={statusFilter} onValueChange={setStatusFilter}>
          <SelectTrigger className="w-[180px] h-9 text-sm" data-testid="agency-status-filter">
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

      {/* Balances Table */}
      <Card>
        <CardContent className="p-0" data-testid="agency-balances-table">
          <div className="overflow-auto border rounded-lg">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead className="text-xs">Acenta</TableHead>
                  <TableHead className="text-xs text-right">Toplam Alacak</TableHead>
                  <TableHead className="text-xs text-right">Tahsil Edilen</TableHead>
                  <TableHead className="text-xs text-right">Açık Bakiye</TableHead>
                  <TableHead className="text-xs text-right">Gecikmiş</TableHead>
                  <TableHead className="text-xs text-right">Kredi Limiti</TableHead>
                  <TableHead className="text-xs text-center">Rez. Sayısı</TableHead>
                  <TableHead className="text-xs">Durum</TableHead>
                  <TableHead className="text-xs">Son Ödeme</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                <TooltipProvider>
                  {balances.map((b) => {
                    const cfg = STATUS_MAP[b.status] || STATUS_MAP.current;
                    const utilization = b.credit_limit ? ((b.outstanding_balance / b.credit_limit) * 100).toFixed(0) : 0;
                    return (
                      <TableRow key={b.agency_id} data-testid={`agency-row-${b.agency_id}`}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className="p-1.5 rounded-md bg-muted">
                              <Building2 className="h-3.5 w-3.5" />
                            </div>
                            <div>
                              <div className="font-medium text-sm">{b.agency_name}</div>
                              <div className="text-xs text-muted-foreground font-mono">{b.agency_id}</div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell className="text-right font-medium text-sm">{fmt(b.total_receivable)}</TableCell>
                        <TableCell className="text-right text-sm">{fmt(b.total_collected)}</TableCell>
                        <TableCell className="text-right font-medium text-sm">
                          <span className={b.outstanding_balance < 0 ? "text-amber-600" : b.outstanding_balance > 0 ? "" : "text-emerald-600"}>
                            {fmt(b.outstanding_balance)}
                          </span>
                        </TableCell>
                        <TableCell className="text-right text-sm">
                          <span className={b.overdue_amount > 0 ? "text-red-600 font-medium" : ""}>
                            {fmt(b.overdue_amount)}
                          </span>
                        </TableCell>
                        <TableCell className="text-right text-sm">
                          <Tooltip>
                            <TooltipTrigger asChild>
                              <span>{fmt(b.credit_limit)}</span>
                            </TooltipTrigger>
                            <TooltipContent>Kullanım: %{utilization}</TooltipContent>
                          </Tooltip>
                        </TableCell>
                        <TableCell className="text-center text-sm">{b.booking_count}</TableCell>
                        <TableCell>
                          <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${cfg.color}`}>
                            <cfg.icon className="h-3 w-3" />
                            {cfg.label}
                          </span>
                        </TableCell>
                        <TableCell className="text-xs text-muted-foreground">
                          {b.last_payment_date ? new Date(b.last_payment_date).toLocaleDateString("tr-TR") : "-"}
                        </TableCell>
                      </TableRow>
                    );
                  })}
                  {balances.length === 0 && (
                    <TableRow>
                      <TableCell colSpan={9} className="text-center py-8 text-muted-foreground">
                        Acenta bakiye kaydı bulunamadı
                      </TableCell>
                    </TableRow>
                  )}
                </TooltipProvider>
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
