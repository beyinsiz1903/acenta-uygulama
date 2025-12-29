import React, { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { toast } from "sonner";
import { safeCopyText } from "../utils/copyText";

const STATUS_LABELS = {
  new: "Yeni",
  approved: "Onaylandı",
  rejected: "Reddedildi",
  cancelled: "İptal",
};

function StatusBadge({ status }) {
  const label = STATUS_LABELS[status] || status;
  let classes = "px-2 py-1 rounded-full border text-xs ";
  if (status === "new") classes += "bg-amber-50 border-amber-300 text-amber-700";
  else if (status === "approved") classes += "bg-emerald-50 border-emerald-300 text-emerald-700";
  else if (status === "rejected") classes += "bg-rose-50 border-rose-300 text-rose-700";
  else classes += "bg-gray-50 border-gray-300 text-gray-700";
  return <span className={classes}>{label}</span>;
}

export default function AgencyTourBookingDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(true);
  const [savingStatus, setSavingStatus] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [addingNote, setAddingNote] = useState(false);

  const load = async () => {
    if (!id) return;
    setLoading(true);
    try {
      const resp = await api.get(`/agency/tour-bookings/${id}`);
      setItem(resp.data || null);
    } catch (e) {
      console.error(e);
      toast.error(apiErrorMessage(e) || "Kayıt yüklenemedi");
      setItem(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  const changeStatus = async (nextStatus) => {
    if (!item) return;
    const label = STATUS_LABELS[nextStatus] || nextStatus;
    if (!window.confirm(`Bu talebi '${label}' durumuna almak istediğinize emin misiniz?`)) {
      return;
    }
    setSavingStatus(true);
    try {
      await api.post(`/agency/tour-bookings/${item.id}/set-status`, { status: nextStatus });
      toast.success("Durum güncellendi.");
      await load();
    } catch (e) {
      toast.error(apiErrorMessage(e) || "Durum güncellenemedi");
    } finally {
      setSavingStatus(false);
    }
  };

  const addNote = async (e) => {
    e.preventDefault();
    if (!item) return;
    const text = noteText.trim();
    if (text.length < 2) {
      toast.error("Lütfen en az 2 karakterlik bir not girin.");
      return;
    }
    setAddingNote(true);
    try {
      await api.post(`/agency/tour-bookings/${item.id}/add-note`, { text });
      setNoteText("");
      toast.success("Not eklendi.");
      await load();
    } catch (e) {
      toast.error(apiErrorMessage(e) || "Not eklenemedi");
    } finally {
      setAddingNote(false);
    }
  };

  const phoneHref = item?.guest?.phone ? `tel:${(item.guest.phone || "").replace(/[^0-9+]/g, "")}` : null;

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto p-4 text-sm text-gray-600">Kayıt yükleniyor…</div>
    );
  }

  if (!item) {
    return (
      <div className="max-w-4xl mx-auto p-4 space-y-3 text-sm text-gray-600">
        <div>Kayıt bulunamadı.</div>
        <Button variant="outline" size="sm" onClick={() => navigate(-1)}>
          Geri Dön
        </Button>
      </div>
    );
  }

  const notes = Array.isArray(item.internal_notes) ? item.internal_notes : [];
  const payment = item.payment || null;
  const offline = payment && payment.mode === "offline" ? payment : null;

  const copyWithToast = async (label, value) => {
    if (!value) {
      toast.error(`${label} kopyalanamadı.`);
      return;
    }
    const ok = await safeCopyText(value);
    if (ok) {
      toast.success(`${label} panoya kopyalandı.`);
    } else {
      toast.error(`${label} kopyalanamadı.`);
    }
  };

  const voucher = item?.voucher || null;

  const renderOfflinePaymentCard = () => {
    if (!item) return null;

    // Payment snapshot varsa readonly kart
    if (offline) {
      const snap = offline.iban_snapshot || {};
      const ref = offline.reference_code;
      const currency = offline.currency || snap.currency || "TRY";
      const due = offline.due_at;
      const status = offline.status || "unpaid";
      const isPaid = status === "paid";
      const paidAt = offline.paid_at;
      const paidBy = offline.paid_by || {};
      const paidByName = paidBy.name || paidBy.role || null;

      const filledNote = (() => {
        const tpl = snap.note_template || "Rezervasyon: {reference_code}";
        return tpl.replace("{reference_code}", ref || "");
      })();

      return (
        <div
          data-testid="offline-payment-card"
          className="rounded-xl border bg-white p-4 space-y-3 text-sm"
        >
          <div className="flex items-center justify-between gap-2">
            <div className="font-medium">Offline Ödeme (IBAN)</div>
            <div className="flex flex-col items-end text-[11px] text-muted-foreground gap-0.5">
              <span className={isPaid ? "text-emerald-700" : ""}>
                {isPaid ? "Ödendi" : "Ödeme bekleniyor"}
              </span>
              {isPaid && (
                <span>
                  {paidAt && <span>{paidAt}</span>}
                  {paidByName && <span className="ml-1">({paidByName})</span>}
                </span>
              )}
            </div>
          </div>

          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-xs text-gray-700">
            <div className="space-y-1">
              <div className="font-medium">Hesap Sahibi</div>
              <div className="rounded border bg-muted/40 px-2 py-1 break-all">
                {snap.account_name || "-"}
              </div>
            </div>
            <div className="space-y-1">
              <div className="font-medium">Banka Adı</div>
              <div className="rounded border bg-muted/40 px-2 py-1 break-all">
                {snap.bank_name || "-"}
              </div>
            </div>
            <div className="space-y-1">
              <div className="font-medium">IBAN</div>
              <div className="rounded border bg-muted/40 px-2 py-1 break-all">
                {snap.iban || "-"}
              </div>
            </div>
            <div className="space-y-1">
              <div className="font-medium">Para Birimi / SWIFT</div>
              <div className="rounded border bg-muted/40 px-2 py-1 break-all">
                {currency} {snap.swift ? ` / ${snap.swift}` : ""}
              </div>
            </div>
            <div className="space-y-1">
              <div className="font-medium">Son Ödeme Tarihi</div>
              <div className="rounded border bg-muted/40 px-2 py-1 break-all">
                {due || "-"}
              </div>
            </div>
            <div className="space-y-1">
              <div className="font-medium">Referans Kodu</div>
              <div className="rounded border bg-muted/40 px-2 py-1 break-all">
                {ref || "-"}
              </div>
            </div>
          </div>

          <div className="space-y-1 text-xs text-gray-700">
            <div className="font-medium">Ödeme Açıklaması Önerisi</div>
            <div className="rounded border bg-muted/40 px-2 py-1 break-all">
              {filledNote}
            </div>
          </div>

          <div className="flex flex-wrap gap-2 pt-2 text-xs">
            <Button
              type="button"
              size="sm"
              variant="outline"
              data-testid="btn-copy-iban"
              onClick={() => copyWithToast("IBAN", snap.iban)}
            >
              IBAN Kopyala
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              data-testid="btn-copy-reference"
              onClick={() => copyWithToast("Referans kodu", ref)}
            >
              Referans Kodunu Kopyala
            </Button>
            <Button
              type="button"
              size="sm"
              variant="outline"
              data-testid="btn-copy-payment-note"
              onClick={() => copyWithToast("Ödeme açıklaması", filledNote)}
            >
              Ödeme Açıklamasını Kopyala
            </Button>
          </div>
        </div>
      );
    }

    // Snapshot yoksa hazırlama butonu
    return (
      <div className="rounded-xl border bg-white p-4 space-y-2 text-sm">
        <div className="flex items-center justify-between gap-2">
          <div className="font-medium">Offline Ödeme</div>
          <div className="text-[11px] text-muted-foreground">
            Bu talep için IBAN ile ödeme talimatı oluşturun.
          </div>
        </div>
        <Button
          type="button"
          size="sm"
          variant="outline"
          data-testid="btn-prepare-offline-payment"
          onClick={async () => {
            try {
              const resp = await api.post(`/agency/tour-bookings/${item.id}/prepare-offline-payment`);
              setItem(resp.data || item);
              toast.success("Offline ödeme talimatı hazırlandı.");
            } catch (err) {
              const detail = err?.response?.data?.detail;
              const code = typeof detail === "object" ? detail.code : null;
              if (code === "PAYMENT_SETTINGS_MISSING" || code === "OFFLINE_PAYMENT_DISABLED") {
                toast.error(
                  "Offline ödeme için önce Ayarlar > Ödeme Ayarları bölümünden hesap bilgilerinizi tanımlayın.",
                );
              } else if (code === "INVALID_STATUS_FOR_PAYMENT") {
                toast.error("Bu rezervasyon durumunda ödeme hazırlanamaz.");
              } else {
                toast.error(apiErrorMessage(err));
              }
            }
          }}
        >
          Offline Ödemeyi Hazırla
        </Button>
      </div>
    );
  };

  return (
    <div className="max-w-4xl mx-auto p-4 space-y-4">
      <div className="flex items-center justify-between gap-3">
        <div>
          <div className="text-xs text-gray-500 mb-1">Tur Rezervasyon Talebi</div>
          <h1 className="text-xl font-semibold truncate">{item.tour_title || "Tur"}</h1>
        </div>
        <div className="flex flex-col items-end gap-2 text-xs">
          <StatusBadge status={item.status} />
          <Button variant="outline" size="sm" onClick={() => navigate(-1)}>
            Geri Dön
          </Button>
        </div>
      </div>

      {/* Guest card */}
      <div className="rounded-xl border bg-white p-4 flex flex-col gap-2 text-sm">
        <div className="font-medium">Misafir Bilgileri</div>
        <div className="text-sm">{item.guest?.full_name || "-"}</div>
        <div className="text-xs text-gray-700 flex items-center gap-2">
          <span>{item.guest?.phone || "-"}</span>
          {phoneHref && (
            <a
              href={phoneHref}
              className="inline-flex items-center rounded-full border px-2 py-0.5 text-[11px] text-blue-700 border-blue-200 hover:bg-blue-50"
            >
              Müşteriyi Ara
            </a>
          )}
        </div>
        {item.guest?.email && (
          <div className="text-xs text-gray-700">{item.guest.email}</div>
        )}
      </div>

      {/* Booking details */}
      <div className="rounded-xl border bg-white p-4 grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
        <div>
          <div className="font-medium mb-1">Tur & Tarih</div>
          <div className="text-xs text-gray-700 truncate">Tur ID: {item.tour_id}</div>
          <div className="text-xs text-gray-700 mt-1">Tarih: {item.desired_date || "-"}</div>
          <div className="text-xs text-gray-700 mt-1">Oluşturma: {item.created_at || "-"}</div>
        </div>
        <div>
          <div className="font-medium mb-1">Detaylar</div>
          <div className="text-xs text-gray-700">Kişi sayısı: {item.pax || 1}</div>
          {item.note && (
            <div className="text-xs text-gray-700 mt-1 whitespace-pre-wrap">Misafir notu: {item.note}</div>
          )}
        </div>
      </div>

      {/* Status actions */}
      <div className="rounded-xl border bg-white p-4 flex flex-wrap items-center gap-2 text-xs">
        <div className="font-medium mr-2">Durum Aksiyonları</div>
        <Button
          size="sm"
          variant="outline"
          disabled={savingStatus || item.status === "approved"}
          onClick={() => changeStatus("approved")}
        >
          Onayla
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={savingStatus || item.status === "rejected"}
          onClick={() => changeStatus("rejected")}
        >
          Reddet
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={savingStatus || item.status === "cancelled"}
          onClick={() => changeStatus("cancelled")}
        >
          İptal Et
        </Button>
        <Button
          size="sm"
          variant="outline"
          disabled={savingStatus || item.status === "new"}
          onClick={() => changeStatus("new")}
        >
          Yeni Olarak İşaretle
        </Button>
      </div>

      {renderOfflinePaymentCard()}

      {voucher && voucher.voucher_id && voucher.pdf_url && (
        <div className="rounded-xl border bg-white p-4 flex items-center justify-between gap-2 text-sm">
          <div className="space-y-0.5">
            <div className="font-medium">Voucher PDF</div>
            <div className="text-[11px] text-muted-foreground break-all">
              {voucher.pdf_url}
            </div>
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              type="button"
              size="sm"
              variant="outline"
              data-testid="btn-open-tour-voucher-pdf"
              onClick={async () => {
                try {
                  const resp = await api.post(
                    `/agency/tour-bookings/${item.id}/voucher-signed-url`,
                  );
                  const signedUrl = resp?.data?.url;
                  if (!signedUrl) {
                    toast.error("Voucher PDF linki alınamadı.");
                    return;
                  }
                  const base = process.env.REACT_APP_BACKEND_URL || window.origin || "";
                  const finalUrl = signedUrl.startsWith("http")
                    ? signedUrl
                    : `${base}${signedUrl}`;
                  window.open(finalUrl, "_blank", "noopener,noreferrer");
                } catch (err) {
                  const detail = err?.response?.data?.detail;
                  const code = typeof detail === "object" ? detail.code : null;
                  if (code === "VOUCHER_NOT_READY") {
                    toast.error("Bu talep için önce offline ödemeyi hazırlayın.");
                  } else if (code === "VOUCHER_DISABLED") {
                    toast.error("Bu voucher devre dışı bırakılmış.");
                  } else {
                    toast.error(apiErrorMessage(err) || "Voucher PDF açılamadı.");
                  }
                }
              }}
            >
              Voucher PDF&apos;yi Aç
            </Button>
          </div>
        </div>
      )}

      {/* Internal notes */}
      <div className="rounded-xl border bg-white p-4 space-y-3 text-sm">
        <div className="font-medium">İç Notlar</div>

        {notes.length === 0 ? (
          <div className="text-xs text-gray-500">Henüz iç not yok.</div>
        ) : (
          <div className="space-y-2">
            {notes.map((n, idx) => (
              <div key={idx} className="rounded-lg border bg-gray-50 px-3 py-2 text-xs text-gray-800">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-medium">
                    {n.actor?.name || n.actor?.role || "Kullanıcı"}
                  </span>
                  <span className="text-[11px] text-gray-500">{n.created_at}</span>
                </div>
                <div className="whitespace-pre-wrap">{n.text}</div>
              </div>
            ))}
          </div>
        )}

        <form className="mt-3 space-y-2" onSubmit={addNote}>
          <textarea
            rows={3}
            value={noteText}
            onChange={(e) => setNoteText(e.target.value)}
            placeholder="Sadece acenta ekibinizin göreceği kısa bir iç not ekleyin..."
            className="w-full rounded-md border px-2 py-1.5 text-xs sm:text-sm focus:outline-none focus:ring-2 focus:ring-primary/60 focus:border-primary"
          />
          <div className="flex justify-end">
            <Button type="submit" size="sm" disabled={addingNote}>
              {addingNote ? "Kaydediliyor…" : "Not Ekle"}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
