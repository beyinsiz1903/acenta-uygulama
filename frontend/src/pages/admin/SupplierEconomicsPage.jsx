import React, { useState, useEffect, useCallback } from "react";
import {
  TrendingUp, DollarSign, Award, RefreshCw, Loader2,
  BarChart3, ArrowUp, ArrowDown, Minus, Layers, Shield, Zap,
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
  getSupplierEconomics, getProfitabilityScores, getMarkupRules,
  upsertMarkupRule, deleteMarkupRule, getCommissionSummary,
} from "../../lib/unifiedBooking";

function fmtPrice(amt, cur = "TRY") {
  if (!amt && amt !== 0) return "-";
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: cur }).format(amt);
}

function supplierLabel(code) {
  return (code || "").replace("real_", "").replace(/_/g, " ").replace(/\b\w/g, c => c.toUpperCase());
}

const TIER_STYLES = {
  platinum: "bg-violet-100 text-violet-800 border-violet-300",
  gold: "bg-amber-100 text-amber-800 border-amber-300",
  silver: "bg-gray-100 text-gray-700 border-gray-300",
  bronze: "bg-orange-100 text-orange-700 border-orange-300",
};

// ========================= COMMISSION SUMMARY =========================
function CommissionSummaryCards({ data }) {
  const cards = [
    { label: "Toplam Maliyet", value: fmtPrice(data.total_supplier_cost), icon: Layers, color: "text-slate-600", bg: "bg-slate-50" },
    { label: "Toplam Satis", value: fmtPrice(data.total_sell_price), icon: DollarSign, color: "text-green-600", bg: "bg-green-50" },
    { label: "Platform Komisyon", value: fmtPrice(data.total_platform_commission), icon: Award, color: "text-violet-600", bg: "bg-violet-50" },
    { label: "Platform Markup", value: fmtPrice(data.total_platform_markup), icon: TrendingUp, color: "text-blue-600", bg: "bg-blue-50" },
    { label: "Toplam Marj", value: fmtPrice(data.total_margin), icon: BarChart3, color: "text-emerald-600", bg: "bg-emerald-50" },
    { label: "Ort. Marj %", value: `%${data.avg_margin_pct}`, icon: Zap, color: "text-amber-600", bg: "bg-amber-50" },
  ];
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3" data-testid="commission-summary-cards">
      {cards.map((c, i) => (
        <Card key={i} data-testid={`commission-card-${i}`}>
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

// ========================= PROFITABILITY TABLE =========================
function ProfitabilityTable({ scores }) {
  if (!scores.length) return <p className="text-muted-foreground text-sm p-4">Henuz veri yok.</p>;

  return (
    <div className="overflow-x-auto" data-testid="profitability-table">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Supplier</TableHead>
            <TableHead className="text-center">Skor</TableHead>
            <TableHead className="text-center">Tier</TableHead>
            <TableHead className="text-center">Komisyon</TableHead>
            <TableHead className="text-center">Basari</TableHead>
            <TableHead className="text-center">Gecikme</TableHead>
            <TableHead className="text-center">Iptal Riski</TableHead>
            <TableHead className="text-center">Marj %</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {scores.map((s) => (
            <TableRow key={s.supplier_code} data-testid={`profit-row-${s.supplier_code}`}>
              <TableCell className="font-medium">{supplierLabel(s.supplier_code)}</TableCell>
              <TableCell className="text-center">
                <span className="font-mono font-bold text-base">{s.profitability_score}</span>
              </TableCell>
              <TableCell className="text-center">
                <Badge variant="outline" className={TIER_STYLES[s.tier] || TIER_STYLES.bronze}>
                  {s.tier.toUpperCase()}
                </Badge>
              </TableCell>
              <TableCell className="text-center">{s.components.commission_margin}</TableCell>
              <TableCell className="text-center">{s.components.success_rate}</TableCell>
              <TableCell className="text-center">{s.components.latency_score}</TableCell>
              <TableCell className="text-center">{s.components.cancellation_risk_inv}</TableCell>
              <TableCell className="text-center font-mono">%{s.stats.margin_pct}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// ========================= ECONOMICS TABLE =========================
function EconomicsTable({ economics }) {
  if (!economics.length) return <p className="text-muted-foreground text-sm p-4">Henuz veri yok.</p>;

  return (
    <div className="overflow-x-auto" data-testid="economics-table">
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>Supplier</TableHead>
            <TableHead className="text-right">Gelir</TableHead>
            <TableHead className="text-center">Pay %</TableHead>
            <TableHead className="text-center">Rez.</TableHead>
            <TableHead className="text-center">Ort. Rez.</TableHead>
            <TableHead className="text-center">Karlilik</TableHead>
            <TableHead className="text-center">Tier</TableHead>
            <TableHead className="text-center">Performans</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {economics.map((e) => (
            <TableRow key={e.supplier_code} data-testid={`econ-row-${e.supplier_code}`}>
              <TableCell className="font-medium">{supplierLabel(e.supplier_code)}</TableCell>
              <TableCell className="text-right font-mono">{fmtPrice(e.revenue.total_revenue)}</TableCell>
              <TableCell className="text-center">%{e.revenue.revenue_share_pct}</TableCell>
              <TableCell className="text-center">{e.revenue.total_bookings}</TableCell>
              <TableCell className="text-center font-mono">{fmtPrice(e.revenue.avg_booking_value)}</TableCell>
              <TableCell className="text-center font-mono font-bold">{e.profitability.score}</TableCell>
              <TableCell className="text-center">
                <Badge variant="outline" className={TIER_STYLES[e.profitability.tier] || TIER_STYLES.bronze}>
                  {(e.profitability.tier || "bronze").toUpperCase()}
                </Badge>
              </TableCell>
              <TableCell className="text-center">
                {e.performance.tags?.map(t => (
                  <Badge key={t} variant="secondary" className="text-[9px] mr-0.5">{t}</Badge>
                ))}
                {!e.performance.tags?.length && <span className="text-muted-foreground text-xs">-</span>}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}

// ========================= MARKUP RULES =========================
function MarkupRulesPanel({ rules, onRefresh }) {
  const RULE_TYPE_LABELS = { platform: "Platform", supplier: "Supplier", destination: "Destinasyon", season: "Sezon", agency_tier: "Acenta Tier" };

  const handleDelete = async (ruleId) => {
    try {
      await deleteMarkupRule(ruleId);
      toast.success("Kural deaktive edildi");
      onRefresh();
    } catch { toast.error("Silme hatasi"); }
  };

  return (
    <div data-testid="markup-rules-panel">
      <div className="overflow-x-auto">
        <Table>
          <TableHeader>
            <TableRow>
              <TableHead>Kural ID</TableHead>
              <TableHead>Tip</TableHead>
              <TableHead>Hedef</TableHead>
              <TableHead className="text-center">Markup %</TableHead>
              <TableHead className="text-center">Max %</TableHead>
              <TableHead className="text-center">Oncelik</TableHead>
              <TableHead className="text-center">Islem</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {rules.map((r) => (
              <TableRow key={r.rule_id} data-testid={`markup-rule-${r.rule_id}`}>
                <TableCell className="font-mono text-xs">{r.rule_id}</TableCell>
                <TableCell><Badge variant="outline">{RULE_TYPE_LABELS[r.rule_type] || r.rule_type}</Badge></TableCell>
                <TableCell>{r.target}</TableCell>
                <TableCell className="text-center font-mono">%{r.markup_pct}</TableCell>
                <TableCell className="text-center font-mono">%{r.max_pct}</TableCell>
                <TableCell className="text-center">{r.priority}</TableCell>
                <TableCell className="text-center">
                  <Button variant="ghost" size="sm" className="text-red-500 h-7" onClick={() => handleDelete(r.rule_id)}>
                    Sil
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}

// ========================= SCORE BAR =========================
function ScoreBar({ score, maxScore = 100 }) {
  const pct = Math.min(100, (score / maxScore) * 100);
  const color = pct >= 70 ? "bg-emerald-500" : pct >= 40 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 h-2 bg-muted rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
      <span className="text-xs font-mono w-8 text-right">{score}</span>
    </div>
  );
}

// ========================= MAIN PAGE =========================
export default function SupplierEconomicsPage() {
  const [days, setDays] = useState("30");
  const [loading, setLoading] = useState(true);
  const [economics, setEconomics] = useState([]);
  const [profitability, setProfitability] = useState([]);
  const [markupRules, setMarkupRules] = useState([]);
  const [commission, setCommission] = useState({});
  const [activeTab, setActiveTab] = useState("overview");

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [econRes, profRes, rulesRes, commRes] = await Promise.all([
        getSupplierEconomics(parseInt(days)),
        getProfitabilityScores(parseInt(days)),
        getMarkupRules(),
        getCommissionSummary(parseInt(days)),
      ]);
      setEconomics(econRes.economics || []);
      setProfitability(profRes.scores || []);
      setMarkupRules(rulesRes.rules || []);
      setCommission(commRes || {});
    } catch (err) {
      toast.error("Veri yuklenemedi");
    } finally {
      setLoading(false);
    }
  }, [days]);

  useEffect(() => { fetchData(); }, [fetchData]);

  return (
    <div className="space-y-6 max-w-[1400px] mx-auto" data-testid="supplier-economics-page">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight">Supplier Ekonomisi</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Supplier gelir payi, karlilik, konversiyon ve performans analizi
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Select value={days} onValueChange={setDays}>
            <SelectTrigger className="w-[140px] h-9" data-testid="economics-period-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="7">Son 7 Gun</SelectItem>
              <SelectItem value="30">Son 30 Gun</SelectItem>
              <SelectItem value="90">Son 90 Gun</SelectItem>
            </SelectContent>
          </Select>
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading} data-testid="economics-refresh-btn">
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
          {/* Commission Summary */}
          <CommissionSummaryCards data={commission} />

          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList data-testid="economics-tabs">
              <TabsTrigger value="overview" data-testid="tab-overview">Genel Bakis</TabsTrigger>
              <TabsTrigger value="profitability" data-testid="tab-profitability">Karlilik Skoru</TabsTrigger>
              <TabsTrigger value="markup" data-testid="tab-markup">Markup Kurallari</TabsTrigger>
            </TabsList>

            {/* OVERVIEW */}
            <TabsContent value="overview">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <BarChart3 className="h-4 w-4" /> Supplier Ekonomik Gorunumu
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <EconomicsTable economics={economics} />
                </CardContent>
              </Card>
            </TabsContent>

            {/* PROFITABILITY */}
            <TabsContent value="profitability">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <Shield className="h-4 w-4" /> Karlilik Skorlari
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-6">
                  {/* Score bars */}
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {profitability.map((s) => (
                      <div key={s.supplier_code} className="border rounded-lg p-4" data-testid={`profit-card-${s.supplier_code}`}>
                        <div className="flex items-center justify-between mb-3">
                          <span className="font-medium">{supplierLabel(s.supplier_code)}</span>
                          <Badge variant="outline" className={TIER_STYLES[s.tier] || TIER_STYLES.bronze}>
                            {s.tier.toUpperCase()}
                          </Badge>
                        </div>
                        <ScoreBar score={s.profitability_score} />
                        <div className="grid grid-cols-5 gap-2 mt-3 text-[10px] text-muted-foreground">
                          <div className="text-center"><p>Komisyon</p><p className="font-mono font-bold text-foreground">{s.components.commission_margin}</p></div>
                          <div className="text-center"><p>Basari</p><p className="font-mono font-bold text-foreground">{s.components.success_rate}</p></div>
                          <div className="text-center"><p>Fallback</p><p className="font-mono font-bold text-foreground">{s.components.fallback_frequency_inv}</p></div>
                          <div className="text-center"><p>Gecikme</p><p className="font-mono font-bold text-foreground">{s.components.latency_score}</p></div>
                          <div className="text-center"><p>Iptal</p><p className="font-mono font-bold text-foreground">{s.components.cancellation_risk_inv}</p></div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Detailed table */}
                  <ProfitabilityTable scores={profitability} />
                </CardContent>
              </Card>
            </TabsContent>

            {/* MARKUP RULES */}
            <TabsContent value="markup">
              <Card>
                <CardHeader>
                  <CardTitle className="text-base flex items-center gap-2">
                    <DollarSign className="h-4 w-4" /> Markup Kural Motoru
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <MarkupRulesPanel rules={markupRules} onRefresh={fetchData} />
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>
        </>
      )}
    </div>
  );
}
