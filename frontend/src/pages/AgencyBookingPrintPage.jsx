import React, { useEffect, useMemo, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";

import { Button } from "../components/ui/button";
import { api, apiErrorMessage } from "../lib/api";
import { useToast } from "../hooks/use-toast";

function buildShareText(booking) {
  const stay = booking?.stay || {};
  const guest = booking?.guest || {};
  const customer = booking?.customer || {};
  const snap = booking?.catalog_snapshot || {};
  const commission = snap?.commission?.value;
  const markup = snap?.pricing_policy?.markup_percent;

  const lines = [];
  lines.push(`REZERVASYON TALEBİ`);
  lines.push(
    `Kaynak: ${
      booking?.source === "public_booking"
        ? "Public Booking"
        : booking?.source || "-"
    }`,
  );
  lines.push(`Durum: ${booking?.status || "-"}`);
  lines.push("");
  lines.push(`Otel: ${booking?.hotel_name || "-"}`);
  lines.push(`Tarih: ${stay?.check_in || "-"} → ${stay?.check_out || "-"}`);
  lines.push(
    `Pax: ${booking?.adults ?? "-"} yetişkin / ${booking?.children ?? 0} çocuk`,
  );
  lines.push("");

  if (booking?.source === "public_booking") {
    lines.push(`Müşteri: ${customer?.name || "-"}`);
    lines.push(`Telefon: ${customer?.phone || "-"}`);
    if (customer?.email) lines.push(`E-posta: ${customer.email}`);
    lines.push("");
    lines.push(`Katalog Koşulları`);
    lines.push(`- Min gece: ${snap?.min_nights ?? "-"}`);
    lines.push(
      `- Komisyon: ${
        commission != null && commission !== "" ? `%${commission}` : "-"
      }`,
    );
    lines.push(
      `- Markup: ${
        markup != null && markup !== "" ? `%${markup}` : "-"
      }`,
    );
    lines.push("");
  } else {
    lines.push(`Misafir: ${guest?.full_name || "-"}`);
    if (guest?.email) lines.push(`E-posta: ${guest.email}`);
    lines.push("");
  }

  if (booking?.note) {
    lines.push(`Not: ${booking.note}`);
    lines.push("");
  }

  lines.push(`— Syroce Acenta`);
  return lines.join("\n");
}

export default function AgencyBookingPrintPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [loading, setLoading] = useState(true);
  const [booking, setBooking] = useState(null);

  useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        setLoading(true);

        const resp = await api.get("/agency/bookings", { params: { limit: 500 } });
        const items = Array.isArray(resp.data) ? resp.data : resp.data?.items || [];
        const found = items.find((b) => String(b.id || b._id) === String(id));

        if (!mounted) return;
        setBooking(found || null);
      } catch (e) {
        if (!mounted) return;
        toast({
          title: "Yüklenemedi",
          description: apiErrorMessage(e),
          variant: "destructive",
        });
        setBooking(null);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, [id, toast]);

  const shareText = useMemo(
    () => (booking ? buildShareText(booking) : ""),
    [booking],
  );

  useEffect(() => {
    if (!loading && booking) {
      setTimeout(() => window.print(), 50);
    }
  }, [loading, booking]);

  if (loading) {
    return <div className="p-6 text-sm text-muted-foreground">Yükleniyor…</div>;
  }

  if (!booking) {
    return (
      <div className="p-6 space-y-3">
        <div className="text-sm">Kayıt bulunamadı.</div>
        <Button variant="outline" onClick={() => navigate(-1)}>
          Geri
        </Button>
      </div>
    );
  }

  const stay = booking?.stay || {};
  const customer = booking?.customer || {};
  const snap = booking?.catalog_snapshot || {};
  const isPublic = booking?.source === "public_booking";

  return (
    <div className="p-6 print:p-0">
      <div className="flex items-start justify-between gap-4 print:hidden">
        <div>
          <div className="text-lg font-semibold">Rezervasyon Özeti</div>
          <div className="text-xs text-muted-foreground">
            ID: {String(booking.id || booking._id || "-")}
          </div>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" onClick={() => navigate(-1)}>
            Geri
          </Button>
          <Button onClick={() => window.print()}>Yazdır / PDF</Button>
        </div>
      </div>

      <div className="mt-6 space-y-4">
        <div className="border rounded-md p-4">
          <div className="font-medium">🏨 {booking.hotel_name || "-"}</div>
          <div className="text-sm text-muted-foreground mt-1">
            📅 {stay.check_in || "-"} → {stay.check_out || "-"} • 👤
            {" "}
            {booking.adults ?? "-"} / {booking.children ?? 0}
          </div>
          <div className="text-sm mt-2">
            Durum: <span className="font-medium">{booking.status || "-"}</span>{" "}
            <span className="text-muted-foreground">
              ({isPublic ? "Public Booking" : booking.source || "-"})
            </span>
          </div>
        </div>

        {isPublic ? (
          <div className="border rounded-md p-4">
            <div className="font-medium">🙋 Müşteri</div>
            <div className="text-sm mt-2">
              <div>Ad Soyad: {customer.name || "-"}</div>
              <div>Telefon: {customer.phone || "-"}</div>
              {customer.email ? <div>E-posta: {customer.email}</div> : null}
            </div>
          </div>
        ) : null}

        {isPublic ? (
          <div className="border rounded-md p-4">
            <div className="font-medium">🧾 Katalog Koşulları</div>
            <div className="text-sm mt-2">
              <div>Min gece: {snap?.min_nights ?? "-"}</div>
              <div>Komisyon: %{snap?.commission?.value ?? "-"}</div>
              <div>Markup: %{snap?.pricing_policy?.markup_percent ?? "-"}</div>
            </div>
          </div>
        ) : null}

        <div className="border rounded-md p-4">
          <div className="font-medium">Paylaşım Metni</div>
          <pre className="mt-2 whitespace-pre-wrap text-sm">{shareText}</pre>
        </div>
      </div>
    </div>
  );
}
