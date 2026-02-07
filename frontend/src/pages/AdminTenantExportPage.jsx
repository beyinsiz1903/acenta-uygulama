import React, { useState } from "react";
import { api } from "../lib/api";
import { Button } from "../components/ui/button";
import { Download, FileArchive, Loader2, AlertCircle } from "lucide-react";

export default function AdminTenantExportPage() {
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);

  const handleExport = async () => {
    try {
      setExporting(true);
      setError(null);
      setSuccess(false);

      const res = await api.post("/admin/tenant/export", {}, {
        responseType: "blob",
        timeout: 120000,
      });

      // Create download link
      const blob = new Blob([res.data], { type: "application/zip" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `tenant_export_${new Date().toISOString().slice(0, 10)}.zip`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

      setSuccess(true);
    } catch (e) {
      if (e.response?.status === 429) {
        setError("Rate limit aşıldı. Lütfen birkaç dakika bekleyin.");
      } else {
        setError(e.response?.data?.error?.message || e.message || "Export hatası");
      }
    } finally {
      setExporting(false);
    }
  };

  return (
    <div className="p-6 max-w-2xl" data-testid="tenant-export-page">
      <div className="mb-6">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <FileArchive className="h-6 w-6" />
          Veri Dışa Aktarma
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Tüm tenant verilerinizi ZIP dosyası olarak indirin.
        </p>
      </div>

      <div className="rounded-lg border p-6">
        <h2 className="text-lg font-semibold mb-3">Tam Veri Paketi</h2>
        <p className="text-sm text-muted-foreground mb-4">
          Aşağıdaki koleksiyonlar dahil edilecektir:
        </p>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mb-6">
          {["customers", "deals", "tasks", "reservations", "payments", "products", "notes", "activities"].map((name) => (
            <div key={name} className="rounded-md bg-muted/50 px-3 py-1.5 text-xs font-medium text-center">
              {name}.json
            </div>
          ))}
        </div>

        <div className="flex items-center gap-3">
          <Button
            onClick={handleExport}
            disabled={exporting}
            data-testid="export-btn"
            className="gap-2"
            size="lg"
          >
            {exporting ? (
              <><Loader2 className="h-4 w-4 animate-spin" /> Dışa Aktarılıyor...</>
            ) : (
              <><Download className="h-4 w-4" /> Dışa Aktar (ZIP)</>
            )}
          </Button>

          {success && (
            <span className="text-sm text-green-600 font-medium" data-testid="export-success">
              ✓ İndirme başladı
            </span>
          )}

          {error && (
            <div className="flex items-center gap-2 text-sm text-red-600" data-testid="export-error">
              <AlertCircle className="h-4 w-4" />
              {error}
            </div>
          )}
        </div>
      </div>

      <div className="mt-6 rounded-lg border border-amber-200 bg-amber-50 dark:bg-amber-950/20 dark:border-amber-800 p-4">
        <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-300 mb-1">Not</h3>
        <p className="text-xs text-amber-700 dark:text-amber-400">
          Export işlemi rate-limit ile korunmaktadır (5 istek / 10 dakika).
          Büyük veri setleri için işlem birkaç saniye sürebilir.
        </p>
      </div>
    </div>
  );
}
