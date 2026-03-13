import React, { useState, useEffect, useCallback } from "react";
import {
  Shield, CheckCircle, XCircle, AlertTriangle, Loader2, RefreshCw,
  Play, BarChart3, Zap, Activity, Server, Gauge, ArrowRight,
  FileText, Clock, Globe, TrendingUp,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "../../components/ui/table";
import { toast } from "sonner";
import { operationsApi } from "../../api/operations";

function StatusIcon({ status, size = 4 }) {
  const cls = `h-${size} w-${size}`;
  if (status === "pass" || status === "ready" || status === "production_ready" || status === true)
    return <CheckCircle className={`${cls} text-emerald-500`} />;
  if (status === "fail" || status === false)
    return <XCircle className={`${cls} text-red-500`} />;
  if (status === "warn" || status === "partial" || status === "needs_work" || status === "needs_traffic" || status === "needs_data" || status === "needs_bookings")
    return <AlertTriangle className={`${cls} text-amber-500`} />;
  return <Clock className={`${cls} text-gray-400`} />;
}

function SeverityBadge({ severity }) {
  const styles = {
    critical: "bg-red-100 text-red-800 border-red-300",
    high: "bg-orange-100 text-orange-800 border-orange-300",
    medium: "bg-amber-100 text-amber-800 border-amber-300",
    low: "bg-blue-100 text-blue-800 border-blue-300",
  };
  return <Badge className={styles[severity] || styles.low}>{severity?.toUpperCase()}</Badge>;
}

function ScoreGauge({ score, max = 10, label }) {
  const pct = (score / max) * 100;
  const color = pct >= 90 ? "bg-emerald-500" : pct >= 70 ? "bg-amber-500" : "bg-red-500";
  return (
    <div className="text-center">
      <div className="relative w-16 h-16 mx-auto">
        <svg className="w-16 h-16 -rotate-90" viewBox="0 0 64 64">
          <circle cx="32" cy="32" r="28" fill="none" stroke="currentColor" strokeWidth="4" className="text-muted/20" />
          <circle cx="32" cy="32" r="28" fill="none" stroke="currentColor" strokeWidth="4"
            className={pct >= 90 ? "text-emerald-500" : pct >= 70 ? "text-amber-500" : "text-red-500"}
            strokeDasharray={`${pct * 1.76} 176`} strokeLinecap="round" />
        </svg>
        <span className="absolute inset-0 flex items-center justify-center text-sm font-bold">{score}</span>
      </div>
      <p className="text-xs text-muted-foreground mt-1">{label}</p>
    </div>
  );
}

// ========================= CAPABILITY MATRIX =========================
function CapabilityMatrixTab() {
  const [matrix, setMatrix] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try { setMatrix(await operationsApi.getCapabilityMatrix()); }
    catch { toast.error("Capability matrix yuklenemedi"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  if (loading || !matrix) return <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" /></div>;

  return (
    <div className="space-y-4" data-testid="capability-matrix-tab">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Globe className="h-4 w-4" /> Supplier Yetenek Matrisi ({matrix.total_suppliers} Supplier)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Supplier</TableHead>
                <TableHead>Urunler</TableHead>
                <TableHead className="text-center">Arama</TableHead>
                <TableHead className="text-center">Fiyat Kontrol</TableHead>
                <TableHead className="text-center">Hold</TableHead>
                <TableHead className="text-center">Rezervasyon</TableHead>
                <TableHead className="text-center">Iptal</TableHead>
                <TableHead className="text-center">Sandbox</TableHead>
                <TableHead>Auth Tipi</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {matrix.matrix.map(s => (
                <TableRow key={s.supplier_code}>
                  <TableCell className="font-medium">{s.display_name}</TableCell>
                  <TableCell>
                    <div className="flex gap-1">
                      {s.product_types.map(pt => (
                        <Badge key={pt} variant="outline" className="text-xs capitalize">{pt}</Badge>
                      ))}
                    </div>
                  </TableCell>
                  <TableCell className="text-center"><StatusIcon status={s.search} /></TableCell>
                  <TableCell className="text-center"><StatusIcon status={s.price_check} /></TableCell>
                  <TableCell className="text-center"><StatusIcon status={s.hold} /></TableCell>
                  <TableCell className="text-center"><StatusIcon status={s.booking} /></TableCell>
                  <TableCell className="text-center"><StatusIcon status={s.cancel} /></TableCell>
                  <TableCell className="text-center"><StatusIcon status={s.sandbox_available} /></TableCell>
                  <TableCell className="text-xs text-muted-foreground">{s.auth_type}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

// ========================= VALIDATION TAB =========================
function ValidationTab() {
  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);

  const runAll = async () => {
    setLoading(true);
    try {
      const r = await operationsApi.validateAll();
      setResults(r);
      toast.success("Tum supplier'lar dogrulandi");
    } catch { toast.error("Dogrulama basarisiz"); }
    finally { setLoading(false); }
  };

  return (
    <div className="space-y-4" data-testid="validation-tab">
      <div className="flex items-center justify-between">
        <p className="text-sm text-muted-foreground">Her supplier icin credential, auth, search ve capability dogrulamasi</p>
        <Button onClick={runAll} disabled={loading} data-testid="run-validation-btn">
          {loading ? <Loader2 className="h-4 w-4 animate-spin mr-1" /> : <Play className="h-4 w-4 mr-1" />}
          Tum Supplier'lari Dogrula
        </Button>
      </div>
      {results && (
        <div className="space-y-3">
          <div className="flex gap-2 flex-wrap">
            {Object.entries(results.summary || {}).map(([sc, status]) => (
              <Badge key={sc} className={
                status === "pass" ? "bg-emerald-100 text-emerald-800" :
                status === "partial" ? "bg-amber-100 text-amber-800" :
                status === "no_credentials" ? "bg-gray-100 text-gray-700" :
                "bg-red-100 text-red-800"
              }>
                {sc}: {status}
              </Badge>
            ))}
          </div>
          {Object.entries(results.suppliers || {}).map(([sc, report]) => (
            <Card key={sc}>
              <CardHeader className="pb-2">
                <CardTitle className="text-sm flex items-center gap-2">
                  <StatusIcon status={report.overall_status} />
                  {sc} — {report.overall_status}
                  {report.duration_ms && <span className="text-xs text-muted-foreground ml-auto">{report.duration_ms}ms</span>}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-1">
                  {(report.steps || []).map((step, i) => (
                    <div key={i} className="flex items-center gap-2 text-sm">
                      <StatusIcon status={step.status} size={3} />
                      <span className="font-medium capitalize w-28">{step.step.replace(/_/g, " ")}</span>
                      <span className="text-muted-foreground">{step.message}</span>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}

// ========================= PERFORMANCE TAB =========================
function PerformanceTab() {
  const [cacheResult, setCacheResult] = useState(null);
  const [fallbackResult, setFallbackResult] = useState(null);
  const [rateLimitResult, setRateLimitResult] = useState(null);
  const [loading, setLoading] = useState("");

  const runCacheBurst = async () => {
    setLoading("cache");
    try { setCacheResult(await operationsApi.cacheBurstTest(5)); toast.success("Cache burst testi tamamlandi"); }
    catch { toast.error("Cache testi basarisiz"); }
    finally { setLoading(""); }
  };

  const runFallback = async () => {
    setLoading("fallback");
    try { setFallbackResult(await operationsApi.fallbackTest()); toast.success("Fallback testi tamamlandi"); }
    catch { toast.error("Fallback testi basarisiz"); }
    finally { setLoading(""); }
  };

  const runRateLimit = async () => {
    setLoading("ratelimit");
    try { setRateLimitResult(await operationsApi.rateLimitTest("ratehawk", 10)); toast.success("Rate limit testi tamamlandi"); }
    catch { toast.error("Rate limit testi basarisiz"); }
    finally { setLoading(""); }
  };

  return (
    <div className="space-y-4" data-testid="performance-tab">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium">Cache Burst Test</h3>
              <Button size="sm" variant="outline" onClick={runCacheBurst} disabled={loading === "cache"} data-testid="run-cache-test">
                {loading === "cache" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
              </Button>
            </div>
            {cacheResult && (
              <div className="space-y-1 text-xs">
                <p>Hit: <span className="font-bold text-emerald-600">{cacheResult.summary.cache_hits}</span> / {cacheResult.burst_count}</p>
                <p>Hit Rate: <span className="font-bold">{cacheResult.summary.hit_rate_pct}%</span></p>
                <p>Avg Hit: {cacheResult.summary.avg_hit_latency_ms}ms</p>
                <p>Avg Miss: {cacheResult.summary.avg_miss_latency_ms}ms</p>
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium">Fallback Validation</h3>
              <Button size="sm" variant="outline" onClick={runFallback} disabled={loading === "fallback"} data-testid="run-fallback-test">
                {loading === "fallback" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
              </Button>
            </div>
            {fallbackResult && (
              <div className="space-y-1 text-xs">
                <p>Tum zincirler dogru: <span className={`font-bold ${fallbackResult.summary.all_chains_correct ? "text-emerald-600" : "text-red-600"}`}>
                  {fallbackResult.summary.all_chains_correct ? "Evet" : "Hayir"}
                </span></p>
                {fallbackResult.scenarios.map(s => (
                  <div key={s.primary} className="flex items-center gap-1">
                    <StatusIcon status={s.chain_correct} size={3} />
                    <span>{s.primary} → {s.actual_fallbacks.join(" → ")}</span>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-medium">Rate Limit Stress</h3>
              <Button size="sm" variant="outline" onClick={runRateLimit} disabled={loading === "ratelimit"} data-testid="run-ratelimit-test">
                {loading === "ratelimit" ? <Loader2 className="h-3 w-3 animate-spin" /> : <Play className="h-3 w-3" />}
              </Button>
            </div>
            {rateLimitResult && (
              <div className="space-y-1 text-xs">
                <p>Izin verilen: <span className="font-bold text-emerald-600">{rateLimitResult.summary.allowed}</span></p>
                <p>Reddedilen: <span className="font-bold text-red-600">{rateLimitResult.summary.rejected}</span></p>
                <p>Red orani: {rateLimitResult.summary.rejection_rate_pct}%</p>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

// ========================= LAUNCH READINESS TAB =========================
function LaunchReadinessTab() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(false);

  const load = async () => {
    setLoading(true);
    try { setReport(await operationsApi.getLaunchReadiness()); }
    catch { toast.error("Launch raporu yuklenemedi"); }
    finally { setLoading(false); }
  };

  useEffect(() => { load(); }, []);

  if (loading || !report) return <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" /></div>;

  const ms = report.platform_maturity_score;

  return (
    <div className="space-y-6" data-testid="launch-readiness-tab">
      {/* Maturity Score */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <Gauge className="h-4 w-4" /> Platform Olgunluk Skoru
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-8 flex-wrap">
            <div className="text-center">
              <p className="text-4xl font-bold">{ms.overall}</p>
              <p className="text-xs text-muted-foreground">/10 Genel</p>
            </div>
            {Object.entries(ms.dimensions).map(([k, v]) => (
              <ScoreGauge key={k} score={v.score} label={k.replace(/_/g, " ")} />
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Key Metrics */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        {Object.entries(report.key_metrics || {}).map(([k, v]) => (
          <Card key={k}>
            <CardContent className="p-3 text-center">
              <p className="text-xs text-muted-foreground capitalize">{k.replace(/_/g, " ")}</p>
              <p className="text-lg font-bold mt-1">{typeof v === "number" ? (v % 1 === 0 ? v : v.toFixed(1)) : v}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Risks */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <AlertTriangle className="h-4 w-4" /> Operasyonel Riskler ({report.operational_risks.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            {report.operational_risks.map(r => (
              <div key={r.id} className="border-b pb-2 last:border-0">
                <div className="flex items-center gap-2 mb-1">
                  <SeverityBadge severity={r.severity} />
                  <span className="text-sm font-medium">{r.title}</span>
                </div>
                <p className="text-xs text-muted-foreground ml-16">{r.description}</p>
                <p className="text-xs text-emerald-700 ml-16 mt-0.5">Cozum: {r.mitigation}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Launch Checklist */}
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2">
            <FileText className="h-4 w-4" /> Launch Checklist ({report.launch_checklist.length} madde)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">Durum</TableHead>
                <TableHead>Madde</TableHead>
                <TableHead>Kategori</TableHead>
                <TableHead>Oncelik</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {report.launch_checklist.map((c, i) => (
                <TableRow key={i}>
                  <TableCell><StatusIcon status={c.status === "ready"} /></TableCell>
                  <TableCell>
                    <p className="text-sm font-medium">{c.item}</p>
                    <p className="text-xs text-muted-foreground">{c.description}</p>
                  </TableCell>
                  <TableCell><Badge variant="outline" className="text-xs capitalize">{c.category}</Badge></TableCell>
                  <TableCell>
                    <Badge className={c.priority === "P0" ? "bg-red-100 text-red-800" : c.priority === "P1" ? "bg-amber-100 text-amber-800" : "bg-blue-100 text-blue-800"}>
                      {c.priority}
                    </Badge>
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </CardContent>
      </Card>

      {/* Onboarding Flow */}
      <OnboardingSection />
    </div>
  );
}

function OnboardingSection() {
  const [checklist, setChecklist] = useState(null);
  useEffect(() => {
    operationsApi.getOnboardingChecklist().then(setChecklist).catch(() => {});
  }, []);

  if (!checklist) return null;

  return (
    <Card data-testid="onboarding-section">
      <CardHeader className="pb-2">
        <CardTitle className="text-sm flex items-center gap-2">
          <ArrowRight className="h-4 w-4" /> Acente Onboarding Akisi (Tahmini: {checklist.estimated_time_minutes} dk)
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="space-y-3">
          {checklist.checklist.map((step, i) => (
            <div key={i} className="flex items-start gap-3">
              <div className="flex items-center justify-center h-6 w-6 rounded-full bg-primary/10 text-primary text-xs font-bold shrink-0">
                {step.step}
              </div>
              <div>
                <p className="text-sm font-medium">{step.title}</p>
                <p className="text-xs text-muted-foreground">{step.description}</p>
                <code className="text-xs bg-muted px-1.5 py-0.5 rounded mt-0.5 inline-block">{step.endpoint}</code>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

// ========================= MAIN PAGE =========================
export default function OperationsReadinessPage() {
  const [tab, setTab] = useState("launch");

  return (
    <div className="space-y-6 p-4 md:p-6" data-testid="operations-readiness-page">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Live Operations & Market Readiness</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Supplier dogrulama, performans testleri, operasyon hazirlik ve launch raporu
        </p>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList data-testid="operations-tabs">
          <TabsTrigger value="launch" data-testid="tab-launch">
            <Gauge className="h-3.5 w-3.5 mr-1" /> Launch Raporu
          </TabsTrigger>
          <TabsTrigger value="capability" data-testid="tab-capability">
            <Globe className="h-3.5 w-3.5 mr-1" /> Yetenek Matrisi
          </TabsTrigger>
          <TabsTrigger value="validation" data-testid="tab-validation">
            <Shield className="h-3.5 w-3.5 mr-1" /> Dogrulama
          </TabsTrigger>
          <TabsTrigger value="performance" data-testid="tab-performance">
            <Zap className="h-3.5 w-3.5 mr-1" /> Performans
          </TabsTrigger>
        </TabsList>

        <TabsContent value="launch"><LaunchReadinessTab /></TabsContent>
        <TabsContent value="capability"><CapabilityMatrixTab /></TabsContent>
        <TabsContent value="validation"><ValidationTab /></TabsContent>
        <TabsContent value="performance"><PerformanceTab /></TabsContent>
      </Tabs>
    </div>
  );
}
