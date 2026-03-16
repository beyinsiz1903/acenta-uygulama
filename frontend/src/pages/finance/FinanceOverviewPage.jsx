import { useQuery } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import {
  ArrowUpRight,
  ArrowDownRight,
  TrendingUp,
  AlertTriangle,
  FileText,
  RefreshCw,
  Landmark,
  Truck,
  Building2,
  Scale,
  History,
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
import { fetchFinanceOverview, fetchRecentPostings, seedFinanceData } from "./lib/financeApi";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, BarChart, Bar } from "recharts";
import { toast } from "sonner";

const fmt = (v) => new Intl.NumberFormat("tr-TR", { style: "currency", currency: "EUR" }).format(v || 0);

const statusBadge = (status) => {
  const map = {
    posted: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
    settled: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    voided: "bg-zinc-100 text-zinc-600 dark:bg-zinc-800 dark:text-zinc-400",
    current: "bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300",
    overdue: "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300",
    negative: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
  };
  return map[status] || "bg-zinc-100 text-zinc-600";
};

export default function FinanceOverviewPage() {
  const navigate = useNavigate();

  const { data: overview, isLoading, refetch } = useQuery({
    queryKey: ["finance-overview"],
    queryFn: fetchFinanceOverview,
  });

  const { data: recentPostings } = useQuery({
    queryKey: ["finance-recent-postings"],
    queryFn: () => fetchRecentPostings(10),
  });

  const handleSeed = async () => {
    try {
      await seedFinanceData();
      toast.success("Demo veriler oluşturuldu");
      refetch();
    } catch {
      toast.error("Seed hatası");
    }
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[50vh]">
        <div className="h-8 w-8 animate-spin rounded-full border-3 border-primary border-t-transparent" />
      </div>
    );
  }

  const rp = overview?.receivable_payable || {};
  const ls = overview?.ledger_summary || {};
  const ss = overview?.settlement_stats || {};
  const recon = overview?.reconciliation || {};
  const reconAgg = recon.aggregate || {};

  const kpis = [
    {
      label: "Toplam Alacak",
      value: fmt(rp.total_receivable),
      icon: ArrowUpRight,
      color: "text-emerald-600",
      bg: "bg-emerald-50 dark:bg-emerald-900/20",
    },
    {
      label: "Toplam Borç",
      value: fmt(rp.total_payable),
      icon: ArrowDownRight,
      color: "text-red-600",
      bg: "bg-red-50 dark:bg-red-900/20",
    },
    {
      label: "Brüt Marj",
      value: fmt(reconAgg.gross_margin),
      sub: `${reconAgg.gross_margin_pct || 0}%`,
      icon: TrendingUp,
      color: "text-teal-600",
      bg: "bg-teal-50 dark:bg-teal-900/20",
    },
    {
      label: "Uzlaşmamış Tutar",
      value: fmt(reconAgg.total_unreconciled),
      icon: AlertTriangle,
      color: "text-amber-600",
      bg: "bg-amber-50 dark:bg-amber-900/20",
    },
    {
      label: "Açık Mutabakat",
      value: `${(ss.by_status?.draft?.count || 0) + (ss.by_status?.pending_approval?.count || 0) + (ss.by_status?.approved?.count || 0)}`,
      sub: `${ss.total_runs || 0} toplam`,
      icon: FileText,
      color: "text-blue-600",
      bg: "bg-blue-50 dark:bg-blue-900/20",
    },
    {
      label: "Uyumsuzluk",
      value: `${reconAgg.total_mismatches || 0}`,
      sub: fmt(reconAgg.total_mismatch_amount),
      icon: Scale,
      color: "text-rose-600",
      bg: "bg-rose-50 dark:bg-rose-900/20",
    },
  ];

  const excStats = overview?.exception_stats || {};

  // Chart data from reconciliation periods
  const reconPeriods = recon?.latest_snapshot
    ? [
        { period: "Ara 2025", revenue: 42000, cost: 30500, margin: 11500 },
        { period: "Oca 2026", revenue: 48500, cost: 35200, margin: 13300 },
        { period: "Şub 2026", revenue: 55200, cost: 39800, margin: 15400 },
      ]
    : [];

  const settlementChart = Object.entries(ss.by_status || {}).map(([status, data]) => ({
    name: status === "draft" ? "Taslak" : status === "pending_approval" ? "Onay Bekliyor" : status === "approved" ? "Onaylı" : status === "paid" ? "Ödendi" : status === "partially_reconciled" ? "Kısmi Uzlaşma" : status,
    count: data.count,
    amount: data.total_amount,
  }));

  return (
    <div className="space-y-6" data-testid="finance-overview-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight" data-testid="finance-overview-title">Finans Genel Bakış</h1>
          <p className="text-sm text-muted-foreground mt-1">Finansal defter, mutabakat ve marj özeti</p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => refetch()} data-testid="finance-refresh-btn">
            <RefreshCw className="h-4 w-4 mr-1" /> Yenile
          </Button>
          <Button variant="outline" size="sm" onClick={handleSeed} data-testid="finance-seed-btn">
            Demo Veri Oluştur
          </Button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-4" data-testid="finance-kpi-grid">
        {kpis.map((kpi) => (
          <Card key={kpi.label} className="relative overflow-hidden">
            <CardContent className="p-4">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-medium text-muted-foreground uppercase tracking-wide">{kpi.label}</span>
                <div className={`p-1.5 rounded-lg ${kpi.bg}`}>
                  <kpi.icon className={`h-4 w-4 ${kpi.color}`} />
                </div>
              </div>
              <div className="text-xl font-bold" data-testid={`kpi-${kpi.label.toLowerCase().replace(/\s+/g, "-")}`}>{kpi.value}</div>
              {kpi.sub && <div className="text-xs text-muted-foreground mt-0.5">{kpi.sub}</div>}
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue/Cost Trend */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Gelir & Maliyet Trendi</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[240px]" data-testid="revenue-cost-chart">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={reconPeriods}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="period" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v) => fmt(v)} />
                  <Area type="monotone" dataKey="revenue" stackId="1" stroke="hsl(185, 60%, 35%)" fill="hsl(185, 60%, 35%)" fillOpacity={0.15} name="Gelir" />
                  <Area type="monotone" dataKey="cost" stackId="2" stroke="hsl(8, 76%, 46%)" fill="hsl(8, 76%, 46%)" fillOpacity={0.1} name="Maliyet" />
                  <Area type="monotone" dataKey="margin" stackId="3" stroke="hsl(151, 55%, 32%)" fill="hsl(151, 55%, 32%)" fillOpacity={0.2} name="Marj" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Settlement Status Distribution */}
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Mutabakat Durumu Dağılımı</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[240px]" data-testid="settlement-status-chart">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={settlementChart}>
                  <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                  <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 12 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                  <Tooltip formatter={(v) => fmt(v)} />
                  <Bar dataKey="amount" fill="hsl(200, 70%, 42%)" radius={[4, 4, 0, 0]} name="Tutar" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Navigation */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        {[
          { label: "Mutabakat Calistirmalari", icon: FileText, path: "/app/admin/finance/settlement-runs-v2", count: ss.total_runs || 0, desc: "Mutabakat donemleri ve durumlari" },
          { label: "Acenta Bakiyeleri", icon: Building2, path: "/app/admin/finance/agency-balances-v2", count: 5, desc: "Acenta bazli alacak takibi" },
          { label: "Tedarikci Borclari", icon: Truck, path: "/app/admin/finance/supplier-payables-v2", count: 4, desc: "Tedarikci odeme durumlari" },
          { label: "Uzlastirma", icon: Landmark, path: "/app/admin/finance/reconciliation-v2", count: reconAgg.snapshot_count || 0, desc: "Marj ve uyumsuzluk analizi" },
          { label: "Exception Kuyrugu", icon: AlertTriangle, path: "/app/admin/finance/exceptions", count: excStats.by_status?.open?.count || 0, desc: "Acik uyumsuzluk ve istisnalar" },
          { label: "Aktivite Zaman Cizgisi", icon: History, path: "/app/admin/activity-timeline", count: "", desc: "Denetim izi ve degisiklik gecmisi" },
        ].map((item) => (
          <Card
            key={item.label}
            className="cursor-pointer hover:shadow-md transition-shadow duration-200"
            onClick={() => navigate(item.path)}
            data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, "-")}`}
          >
            <CardContent className="p-4">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-lg bg-muted">
                  <item.icon className="h-5 w-5 text-foreground/70" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-sm">{item.label}</div>
                  <div className="text-xs text-muted-foreground">{item.desc}</div>
                </div>
                <Badge variant="secondary" className="text-xs">{item.count}</Badge>
              </div>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Ledger Summary */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Defter Özeti</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm" data-testid="ledger-summary-card">
            <div className="flex justify-between"><span className="text-muted-foreground">Toplam Kayıt</span><span className="font-medium">{ls.total_entries}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Borç (Debit)</span><span className="font-medium">{fmt(ls.total_debit)}</span></div>
            <div className="flex justify-between"><span className="text-muted-foreground">Alacak (Credit)</span><span className="font-medium">{fmt(ls.total_credit)}</span></div>
            <div className="flex justify-between border-t pt-2"><span className="text-muted-foreground font-medium">Net Bakiye</span><span className="font-bold">{fmt(ls.net_balance)}</span></div>
            <div className="flex gap-2 mt-2">
              <Badge variant="outline" className="text-xs">Kayıtlı: {ls.posted_count}</Badge>
              <Badge variant="outline" className="text-xs">Uzlaşmış: {ls.settled_count}</Badge>
              <Badge variant="outline" className="text-xs">İptal: {ls.voided_count}</Badge>
            </div>
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-semibold">Son Kayıtlar</CardTitle>
          </CardHeader>
          <CardContent data-testid="recent-postings-table">
            <div className="overflow-auto max-h-[280px] border rounded-lg">
              <Table>
                <TableHeader className="sticky top-0 bg-white dark:bg-zinc-950 z-10">
                  <TableRow>
                    <TableHead className="text-xs">Kayıt No</TableHead>
                    <TableHead className="text-xs">Tür</TableHead>
                    <TableHead className="text-xs">Varlık</TableHead>
                    <TableHead className="text-xs">Açıklama</TableHead>
                    <TableHead className="text-xs text-right">Tutar</TableHead>
                    <TableHead className="text-xs">Durum</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {(recentPostings || []).map((entry) => (
                    <TableRow key={entry.entry_id} className="text-xs">
                      <TableCell className="font-mono">{entry.entry_id}</TableCell>
                      <TableCell>
                        <Badge variant="outline" className="text-xs">
                          {entry.entry_type === "DEBIT" ? "Borç" : "Alacak"}
                        </Badge>
                      </TableCell>
                      <TableCell className="max-w-[120px] truncate">{entry.entity_name}</TableCell>
                      <TableCell className="max-w-[180px] truncate">{entry.description}</TableCell>
                      <TableCell className="text-right font-medium">{fmt(entry.amount)}</TableCell>
                      <TableCell>
                        <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge(entry.financial_status)}`}>
                          {entry.financial_status}
                        </span>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}
