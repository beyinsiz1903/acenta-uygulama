import React, { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import {
  Building2, CheckSquare, Square, Loader2, Save,
  RefreshCw, ChevronDown, ChevronRight,
} from "lucide-react";
import { toast } from "sonner";

const ALL_MODULES = [
  { group: "TEMEL", items: [
    { key: "dashboard", label: "Genel Bakis" },
    { key: "turlarimiz", label: "Turlarimiz" },
    { key: "rezervasyonlar", label: "Rezervasyonlar" },
    { key: "urunler", label: "Urunler" },
    { key: "musaitlik", label: "Musaitlik" },
  ]},
  { group: "MUSTERI ILISKILERI", items: [
    { key: "musteriler", label: "Musteriler" },
    { key: "pipeline", label: "Satis Sureci" },
    { key: "gorevler", label: "Gorevler" },
    { key: "inbox", label: "Gelen Kutusu" },
  ]},
  { group: "B2B AG", items: [
    { key: "partner_yonetimi", label: "Ortaklik Yonetimi" },
    { key: "musaitlik_takibi", label: "Musaitlik Takibi" },
    { key: "sheet_baglantilari", label: "Sheet Baglantilari" },
    { key: "marketplace", label: "Pazar Yeri" },
    { key: "b2b_funnel", label: "Satis Hunisi" },
  ]},
  { group: "FINANS", items: [
    { key: "webpos", label: "Sanal Kasa" },
    { key: "mutabakat", label: "Mutabakat" },
    { key: "iadeler", label: "Iadeler" },
    { key: "exposure", label: "Acik Bakiye" },
    { key: "raporlar", label: "Raporlar" },
  ]},
  { group: "OPERASYON", items: [
    { key: "guest_cases", label: "Misafir Talepleri" },
    { key: "ops_tasks", label: "Gorev Takibi" },
    { key: "ops_incidents", label: "Olaylar" },
  ]},
];

function AgencyModuleCard({ agency, onSaved }) {
  const [expanded, setExpanded] = useState(false);
  const [modules, setModules] = useState([]);
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  const loadModules = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get(`/admin/agencies/${agency._id || agency.id}/modules`);
      setModules(res.data?.allowed_modules || []);
    } catch { /* silent */ }
    setLoading(false);
  }, [agency]);

  useEffect(() => {
    if (expanded) loadModules();
  }, [expanded, loadModules]);

  const toggle = (key) => {
    setModules((prev) =>
      prev.includes(key) ? prev.filter((k) => k !== key) : [...prev, key]
    );
  };

  const selectAll = () => {
    const allKeys = ALL_MODULES.flatMap((g) => g.items.map((i) => i.key));
    setModules(allKeys);
  };

  const clearAll = () => setModules([]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await api.put(`/admin/agencies/${agency._id || agency.id}/modules`, {
        allowed_modules: modules,
      });
      toast.success(`${agency.name} modulleri guncellendi`);
      if (onSaved) onSaved();
    } catch (e) {
      toast.error(e.response?.data?.detail || "Kaydetme hatasi");
    }
    setSaving(false);
  };

  return (
    <div className="bg-white dark:bg-gray-800 rounded-xl border border-gray-200 dark:border-gray-700" data-testid={`agency-module-card-${agency._id || agency.id}`}>
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center justify-between p-4 hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors rounded-xl"
        data-testid={`agency-expand-${agency._id || agency.id}`}
      >
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-lg bg-primary/10 flex items-center justify-center">
            <Building2 className="w-4 h-4 text-primary" />
          </div>
          <div className="text-left">
            <div className="font-medium text-sm">{agency.name}</div>
            <div className="text-xs text-muted-foreground">
              {modules.length > 0 ? `${modules.length} modul aktif` : "Modul ayarlanmamis (tumu acik)"}
            </div>
          </div>
        </div>
        {expanded ? <ChevronDown className="w-4 h-4 text-muted-foreground" /> : <ChevronRight className="w-4 h-4 text-muted-foreground" />}
      </button>

      {expanded && (
        <div className="border-t border-gray-200 dark:border-gray-700 p-4 space-y-4">
          {loading ? (
            <div className="flex justify-center py-4"><Loader2 className="w-5 h-5 animate-spin text-primary" /></div>
          ) : (
            <>
              <div className="flex gap-2 mb-3">
                <button onClick={selectAll} className="text-xs text-primary hover:underline" data-testid="select-all">Tumunu Sec</button>
                <span className="text-xs text-muted-foreground">|</span>
                <button onClick={clearAll} className="text-xs text-red-500 hover:underline" data-testid="clear-all">Tumunu Kaldir</button>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {ALL_MODULES.map((group) => (
                  <div key={group.group} className="space-y-1">
                    <div className="text-xs font-bold text-muted-foreground uppercase tracking-wider pb-1">{group.group}</div>
                    {group.items.map((item) => (
                      <button
                        key={item.key}
                        onClick={() => toggle(item.key)}
                        className="flex items-center gap-2 w-full text-left px-2 py-1.5 rounded-lg hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors"
                        data-testid={`module-toggle-${item.key}`}
                      >
                        {modules.includes(item.key) ? (
                          <CheckSquare className="w-4 h-4 text-primary flex-shrink-0" />
                        ) : (
                          <Square className="w-4 h-4 text-muted-foreground flex-shrink-0" />
                        )}
                        <span className="text-sm">{item.label}</span>
                      </button>
                    ))}
                  </div>
                ))}
              </div>

              <div className="flex justify-end pt-2 border-t border-gray-100 dark:border-gray-700">
                <button
                  onClick={handleSave}
                  disabled={saving}
                  className="inline-flex items-center gap-1.5 px-4 py-2 rounded-lg bg-primary text-primary-foreground hover:bg-primary/90 disabled:opacity-50 transition-colors text-sm font-medium"
                  data-testid={`save-modules-${agency._id || agency.id}`}
                >
                  {saving ? <Loader2 className="w-4 h-4 animate-spin" /> : <Save className="w-4 h-4" />}
                  Kaydet
                </button>
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
}

export default function AdminAgencyModulesPage() {
  const [agencies, setAgencies] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadAgencies = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api.get("/admin/agencies");
      setAgencies(res.data || []);
    } catch { /* silent */ }
    setLoading(false);
  }, []);

  useEffect(() => { loadAgencies(); }, [loadAgencies]);

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-6 h-6 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="agency-modules-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight flex items-center gap-2">
            <CheckSquare className="w-6 h-6 text-primary" />
            Acente Modul Yonetimi
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Her acentenin gorebilecegi sekmeleri buradan yonetin. Bos birakilan acenteler tum modulleri gorur.
          </p>
        </div>
        <button
          onClick={loadAgencies}
          className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg border border-gray-200 dark:border-gray-700 hover:bg-gray-50 dark:hover:bg-gray-800 transition-colors text-sm"
          data-testid="refresh-agencies"
        >
          <RefreshCw className="w-4 h-4" /> Yenile
        </button>
      </div>

      {agencies.length === 0 ? (
        <div className="bg-white dark:bg-gray-800 rounded-xl border p-10 text-center">
          <Building2 className="w-10 h-10 mx-auto text-muted-foreground/40" />
          <p className="mt-3 font-medium">Henuz acente yok</p>
        </div>
      ) : (
        <div className="space-y-3">
          {agencies.map((ag) => (
            <AgencyModuleCard key={ag._id || ag.id} agency={ag} onSaved={loadAgencies} />
          ))}
        </div>
      )}
    </div>
  );
}
