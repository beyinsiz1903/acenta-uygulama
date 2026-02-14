import React, { useState, useEffect } from "react";
import { getTenantsHealth } from "../../lib/gtm";
import { AlertTriangle, Activity, Filter } from "lucide-react";

export default function AdminTenantHealthPage() {
  const [data, setData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [filter, setFilter] = useState("");

  useEffect(() => { loadData(); }, [filter]);

  async function loadData() {
    setLoading(true); setError("");
    try {
      const res = await getTenantsHealth(filter||undefined);
      setData(res.items||[]);
    } catch (e) { setError(e?.message||"Yuklenemedi"); }
    finally { setLoading(false); }
  }

  const filters = [{value:"",label:"Tumu"},{value:"trial_expiring",label:"Deneme Dolacak"},{value:"inactive",label:"Inaktif"},{value:"overdue",label:"Gecikmis Odeme"}];

  return (
    <div className="p-6 max-w-7xl mx-auto" data-testid="tenant-health-page">
      <div className="flex items-center justify-between mb-6">
        <div><h1 className="text-2xl font-bold text-foreground">Tenant Saglik Paneli</h1>
          <p className="text-sm text-muted-foreground mt-1">Tum tenantlarin saglik durumunu izleyin</p></div>
        <div className="flex items-center gap-2"><Filter size={16} className="text-muted-foreground" />
          {filters.map(f=>(<button key={f.value} onClick={()=>setFilter(f.value)}
            className={`px-3 py-1.5 text-xs rounded-full border transition-colors ${filter===f.value?"bg-blue-600 text-white border-blue-600":"bg-white text-muted-foreground border-gray-300 hover:bg-gray-50"}`}
            data-testid={`filter-${f.value||'all'}`}>{f.label}</button>))}
        </div>
      </div>
      {error && <div className="bg-red-50 text-red-700 p-4 rounded-lg mb-4">{error}</div>}
      {loading ? <div className="flex justify-center py-12"><div className="w-8 h-8 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" /></div>
      : data.length===0 ? <div className="text-center py-12 text-muted-foreground">Tenant bulunamadi</div>
      : (
        <div className="bg-white border rounded-xl overflow-hidden">
          <table className="w-full text-sm" data-testid="tenant-health-table">
            <thead className="bg-gray-50 border-b"><tr>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">Tenant</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">Durum</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">Son Giris</th>
              <th className="text-left px-4 py-3 font-medium text-muted-foreground">Son Aktivite</th>
              <th className="text-center px-4 py-3 font-medium text-muted-foreground">Deneme (gun)</th>
              <th className="text-center px-4 py-3 font-medium text-muted-foreground">Gecikmis</th>
              <th className="text-center px-4 py-3 font-medium text-muted-foreground">Kota</th>
            </tr></thead>
            <tbody className="divide-y">
              {data.map((t,i)=>(
                <tr key={t.tenant_id||i} className="hover:bg-gray-50">
                  <td className="px-4 py-3"><div className="font-medium text-foreground">{t.tenant_name||t.tenant_id}</div></td>
                  <td className="px-4 py-3"><span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium ${t.status==='active'?'bg-green-100 text-green-700':'bg-gray-100 text-muted-foreground'}`}><Activity size={12} />{t.status}</span></td>
                  <td className="px-4 py-3 text-muted-foreground">{t.last_login_at?new Date(t.last_login_at).toLocaleDateString('tr-TR'):'-'}</td>
                  <td className="px-4 py-3 text-muted-foreground">{t.last_activity_at?new Date(t.last_activity_at).toLocaleDateString('tr-TR'):'-'}</td>
                  <td className="px-4 py-3 text-center">{t.trial_days_left!=null?<span className={`font-medium ${t.trial_days_left<=3?'text-red-600':t.trial_days_left<=7?'text-amber-600':'text-foreground'}`}>{t.trial_days_left}</span>:'-'}</td>
                  <td className="px-4 py-3 text-center">{t.overdue_payments_count>0?<span className="inline-flex items-center gap-1 text-red-600 font-medium"><AlertTriangle size={14} />{t.overdue_payments_count}</span>:<span className="text-muted-foreground/60">0</span>}</td>
                  <td className="px-4 py-3 text-center">{t.quota_ratio!=null?<span className={`font-medium ${t.quota_ratio>0.8?'text-red-600':'text-foreground'}`}>{Math.round(t.quota_ratio*100)}%</span>:'-'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
