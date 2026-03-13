import React, { useState, useEffect, useCallback } from "react";
import {
  Users, BarChart3, MessageSquare, CreditCard, FileText,
  Loader2, RefreshCw, Plus, CheckCircle, XCircle, Clock,
  TrendingUp, Zap, Star, Send, Building2, ArrowRight,
  Globe, Shield, Phone, Mail, BookOpen, AlertTriangle,
} from "lucide-react";
import { Button } from "../../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "../../components/ui/tabs";
import { Input } from "../../components/ui/input";
import {
  Table, TableHeader, TableBody, TableRow, TableHead, TableCell,
} from "../../components/ui/table";
import { toast } from "sonner";
import { marketLaunchApi } from "../../api/marketLaunch";

function KPICard({ title, value, subtitle, icon: Icon, testId }) {
  return (
    <Card data-testid={testId}>
      <CardContent className="p-4">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs text-muted-foreground font-medium uppercase tracking-wide">{title}</p>
            <p className="text-2xl font-bold mt-1">{value}</p>
            {subtitle && <p className="text-xs text-muted-foreground mt-0.5">{subtitle}</p>}
          </div>
          <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
            <Icon className="h-5 w-5 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

// ========================= PILOT AGENCIES TAB =========================
function PilotAgenciesTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ company_name: "", contact_name: "", contact_email: "", contact_phone: "", pricing_tier: "free" });

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await marketLaunchApi.getPilotAgencies()); }
    catch { toast.error("Pilot acenteler yuklenemedi"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleOnboard = async () => {
    if (!form.company_name) { toast.error("Sirket adi zorunlu"); return; }
    try {
      await marketLaunchApi.onboardAgency(form);
      toast.success(`${form.company_name} onboard edildi`);
      setForm({ company_name: "", contact_name: "", contact_email: "", contact_phone: "", pricing_tier: "free" });
      setShowForm(false);
      load();
    } catch { toast.error("Onboard basarisiz"); }
  };

  const handleActivate = async (name) => {
    try {
      await marketLaunchApi.updateAgency({ company_name: name, status: "active", supplier_credentials_status: "configured" });
      toast.success(`${name} aktif edildi`);
      load();
    } catch { toast.error("Guncelleme basarisiz"); }
  };

  if (loading && !data) return <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" /></div>;

  const summary = data?.summary || {};

  return (
    <div className="space-y-4" data-testid="pilot-agencies-tab">
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <KPICard title="Toplam Acente" value={summary.total || 0} icon={Building2} testId="kpi-total-agencies" />
        <KPICard title="Aktif" value={summary.active || 0} icon={CheckCircle} testId="kpi-active" />
        <KPICard title="Onboarding" value={summary.onboarding || 0} icon={Clock} testId="kpi-onboarding" />
        <KPICard title="Rez. Yapan" value={summary.with_bookings || 0} icon={Zap} testId="kpi-with-bookings" />
        <KPICard title="Adoption" value={`%${summary.adoption_rate_pct || 0}`} icon={TrendingUp} testId="kpi-adoption" />
      </div>

      <div className="flex items-center justify-between">
        <h3 className="text-sm font-medium">Pilot Acenteler</h3>
        <Button size="sm" onClick={() => setShowForm(!showForm)} data-testid="add-agency-btn">
          <Plus className="h-3.5 w-3.5 mr-1" /> Acente Ekle
        </Button>
      </div>

      {showForm && (
        <Card data-testid="onboard-form">
          <CardContent className="p-4 grid grid-cols-2 md:grid-cols-5 gap-2">
            <Input placeholder="Sirket Adi" value={form.company_name} onChange={e => setForm({...form, company_name: e.target.value})} data-testid="input-company" />
            <Input placeholder="Yetkili" value={form.contact_name} onChange={e => setForm({...form, contact_name: e.target.value})} data-testid="input-contact" />
            <Input placeholder="Email" value={form.contact_email} onChange={e => setForm({...form, contact_email: e.target.value})} data-testid="input-email" />
            <Input placeholder="Telefon" value={form.contact_phone} onChange={e => setForm({...form, contact_phone: e.target.value})} data-testid="input-phone" />
            <Button onClick={handleOnboard} data-testid="submit-onboard">Onboard</Button>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Acente</TableHead>
                <TableHead>Yetkili</TableHead>
                <TableHead>Plan</TableHead>
                <TableHead>Durum</TableHead>
                <TableHead>Credential</TableHead>
                <TableHead className="text-right">Aramalar</TableHead>
                <TableHead className="text-right">Rez.</TableHead>
                <TableHead className="text-right">Son Aktivite</TableHead>
                <TableHead>Islem</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {(data?.agencies || []).map((a, i) => (
                <TableRow key={i}>
                  <TableCell className="font-medium">{a.company_name}</TableCell>
                  <TableCell className="text-sm text-muted-foreground">{a.contact_name}</TableCell>
                  <TableCell><Badge variant="outline" className="text-xs capitalize">{a.pricing_tier}</Badge></TableCell>
                  <TableCell>
                    <Badge className={a.status === "active" ? "bg-emerald-100 text-emerald-800" : "bg-amber-100 text-amber-800"}>
                      {a.status}
                    </Badge>
                  </TableCell>
                  <TableCell>
                    <Badge className={a.supplier_credentials_status === "configured" ? "bg-emerald-100 text-emerald-800" : "bg-gray-100 text-gray-700"}>
                      {a.supplier_credentials_status}
                    </Badge>
                  </TableCell>
                  <TableCell className="text-right">{a.total_searches}</TableCell>
                  <TableCell className="text-right">{a.total_bookings}</TableCell>
                  <TableCell className="text-right text-xs text-muted-foreground">
                    {a.last_activity ? new Date(a.last_activity).toLocaleDateString("tr-TR") : "-"}
                  </TableCell>
                  <TableCell>
                    {a.status === "onboarding" && (
                      <Button size="sm" variant="outline" onClick={() => handleActivate(a.company_name)}>
                        Aktif Et
                      </Button>
                    )}
                  </TableCell>
                </TableRow>
              ))}
              {(!data?.agencies || data.agencies.length === 0) && (
                <TableRow><TableCell colSpan={9} className="text-center text-muted-foreground py-8">Henuz pilot acente yok</TableCell></TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
}

// ========================= USAGE METRICS TAB =========================
function UsageMetricsTab() {
  const [data, setData] = useState(null);
  const [days, setDays] = useState(7);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await marketLaunchApi.getUsageMetrics(days)); }
    catch { toast.error("Metrikler yuklenemedi"); }
    finally { setLoading(false); }
  }, [days]);

  useEffect(() => { load(); }, [load]);

  if (loading && !data) return <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" /></div>;

  return (
    <div className="space-y-4" data-testid="usage-metrics-tab">
      <div className="flex items-center gap-2">
        {[7, 14, 30].map(d => (
          <Button key={d} size="sm" variant={days === d ? "default" : "outline"} onClick={() => setDays(d)} data-testid={`days-${d}`}>
            {d} Gun
          </Button>
        ))}
      </div>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
        <KPICard title="Aramalar" value={data?.searches || 0} icon={BarChart3} testId="usage-searches" />
        <KPICard title="Rezervasyonlar" value={data?.bookings || 0} icon={Zap} testId="usage-bookings" />
        <KPICard title="Komisyonlar" value={data?.commissions || 0} icon={CreditCard} testId="usage-commissions" />
        <KPICard title="Conversion" value={`%${data?.conversion_rate_pct || 0}`} icon={TrendingUp} testId="usage-conversion" />
        <KPICard title="Gelir" value={`${(data?.revenue || 0).toLocaleString("tr-TR")} EUR`} icon={CreditCard} testId="usage-revenue" />
        <KPICard title="Kar Marji" value={`${(data?.margin || 0).toLocaleString("tr-TR")} EUR`} icon={TrendingUp} testId="usage-margin" />
      </div>
      {data?.daily && data.daily.length > 0 && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Gunluk Aktivite</CardTitle></CardHeader>
          <CardContent>
            <div className="grid grid-cols-7 gap-1">
              {data.daily.map((d, i) => {
                const maxS = Math.max(1, ...data.daily.map(x => x.searches));
                const h = Math.max(4, (d.searches / maxS) * 60);
                return (
                  <div key={i} className="flex flex-col items-center">
                    <div className="w-full bg-primary/20 rounded-t" style={{ height: `${h}px` }}>
                      <div className="w-full bg-primary rounded-t" style={{ height: `${Math.max(2, (d.bookings / Math.max(d.searches, 1)) * h)}px` }} />
                    </div>
                    <span className="text-[9px] text-muted-foreground mt-1">{d.date?.slice(5)}</span>
                    <span className="text-[9px] font-medium">{d.searches}</span>
                  </div>
                );
              })}
            </div>
            <div className="flex gap-4 mt-2 text-xs text-muted-foreground">
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-primary/20" /> Arama</span>
              <span className="flex items-center gap-1"><span className="w-2 h-2 rounded-full bg-primary" /> Rez.</span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ========================= FEEDBACK TAB =========================
function FeedbackTab() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [fbForm, setFbForm] = useState({ agency_name: "", ratings: {}, comments: "" });

  const load = useCallback(async () => {
    setLoading(true);
    try { setData(await marketLaunchApi.getFeedback()); }
    catch { toast.error("Feedback yuklenemedi"); }
    finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSubmit = async () => {
    if (!fbForm.agency_name) { toast.error("Acente adi zorunlu"); return; }
    try {
      await marketLaunchApi.submitFeedback(fbForm);
      toast.success("Feedback gonderildi");
      setShowForm(false);
      setFbForm({ agency_name: "", ratings: {}, comments: "" });
      load();
    } catch { toast.error("Feedback gonderilemedi"); }
  };

  const setRating = (qId, val) => setFbForm({ ...fbForm, ratings: { ...fbForm.ratings, [qId]: val } });

  if (loading && !data) return <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" /></div>;

  const questions = data?.questions || [];
  const ratingQuestions = questions.filter(q => q.type === "rating");

  return (
    <div className="space-y-4" data-testid="feedback-tab">
      <div className="flex items-center justify-between">
        <div>
          <p className="text-sm text-muted-foreground">{data?.total_responses || 0} yanit, Genel skor: <span className="font-bold">{data?.overall_score || 0}/5</span></p>
        </div>
        <Button size="sm" onClick={() => setShowForm(!showForm)} data-testid="add-feedback-btn">
          <MessageSquare className="h-3.5 w-3.5 mr-1" /> Feedback Ekle
        </Button>
      </div>

      {data?.averages && Object.keys(data.averages).length > 0 && (
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3">
          {ratingQuestions.map(q => (
            <Card key={q.id}>
              <CardContent className="p-3 text-center">
                <p className="text-xs text-muted-foreground">{q.question}</p>
                <p className="text-xl font-bold mt-1">{data.averages[q.id] || "-"}</p>
                <div className="flex justify-center mt-1">
                  {[1,2,3,4,5].map(s => (
                    <Star key={s} className={`h-3 w-3 ${s <= (data.averages[q.id] || 0) ? "text-amber-400 fill-amber-400" : "text-gray-300"}`} />
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {showForm && (
        <Card data-testid="feedback-form">
          <CardContent className="p-4 space-y-3">
            <Input placeholder="Acente Adi" value={fbForm.agency_name} onChange={e => setFbForm({...fbForm, agency_name: e.target.value})} data-testid="fb-agency" />
            {ratingQuestions.map(q => (
              <div key={q.id} className="flex items-center justify-between">
                <span className="text-sm">{q.question}</span>
                <div className="flex gap-1">
                  {[1,2,3,4,5].map(s => (
                    <button key={s} onClick={() => setRating(q.id, s)} className="p-0.5" data-testid={`rate-${q.id}-${s}`}>
                      <Star className={`h-5 w-5 ${s <= (fbForm.ratings[q.id] || 0) ? "text-amber-400 fill-amber-400" : "text-gray-300"}`} />
                    </button>
                  ))}
                </div>
              </div>
            ))}
            <Input placeholder="Ek yorumlariniz" value={fbForm.comments} onChange={e => setFbForm({...fbForm, comments: e.target.value})} data-testid="fb-comments" />
            <Button onClick={handleSubmit} data-testid="submit-feedback">
              <Send className="h-3.5 w-3.5 mr-1" /> Gonder
            </Button>
          </CardContent>
        </Card>
      )}

      {(data?.feedbacks || []).length > 0 && (
        <Card>
          <CardHeader className="pb-2"><CardTitle className="text-sm">Son Geri Bildirimler</CardTitle></CardHeader>
          <CardContent>
            <div className="space-y-2">
              {(data.feedbacks || []).slice(-5).reverse().map((fb, i) => (
                <div key={i} className="border-b pb-2 last:border-0">
                  <div className="flex items-center justify-between">
                    <span className="text-sm font-medium">{fb.agency_name}</span>
                    <span className="text-xs text-muted-foreground">{fb.submitted_at ? new Date(fb.submitted_at).toLocaleDateString("tr-TR") : ""}</span>
                  </div>
                  <div className="flex gap-2 mt-1">
                    {Object.entries(fb.ratings || {}).map(([k, v]) => (
                      <Badge key={k} variant="outline" className="text-xs">{k.replace(/_/g, " ")}: {v}/5</Badge>
                    ))}
                  </div>
                  {fb.comments && <p className="text-xs text-muted-foreground mt-1">{fb.comments}</p>}
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ========================= PRICING TAB =========================
function PricingTab() {
  const [tiers, setTiers] = useState([]);
  useEffect(() => {
    marketLaunchApi.getPricing().then(d => setTiers(d.tiers || [])).catch(() => {});
  }, []);

  return (
    <div className="space-y-4" data-testid="pricing-tab">
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {tiers.map(t => (
          <Card key={t.tier} className={t.tier === "pro" ? "border-primary border-2" : ""}>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{t.name}</CardTitle>
                {t.tier === "pro" && <Badge className="bg-primary text-white">Populer</Badge>}
              </div>
              <div className="mt-2">
                {t.price_monthly_eur >= 0 ? (
                  <span className="text-3xl font-bold">{t.price_monthly_eur === 0 ? "Ucretsiz" : `${t.price_monthly_eur} EUR`}</span>
                ) : (
                  <span className="text-xl font-bold">Ozel Fiyat</span>
                )}
                {t.price_monthly_eur > 0 && <span className="text-sm text-muted-foreground">/ay</span>}
              </div>
            </CardHeader>
            <CardContent>
              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span>Komisyon</span>
                  <span className="font-medium">{t.commission_pct >= 0 ? `%${t.commission_pct}` : "Ozel"}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Aylk Rez. Limiti</span>
                  <span className="font-medium">{t.max_bookings_month >= 0 ? t.max_bookings_month.toLocaleString() : "Sinirsiz"}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span>Kullanici</span>
                  <span className="font-medium">{t.max_users >= 0 ? t.max_users : "Sinirsiz"}</span>
                </div>
              </div>
              <div className="border-t pt-3 space-y-1.5">
                {t.features.map((f, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <CheckCircle className="h-3 w-3 text-emerald-500 shrink-0" />
                    <span>{f}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  );
}

// ========================= LAUNCH REPORT TAB =========================
function LaunchReportTab() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    marketLaunchApi.getLaunchReport()
      .then(setReport)
      .catch(() => toast.error("Launch raporu yuklenemedi"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="flex justify-center py-12"><Loader2 className="h-6 w-6 animate-spin" /></div>;
  if (!report) return null;

  const ms = report.market_readiness_score || {};

  return (
    <div className="space-y-6" data-testid="launch-report-tab">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm">Market Readiness Score</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-6 flex-wrap">
            <div className="text-center">
              <p className="text-4xl font-bold">{ms.overall}</p>
              <p className="text-xs text-muted-foreground">/10</p>
            </div>
            {Object.entries(ms.dimensions || {}).map(([k, v]) => (
              <div key={k} className="text-center">
                <p className="text-lg font-bold">{v}</p>
                <p className="text-[10px] text-muted-foreground capitalize">{k.replace(/_/g, " ")}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <KPICard title="Aramalar (30g)" value={report.usage_metrics?.searches_30d || 0} icon={BarChart3} testId="lr-searches" />
        <KPICard title="Rez. (30g)" value={report.usage_metrics?.bookings_30d || 0} icon={Zap} testId="lr-bookings" />
        <KPICard title="Conversion" value={`%${report.usage_metrics?.conversion_pct || 0}`} icon={TrendingUp} testId="lr-conversion" />
        <KPICard title="Gelir" value={`${(report.usage_metrics?.revenue || 0).toLocaleString("tr-TR")} EUR`} icon={CreditCard} testId="lr-revenue" />
      </div>

      {report.positioning && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2"><Globe className="h-4 w-4" /> Pazar Konumlandirma</CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-lg font-bold">{report.positioning.headline}</p>
            <p className="text-sm text-muted-foreground mt-1">{report.positioning.tagline}</p>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2 mt-3">
              {report.positioning.value_props?.map((vp, i) => (
                <div key={i} className="flex items-center gap-2 text-sm">
                  <CheckCircle className="h-3.5 w-3.5 text-emerald-500 shrink-0" />
                  <span>{vp}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {report.operational_risks?.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2"><AlertTriangle className="h-4 w-4" /> Riskler ({report.operational_risks.length})</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {report.operational_risks.map((r, i) => (
                <div key={i} className="flex items-start gap-2">
                  <Badge className={r.severity === "critical" ? "bg-red-100 text-red-800" : r.severity === "medium" ? "bg-amber-100 text-amber-800" : "bg-blue-100 text-blue-800"}>
                    {r.severity}
                  </Badge>
                  <div>
                    <p className="text-sm font-medium">{r.title}</p>
                    <p className="text-xs text-muted-foreground">{r.mitigation}</p>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {report.support_channels && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2"><Phone className="h-4 w-4" /> Destek Kanallari</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              {report.support_channels.map((ch, i) => (
                <div key={i} className="text-center p-3 border rounded-lg">
                  {ch.channel === "email" ? <Mail className="h-5 w-5 mx-auto mb-1 text-primary" /> :
                   ch.channel === "whatsapp" ? <Phone className="h-5 w-5 mx-auto mb-1 text-emerald-500" /> :
                   <BookOpen className="h-5 w-5 mx-auto mb-1 text-blue-500" />}
                  <p className="text-sm font-medium capitalize">{ch.channel}</p>
                  <p className="text-xs text-muted-foreground">{ch.response_sla}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ========================= MAIN PAGE =========================
export default function MarketLaunchPage() {
  const [tab, setTab] = useState("pilot");

  return (
    <div className="space-y-6 p-4 md:p-6" data-testid="market-launch-page">
      <div>
        <h1 className="text-xl font-bold tracking-tight">Market Launch & First Customers</h1>
        <p className="text-sm text-muted-foreground mt-0.5">
          Pilot acenteler, kullanim metrikleri, geri bildirim, fiyatlandirma ve launch raporu
        </p>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList data-testid="market-launch-tabs">
          <TabsTrigger value="pilot" data-testid="tab-pilot">
            <Users className="h-3.5 w-3.5 mr-1" /> Pilot Acenteler
          </TabsTrigger>
          <TabsTrigger value="usage" data-testid="tab-usage">
            <BarChart3 className="h-3.5 w-3.5 mr-1" /> Kullanim
          </TabsTrigger>
          <TabsTrigger value="feedback" data-testid="tab-feedback">
            <MessageSquare className="h-3.5 w-3.5 mr-1" /> Feedback
          </TabsTrigger>
          <TabsTrigger value="pricing" data-testid="tab-pricing">
            <CreditCard className="h-3.5 w-3.5 mr-1" /> Fiyatlandirma
          </TabsTrigger>
          <TabsTrigger value="report" data-testid="tab-report">
            <FileText className="h-3.5 w-3.5 mr-1" /> Launch Raporu
          </TabsTrigger>
        </TabsList>

        <TabsContent value="pilot"><PilotAgenciesTab /></TabsContent>
        <TabsContent value="usage"><UsageMetricsTab /></TabsContent>
        <TabsContent value="feedback"><FeedbackTab /></TabsContent>
        <TabsContent value="pricing"><PricingTab /></TabsContent>
        <TabsContent value="report"><LaunchReportTab /></TabsContent>
      </Tabs>
    </div>
  );
}
