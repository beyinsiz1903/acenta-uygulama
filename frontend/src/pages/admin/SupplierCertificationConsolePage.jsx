import React, { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import {
  CheckCircle2, XCircle, AlertTriangle, Clock, Play, RotateCcw,
  ChevronRight, ChevronDown, Activity, Wifi, WifiOff, Timer,
  Zap, History, ArrowLeft, Server, Shield, TrendingUp
} from "lucide-react";
import { api } from "../../lib/api";

const STATUS_STYLES = {
  pass: { bg: "bg-emerald-500/15", text: "text-emerald-400", border: "border-emerald-500/30", icon: CheckCircle2, label: "PASS" },
  fail: { bg: "bg-red-500/15", text: "text-red-400", border: "border-red-500/30", icon: XCircle, label: "FAIL" },
  warn: { bg: "bg-amber-500/15", text: "text-amber-400", border: "border-amber-500/30", icon: AlertTriangle, label: "WARN" },
  skipped: { bg: "bg-zinc-600/15", text: "text-zinc-500", border: "border-zinc-600/30", icon: Clock, label: "SKIP" },
  running: { bg: "bg-blue-500/15", text: "text-blue-400", border: "border-blue-500/30", icon: Activity, label: "..." },
};

const SCENARIO_ICONS = {
  success: CheckCircle2, price_mismatch: TrendingUp, delayed_confirmation: Timer,
  booking_timeout: XCircle, cancel_success: RotateCcw, supplier_unavailable: WifiOff,
};

const SUPPLIER_COLORS = {
  ratehawk: "from-orange-500 to-red-600",
  paximum: "from-emerald-500 to-teal-600",
  tbo: "from-sky-500 to-blue-600",
  wtatil: "from-indigo-500 to-violet-600",
};

/* ─── Step Detail Drawer ──────────────────────────────── */
function StepDrawer({ step, onClose, onRerun, rerunning }) {
  if (!step) return null;
  const st = STATUS_STYLES[step.status] || STATUS_STYLES.skipped;
  const Icon = st.icon;
  return (
    <div data-testid="step-drawer" className="fixed inset-0 z-50 flex justify-end" onClick={onClose}>
      <div className="absolute inset-0 bg-black/50 backdrop-blur-sm" />
      <div className="relative w-full max-w-lg bg-zinc-900 border-l border-zinc-800 overflow-y-auto p-6 space-y-5"
        onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Icon className={`w-5 h-5 ${st.text}`} />
            <h3 className="text-lg font-semibold text-zinc-100">{step.name}</h3>
            <Badge className={`${st.bg} ${st.text} ${st.border} text-[10px]`}>{st.label}</Badge>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
            <XCircle className="w-4 h-4" />
          </Button>
        </div>
        <p className="text-sm text-zinc-400">{step.message}</p>
        {step.error && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
            <p className="text-xs font-mono text-red-400">{step.error}</p>
          </div>
        )}
        {step.warnings?.length > 0 && (
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3 space-y-1">
            {step.warnings.map((w, i) => (
              <p key={i} className="text-xs text-amber-400 flex items-center gap-1.5">
                <AlertTriangle className="w-3 h-3 shrink-0" /> {w}
              </p>
            ))}
          </div>
        )}
        <div className="grid grid-cols-2 gap-3">
          <InfoCard label="Latency" value={`${step.latency_ms}ms`} />
          <InfoCard label="Request ID" value={step.request_id} mono />
          <InfoCard label="Trace ID" value={step.trace_id} mono />
          <InfoCard label="Status" value={st.label} />
        </div>
        {step.supplier_response && Object.keys(step.supplier_response).length > 0 && (
          <div>
            <h4 className="text-xs font-semibold text-zinc-400 uppercase tracking-wider mb-2">Supplier Response</h4>
            <pre className="bg-zinc-950 border border-zinc-800 rounded-lg p-3 text-[11px] text-zinc-300 font-mono overflow-x-auto max-h-60">
              {JSON.stringify(step.supplier_response, null, 2)}
            </pre>
          </div>
        )}
        {(step.status === "fail" || step.status === "warn") && (
          <Button data-testid="rerun-step-btn" onClick={() => onRerun(step.id)} disabled={rerunning}
            className="w-full bg-blue-600 hover:bg-blue-700 text-white" size="sm">
            <RotateCcw className={`w-3.5 h-3.5 mr-1.5 ${rerunning ? "animate-spin" : ""}`} />
            {rerunning ? "Yeniden calistiriliyor..." : "Bu adimi yeniden calistir"}
          </Button>
        )}
      </div>
    </div>
  );
}

function InfoCard({ label, value, mono }) {
  return (
    <div className="bg-zinc-800/50 rounded-lg p-2.5">
      <p className="text-[10px] text-zinc-500 uppercase tracking-wider">{label}</p>
      <p className={`text-xs text-zinc-200 mt-0.5 ${mono ? "font-mono" : ""} truncate`}>{value || "—"}</p>
    </div>
  );
}

/* ─── Lifecycle Stepper ───────────────────────────────── */
function LifecycleStepper({ steps, onStepClick }) {
  return (
    <div data-testid="lifecycle-stepper" className="space-y-2">
      {steps.map((step, idx) => {
        const st = STATUS_STYLES[step.status] || STATUS_STYLES.skipped;
        const Icon = st.icon;
        return (
          <button key={step.id} data-testid={`step-${step.id}`}
            onClick={() => onStepClick(step)}
            className={`w-full flex items-center gap-3 p-3 rounded-lg border transition-all hover:border-zinc-600 cursor-pointer ${st.border} ${st.bg}`}>
            <div className="flex items-center gap-2 shrink-0">
              <span className="text-[10px] text-zinc-600 font-mono w-4">{idx + 1}</span>
              <Icon className={`w-4 h-4 ${st.text}`} />
            </div>
            <div className="flex-1 text-left min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-zinc-200">{step.name}</span>
                <Badge className={`${st.bg} ${st.text} text-[9px] px-1.5 py-0`}>{st.label}</Badge>
              </div>
              <p className="text-[11px] text-zinc-500 truncate mt-0.5">{step.message}</p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-xs text-zinc-400 font-mono">{step.latency_ms}ms</p>
            </div>
            <ChevronRight className="w-4 h-4 text-zinc-600 shrink-0" />
          </button>
        );
      })}
    </div>
  );
}

/* ─── Certification Summary Card ──────────────────────── */
function CertificationCard({ certification, supplierName }) {
  if (!certification) return null;
  const eligible = certification.go_live_eligible;
  return (
    <Card data-testid="certification-card" className="bg-zinc-900/80 border-zinc-800">
      <CardContent className="p-5 space-y-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Shield className="w-5 h-5 text-zinc-400" />
            <span className="text-sm font-semibold text-zinc-200">Sertifikasyon Sonucu</span>
          </div>
          <Badge data-testid="go-live-badge"
            className={eligible
              ? "bg-emerald-500/20 text-emerald-400 border-emerald-500/30"
              : "bg-red-500/20 text-red-400 border-red-500/30"}>
            {eligible ? "Go-Live Eligible" : "Not Eligible"}
          </Badge>
        </div>
        <div className="flex items-center gap-4">
          <div className="relative w-20 h-20">
            <svg className="w-20 h-20 -rotate-90" viewBox="0 0 36 36">
              <circle cx="18" cy="18" r="15.9" fill="none" stroke="#27272a" strokeWidth="3" />
              <circle cx="18" cy="18" r="15.9" fill="none"
                stroke={eligible ? "#10b981" : "#ef4444"}
                strokeWidth="3" strokeDasharray={`${certification.score} ${100 - certification.score}`}
                strokeLinecap="round" />
            </svg>
            <div className="absolute inset-0 flex items-center justify-center">
              <span className="text-lg font-bold text-zinc-100">{certification.score}%</span>
            </div>
          </div>
          <div className="flex-1 grid grid-cols-2 gap-2">
            <MiniStat label="Passed" value={certification.passed} color="text-emerald-400" />
            <MiniStat label="Failed" value={certification.failed} color="text-red-400" />
            <MiniStat label="Warnings" value={certification.warnings} color="text-amber-400" />
            <MiniStat label="Skipped" value={certification.skipped} color="text-zinc-500" />
          </div>
        </div>
        {certification.failed_steps?.length > 0 && (
          <div className="bg-red-500/10 border border-red-500/20 rounded-lg p-3">
            <p className="text-[10px] text-red-500 uppercase font-semibold mb-1">Basarisiz Adimlar</p>
            {certification.failed_steps.map((s) => (
              <p key={s} className="text-xs text-red-400 flex items-center gap-1"><XCircle className="w-3 h-3" />{s}</p>
            ))}
          </div>
        )}
        {certification.warning_steps?.length > 0 && (
          <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-3">
            <p className="text-[10px] text-amber-500 uppercase font-semibold mb-1">Uyarilar</p>
            {certification.warning_steps.map((s) => (
              <p key={s} className="text-xs text-amber-400 flex items-center gap-1"><AlertTriangle className="w-3 h-3" />{s}</p>
            ))}
          </div>
        )}
      </CardContent>
    </Card>
  );
}

function MiniStat({ label, value, color }) {
  return (
    <div className="bg-zinc-800/50 rounded p-2 text-center">
      <p className={`text-lg font-bold ${color}`}>{value}</p>
      <p className="text-[10px] text-zinc-500">{label}</p>
    </div>
  );
}

/* ─── History Panel ───────────────────────────────────── */
function HistoryPanel({ history, onSelect }) {
  if (!history?.length) return (
    <div className="text-center py-8 text-zinc-500 text-sm">Henuz test gecmisi yok</div>
  );
  return (
    <div data-testid="history-panel" className="space-y-2">
      {history.map((t) => {
        const eligible = t.certification?.go_live_eligible;
        return (
          <button key={t.run_id} data-testid={`history-${t.run_id}`}
            onClick={() => onSelect(t)}
            className="w-full flex items-center gap-3 p-3 rounded-lg border border-zinc-800 bg-zinc-900/60 hover:border-zinc-700 transition-all text-left">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${eligible ? "bg-emerald-500/15" : "bg-red-500/15"}`}>
              {eligible ? <CheckCircle2 className="w-4 h-4 text-emerald-400" /> : <XCircle className="w-4 h-4 text-red-400" />}
            </div>
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="text-sm font-medium text-zinc-200">{t.supplier_name}</span>
                <Badge variant="outline" className="text-[9px] border-zinc-700 text-zinc-400">{t.scenario_name}</Badge>
                <Badge variant="outline" className="text-[9px] border-zinc-700 text-zinc-400">{t.mode}</Badge>
              </div>
              <p className="text-[11px] text-zinc-500 mt-0.5">
                {t.summary?.passed}/{t.summary?.total} passed | {t.certification?.score}% | {t.total_duration_ms}ms
              </p>
            </div>
            <div className="text-right shrink-0">
              <p className="text-[10px] text-zinc-500">{new Date(t.timestamp).toLocaleString("tr-TR")}</p>
              <Badge className={`text-[9px] mt-0.5 ${eligible ? "bg-emerald-500/15 text-emerald-400" : "bg-red-500/15 text-red-400"}`}>
                {t.certification?.score}%
              </Badge>
            </div>
            <ChevronRight className="w-4 h-4 text-zinc-600" />
          </button>
        );
      })}
    </div>
  );
}

/* ─── Main Page ───────────────────────────────────────── */
export default function SupplierCertificationConsolePage() {
  const [scenarios, setScenarios] = useState([]);
  const [selectedSupplier, setSelectedSupplier] = useState("ratehawk");
  const [selectedScenario, setSelectedScenario] = useState("success");
  const [running, setRunning] = useState(false);
  const [testResult, setTestResult] = useState(null);
  const [history, setHistory] = useState([]);
  const [activeTab, setActiveTab] = useState("test");
  const [drawerStep, setDrawerStep] = useState(null);
  const [rerunning, setRerunning] = useState(false);
  const [historyFilter, setHistoryFilter] = useState(null);

  const suppliers = Object.entries(SUPPLIER_COLORS).map(([code, grad]) => ({
    code, gradient: grad,
    name: { ratehawk: "RateHawk", paximum: "Paximum", tbo: "TBO Holidays", wtatil: "WTatil" }[code],
  }));

  const loadScenarios = useCallback(async () => {
    try {
      const { data } = await api.get("/e2e-demo/scenarios");
      setScenarios(data.scenarios || []);
    } catch { /* ignore */ }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const params = historyFilter ? `?supplier=${historyFilter}&limit=20` : "?limit=20";
      const { data } = await api.get(`/e2e-demo/history${params}`);
      setHistory(data.tests || []);
    } catch { /* ignore */ }
  }, [historyFilter]);

  useEffect(() => { loadScenarios(); }, [loadScenarios]);
  useEffect(() => { loadHistory(); }, [loadHistory, activeTab]);

  const runTest = async () => {
    setRunning(true);
    setTestResult(null);
    try {
      const { data } = await api.post("/e2e-demo/run", {
        supplier: selectedSupplier, scenario: selectedScenario,
      });
      setTestResult(data);
      loadHistory();
    } catch (e) {
      console.error(e);
    }
    setRunning(false);
  };

  const rerunStep = async (stepId) => {
    if (!testResult) return;
    setRerunning(true);
    try {
      const { data } = await api.post("/e2e-demo/rerun-step", {
        run_id: testResult.run_id, step_id: stepId,
      });
      if (data.step) {
        setTestResult((prev) => ({
          ...prev,
          steps: prev.steps.map((s) => s.id === stepId ? { ...s, ...data.step } : s),
        }));
      }
    } catch (e) {
      console.error(e);
    }
    setRerunning(false);
    setDrawerStep(null);
  };

  const tabs = [
    { id: "test", label: "Test Konsolu", icon: Zap },
    { id: "history", label: "Gecmis", icon: History },
  ];

  return (
    <div data-testid="certification-console" className="min-h-screen bg-zinc-950 text-zinc-100">
      {/* Header */}
      <div className="border-b border-zinc-800 px-6 py-4">
        <div className="flex items-center justify-between">
          <div>
            <h1 data-testid="page-title" className="text-xl font-bold text-zinc-100 flex items-center gap-2">
              <Server className="w-5 h-5 text-blue-400" />
              Supplier Certification Console
            </h1>
            <p className="text-sm text-zinc-500 mt-0.5">
              E2E lifecycle testi calistir, edge case senaryolarini dogrula, go-live eligibility kontrol et
            </p>
          </div>
          <div className="flex gap-1 bg-zinc-800/50 rounded-lg p-0.5">
            {tabs.map((t) => (
              <button key={t.id} data-testid={`tab-${t.id}`}
                onClick={() => setActiveTab(t.id)}
                className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all ${
                  activeTab === t.id ? "bg-zinc-700 text-zinc-100" : "text-zinc-500 hover:text-zinc-300"
                }`}>
                <t.icon className="w-3.5 h-3.5" /> {t.label}
              </button>
            ))}
          </div>
        </div>
      </div>

      <div className="p-6">
        {activeTab === "test" ? (
          <div className="grid grid-cols-12 gap-6">
            {/* Left: Controls */}
            <div className="col-span-4 space-y-4">
              {/* Supplier Selection */}
              <Card className="bg-zinc-900/80 border-zinc-800">
                <CardHeader className="pb-2 pt-4 px-4">
                  <CardTitle className="text-xs uppercase tracking-wider text-zinc-500">Supplier</CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4 space-y-1.5">
                  {suppliers.map((s) => (
                    <button key={s.code} data-testid={`supplier-btn-${s.code}`}
                      onClick={() => setSelectedSupplier(s.code)}
                      className={`w-full flex items-center gap-2.5 p-2.5 rounded-lg border transition-all ${
                        selectedSupplier === s.code
                          ? "border-blue-500/50 bg-blue-500/10"
                          : "border-zinc-800 hover:border-zinc-700"
                      }`}>
                      <div className={`w-7 h-7 rounded-md bg-gradient-to-br ${s.gradient} flex items-center justify-center`}>
                        <Wifi className="w-3.5 h-3.5 text-white" />
                      </div>
                      <span className="text-sm font-medium text-zinc-200">{s.name}</span>
                    </button>
                  ))}
                </CardContent>
              </Card>

              {/* Scenario Selection */}
              <Card className="bg-zinc-900/80 border-zinc-800">
                <CardHeader className="pb-2 pt-4 px-4">
                  <CardTitle className="text-xs uppercase tracking-wider text-zinc-500">Senaryo</CardTitle>
                </CardHeader>
                <CardContent className="px-4 pb-4 space-y-1.5">
                  {scenarios.map((sc) => {
                    const ScIcon = SCENARIO_ICONS[sc.id] || Activity;
                    return (
                      <button key={sc.id} data-testid={`scenario-btn-${sc.id}`}
                        onClick={() => setSelectedScenario(sc.id)}
                        className={`w-full flex items-center gap-2.5 p-2.5 rounded-lg border transition-all text-left ${
                          selectedScenario === sc.id
                            ? "border-blue-500/50 bg-blue-500/10"
                            : "border-zinc-800 hover:border-zinc-700"
                        }`}>
                        <ScIcon className={`w-4 h-4 shrink-0 ${selectedScenario === sc.id ? "text-blue-400" : "text-zinc-500"}`} />
                        <div className="min-w-0">
                          <p className="text-sm font-medium text-zinc-200">{sc.name}</p>
                          <p className="text-[10px] text-zinc-500 truncate">{sc.description}</p>
                        </div>
                      </button>
                    );
                  })}
                </CardContent>
              </Card>

              {/* Run Button */}
              <Button data-testid="run-test-btn" onClick={runTest} disabled={running}
                className="w-full bg-blue-600 hover:bg-blue-700 text-white h-11 font-semibold" size="lg">
                {running ? (
                  <><Activity className="w-4 h-4 mr-2 animate-spin" /> Test calistiriliyor...</>
                ) : (
                  <><Play className="w-4 h-4 mr-2" /> Testi Baslat</>
                )}
              </Button>
            </div>

            {/* Right: Results */}
            <div className="col-span-8 space-y-4">
              {testResult ? (
                <>
                  {/* Test Info Bar */}
                  <div data-testid="test-info" className="flex items-center gap-3 bg-zinc-900/60 border border-zinc-800 rounded-lg p-3">
                    <div className={`w-8 h-8 rounded-lg bg-gradient-to-br ${SUPPLIER_COLORS[testResult.supplier]} flex items-center justify-center`}>
                      <Server className="w-4 h-4 text-white" />
                    </div>
                    <div className="flex-1">
                      <p className="text-sm font-medium text-zinc-200">{testResult.supplier_name} — {testResult.scenario_name}</p>
                      <p className="text-[10px] text-zinc-500 font-mono">
                        Trace: {testResult.trace_id} | Mode: {testResult.mode} | {testResult.total_duration_ms}ms
                      </p>
                    </div>
                    <Button variant="outline" size="sm" onClick={runTest} disabled={running}
                      className="border-zinc-700 text-zinc-300 hover:bg-zinc-800" data-testid="retry-test-btn">
                      <RotateCcw className={`w-3.5 h-3.5 mr-1 ${running ? "animate-spin" : ""}`} /> Tekrar
                    </Button>
                  </div>

                  {/* Lifecycle + Certification side by side */}
                  <div className="grid grid-cols-5 gap-4">
                    <div className="col-span-3">
                      <h3 className="text-xs uppercase tracking-wider text-zinc-500 mb-2 flex items-center gap-1.5">
                        <Activity className="w-3.5 h-3.5" /> Lifecycle Adimlari
                      </h3>
                      <LifecycleStepper steps={testResult.steps} onStepClick={setDrawerStep} />
                    </div>
                    <div className="col-span-2">
                      <h3 className="text-xs uppercase tracking-wider text-zinc-500 mb-2 flex items-center gap-1.5">
                        <Shield className="w-3.5 h-3.5" /> Sertifikasyon
                      </h3>
                      <CertificationCard certification={testResult.certification} supplierName={testResult.supplier_name} />
                    </div>
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-96 text-center">
                  <Server className="w-12 h-12 text-zinc-700 mb-4" />
                  <p className="text-zinc-500 text-sm">Supplier secin, senaryo belirleyin ve testi baslatin</p>
                  <p className="text-zinc-600 text-xs mt-1">
                    Search → Detail → Revalidation → Booking → Status → Cancel
                  </p>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* ─── History Tab ─── */
          <div className="space-y-4">
            <div className="flex items-center gap-2">
              <span className="text-xs text-zinc-500 uppercase tracking-wider">Filtre:</span>
              <button data-testid="history-filter-all"
                onClick={() => setHistoryFilter(null)}
                className={`px-2.5 py-1 rounded-md text-xs transition-all ${!historyFilter ? "bg-zinc-700 text-zinc-100" : "text-zinc-500 hover:text-zinc-300"}`}>
                Tumu
              </button>
              {suppliers.map((s) => (
                <button key={s.code} data-testid={`history-filter-${s.code}`}
                  onClick={() => setHistoryFilter(s.code)}
                  className={`px-2.5 py-1 rounded-md text-xs transition-all ${historyFilter === s.code ? "bg-zinc-700 text-zinc-100" : "text-zinc-500 hover:text-zinc-300"}`}>
                  {s.name}
                </button>
              ))}
            </div>
            <HistoryPanel history={history} onSelect={(t) => { setTestResult(t); setActiveTab("test"); }} />
          </div>
        )}
      </div>

      {/* Step Drawer */}
      <StepDrawer step={drawerStep} onClose={() => setDrawerStep(null)} onRerun={rerunStep} rerunning={rerunning} />
    </div>
  );
}
