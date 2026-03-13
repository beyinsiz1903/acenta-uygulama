import React, { useState, useEffect, useCallback } from "react";
import {
  TrendingUp, DollarSign, RefreshCw, Loader2,
  BarChart3, Users, ShoppingCart, Globe, Activity,
  ArrowUp, ArrowDown, Minus, Target, Layers,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import {
  Select, SelectTrigger, SelectValue, SelectContent, SelectItem,
} from "../../components/ui/select";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "../../components/ui/table";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import { toast } from "sonner";
import {
  getBusinessKPI, getRevenueForecast, getAgencyRevenueAnalytics,
  getSupplierRevenueAnalytics, getDestinationRevenue,
} from "../../lib/unifiedBooking";

function fmtPrice(amt, cur = "TRY") {
  if (!amt && amt !== 0) return "-";
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: cur }).format(amt);
}

function supplierLabel(code) {
  return (code || "").replace("real_", "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

// ========================= GMV CARDS =========================
function GMVCards({ gmv, commission }) {
  const cards = [
    { label: "GMV (Brut Hacim)", value: fmtPrice(gmv.gmv), icon: DollarSign, color: "text-emerald-600", bg: "bg-emerald-50" },
    { label: "Platform Geliri", value: fmtPrice(commission?.total_margin || gmv.platform_revenue), icon: TrendingUp, color: "text-violet-600", bg: "bg-violet-50" },
    { label: "Toplam Rezervasyon", value: gmv.total_bookings, icon: ShoppingCart, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Ort. Rez. Degeri", value: fmtPrice(gmv.avg_booking_value), icon: Target, color: "text-amber-600", bg: "bg-amber-50" },
    { label: "Aktif Acenta", value: gmv.unique_agencies, icon: Users, color: "text-teal-600", bg: "bg-teal-50" },
    { label: "Aktif Supplier", value: gmv.unique_suppliers, icon: Layers, color: "text-indigo-600", bg: "bg-indigo-50" },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="gmv-cards">
      {cards.map((c, i) => (
        <Card key={i} data-testid={`gmv-card-${i}`}>
          <CardContent className="pt-3 pb-2 px-3">
            <div className={`inline-flex items-center justify-center h-7 w-7 rounded-lg ${c.bg} mb-1.5`}>
              <c.icon className={`h-3.5 w-3.5 ${c.color}`} />
            </div>
            <p className="text-lg font-bold font-mono">{c.value}</p>
            <p className="text-[10px] text-muted-foreground">{c.label}</p>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}

// ========================= CONVERSION FUNNEL MINI =========================
function ConversionFunnelMini({ funnel }) {
  if (!funnel) return null;
  const steps = [
    { key: "search_event", label: "Arama", color: "bg-blue-500" },
    { key: "result_view_event", label: "Goruntuleme", color: "bg-indigo-500" },
    { key: "supplier_select_event", label: "Secim", color: "bg-violet-500" },
    { key: "booking_start_event", label: "Rez. Baslat", color: "bg-amber-500" },
    { key: "booking_confirm_event", label: "Onay", color: "bg-green-500" },
  ];
  const max = Math.max(...steps.map(s => funnel[s.key] || 0), 1);

  return (
    <div className="space-y-2" data-testid="conversion-funnel-mini">
      {steps.map((s) => {
        const count = funnel[s.key] || 0;
        const pct = (count / max) * 100;
        return (
          <div key={s.key} className="flex items-center gap-3">
            <span className="text-xs w-24 text-muted-foreground truncate">{s.label}</span>
            <div className="flex-1 h-5 bg-muted rounded-full overflow-hidden">
              <div className={`h-full ${s.color} rounded-full transition-all flex items-center justify-end pr-2`} style={{ width: `${Math.max(pct, 8)}%` }}>
                <span className="text-[10px] text-white font-mono">{count}</span>
              </div>
            </div>
          </div>
        );
      })}
      {funnel.search_to_confirm_rate != null && (
        <p className="text-xs text-muted-foreground mt-1">
          Arama-Onay Donusum: <span className="font-mono font-bold text-foreground">%{funnel.search_to_confirm_rate}</span>
        </p>
      )}
    </div>
  );
}

// ========================= FORECAST =========================
function ForecastPanel({ forecast }) {
  if (!forecast) return null;

  const TrendIcon = ({ trend }) => {
    if (trend === "up") return <ArrowUp className="h-3 w-3 text-green-500" />;
    if (trend === "down") return <ArrowDown className="h-3 w-3 text-red-500" />;
    return <Minus className="h-3 w-3 text-muted-foreground" />;
  };

  return (
    <div className="space-y-4" data-testid="forecast-panel">
      {/* Revenue forecast */}
      <div>
        <h4 className="text-sm font-medium mb-2">Gelir Tahmini</h4>
        <div className="grid grid-cols-3 gap-3">
          {(forecast.revenue_forecast || []).map((f, i) => (
            <Card key={i} data-testid={`revenue-forecast-${i}`}>
              <CardContent className="p-3">
                <p className="text-[10px] text-muted-foreground">Ay {f.period}</p>
                <p className="text-base font-bold font-mono">{fmtPrice(f.predicted)}</p>
                <div className="flex items-center gap-1 mt-1">
                  <TrendIcon trend={f.trend} />
                  <Badge variant="outline" className="text-[9px] h-4">{f.confidence}</Badge>
                  {f.growth_rate !== undefined && (
                    <span className="text-[10px] text-muted-foreground">%{f.growth_rate}</span>
                  )}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Booking forecast */}
      <div>
        <h4 className="text-sm font-medium mb-2">Rezervasyon Tahmini</h4>
        <div className="grid grid-cols-3 gap-3">
          {(forecast.booking_forecast || []).map((f, i) => (
            <Card key={i} data-testid={`booking-forecast-${i}`}>
              <CardContent className="p-3">
                <p className="text-[10px] text-muted-foreground">Ay {f.period}</p>
                <p className="text-base font-bold font-mono">{Math.round(f.predicted)}</p>
                <div className="flex items-center gap-1 mt-1">
                  <TrendIcon trend={f.trend} />
                  <Badge variant="outline" className="text-[9px] h-4">{f.confidence}</Badge>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Supplier projections */}
      {(forecast.supplier_projections || []).length > 0 && (
        <div>
          <h4 className="text-sm font-medium mb-2">Supplier Projeksiyonlari</h4>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Supplier</TableHead>
                  <TableHead className="text-right">30 Gun Gelir</TableHead>
                  <TableHead className="text-right">Aylik Ort.</TableHead>
                  <TableHead className="text-right">Projeksiyon</TableHead>
                  <TableHead className="text-center">Trend</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {forecast.supplier_projections.map((s) => (
                  <TableRow key={s.supplier_code}>
                    <TableCell className="font-medium">{supplierLabel(s.supplier_code)}</TableCell>
                    <TableCell className="text-right font-mono">{fmtPrice(s.revenue_30d)}</TableCell>
                    <TableCell className="text-right font-mono">{fmtPrice(s.monthly_avg_90d)}</TableCell>
                    <TableCell className="text-right font-mono">{fmtPrice(s.projected_total)}</TableCell>
                    <TableCell className="text-center">
                      <TrendIcon trend={s.trend} />
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        </div>
      )}
    </div>
  );
}

// ========================= AGENCY TABLE =========================
function AgencyTable({ agencies }) {
  if (!agencies.length) return <p className="text-muted-foreground text-sm p-4">Henuz veri yok.</p>;

  return (
    <div className="overflow-x-auto" data-testid="agency-table">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Acenta ID</TableHead>
            <TableHead className="text-center">Rezervasyon</TableHead>
            <TableHead className="text-right">Gelir</TableHead>
            <TableHead className="text-right">Ort. Deger</TableHead>
            <TableHead>Tercih Edilen Supplier</TableHead>
            <TableHead>Urun Tipleri</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {agencies.map((a) => (
            <TableRow key={a.organization_id} data-testid={`agency-row-${a.organization_id}`}>
              <TableCell className="font-mono text-xs">{a.organization_id?.slice(0, 12)}...</TableCell>
              <TableCell className="text-center font-bold">{a.total_bookings}</TableCell>
              <TableCell className="text-right font-mono">{fmtPrice(a.total_revenue)}</TableCell>
              <TableCell className="text-right font-mono">{fmtPrice(a.avg_booking_value)}</TableCell>
              <TableCell>
                {(a.preferred_suppliers || []).map((s) => (
                  <Badge key={s.supplier} variant="secondary" className="text-[9px] mr-1">
                    {supplierLabel(s.supplier)} ({s.count})
                  </Badge>
                ))}
              </TableCell>
              <TableCell>
                {(a.product_types || []).map((t) => (
                  <Badge key={t} variant="outline" className="text-[9px] mr-1">{t}</Badge>
                ))}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// ========================= TOP SUPPLIERS =========================
function TopSuppliersPanel({ suppliers }) {
  if (!suppliers.length) return <p className="text-muted-foreground text-sm p-4">Henuz veri yok.</p>;

  return (
    <div className="space-y-3" data-testid="top-suppliers-panel">
      {suppliers.map((s, i) => (
        <div key={s.supplier_code} className="flex items-center gap-3 p-3 border rounded-lg" data-testid={`top-supplier-${i}`}>
          <div className="flex items-center justify-center h-8 w-8 rounded-full bg-muted font-bold text-sm">
            {i + 1}
          </div>
          <div className="flex-1 min-w-0">
            <p className="font-medium text-sm">{supplierLabel(s.supplier_code)}</p>
            <p className="text-xs text-muted-foreground">{s.total_bookings} rez. | Pay: %{s.revenue_share_pct}</p>
          </div>
          <div className="text-right">
            <p className="font-mono font-bold">{fmtPrice(s.total_revenue)}</p>
            <p className="text-[10px] text-muted-foreground">Ort: {fmtPrice(s.avg_booking_value)}</p>
          </div>
        </div>
      ))}
    </div>
  );
}

// ========================= MAIN PAGE =========================
export default function RevenueOptimizationPage() {
  const [days, setDays] = useState("30");
  const [loading, setLoading] = useState(true);
  const [kpi, setKpi] = useState(null);
  const [forecast, setForecast] = useState(null);
  const [agencies, setAgencies] = useState([]);
  const [suppliers, setSuppliers] = useState([]);
  const [destinations, setDestinations] = useState([]);
  const [activeTab, setActiveTab] = useState("overview");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [kpiRes, forecastRes, agencyRes, supplierRes, destRes] = await Promise.all([
        getBusinessKPI(parseInt(days)),
        getRevenueForecast(3),
        getAgencyRevenueAnalytics(parseInt(days)),
        getSupplierRevenueAnalytics(parseInt(days)),
        getDestinationRevenue(parseInt(days)),
      ]);
      setKpi(kpiRes);
      setForecast(forecastRes);
      setAgencies(agencyRes.agencies || []);
      setSuppliers(supplierRes.suppliers || []);
      setDestinations(destRes.destinations || []);
    } catch (err) {
      toast.error("Veri yuklenemedi");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="revenue-optimization-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Gelir Optimizasyonu</h1>
          <p className="text-sm text-muted-foreground mt-1">
            GMV, platform geliri, acenta buyumesi ve gelir tahminleri
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={days} onValueChange={setDays}>
            <SelectTrigger className="w-[140px] h-9" data-testid="revenue-period-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Son 7 Gun</SelectItem>
              <SelectItem value="30">Son 30 Gun</SelectItem>
              <SelectItem value="90">Son 90 Gun</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading} data-testid="revenue-refresh-btn">
            {loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <RefreshCw className="h-4 w-4" />}
          </Button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <>
          {/* GMV Summary */}
          <GMVCards gmv={kpi?.gmv || {}} commission={kpi?.commission} />

          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList data-testid="revenue-tabs">
              <TabsTrigger value="overview" data-testid="rev-tab-overview">Genel Bakis</TabsTrigger>
              <TabsTrigger value="forecast" data-testid="rev-tab-forecast">Tahmin</TabsTrigger>
              <TabsTrigger value="agencies" data-testid="rev-tab-agencies">Acenta Analizi</TabsTrigger>
              <TabsTrigger value="suppliers" data-testid="rev-tab-suppliers">Supplier Geliri</TabsTrigger>
            </TabsList>

            {/* OVERVIEW */}
            <TabsContent value="overview">
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                {/* Funnel */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Activity className="h-4 w-4" /> Donusum Hunisi
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <ConversionFunnelMini funnel={kpi?.funnel || {}} />
                  </CardContent>
                </Card>

                {/* Top Suppliers */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <BarChart3 className="h-4 w-4" /> En Iyi Supplier'lar
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <TopSuppliersPanel suppliers={(kpi?.top_suppliers || []).slice(0, 5)} />
                  </CardContent>
                </Card>

                {/* Destinations */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Globe className="h-4 w-4" /> Populer Destinasyonlar
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {destinations.length > 0 ? (
                      <div className="space-y-2">
                        {destinations.map((d, i) => (
                          <div key={i} className="flex items-center justify-between p-2 border rounded" data-testid={`destination-${i}`}>
                            <span className="font-medium text-sm">{d.destination}</span>
                            <Badge variant="secondary">{d.search_count} arama</Badge>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-muted-foreground text-sm">Henuz veri yok.</p>
                    )}
                  </CardContent>
                </Card>

                {/* Profitability */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-base flex items-center gap-2">
                      <Target className="h-4 w-4" /> Karlilik Siralamasi
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {(kpi?.profitability || []).length > 0 ? (
                      <div className="space-y-2">
                        {(kpi?.profitability || []).map((p, i) => (
                          <div key={i} className="flex items-center justify-between p-2 border rounded" data-testid={`profit-rank-${i}`}>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-xs bg-muted px-1.5 py-0.5 rounded">{i + 1}</span>
                              <span className="font-medium text-sm">{supplierLabel(p.supplier_code)}</span>
                            </div>
                            <div className="flex items-center gap-2">
                              <span className="font-mono text-sm font-bold">{p.profitability_score}</span>
                              <Badge variant="outline" className="text-[9px]">{(p.tier || "").toUpperCase()}</Badge>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-muted-foreground text-sm">Henuz veri yok.</p>
                    )}
                  </CardContent>
                </Card>
              </div>
            </TabsContent>

            {/* FORECAST */}
            <TabsContent value="forecast">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <TrendingUp className="h-4 w-4" /> Gelir ve Rezervasyon Tahmini
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <ForecastPanel forecast={forecast} />
                </CardContent>
              </Card>
            </TabsContent>

            {/* AGENCIES */}
            <TabsContent value="agencies">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Users className="h-4 w-4" /> Acenta Gelir Analizi
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <AgencyTable agencies={agencies} />
                </CardContent>
              </Card>
            </TabsContent>

            {/* SUPPLIER REVENUE */}
            <TabsContent value="suppliers">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <DollarSign className="h-4 w-4" /> Supplier Gelir Detaylari
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <TopSuppliersPanel suppliers={suppliers} />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
