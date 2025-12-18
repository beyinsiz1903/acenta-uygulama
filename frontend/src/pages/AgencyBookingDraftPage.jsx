import React, { useEffect, useState } from "react";
import { useParams, useNavigate, useLocation } from "react-router-dom";
import { CheckCircle, Hotel, Calendar, Users, User, Loader2, AlertCircle, XCircle } from "lucide-react";
import { api, apiErrorMessage } from "../lib/api";
import { Button } from "../components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { formatMoney } from "../lib/format";
import { toast } from "sonner";

export default function AgencyBookingDraftPage() {
  const { draftId } = useParams();
  const navigate = useNavigate();
  const location = useLocation();

  const [draft, setDraft] = useState(location.state?.draft || null);
  const [loading, setLoading] = useState(!draft);
  const [error, setError] = useState("");
  const [confirmLoading, setConfirmLoading] = useState(false);
  const [cancelLoading, setCancelLoading] = useState(false);

  useEffect(() => {
    if (!draft) {
      loadDraft();
    }
  }, [draftId]);

  async function loadDraft() {
    setLoading(true);
    setError("");
    try {
      const resp = await api.get(`/agency/bookings/draft/${draftId}`);
      console.log("[BookingDraft] Loaded:", resp.data);
      setDraft(resp.data);
    } catch (err) {
      console.error("[BookingDraft] Load error:", err);
      const errorDetail = err?.response?.data?.detail;
      
      // FAZ-3.2: Handle expired draft
      if (errorDetail === "DRAFT_EXPIRED") {
        toast.error("Taslak süresi doldu. Lütfen yeniden arama yapın.");
        setTimeout(() => {
          navigate("/app/agency/hotels");
        }, 2000);
        return;
      }
      
      setError(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  async function handleConfirm() {
    setConfirmLoading(true);
    try {
      const resp = await api.post("/agency/bookings/confirm", {
        draft_id: draftId,
      });
      console.log("[BookingDraft] Confirmed:", resp.data);
      toast.success("Rezervasyon onaylandı");
      
      // Navigate to confirmed page
      navigate(`/app/agency/booking/confirmed/${resp.data.id}`, {
        state: { booking: resp.data },
      });
    } catch (err) {
      console.error("[BookingDraft] Confirm error:", err);
      const errorDetail = err?.response?.data?.detail;
      
      // FAZ-3.2: Handle specific errors
      if (errorDetail === "DRAFT_EXPIRED") {
        toast.error("Taslak süresi doldu. Lütfen yeniden arama yapın.");
        setTimeout(() => {
          navigate("/app/agency/hotels");
        }, 2000);
        return;
      }
      
      if (errorDetail?.code === "PRICE_CHANGED") {
        toast.error(`Fiyat değişti: ${errorDetail.old_total} → ${errorDetail.new_total} ${errorDetail.currency}`);
        return;
      }
      
      toast.error(apiErrorMessage(err));
    } finally {
      setConfirmLoading(false);
    }
  }

  async function handleCancel() {
    if (!window.confirm("Rezervasyon taslağını iptal etmek istediğinize emin misiniz?")) {
      return;
    }

    setCancelLoading(true);
    try {
      await api.delete(`/agency/bookings/draft/${draftId}`);
      console.log("[BookingDraft] Cancelled");
      toast.success("Taslak iptal edildi");
      navigate("/app/agency/hotels");
    } catch (err) {
      console.error("[BookingDraft] Cancel error:", err);
      toast.error(apiErrorMessage(err));
    } finally {
      setCancelLoading(false);
    }
  }

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl border bg-card shadow-sm p-12 flex flex-col items-center justify-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Rezervasyon taslağı yükleniyor...</p>
        </div>
      </div>
    );
  }

  if (error || !draft) {
    return (
      <div className="space-y-6">
        <div className="rounded-2xl border border-destructive/50 bg-destructive/5 p-8 flex flex-col items-center justify-center gap-4">
          <AlertCircle className="h-10 w-10 text-destructive" />
          <div className="text-center">
            <p className="font-semibold text-foreground">Taslak bulunamadı</p>
            <p className="text-sm text-muted-foreground mt-1">{error || "Rezervasyon taslağı bulunamadı"}</p>
          </div>
          <Button onClick={() => navigate("/app/agency/hotels")}>
            Otellerime Dön
          </Button>
        </div>
      </div>
    );
  }

  const { hotel_name, guest, rate_snapshot, status, stay, occupancy } = draft;

  return (
    <div className="space-y-6">
      {/* Success Header */}
      <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-6 flex items-center gap-4">
        <div className="h-12 w-12 rounded-full bg-emerald-500/10 flex items-center justify-center">
          <CheckCircle className="h-6 w-6 text-emerald-600" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-foreground">Rezervasyon Taslağı Oluşturuldu</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Taslak ID: <span className="font-mono">{draft.id}</span>
          </p>
        </div>
      </div>

      {/* Stay & Occupancy Info */}
      {stay && occupancy && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Calendar className="h-5 w-5" />
              Konaklama Bilgileri
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="flex items-center gap-2 text-sm">
              <Calendar className="h-4 w-4 text-muted-foreground" />
              <span>
                {stay.check_in} - {stay.check_out}
                <span className="font-semibold ml-2">({stay.nights} gece)</span>
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <Users className="h-4 w-4 text-muted-foreground" />
              <span>
                {occupancy.adults} yetişkin
                {occupancy.children > 0 && `, ${occupancy.children} çocuk`}
              </span>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Draft Details */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Hotel className="h-5 w-5" />
            Rezervasyon Detayları
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Otel</p>
              <p className="font-medium">{hotel_name}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Durum</p>
              <Badge className="bg-yellow-500/10 text-yellow-700 dark:text-yellow-400 border-yellow-500/20">
                {status === "draft" ? "Taslak" : status}
              </Badge>
            </div>
            <div>
              <p className="text-muted-foreground">Oda Tipi</p>
              <p className="font-medium">{rate_snapshot.room_type_name}</p>
            </div>
            <div>
              <p className="text-muted-foreground">Fiyat Planı</p>
              <p className="font-medium">{rate_snapshot.rate_plan_name}</p>
            </div>
          </div>

          <div className="border-t pt-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm font-medium">Toplam Tutar</p>
                <p className="text-xs text-muted-foreground mt-1">
                  {rate_snapshot.board} • {rate_snapshot.cancellation === "NON_REFUNDABLE" ? "İade edilemez" : "Ücretsiz iptal"}
                </p>
                <Badge variant="outline" className="text-xs mt-2">
                  Fiyat Snapshot
                </Badge>
              </div>
              <div className="text-right">
                <p className="text-3xl font-bold text-primary">
                  {formatMoney(rate_snapshot.price.total, rate_snapshot.price.currency)}
                </p>
                <p className="text-xs text-muted-foreground">
                  Gecelik: {formatMoney(rate_snapshot.price.per_night, rate_snapshot.price.currency)}
                </p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Guest Info */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Misafir Bilgileri
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3 text-sm">
            <div>
              <p className="text-muted-foreground">Ad Soyad</p>
              <p className="font-medium">{guest.full_name}</p>
            </div>
            {guest.email && (
              <div>
                <p className="text-muted-foreground">Email</p>
                <p className="font-medium">{guest.email}</p>
              </div>
            )}
            {guest.phone && (
              <div>
                <p className="text-muted-foreground">Telefon</p>
                <p className="font-medium">{guest.phone}</p>
              </div>
            )}
            {draft.special_requests && (
              <div>
                <p className="text-muted-foreground">Özel İstekler</p>
                <p className="font-medium">{draft.special_requests}</p>
              </div>
            )}
          </div>
        </CardContent>
      </Card>

      {/* Action Buttons */}
      <Card>
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-3">
            <Button
              onClick={handleCancel}
              variant="outline"
              disabled={confirmLoading || cancelLoading || status !== "draft"}
              className="gap-2 flex-1"
            >
              {cancelLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              <XCircle className="h-4 w-4" />
              Taslağı İptal Et
            </Button>
            <Button
              onClick={handleConfirm}
              disabled={confirmLoading || cancelLoading || status !== "draft"}
              className="gap-2 flex-1"
            >
              {confirmLoading && <Loader2 className="h-4 w-4 animate-spin" />}
              <CheckCircle className="h-4 w-4" />
              {confirmLoading ? "Onaylanıyor..." : "Rezervasyonu Onayla"}
            </Button>
          </div>

          {status !== "draft" && (
            <p className="text-xs text-muted-foreground text-center mt-3">
              Bu taslak zaten {status === "confirmed" ? "onaylanmış" : "iptal edilmiş"}
            </p>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
