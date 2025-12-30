import React, { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, apiErrorMessage, getUser } from "../lib/api";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { Textarea } from "../components/ui/textarea";
import { Card } from "../components/ui/card";
import { toast } from "react-hot-toast";

function isAdmin() {
  const user = getUser();
  return user?.roles?.includes("agency_admin");
}

export default function AgencyCatalogBookingDetailPage() {
  const { id } = useParams();
  const [item, setItem] = useState(null);
  const [loading, setLoading] = useState(false);
  const [noteText, setNoteText] = useState("");
  const [offerUrl, setOfferUrl] = useState("");
  const admin = isAdmin();

  async function load() {
    setLoading(true);
    try {
      const resp = await api.get(`/agency/catalog/bookings/${id}`);
      setItem(resp.data);
      const offer = resp.data.offer;
      if (offer && offer.public_url) {
        setOfferUrl(offer.public_url);
      }
    } catch (err) {
      toast.error(apiErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id]);

  async function addNote(e) {
    e.preventDefault();
    const text = noteText.trim();
    if (text.length < 2) {
      toast.error("Lütfen en az 2 karakterlik bir not girin.");
      return;
    }
    try {
      await api.post(`/agency/catalog/bookings/${id}/internal-notes`, { text });
      setNoteText("");
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  async function changeStatus(action) {
    try {
      await api.post(`/agency/catalog/bookings/${id}/${action}`);
      await load();
    } catch (err) {
      toast.error(apiErrorMessage(err));
    }
  }

  if (!item && loading) {
    return <div className="p-4 text-sm text-muted-foreground">Yükleniyor...</div>;
  }

  if (!item) {
    return <div className="p-4 text-sm text-muted-foreground">Kayıt bulunamadı.</div>;
  }

  const pricing = item.pricing || {};

  return (
    <div className="space-y-4 p-4">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold" data-testid="booking-detail-title">
            Katalog Rezervasyon Detayı
          </h1>
          <p className="text-sm text-muted-foreground">
            {item.guest?.full_name} • {item.product_type} • {item.dates?.start}
          </p>
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <span className="text-xs px-2 py-1 rounded-full border bg-muted">
            {item.status}
          </span>
          {admin && (
            <>
              <Button
                type="button"
                size="sm"
                variant="outline"
                data-testid="btn-catalog-approve"
                onClick={() => changeStatus("approve")}
              >
                Onayla
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                data-testid="btn-catalog-reject"
                onClick={() => changeStatus("reject")}
              >
                Reddet
              </Button>
              <Button
                type="button"
                size="sm"
                variant="outline"
                data-testid="btn-catalog-cancel"
                onClick={() => changeStatus("cancel")}
              >
                İptal Et
              </Button>
            </>
          )}
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <Card className="p-3 space-y-1 text-sm">
          <div className="font-medium">Misafir</div>
          <div>{item.guest?.full_name}</div>
          <div className="text-xs text-muted-foreground">{item.guest?.phone}</div>
          <div className="text-xs text-muted-foreground">{item.guest?.email}</div>
        </Card>
        <Card className="p-3 space-y-1 text-sm">
          <div className="font-medium">Rezervasyon</div>
          <div className="text-xs text-muted-foreground">
            Tarihler: {item.dates?.start} {item.dates?.end ? `- ${item.dates.end}` : ""}
          </div>
          <div className="text-xs text-muted-foreground">Kişi sayısı: {item.pax}</div>
          <div className="text-xs text-muted-foreground">
            Fiyatlandırma: {pricing.subtotal} {pricing.currency} + komisyon %
            {Math.round((pricing.commission_rate || 0) * 100)} → toplam {pricing.total} {pricing.currency}
          </div>
        </Card>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <Card className="p-3 space-y-2 text-sm">
          <div className="font-medium mb-1">İç Notlar</div>
          {item.internal_notes && item.internal_notes.length > 0 ? (
            <div className="space-y-2 max-h-64 overflow-auto">
              {item.internal_notes.map((n, idx) => (
                <div key={idx} className="border rounded-md p-2 text-xs space-y-1">
                  <div className="font-medium text-[11px]">{n.actor?.name}</div>
                  <div className="text-[10px] text-muted-foreground">{n.created_at}</div>
                  <div className="whitespace-pre-wrap">{n.text}</div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-xs text-muted-foreground">
              Henüz iç not yok.
            </div>
          )}
        </Card>
        <Card className="p-3 space-y-2 text-sm">
          <div className="font-medium">Yeni Not Ekle</div>
          <form className="space-y-2" onSubmit={addNote}>
            <Textarea
              rows={3}
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              data-testid="internal-note-input"
            />
            <Button
              type="submit"
              size="sm"
              data-testid="btn-add-internal-note"
            >
              Not Ekle
            </Button>
          </form>
        </Card>
      </div>
    </div>
  );
}
