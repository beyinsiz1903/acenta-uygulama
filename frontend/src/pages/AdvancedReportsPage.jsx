import React, { useState, useEffect, useCallback } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { BarChart3, Download, RefreshCcw, Loader2, TrendingUp, Users, Clock } from "lucide-react";

function formatMoney(amount) {
  return new Intl.NumberFormat("tr-TR", { style: "currency", currency: "TRY" }).format(amount || 0);
}

export default function AdvancedReportsPage() {
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [financial, setFinancial] = useState(null);
  const [products, setProducts] = useState([]);
  const [partners, setPartners] = useState([]);
  const [aging, setAging] = useState(null);
  const [loading, setLoading] = useState(true);
  const [activeSection, setActiveSection] = useState("financial");

  const load = useCallback(async () => {
    setLoading(true);
    const params = {};
    if (fromDate) params.from_date = fromDate;
    if (toDate) params.to_date = toDate;

    try {
      const [finRes, prodRes, partRes, agingRes] = await Promise.all([
        api.get("/reports/financial-summary", { params }),
        api.get("/reports/product-performance", { params }),
        api.get("/reports/partner-performance", { params }),
        api.get("/reports/aging"),
      ]);
      setFinancial(finRes.data);
      setProducts(prodRes.data || []);
      setPartners(partRes.data || []);
      setAging(agingRes.data);
    } catch {}
    setLoading(false);
  }, [fromDate, toDate]);

  useEffect(() => { load(); }, [load]);

  const handleExportCSV = () => {
    let csv = "Rapor,Değer\n";
    if (financial) {
      csv += `Toplam Gelir,${financial.total_revenue}\n`;
      csv += `Toplam Ödeme Sayısı,${financial.total_payments}\n`;
      csv += `İade Toplamı,${financial.total_refunds}\n`;
      csv += `Net Gelir,${financial.net_revenue}\n`;
      csv += `Bekleyen Bakiye,${financial.outstanding_balance}\n`;
    }
    csv += "\nÜrün,Rezervasyon,Gelir\n";
    products.forEach((p) => { csv += `${p.product_title},${p.reservation_count},${p.total_revenue}\n`; });
    csv += "\nPartner,Eşleşme,Gelir\n";
    partners.forEach((p) => { csv += `${p.partner_name},${p.match_count},${p.revenue}\n`; });

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `rapor_${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const sections = [
    { key: "financial", label: "Finansal Özet", icon: BarChart3 },
    { key: "products", label: "Ürün Performansı", icon: TrendingUp },
    { key: "partners", label: "Partner Performansı", icon: Users },
    { key: "aging", label: "Yaşlandırma", icon: Clock },
  ];

  return (
    <div className="p-6 max-w-7xl mx-auto space-y-6" data-testid="reports-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold" data-testid="reports-title">Raporlar</h1>
          <p className="text-sm text-muted-foreground">Finansal ve operasyonel raporlar</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={load}><RefreshCcw className="h-4 w-4 mr-1" /> Yenile</Button>
          <Button variant="outline" size="sm" onClick={handleExportCSV} data-testid="export-csv"><Download className="h-4 w-4 mr-1" /> CSV</Button>
        </div>
      </div>

      {/* Date filters */}
      <div className="flex gap-4 items-end">
        <div><label className="text-xs text-muted-foreground">Başlangıç</label><Input type="date" value={fromDate} onChange={(e) => setFromDate(e.target.value)} className="w-40" /></div>
        <div><label className="text-xs text-muted-foreground">Bitiş</label><Input type="date" value={toDate} onChange={(e) => setToDate(e.target.value)} className="w-40" /></div>
        <Button size="sm" onClick={load}>Filtrele</Button>
      </div>

      {/* Section tabs */}
      <div className="flex gap-2 border-b">
        {sections.map((s) => (
          <button key={s.key} onClick={() => setActiveSection(s.key)} className={`flex items-center gap-1.5 px-4 py-2 text-sm font-medium border-b-2 transition-all ${activeSection === s.key ? "border-blue-500 text-blue-600" : "border-transparent text-muted-foreground hover:text-foreground"}`}>
            <s.icon className="h-4 w-4" /> {s.label}
          </button>
        ))}
      </div>

      {loading ? (
        <div className="flex justify-center py-12"><Loader2 className="h-8 w-8 animate-spin text-blue-500" /></div>
      ) : (
        <>
          {activeSection === "financial" && financial && (
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4" data-testid="financial-summary">
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
                <div className="text-sm text-muted-foreground">Toplam Gelir</div>
                <div className="text-xl font-bold text-green-600">{formatMoney(financial.total_revenue)}</div>
              </div>
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
                <div className="text-sm text-muted-foreground">Ödeme Sayısı</div>
                <div className="text-xl font-bold">{financial.total_payments}</div>
              </div>
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
                <div className="text-sm text-muted-foreground">İade Toplamı</div>
                <div className="text-xl font-bold text-rose-600">{formatMoney(financial.total_refunds)}</div>
              </div>
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
                <div className="text-sm text-muted-foreground">Net Gelir</div>
                <div className="text-xl font-bold text-blue-600">{formatMoney(financial.net_revenue)}</div>
              </div>
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-4">
                <div className="text-sm text-muted-foreground">Bekleyen</div>
                <div className="text-xl font-bold text-amber-600">{formatMoney(financial.outstanding_balance)}</div>
              </div>
            </div>
          )}

          {activeSection === "products" && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50"><tr><th className="px-4 py-3 text-left">Ürün</th><th className="px-4 py-3 text-left">Rezervasyon</th><th className="px-4 py-3 text-left">Gelir</th></tr></thead>
                <tbody>
                  {products.length === 0 && <tr><td colSpan={3} className="px-4 py-8 text-center text-muted-foreground">Veri yok</td></tr>}
                  {products.map((p, i) => (
                    <tr key={i} className="border-t hover:bg-muted/20">
                      <td className="px-4 py-3 font-medium">{p.product_title}</td>
                      <td className="px-4 py-3">{p.reservation_count}</td>
                      <td className="px-4 py-3">{formatMoney(p.total_revenue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeSection === "partners" && (
            <div className="bg-white dark:bg-slate-900 rounded-xl border overflow-hidden">
              <table className="w-full text-sm">
                <thead className="bg-muted/50"><tr><th className="px-4 py-3 text-left">Partner</th><th className="px-4 py-3 text-left">Eşleşme</th><th className="px-4 py-3 text-left">Gelir</th></tr></thead>
                <tbody>
                  {partners.length === 0 && <tr><td colSpan={3} className="px-4 py-8 text-center text-muted-foreground">Veri yok</td></tr>}
                  {partners.map((p, i) => (
                    <tr key={i} className="border-t hover:bg-muted/20">
                      <td className="px-4 py-3 font-medium">{p.partner_name}</td>
                      <td className="px-4 py-3">{p.match_count}</td>
                      <td className="px-4 py-3">{formatMoney(p.revenue)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          {activeSection === "aging" && aging && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4" data-testid="aging-report">
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-6">
                <h3 className="font-bold text-lg mb-2">7 Günden Fazla</h3>
                <div className="text-3xl font-bold text-amber-600">{aging.aging?.over_7_days?.count || 0}</div>
                <div className="text-sm text-muted-foreground mt-1">{formatMoney(aging.aging?.over_7_days?.amount || 0)}</div>
              </div>
              <div className="bg-white dark:bg-slate-900 rounded-xl border p-6">
                <h3 className="font-bold text-lg mb-2">30 Günden Fazla</h3>
                <div className="text-3xl font-bold text-rose-600">{aging.aging?.over_30_days?.count || 0}</div>
                <div className="text-sm text-muted-foreground mt-1">{formatMoney(aging.aging?.over_30_days?.amount || 0)}</div>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
}
