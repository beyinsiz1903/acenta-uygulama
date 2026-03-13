import React, { useState, useEffect, useCallback } from "react";
import {
  AlertTriangle, CheckCircle2, XCircle, RefreshCw, Loader2, Search,
  BarChart3, Clock, ArrowUpDown, FileWarning, ShieldAlert, Filter
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Input } from "../../components/ui/input";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "../../components/ui/table";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../../components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import { toast } from "sonner";
import {
  getReconciliationMismatches, getBookingMetrics, getOrgAudit,
} from "../../lib/unifiedBooking";

function formatPrice(amount, currency = "TRY") {
  if (!amount && amount !== 0) return "-";
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency }).format(amount);
}

function formatSupplierName(code) {
  return (code || "").replace("real_", "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

const SEVERITY_CONFIG = {
  critical: { color: "bg-red-100 text-red-800 border-red-200", icon: XCircle },
  high: { color: "bg-orange-100 text-orange-800 border-orange-200", icon: AlertTriangle },
  medium: { color: "bg-amber-100 text-amber-800 border-amber-200", icon: FileWarning },
  low: { color: "bg-blue-100 text-blue-800 border-blue-200", icon: ShieldAlert },
};

function getSeverity(mismatch) {
  const priceDiff = Math.abs(mismatch.price_diff_pct || 0);
  if (mismatch.status_mismatch) return "critical";
  if (priceDiff > 10) return "high";
  if (priceDiff > 5) return "medium";
  return "low";
}

// ==================== KPI CARDS ====================
function MetricsCards({ metrics }) {
  const cards = [
    {
      label: "Toplam Rezervasyon",
      value: metrics?.booking_attempts_total || 0,
      icon: BarChart3,
      color: "text-blue-600",
    },
    {
      label: "Basarili",
      value: metrics?.booking_success_total || 0,
      icon: CheckCircle2,
      color: "text-green-600",
    },
    {
      label: "Basarisiz",
      value: metrics?.booking_failure_total || 0,
      icon: XCircle,
      color: "text-red-600",
    },
    {
      label: "Fallback Tetiklenmesi",
      value: metrics?.fallback_trigger_total || 0,
      icon: RefreshCw,
      color: "text-amber-600",
    },
    {
      label: "Fiyat Sapma",
      value: metrics?.price_drift_total || 0,
      icon: AlertTriangle,
      color: "text-orange-600",
    },
    {
      label: "Iptal Edilen",
      value: metrics?.revalidation_abort_total || 0,
      icon: ShieldAlert,
      color: "text-violet-600",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-4" data-testid="metrics-cards">
      {cards.map((c, idx) => (
        <Card key={idx} data-testid={`metric-card-${idx}`}>
          <CardContent className="pt-4 pb-3 px-4">
            <div className="flex items-center justify-between mb-1">
              <c.icon className={`h-4 w-4 ${c.color}`} />
            </div>
            <p className="text-2xl font-bold font-mono">{c.value}</p>
            <p className="text-[10px] text-muted-foreground mt-0.5">{c.label}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ==================== MISMATCHES TABLE ====================
function MismatchesTable({ mismatches, filterSeverity }) {
  const filtered = filterSeverity === "all"
    ? mismatches
    : mismatches.filter(m => getSeverity(m) === filterSeverity);

  if (filtered.length === 0) {
    return (
      <Card className="border-dashed" data-testid="no-mismatches">
        <CardContent className="py-8 text-center text-muted-foreground text-sm">
          <CheckCircle2 className="h-8 w-8 mx-auto mb-2 text-green-500 opacity-40" />
          Uyumsuzluk bulunamadi
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="border rounded-lg overflow-auto max-h-[50vh]" data-testid="mismatches-table">
      <Table>
        <TableHeader className="sticky top-0 bg-white dark:bg-background z-10">
          <TableRow>
            <TableHead className="text-xs">Onem</TableHead>
            <TableHead className="text-xs">Booking ID</TableHead>
            <TableHead className="text-xs">Supplier</TableHead>
            <TableHead className="text-xs">Dahili Durum</TableHead>
            <TableHead className="text-xs">Supplier Durum</TableHead>
            <TableHead className="text-xs">Fiyat Farki</TableHead>
            <TableHead className="text-xs">Tarih</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {filtered.map((m, idx) => {
            const severity = getSeverity(m);
            const SevIcon = SEVERITY_CONFIG[severity].icon;
            return (
              <TableRow key={idx} data-testid={`mismatch-row-${idx}`}>
                <TableCell>
                  <Badge variant="outline" className={`text-[10px] ${SEVERITY_CONFIG[severity].color}`}>
                    <SevIcon className="h-3 w-3 mr-1" />
                    {severity}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono text-xs">
                  {(m.internal_booking_id || "").slice(0, 8)}...
                </TableCell>
                <TableCell>
                  <Badge variant="outline" className="text-[10px]">
                    {formatSupplierName(m.supplier_code)}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant="secondary" className="text-[10px]">
                    {m.internal_status || "-"}
                  </Badge>
                </TableCell>
                <TableCell>
                  <Badge variant={m.status_mismatch ? "destructive" : "secondary"} className="text-[10px]">
                    {m.supplier_status || "-"}
                  </Badge>
                </TableCell>
                <TableCell className="font-mono text-xs">
                  {m.price_diff_pct ? `${m.price_diff_pct > 0 ? "+" : ""}${m.price_diff_pct.toFixed(2)}%` : "-"}
                </TableCell>
                <TableCell className="text-xs text-muted-foreground">
                  {m.checked_at ? new Date(m.checked_at).toLocaleString("tr-TR") : "-"}
                </TableCell>
              </TableRow>
            );
          })}
        </TableBody>
      </Table>
    </div>
  );
}

// ==================== AUDIT TRAIL ====================
function AuditTrailTable({ events }) {
  if (!events || events.length === 0) {
    return (
      <Card className="border-dashed" data-testid="no-audit-events">
        <CardContent className="py-8 text-center text-muted-foreground text-sm">
          <Clock className="h-8 w-8 mx-auto mb-2 opacity-40" />
          Audit kaydi bulunamadı
        </CardContent>
      </Card>
    );
  }

  const EVENT_COLORS = {
    booking_attempt: "bg-blue-100 text-blue-700",
    booking_confirmed: "bg-green-100 text-green-700",
    booking_failed: "bg-red-100 text-red-700",
    booking_primary_failed: "bg-orange-100 text-orange-700",
    fallback_success: "bg-amber-100 text-amber-700",
    fallback_failed: "bg-red-100 text-red-700",
    price_revalidation: "bg-violet-100 text-violet-700",
    unified_search: "bg-cyan-100 text-cyan-700",
    booking_aborted_price: "bg-red-100 text-red-700",
  };

  return (
    <div className="border rounded-lg overflow-auto max-h-[50vh]" data-testid="audit-trail-table">
      <Table>
        <TableHeader className="sticky top-0 bg-white dark:bg-background z-10">
          <TableRow>
            <TableHead className="text-xs">Olay</TableHead>
            <TableHead className="text-xs">Supplier</TableHead>
            <TableHead className="text-xs">Booking ID</TableHead>
            <TableHead className="text-xs">Detay</TableHead>
            <TableHead className="text-xs">Tarih</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {events.slice(0, 100).map((evt, idx) => (
            <TableRow key={idx} data-testid={`audit-row-${idx}`}>
              <TableCell>
                <Badge variant="outline" className={`text-[10px] ${EVENT_COLORS[evt.event_type] || "bg-gray-100 text-gray-700"}`}>
                  {evt.event_type}
                </Badge>
              </TableCell>
              <TableCell className="text-xs">
                {formatSupplierName(evt.supplier_code)}
              </TableCell>
              <TableCell className="font-mono text-xs">
                {evt.booking_id ? `${evt.booking_id.slice(0, 8)}...` : "-"}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground max-w-[200px] truncate">
                {evt.details ? JSON.stringify(evt.details).slice(0, 80) : "-"}
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {evt.timestamp ? new Date(evt.timestamp).toLocaleString("tr-TR") : "-"}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// ==================== MAIN PAGE ====================
export default function ReconciliationDashboardPage() {
  const [loading, setLoading] = useState(true);
  const [metrics, setMetrics] = useState(null);
  const [mismatches, setMismatches] = useState([]);
  const [summary, setSummary] = useState(null);
  const [auditEvents, setAuditEvents] = useState([]);
  const [filterSeverity, setFilterSeverity] = useState("all");
  const [activeTab, setActiveTab] = useState("overview");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [metricsData, mismatchData, auditData] = await Promise.all([
        getBookingMetrics().catch(() => null),
        getReconciliationMismatches().catch(() => ({ mismatches: [], summary: {} })),
        getOrgAudit().catch(() => ({ events: [] })),
      ]);
      setMetrics(metricsData);
      setMismatches(mismatchData?.mismatches || []);
      setSummary(mismatchData?.summary || {});
      setAuditEvents(auditData?.events || []);
    } catch (err) {
      toast.error("Veri yuklenemedi");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="space-y-6" data-testid="reconciliation-dashboard">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Mutabakat & Izleme</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Booking durumu, supplier uyumsuzluklari ve audit trail
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={fetchData}
          disabled={loading}
          data-testid="refresh-btn"
        >
          <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
          Yenile
        </Button>
      </div>

      {loading && !metrics ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <span className="ml-2 text-sm text-muted-foreground">Yukleniyor...</span>
        </div>
      ) : (
        <>
          <MetricsCards metrics={metrics} />

          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList>
              <TabsTrigger value="overview" data-testid="tab-overview">
                Uyumsuzluklar
                {mismatches.length > 0 && (
                  <Badge variant="destructive" className="ml-1.5 text-[10px] h-4 px-1">
                    {mismatches.length}
                  </Badge>
                )}
              </TabsTrigger>
              <TabsTrigger value="audit" data-testid="tab-audit">
                Audit Trail
                {auditEvents.length > 0 && (
                  <Badge variant="secondary" className="ml-1.5 text-[10px] h-4 px-1">
                    {auditEvents.length}
                  </Badge>
                )}
              </TabsTrigger>
            </TabsList>

            <TabsContent value="overview" className="space-y-4 mt-4">
              {/* Summary cards */}
              {summary && (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4" data-testid="reconciliation-summary">
                  <Card>
                    <CardContent className="pt-3 pb-2 px-4">
                      <p className="text-[10px] text-muted-foreground">Toplam Kontrol</p>
                      <p className="text-lg font-bold font-mono">{summary.total_checked || 0}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-3 pb-2 px-4">
                      <p className="text-[10px] text-muted-foreground">Uyumlu</p>
                      <p className="text-lg font-bold font-mono text-green-600">{summary.matched || 0}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-3 pb-2 px-4">
                      <p className="text-[10px] text-muted-foreground">Uyumsuz</p>
                      <p className="text-lg font-bold font-mono text-red-600">{summary.mismatched || 0}</p>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-3 pb-2 px-4">
                      <p className="text-[10px] text-muted-foreground">Bekleyen</p>
                      <p className="text-lg font-bold font-mono text-amber-600">{summary.pending || 0}</p>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Filter */}
              <div className="flex items-center gap-3">
                <Select value={filterSeverity} onValueChange={setFilterSeverity}>
                  <SelectTrigger className="w-[180px]" data-testid="filter-severity">
                    <Filter className="h-3 w-3 mr-1" />
                    <SelectValue placeholder="Onem filtrele" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">Tum Seviyeler</SelectItem>
                    <SelectItem value="critical">Kritik</SelectItem>
                    <SelectItem value="high">Yuksek</SelectItem>
                    <SelectItem value="medium">Orta</SelectItem>
                    <SelectItem value="low">Dusuk</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <MismatchesTable mismatches={mismatches} filterSeverity={filterSeverity} />
            </TabsContent>

            <TabsContent value="audit" className="mt-4">
              <AuditTrailTable events={auditEvents} />
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
