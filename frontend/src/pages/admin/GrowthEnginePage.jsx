import React, { useState, useCallback } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "../../components/ui/card";
import { Badge } from "../../components/ui/badge";
import { Button } from "../../components/ui/button";
import { Input } from "../../components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "../../components/ui/tabs";
import {
  TrendingUp, Users, Target, Gift, Activity, BarChart3, Zap,
  ChevronRight, Plus, RefreshCw, ArrowRight, CheckCircle2, XCircle,
  Clock, AlertTriangle, UserPlus, Mail, Phone, Building2, Star,
  ChevronDown, FileText, Layers
} from "lucide-react";
import { api } from "../../lib/api";
import { toast } from "sonner";

// ─── Funnel Tab ──────────────────────────────────────────────
function FunnelTab() {
  const { data, isLoading: loading } = useQuery({
    queryKey: ["growth", "funnel"],
    queryFn: async () => {
      const r = await api.get("/growth/funnel");
      return r.data;
    },
  });
  if (loading) return <p className="text-zinc-500 text-xs p-4">Yukleniyor...</p>;
  if (!data) return null;

  const maxCount = Math.max(...(data.stages || []).map(s => s.count), 1);

  return (
    <div data-testid="funnel-tab" className="space-y-5">
      <div className="flex gap-3 text-xs">
        <div className="bg-zinc-800/50 rounded-lg px-4 py-2.5 border border-zinc-800 flex items-center gap-2">
          <Users className="w-3.5 h-3.5 text-zinc-500" />
          <span className="text-zinc-500">Toplam Lead:</span>
          <span className="text-zinc-200 font-mono font-medium" data-testid="total-leads">{data.total_leads}</span>
        </div>
        <div className="bg-zinc-800/50 rounded-lg px-4 py-2.5 border border-zinc-800 flex items-center gap-2">
          <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
          <span className="text-zinc-500">Activated:</span>
          <span className="text-emerald-400 font-mono font-medium">{data.activated}</span>
        </div>
        <div className="bg-zinc-800/50 rounded-lg px-4 py-2.5 border border-zinc-800 flex items-center gap-2">
          <TrendingUp className="w-3.5 h-3.5 text-blue-500" />
          <span className="text-zinc-500">Conversion:</span>
          <span className="text-blue-400 font-mono font-medium">{data.overall_conversion_pct}%</span>
        </div>
      </div>

      <Card className="bg-zinc-900/80 border-zinc-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2"><Target className="w-4 h-4 text-blue-400" />Acquisition Funnel</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2">
          {(data.stages || []).map((s, i) => (
            <div key={s.key} className="flex items-center gap-3">
              <span className="text-[11px] text-zinc-500 w-6 text-right">{i + 1}</span>
              <span className="text-[11px] text-zinc-300 w-32 shrink-0">{s.label}</span>
              <div className="flex-1 bg-zinc-800 rounded-full h-5 overflow-hidden">
                <div
                  className="h-full bg-gradient-to-r from-blue-600 to-cyan-500 rounded-full flex items-center justify-end pr-2 transition-all"
                  style={{ width: `${Math.max((s.count / maxCount) * 100, 8)}%` }}
                >
                  <span className="text-[10px] font-mono text-white font-bold">{s.count}</span>
                </div>
              </div>
              <span className="text-[10px] text-zinc-500 w-12 text-right font-mono">{s.conversion_pct}%</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Leads Tab ───────────────────────────────────────────────
function LeadsTab() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ company_name: "", contact_name: "", contact_email: "", contact_phone: "", source: "inbound" });

  const { data: leads = [], isLoading: loading } = useQuery({
    queryKey: ["growth", "leads"],
    queryFn: async () => {
      const r = await api.get("/growth/leads");
      return r.data.leads || [];
    },
  });

  const refetchLeads = () => queryClient.invalidateQueries({ queryKey: ["growth", "leads"] });

  const createLead = async () => {
    await api.post("/growth/leads", form);
    setShowForm(false);
    setForm({ company_name: "", contact_name: "", contact_email: "", contact_phone: "", source: "inbound" });
    refetchLeads();
  };

  const updateStage = async (leadId, stage) => {
    await api.put(`/growth/leads/${leadId}/stage`, { stage });
    refetchLeads();
  };

  const STAGE_COLORS = {
    lead_captured: "bg-blue-500/20 text-blue-300",
    demo_scheduled: "bg-amber-500/20 text-amber-300",
    demo_completed: "bg-purple-500/20 text-purple-300",
    pilot_started: "bg-cyan-500/20 text-cyan-300",
    first_search: "bg-teal-500/20 text-teal-300",
    first_booking: "bg-emerald-500/20 text-emerald-300",
    activated: "bg-green-500/20 text-green-300",
    churned: "bg-red-500/20 text-red-300",
  };

  return (
    <div data-testid="leads-tab" className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-500">{leads.length} lead</span>
        <div className="flex gap-2">
          <Button size="sm" variant="outline" className="text-xs h-7" onClick={fetch}>
            <RefreshCw className={`w-3 h-3 ${loading ? "animate-spin" : ""}`} />
          </Button>
          <Button data-testid="add-lead-btn" size="sm" className="text-xs h-7" onClick={() => setShowForm(!showForm)}>
            <Plus className="w-3 h-3 mr-1" />Yeni Lead
          </Button>
        </div>
      </div>

      {showForm && (
        <Card data-testid="lead-form" className="bg-zinc-900/80 border-zinc-800">
          <CardContent className="pt-4 space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <Input data-testid="lead-company" placeholder="Sirket Adi" value={form.company_name} onChange={e => setForm(p => ({ ...p, company_name: e.target.value }))} className="h-8 text-xs bg-zinc-800/80 border-zinc-700" />
              <Input data-testid="lead-contact" placeholder="Ilgili Kisi" value={form.contact_name} onChange={e => setForm(p => ({ ...p, contact_name: e.target.value }))} className="h-8 text-xs bg-zinc-800/80 border-zinc-700" />
              <Input data-testid="lead-email" placeholder="Email" value={form.contact_email} onChange={e => setForm(p => ({ ...p, contact_email: e.target.value }))} className="h-8 text-xs bg-zinc-800/80 border-zinc-700" />
              <Input data-testid="lead-phone" placeholder="Telefon" value={form.contact_phone} onChange={e => setForm(p => ({ ...p, contact_phone: e.target.value }))} className="h-8 text-xs bg-zinc-800/80 border-zinc-700" />
            </div>
            <select data-testid="lead-source" value={form.source} onChange={e => setForm(p => ({ ...p, source: e.target.value }))} className="h-8 text-xs bg-zinc-800/80 border border-zinc-700 rounded px-2 text-zinc-300">
              <option value="inbound">Inbound</option>
              <option value="outbound">Outbound</option>
              <option value="referral">Referral</option>
              <option value="organic">Organic</option>
            </select>
            <Button data-testid="submit-lead" size="sm" className="text-xs h-7" onClick={createLead}>Kaydet</Button>
          </CardContent>
        </Card>
      )}

      <div className="space-y-1">
        {leads.map(lead => (
          <div key={lead.lead_id} className="flex items-center gap-3 bg-zinc-900/50 rounded-lg px-4 py-2.5 border border-zinc-800/50 text-xs">
            <Building2 className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
            <span className="text-zinc-200 font-medium w-40 truncate">{lead.company_name}</span>
            <span className="text-zinc-500 w-28 truncate">{lead.contact_name}</span>
            <Badge variant="outline" className={`text-[9px] ${STAGE_COLORS[lead.stage] || "text-zinc-400"}`}>{lead.stage}</Badge>
            <Badge variant="outline" className="text-[9px] text-zinc-500">{lead.source}</Badge>
            <span className="text-zinc-600 text-[10px] ml-auto">{lead.created_at ? new Date(lead.created_at).toLocaleDateString("tr-TR") : ""}</span>
            <select className="text-[10px] bg-zinc-800 border border-zinc-700 rounded px-1 py-0.5 text-zinc-300" value={lead.stage} onChange={e => updateStage(lead.lead_id, e.target.value)}>
              <option value="lead_captured">Lead Captured</option>
              <option value="demo_scheduled">Demo Scheduled</option>
              <option value="demo_completed">Demo Completed</option>
              <option value="pilot_started">Pilot Started</option>
              <option value="first_search">First Search</option>
              <option value="first_booking">First Booking</option>
              <option value="activated">Activated</option>
              <option value="churned">Churned</option>
            </select>
          </div>
        ))}
        {leads.length === 0 && !loading && <p className="text-zinc-500 text-xs text-center py-6">Henuz lead yok</p>}
      </div>
    </div>
  );
}

// ─── Referrals Tab ───────────────────────────────────────────
function ReferralsTab() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ referrer_name: "", referred_company_name: "", referred_contact_name: "", referred_email: "" });

  const { data = { referrals: [], stats: {}, reward_rules: {} } } = useQuery({
    queryKey: ["growth", "referrals"],
    queryFn: async () => {
      const r = await api.get("/growth/referrals");
      return r.data;
    },
  });

  const refetchReferrals = () => queryClient.invalidateQueries({ queryKey: ["growth", "referrals"] });

  const create = async () => {
    const res = await api.post("/growth/referrals", form);
    if (res.data?.error) { toast.error(res.data.error); return; }
    setShowForm(false);
    setForm({ referrer_name: "", referred_company_name: "", referred_contact_name: "", referred_email: "" });
    refetchReferrals();
  };

  const updateStatus = async (id, status) => {
    await api.put(`/growth/referrals/${id}/status`, { status });
    refetchReferrals();
  };

  return (
    <div data-testid="referrals-tab" className="space-y-4">
      <div className="flex gap-3 text-xs">
        {Object.entries(data.stats || {}).map(([k, v]) => (
          <div key={k} className="bg-zinc-800/50 rounded-lg px-3 py-2 border border-zinc-800 flex items-center gap-2">
            <span className="text-zinc-500 capitalize">{k}:</span>
            <span className="text-zinc-200 font-mono">{v}</span>
          </div>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-500">{data.referrals?.length || 0} referral</span>
        <Button data-testid="add-referral-btn" size="sm" className="text-xs h-7" onClick={() => setShowForm(!showForm)}>
          <Gift className="w-3 h-3 mr-1" />Yeni Referral
        </Button>
      </div>

      {showForm && (
        <Card data-testid="referral-form" className="bg-zinc-900/80 border-zinc-800">
          <CardContent className="pt-4 space-y-2">
            <div className="grid grid-cols-2 gap-2">
              <Input data-testid="ref-referrer" placeholder="Referans Veren" value={form.referrer_name} onChange={e => setForm(p => ({ ...p, referrer_name: e.target.value }))} className="h-8 text-xs bg-zinc-800/80 border-zinc-700" />
              <Input data-testid="ref-company" placeholder="Referans Edilen Sirket" value={form.referred_company_name} onChange={e => setForm(p => ({ ...p, referred_company_name: e.target.value }))} className="h-8 text-xs bg-zinc-800/80 border-zinc-700" />
              <Input data-testid="ref-contact" placeholder="Ilgili Kisi" value={form.referred_contact_name} onChange={e => setForm(p => ({ ...p, referred_contact_name: e.target.value }))} className="h-8 text-xs bg-zinc-800/80 border-zinc-700" />
              <Input data-testid="ref-email" placeholder="Email" value={form.referred_email} onChange={e => setForm(p => ({ ...p, referred_email: e.target.value }))} className="h-8 text-xs bg-zinc-800/80 border-zinc-700" />
            </div>
            <Button data-testid="submit-referral" size="sm" className="text-xs h-7" onClick={create}>Gonder</Button>
          </CardContent>
        </Card>
      )}

      {/* Reward rules */}
      <Card className="bg-zinc-800/30 border-zinc-700/50">
        <CardContent className="pt-4 text-xs">
          <p className="text-zinc-400 font-medium mb-2">Odul Kurallari:</p>
          {Object.entries(data.reward_rules || {}).map(([k, v]) => (
            <p key={k} className="text-zinc-500"><span className="text-zinc-300 capitalize">{k}:</span> {v.description}</p>
          ))}
        </CardContent>
      </Card>

      <div className="space-y-1">
        {(data.referrals || []).map(r => (
          <div key={r.referral_id} className="flex items-center gap-3 bg-zinc-900/50 rounded-lg px-4 py-2.5 border border-zinc-800/50 text-xs">
            <Gift className="w-3.5 h-3.5 text-zinc-500 shrink-0" />
            <span className="text-zinc-200 w-32 truncate">{r.referred_company_name}</span>
            <span className="text-zinc-500 w-32 truncate">{r.referred_email}</span>
            <Badge variant="outline" className="text-[9px]">{r.status}</Badge>
            {r.reward_type && <span className="text-amber-400 text-[10px]">{r.reward_amount} {r.reward_type}</span>}
            <span className="text-zinc-600 text-[10px] ml-auto">{r.referrer_name}</span>
            <select className="text-[10px] bg-zinc-800 border border-zinc-700 rounded px-1 py-0.5 text-zinc-300" value={r.status} onChange={e => updateStatus(r.referral_id, e.target.value)}>
              <option value="pending">Pending</option>
              <option value="registered">Registered</option>
              <option value="activated">Activated</option>
              <option value="rewarded">Rewarded</option>
              <option value="rejected">Rejected</option>
            </select>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Customer Success Tab ────────────────────────────────────
function CustomerSuccessTab() {
  const { data, isLoading: loading } = useQuery({
    queryKey: ["growth", "customer-success"],
    queryFn: async () => {
      const r = await api.get("/growth/customer-success");
      return r.data;
    },
  });
  if (loading) return <p className="text-zinc-500 text-xs p-4">Yukleniyor...</p>;
  if (!data) return null;

  const s = data.summary || {};
  const cards = [
    { label: "Aktif", value: s.active, icon: CheckCircle2, color: "text-emerald-400" },
    { label: "Dormant", value: s.dormant, icon: Clock, color: "text-amber-400" },
    { label: "At Risk", value: s.at_risk, icon: AlertTriangle, color: "text-red-400" },
    { label: "Failed Conn.", value: s.failed_connections, icon: XCircle, color: "text-red-400" },
    { label: "Zero Bookings", value: s.zero_bookings, icon: BarChart3, color: "text-zinc-400" },
  ];

  const sections = [
    { key: "active_agencies", label: "Aktif Acenteler", color: "border-emerald-800/50" },
    { key: "dormant_agencies", label: "Dormant Acenteler", color: "border-amber-800/50" },
    { key: "at_risk_agencies", label: "Risk Altinda", color: "border-red-800/50" },
    { key: "failed_connection_agencies", label: "Basarisiz Baglantilar", color: "border-red-800/50" },
  ];

  return (
    <div data-testid="customer-success-tab" className="space-y-5">
      <div className="grid grid-cols-5 gap-3">
        {cards.map(c => (
          <div key={c.label} className="bg-zinc-900/60 rounded-lg px-4 py-3 border border-zinc-800">
            <c.icon className={`w-4 h-4 ${c.color} mb-1`} />
            <p className="text-lg font-bold text-zinc-200 font-mono">{c.value}</p>
            <p className="text-[10px] text-zinc-500">{c.label}</p>
          </div>
        ))}
      </div>

      {sections.map(sec => {
        const list = data[sec.key] || [];
        if (list.length === 0) return null;
        return (
          <Card key={sec.key} className={`bg-zinc-900/60 border-zinc-800 ${sec.color}`}>
            <CardHeader className="pb-2">
              <CardTitle className="text-xs text-zinc-400">{sec.label} ({list.length})</CardTitle>
            </CardHeader>
            <CardContent className="space-y-1">
              {list.slice(0, 5).map(a => (
                <div key={a.organization_id} className="flex items-center gap-3 text-[11px] py-1">
                  <span className="text-zinc-300 w-40 truncate">{a.name}</span>
                  <span className="text-zinc-500">Suppliers: {a.connected_suppliers}</span>
                  <span className="text-zinc-500">Bookings: {a.bookings_30d}</span>
                  <span className="text-zinc-500">Score: {a.activation_score}</span>
                </div>
              ))}
            </CardContent>
          </Card>
        );
      })}

      <Card className="bg-zinc-800/30 border-zinc-700/50">
        <CardHeader className="pb-2"><CardTitle className="text-xs text-zinc-400">Success Playbook</CardTitle></CardHeader>
        <CardContent className="space-y-1.5">
          {(data.success_playbook || []).map((p, i) => (
            <div key={i} className="flex items-start gap-2 text-[11px]">
              <ArrowRight className="w-3 h-3 text-blue-400 mt-0.5 shrink-0" />
              <span className="text-zinc-500">{p.trigger}:</span>
              <span className="text-zinc-300">{p.action}</span>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── Growth KPIs Tab ─────────────────────────────────────────
function GrowthKPIsTab() {
  const { data: kpiData, isLoading: loadingKpis } = useQuery({
    queryKey: ["growth", "kpis"],
    queryFn: async () => {
      const r = await api.get("/growth/kpis");
      return r.data;
    },
  });
  const { data: segmentsData, isLoading: loadingSegments } = useQuery({
    queryKey: ["growth", "segments"],
    queryFn: async () => {
      const r = await api.get("/growth/segments");
      return r.data;
    },
  });
  const loading = loadingKpis || loadingSegments;
  const data = kpiData;
  const segments = segmentsData;
  if (loading) return <p className="text-zinc-500 text-xs p-4">Yukleniyor...</p>;

  const kpis = data?.kpis || {};
  const kpiCards = [
    { label: "Yeni Lead", value: kpis.new_leads, color: "text-blue-400" },
    { label: "Toplam Lead", value: kpis.total_leads, color: "text-zinc-300" },
    { label: "Activated", value: kpis.activated_agencies, color: "text-emerald-400" },
    { label: "Booking Rate", value: `${kpis.first_booking_rate_pct}%`, color: "text-cyan-400" },
    { label: "Referral", value: kpis.total_referrals, color: "text-amber-400" },
    { label: "Ref. Conv.", value: `${kpis.referral_conversion_rate_pct}%`, color: "text-emerald-400" },
    { label: "Bookings", value: kpis.bookings_period, color: "text-teal-400" },
    { label: "Supplier Req.", value: kpis.pending_supplier_requests, color: "text-purple-400" },
  ];

  const segSummary = segments?.summary || {};

  return (
    <div data-testid="growth-kpis-tab" className="space-y-5">
      <div className="grid grid-cols-4 gap-3">
        {kpiCards.map(k => (
          <div key={k.label} className="bg-zinc-900/60 rounded-lg px-4 py-3 border border-zinc-800">
            <p className={`text-lg font-bold font-mono ${k.color}`}>{k.value}</p>
            <p className="text-[10px] text-zinc-500">{k.label}</p>
          </div>
        ))}
      </div>

      {segments && (
        <Card className="bg-zinc-900/80 border-zinc-800">
          <CardHeader className="pb-2">
            <CardTitle className="text-sm flex items-center gap-2"><Layers className="w-4 h-4 text-purple-400" />Agency Segmentation</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-4 gap-3">
              {[
                { key: "enterprise", label: "Enterprise (50+ booking)", color: "bg-purple-500/20 text-purple-300 border-purple-500/30" },
                { key: "growth", label: "Growth (10-49)", color: "bg-blue-500/20 text-blue-300 border-blue-500/30" },
                { key: "starter", label: "Starter (1-9)", color: "bg-cyan-500/20 text-cyan-300 border-cyan-500/30" },
                { key: "inactive", label: "Inactive (0)", color: "bg-zinc-600/30 text-zinc-400 border-zinc-600/30" },
              ].map(seg => (
                <div key={seg.key} className={`rounded-lg px-4 py-3 border ${seg.color}`}>
                  <p className="text-lg font-bold font-mono">{segSummary[seg.key] || 0}</p>
                  <p className="text-[10px]">{seg.label}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {data?.funnel_distribution && Object.keys(data.funnel_distribution).length > 0 && (
        <Card className="bg-zinc-900/80 border-zinc-800">
          <CardHeader className="pb-2"><CardTitle className="text-xs text-zinc-400">Funnel Distribution</CardTitle></CardHeader>
          <CardContent>
            <div className="flex flex-wrap gap-2">
              {Object.entries(data.funnel_distribution).map(([stage, count]) => (
                <Badge key={stage} variant="outline" className="text-[10px] gap-1 text-zinc-300">
                  {stage}: <span className="font-mono font-bold">{count}</span>
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}

// ─── Supplier Expansion Tab ──────────────────────────────────
function SupplierExpansionTab() {
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState({ supplier_name: "", supplier_type: "hotel", region: "" });

  const { data = { requests: [] } } = useQuery({
    queryKey: ["growth", "supplier-requests"],
    queryFn: async () => {
      const r = await api.get("/growth/supplier-requests");
      return r.data;
    },
  });

  const refetchRequests = () => queryClient.invalidateQueries({ queryKey: ["growth", "supplier-requests"] });

  const create = async () => {
    await api.post("/growth/supplier-requests", form);
    setShowForm(false);
    setForm({ supplier_name: "", supplier_type: "hotel", region: "" });
    refetchRequests();
  };

  return (
    <div data-testid="supplier-expansion-tab" className="space-y-4">
      <div className="flex items-center justify-between">
        <span className="text-xs text-zinc-500">{data.requests?.length || 0} talep</span>
        <Button data-testid="add-supplier-req-btn" size="sm" className="text-xs h-7" onClick={() => setShowForm(!showForm)}>
          <Plus className="w-3 h-3 mr-1" />Yeni Talep
        </Button>
      </div>

      {showForm && (
        <Card data-testid="supplier-req-form" className="bg-zinc-900/80 border-zinc-800">
          <CardContent className="pt-4 space-y-2">
            <div className="grid grid-cols-3 gap-2">
              <Input data-testid="sr-name" placeholder="Supplier Adi" value={form.supplier_name} onChange={e => setForm(p => ({ ...p, supplier_name: e.target.value }))} className="h-8 text-xs bg-zinc-800/80 border-zinc-700" />
              <select value={form.supplier_type} onChange={e => setForm(p => ({ ...p, supplier_type: e.target.value }))} className="h-8 text-xs bg-zinc-800/80 border border-zinc-700 rounded px-2 text-zinc-300">
                <option value="hotel">Hotel</option>
                <option value="flight">Flight</option>
                <option value="tour">Tour</option>
                <option value="transfer">Transfer</option>
              </select>
              <Input placeholder="Bolge" value={form.region} onChange={e => setForm(p => ({ ...p, region: e.target.value }))} className="h-8 text-xs bg-zinc-800/80 border-zinc-700" />
            </div>
            <Button data-testid="submit-supplier-req" size="sm" className="text-xs h-7" onClick={create}>Gonder</Button>
          </CardContent>
        </Card>
      )}

      <div className="space-y-1">
        {(data.requests || []).map(r => (
          <div key={r.request_id} className="flex items-center gap-3 bg-zinc-900/50 rounded-lg px-4 py-2.5 border border-zinc-800/50 text-xs">
            <Zap className="w-3.5 h-3.5 text-amber-400 shrink-0" />
            <span className="text-zinc-200 font-medium w-36">{r.supplier_name}</span>
            <Badge variant="outline" className="text-[9px]">{r.supplier_type}</Badge>
            <span className="text-zinc-500">{r.region}</span>
            <span className="text-zinc-500 ml-auto">Talep: <span className="text-amber-400 font-mono">{r.demand_count}</span></span>
            <Badge variant="outline" className="text-[9px]">{r.status}</Badge>
            <span className="text-zinc-600 font-mono text-[10px]">P{Math.round(r.priority_score / 10)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Growth Report Tab ───────────────────────────────────────
function GrowthReportTab() {
  const { data, isLoading: loading } = useQuery({
    queryKey: ["growth", "report"],
    queryFn: async () => {
      const r = await api.get("/growth/report");
      return r.data;
    },
  });
  if (loading) return <p className="text-zinc-500 text-xs p-4">Yukleniyor...</p>;
  if (!data) return null;

  return (
    <div data-testid="growth-report-tab" className="space-y-5">
      {/* Maturity Score */}
      <Card className="bg-zinc-900/80 border-zinc-800">
        <CardHeader className="pb-2">
          <CardTitle className="text-sm flex items-center gap-2"><Star className="w-4 h-4 text-amber-400" />Growth Maturity Score</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-3xl font-bold text-amber-400 font-mono">{data.growth_maturity_score}/10</p>
          <div className="grid grid-cols-4 gap-2 mt-3">
            {Object.entries(data.dimension_scores || {}).map(([k, v]) => (
              <div key={k} className="text-center">
                <p className="text-sm font-bold font-mono text-zinc-200">{v}</p>
                <p className="text-[9px] text-zinc-500 capitalize">{k.replace(/_/g, " ")}</p>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Tasks */}
      <Card className="bg-zinc-900/80 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-xs text-zinc-400">Top 25 Implementation Tasks</CardTitle></CardHeader>
        <CardContent className="space-y-1">
          {(data.implementation_tasks || []).map((t, i) => (
            <div key={i} className="flex items-center gap-2 text-[11px] py-0.5">
              <Badge variant="outline" className={`text-[9px] w-8 justify-center ${t.priority === "P0" ? "text-red-400 border-red-800" : t.priority === "P1" ? "text-amber-400 border-amber-800" : "text-zinc-500 border-zinc-700"}`}>{t.priority}</Badge>
              <span className="text-zinc-300">{t.task}</span>
            </div>
          ))}
        </CardContent>
      </Card>

      {/* Risks */}
      <Card className="bg-zinc-900/80 border-zinc-800">
        <CardHeader className="pb-2"><CardTitle className="text-xs text-zinc-400">Top 15 Growth Risks</CardTitle></CardHeader>
        <CardContent className="space-y-1.5">
          {(data.growth_risks || []).map((r, i) => (
            <div key={i} className="flex items-start gap-2 text-[11px] py-0.5">
              <Badge variant="outline" className={`text-[9px] w-14 justify-center shrink-0 ${r.severity === "high" ? "text-red-400 border-red-800" : r.severity === "medium" ? "text-amber-400 border-amber-800" : "text-zinc-500 border-zinc-700"}`}>{r.severity}</Badge>
              <div>
                <span className="text-zinc-300">{r.risk}</span>
                <p className="text-zinc-600 text-[10px]">Mitigation: {r.mitigation}</p>
              </div>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  );
}

// ─── MAIN PAGE ───────────────────────────────────────────────
export default function GrowthEnginePage() {
  return (
    <div data-testid="growth-engine-page" className="p-6 space-y-6">
      <div>
        <h2 className="text-lg font-bold text-zinc-100 flex items-center gap-2">
          <TrendingUp className="w-5 h-5 text-emerald-400" />
          Growth Engine
        </h2>
        <p className="text-xs text-zinc-500 mt-1">Agency acquisition, activation, retention ve buyume metrikleri</p>
      </div>

      <Tabs defaultValue="funnel" className="w-full">
        <TabsList className="bg-zinc-800/50 border border-zinc-700 flex-wrap h-auto gap-0.5 p-1">
          <TabsTrigger value="funnel" className="text-xs">Funnel</TabsTrigger>
          <TabsTrigger value="leads" className="text-xs">Leads</TabsTrigger>
          <TabsTrigger value="referrals" className="text-xs">Referrals</TabsTrigger>
          <TabsTrigger value="success" className="text-xs">Customer Success</TabsTrigger>
          <TabsTrigger value="kpis" className="text-xs">KPIs</TabsTrigger>
          <TabsTrigger value="suppliers" className="text-xs">Supplier Expansion</TabsTrigger>
          <TabsTrigger value="report" className="text-xs">Growth Report</TabsTrigger>
        </TabsList>

        <TabsContent value="funnel" className="mt-4"><FunnelTab /></TabsContent>
        <TabsContent value="leads" className="mt-4"><LeadsTab /></TabsContent>
        <TabsContent value="referrals" className="mt-4"><ReferralsTab /></TabsContent>
        <TabsContent value="success" className="mt-4"><CustomerSuccessTab /></TabsContent>
        <TabsContent value="kpis" className="mt-4"><GrowthKPIsTab /></TabsContent>
        <TabsContent value="suppliers" className="mt-4"><SupplierExpansionTab /></TabsContent>
        <TabsContent value="report" className="mt-4"><GrowthReportTab /></TabsContent>
      </Tabs>
    </div>
  );
}
