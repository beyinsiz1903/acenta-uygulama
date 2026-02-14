import React, { useEffect, useState, useCallback } from "react";
import { api } from "../../lib/api";
import { Button } from "../../components/ui/button";
import { Badge } from "../../components/ui/badge";
import { ShieldCheck, RefreshCw, AlertTriangle, CheckCircle } from "lucide-react";

export default function AdminSystemIntegrityPage() {
  const [report, setReport] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setLoading(true);
      const res = await api.get("/admin/system/integrity-report");
      setReport(res.data);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const OrphansSection = ({ title, items }) => (
    <div className="border rounded-lg p-4">
      <h3 className="font-medium text-foreground mb-2 flex items-center gap-2">
        {items && items.length > 0 ? (
          <AlertTriangle className="h-4 w-4 text-amber-500" />
        ) : (
          <CheckCircle className="h-4 w-4 text-green-500" />
        )}
        {title}
        <Badge variant="outline" className="ml-auto">{items ? items.length : 0}</Badge>
      </h3>
      {items && items.length > 0 ? (
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {items.map((item, i) => (
            <div key={i} className="text-xs bg-amber-50 text-amber-800 p-2 rounded font-mono">
              {JSON.stringify(item)}
            </div>
          ))}
        </div>
      ) : (
        <p className="text-sm text-muted-foreground/60">Sorun bulunamadı</p>
      )}
    </div>
  );

  return (
    <div className="space-y-6" data-testid="system-integrity-page">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <ShieldCheck className="h-6 w-6 text-emerald-600" />
          <h1 className="text-2xl font-bold text-foreground">Veri Bütünlüğü Raporu</h1>
        </div>
        <Button variant="outline" size="sm" onClick={load} disabled={loading}>
          <RefreshCw className={`h-4 w-4 mr-1 ${loading ? "animate-spin" : ""}`} />
          Yenile
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="h-6 w-6 animate-spin text-muted-foreground/60" />
        </div>
      ) : !report ? (
        <div className="text-center py-12 text-muted-foreground" data-testid="empty-state">
          <p>Rapor yüklenemedi</p>
        </div>
      ) : (
        <div className="space-y-6" data-testid="integrity-report">
          {/* Summary Cards */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-muted-foreground">Audit Zinciri</p>
              <p className="text-2xl font-bold">
                {report.audit_chains?.broken_chains === 0 ? (
                  <span className="text-green-600">Sağlam</span>
                ) : (
                  <span className="text-red-600">{report.audit_chains?.broken_chains} Kırık</span>
                )}
              </p>
              <p className="text-xs text-muted-foreground/60">{report.audit_chains?.tenants_checked || 0} tenant kontrol edildi</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-muted-foreground">Muhasebe Defteri</p>
              <p className="text-2xl font-bold">
                {report.ledger?.mismatches === 0 ? (
                  <span className="text-green-600">Tutarlı</span>
                ) : (
                  <span className="text-red-600">{report.ledger?.mismatches} Uyumsuz</span>
                )}
              </p>
              <p className="text-xs text-muted-foreground/60">{report.ledger?.checked_accounts || 0} hesap kontrol edildi</p>
            </div>
            <div className="bg-white border rounded-lg p-4">
              <p className="text-sm text-muted-foreground">Yetim Kayıtlar</p>
              <p className="text-2xl font-bold">
                {(report.orphans?.total_orphans || 0) === 0 ? (
                  <span className="text-green-600">Temiz</span>
                ) : (
                  <span className="text-amber-600">{report.orphans?.total_orphans}</span>
                )}
              </p>
            </div>
          </div>

          {/* Orphan Details */}
          <div className="space-y-4">
            <h2 className="text-lg font-semibold text-foreground">Yetim Kayıt Detayları</h2>
            <OrphansSection title="Ödemesiz Faturalar" items={report.orphans?.orphans?.invoices_without_payments} />
            <OrphansSection title="Rezervasyonsuz Biletler" items={report.orphans?.orphans?.tickets_without_reservation} />
            <OrphansSection title="Ürünsüz Rezervasyonlar" items={report.orphans?.orphans?.reservations_without_product} />
          </div>
        </div>
      )}
    </div>
  );
}
