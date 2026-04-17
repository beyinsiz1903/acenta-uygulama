import React, { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api, apiErrorMessage } from "../../lib/api";
import {
  Link2, RefreshCw, KeyRound, PowerOff, Loader2, AlertTriangle, CheckCircle2,
} from "lucide-react";

const STATUS_BADGE = {
  active: { label: "Aktif", cls: "bg-green-100 text-green-800" },
  failed: { label: "Hata", cls: "bg-red-100 text-red-800" },
  not_configured: { label: "Yapılandırılmamış", cls: "bg-gray-100 text-gray-700" },
  disabled: { label: "Devre Dışı", cls: "bg-gray-200 text-gray-800" },
};

function StatusBadge({ status }) {
  if (!status) return <span className="text-xs text-gray-400">—</span>;
  const s = STATUS_BADGE[status] || { label: status, cls: "bg-gray-100 text-gray-800" };
  return <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${s.cls}`}>{s.label}</span>;
}

export default function AdminSyroceMarketplacePage() {
  const qc = useQueryClient();
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [confirmAction, setConfirmAction] = useState(null); // {type, label}

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["admin-syroce-status"],
    queryFn: () => api.get("/admin/syroce-agencies").then((r) => r.data),
  });

  const flash = (msg, isError = false) => {
    if (isError) { setError(msg); setSuccess(""); }
    else { setSuccess(msg); setError(""); }
    setTimeout(() => { setError(""); setSuccess(""); }, 6000);
  };

  const syncMut = useMutation({
    mutationFn: () => api.post("/admin/syroce-agencies/sync", {}).then((r) => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-syroce-status"] }); flash("Syroce ile senkronize edildi."); },
    onError: (e) => flash(apiErrorMessage(e) || "Senkronizasyon başarısız.", true),
  });
  const regenMut = useMutation({
    mutationFn: () => api.post("/admin/syroce-agencies/regenerate", {}).then((r) => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-syroce-status"] }); flash("Yeni API anahtarı oluşturuldu."); setConfirmAction(null); },
    onError: (e) => { flash(apiErrorMessage(e) || "Yenileme başarısız.", true); setConfirmAction(null); },
  });
  const disableMut = useMutation({
    mutationFn: () => api.post("/admin/syroce-agencies/disable", {}).then((r) => r.data),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ["admin-syroce-status"] }); flash("Syroce bağlantısı devre dışı bırakıldı."); setConfirmAction(null); },
    onError: (e) => { flash(apiErrorMessage(e) || "İşlem başarısız.", true); setConfirmAction(null); },
  });

  const s = data || {};
  const provisioned = !!s.provisioned;
  const keySet = !!s.key_set;

  const runConfirm = () => {
    if (!confirmAction) return;
    if (confirmAction.type === "regenerate") regenMut.mutate();
    if (confirmAction.type === "disable") disableMut.mutate();
  };

  return (
    <div className="p-6 max-w-5xl mx-auto space-y-4">
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Link2 className="text-blue-600" /> Syroce Marketplace Bağlantısı
        </h1>
        <p className="text-sm text-gray-500">
          Acentanızın Syroce PMS Marketplace'teki kaydını ve API anahtarını yönetin.
          API anahtarınız sunucumuzda şifreli saklanır; hiçbir şekilde gösterilmez.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-700 p-3 rounded flex items-start gap-2">
          <AlertTriangle size={18} className="mt-0.5" /> <span className="text-sm">{error}</span>
        </div>
      )}
      {success && (
        <div className="bg-green-50 border border-green-200 text-green-700 p-3 rounded flex items-start gap-2">
          <CheckCircle2 size={18} className="mt-0.5" /> <span className="text-sm">{success}</span>
        </div>
      )}

      <div className="bg-white border rounded-lg p-6 space-y-4">
        {isLoading ? (
          <div className="flex items-center gap-2 text-gray-500"><Loader2 className="animate-spin" size={16} /> Yükleniyor…</div>
        ) : (
          <>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div><div className="text-gray-500">Durum</div><div className="mt-1"><StatusBadge status={s.syroce_status} /></div></div>
              <div><div className="text-gray-500">Kayıtlı mı?</div><div className="mt-1 font-medium">{provisioned ? "Evet" : "Hayır"}</div></div>
              <div><div className="text-gray-500">API Anahtarı</div><div className="mt-1 font-medium">{keySet ? "Mevcut (şifreli)" : "Yok"}</div></div>
              <div><div className="text-gray-500">Syroce Acenta ID</div><div className="mt-1 font-mono text-xs break-all">{s.syroce_agency_id || "—"}</div></div>
              <div><div className="text-gray-500">Acenta Adı</div><div className="mt-1">{s.name || "—"}</div></div>
              <div><div className="text-gray-500">İletişim</div><div className="mt-1">{s.contact_email || "—"}</div></div>
              <div><div className="text-gray-500">Ülke</div><div className="mt-1">{s.country || "—"}</div></div>
              <div><div className="text-gray-500">Komisyon (%)</div><div className="mt-1">{s.default_commission_pct ?? "—"}</div></div>
              <div className="col-span-2"><div className="text-gray-500">Son Senkronizasyon</div><div className="mt-1 text-xs">{s.syroce_last_synced_at ? new Date(s.syroce_last_synced_at).toLocaleString("tr-TR") : "—"}</div></div>
              {s.syroce_sync_error && (
                <div className="col-span-2">
                  <div className="text-gray-500">Son Hata</div>
                  <div className="mt-1 text-xs text-red-700 bg-red-50 border border-red-200 p-2 rounded">{s.syroce_sync_error}</div>
                </div>
              )}
            </div>

            <div className="border-t pt-4 flex flex-wrap gap-2">
              <button
                onClick={() => syncMut.mutate()}
                disabled={syncMut.isPending}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded text-sm flex items-center gap-2 disabled:opacity-50"
              >
                {syncMut.isPending ? <Loader2 size={16} className="animate-spin" /> : <RefreshCw size={16} />}
                {provisioned && keySet ? "Tekrar Senkronize Et" : "Syroce'da Yeni Kayıt Aç"}
              </button>
              <button
                onClick={() => setConfirmAction({ type: "regenerate", label: "API anahtarını yenilemek istediğinize emin misiniz? Eski anahtar geçersiz olacak." })}
                disabled={!provisioned || !keySet || regenMut.isPending}
                className="bg-amber-500 hover:bg-amber-600 text-white px-4 py-2 rounded text-sm flex items-center gap-2 disabled:opacity-50"
              >
                <KeyRound size={16} /> API Anahtarını Yenile
              </button>
              <button
                onClick={() => setConfirmAction({ type: "disable", label: "Syroce bağlantınızı kapatmak istediğinize emin misiniz? Bu işlemden sonra arama/rezervasyon yapılamaz." })}
                disabled={!provisioned || s.syroce_status === "disabled" || disableMut.isPending}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded text-sm flex items-center gap-2 disabled:opacity-50"
              >
                <PowerOff size={16} /> Bağlantıyı Kapat
              </button>
              <button
                onClick={() => refetch()}
                className="ml-auto px-3 py-2 text-sm border rounded hover:bg-gray-50"
              >
                Yenile
              </button>
            </div>
          </>
        )}
      </div>

      {confirmAction && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-lg p-6 max-w-md w-full">
            <div className="flex items-start gap-3">
              <AlertTriangle className="text-amber-500 mt-1" />
              <div>
                <h3 className="font-bold">Onay Gerekli</h3>
                <p className="text-sm text-gray-600 mt-1">{confirmAction.label}</p>
              </div>
            </div>
            <div className="flex gap-2 mt-6 justify-end">
              <button onClick={() => setConfirmAction(null)} className="px-4 py-2 border rounded hover:bg-gray-50 text-sm">Vazgeç</button>
              <button
                onClick={runConfirm}
                disabled={regenMut.isPending || disableMut.isPending}
                className="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded text-sm disabled:opacity-50 flex items-center gap-2"
              >
                {(regenMut.isPending || disableMut.isPending) && <Loader2 size={14} className="animate-spin" />}
                Onayla
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
