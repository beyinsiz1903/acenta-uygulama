import React, { useEffect, useMemo, useState } from "react";
import { api, apiErrorMessage } from "../../lib/api";
import { toast } from "sonner";
import { Button } from "../ui/button";
import { Card } from "../ui/card";
import { Input } from "../ui/input";

const sanitizePhone = (p) => String(p || "").replace(/[^+\d]/g, "");
const toLower = (s) => String(s || "").toLowerCase().trim();

const buildContactSummary = (c) => {
  const fullName =
    c?.full_name ||
    [c?.first_name, c?.last_name].filter(Boolean).join(" ").trim() ||
    "-";

  const position = c?.position || "-";
  const phone = c?.phone || "-";
  const whatsapp = c?.whatsapp || "-";
  const email = c?.email || "-";
  const notes = c?.notes || "-";
  const id = c?._id || c?.id || "-";

  return `CRM Kontakt:

İsim: ${fullName}
Pozisyon: ${position}
Telefon: ${phone}
WhatsApp: ${whatsapp}
Email: ${email}
Not: ${notes}
ID: ${id}
`;
};

export default function HotelContactsTab({ hotelId, agencyId, user }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [q, setQ] = useState("");

  const canFetch = Boolean(hotelId && agencyId);

  const load = async () => {
    if (!canFetch) return;
    setLoading(true);
    try {
      const res = await api.get("/crm/hotel-contacts", {
        params: { hotel_id: hotelId },
      });

      const data = res.data;
      const list = Array.isArray(data) ? data : data?.contacts || [];
      setItems(Array.isArray(list) ? list : []);
    } catch (err) {
      console.error("HotelContactsTab load error:", err);
      toast.error(apiErrorMessage(err));
      setItems([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [hotelId, agencyId]);

  const filtered = useMemo(() => {
    const needle = toLower(q);
    if (!needle) return items;

    return (items || []).filter((c) => {
      const fullName =
        c?.full_name ||
        [c?.first_name, c?.last_name].filter(Boolean).join(" ").trim();
      return (
        toLower(fullName).includes(needle) ||
        toLower(c?.position).includes(needle) ||
        toLower(c?.phone).includes(needle) ||
        toLower(c?.whatsapp).includes(needle) ||
        toLower(c?.email).includes(needle) ||
        toLower(c?.notes).includes(needle)
      );
    });
  }, [items, q]);

  const openWhatsApp = (c) => {
    const wa = sanitizePhone(c?.whatsapp || c?.phone);
    if (!wa) {
      toast.error("WhatsApp numarası bulunamadı");
      return;
    }
    const msg = encodeURIComponent(buildContactSummary(c));
    window.open(`https://wa.me/${wa}?text=${msg}`, "_blank");
  };

  const copySummary = async (c) => {
    try {
      await navigator.clipboard.writeText(buildContactSummary(c));
      toast.success("Kontakt özeti panoya kopyalandı");
    } catch {
      toast.error("Kopyalama başarısız oldu");
    }
  };

  if (!agencyId) {
    return (
      <div data-testid="crm-contacts-tab" className="text-xs text-muted-foreground">
        Agency kimliği bulunamadı.
      </div>
    );
  }

  if (!hotelId) {
    return (
      <div data-testid="crm-contacts-tab" className="text-xs text-muted-foreground">
        Hotel bulunamadı.
      </div>
    );
  }

  return (
    <div data-testid="crm-contacts-tab" className="space-y-3">
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2 w-full sm:w-auto">
          <Input
            data-testid="contacts-search"
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="İsim / pozisyon / telefon / email ara..."
            className="h-9 text-sm"
          />
          <Button
            data-testid="contacts-refresh-button"
            variant="outline"
            size="sm"
            onClick={load}
            disabled={loading}
            className="h-9"
          >
            {loading ? "Yükleniyor..." : "Yenile"}
          </Button>
        </div>

        <div className="text-[11px] text-slate-500">
          Toplam: <span className="text-slate-300">{filtered.length}</span>
        </div>
      </div>

      <Card className="p-0 overflow-hidden">
        <div className="w-full overflow-auto">
          <table className="min-w-[900px] w-full text-sm">
            <thead className="bg-slate-950/40 text-slate-300">
              <tr>
                <th className="px-3 py-2 text-left">Kişi</th>
                <th className="px-3 py-2 text-left">Pozisyon</th>
                <th className="px-3 py-2 text-left">Telefon</th>
                <th className="px-3 py-2 text-left">WhatsApp</th>
                <th className="px-3 py-2 text-left">Email</th>
                <th className="px-3 py-2 text-left">Not</th>
                <th className="px-3 py-2 text-left w-48">Aksiyon</th>
              </tr>
            </thead>

            <tbody>
              {filtered.length === 0 ? (
                <tr>
                  <td className="px-3 py-4 text-xs text-slate-400" colSpan={7}>
                    Bu otel için kontakt bulunmuyor.
                  </td>
                </tr>
              ) : (
                filtered.map((c) => {
                  const id = c?._id || c?.id || `${c?.email || ""}-${c?.phone || ""}`;
                  const fullName =
                    c?.full_name ||
                    [c?.first_name, c?.last_name].filter(Boolean).join(" ").trim() ||
                    "-";

                  const phone = sanitizePhone(c?.phone);
                  const whatsapp = sanitizePhone(c?.whatsapp || c?.phone);

                  return (
                    <tr
                      key={id}
                      data-testid="contact-list-row"
                      className="border-t border-slate-800/60 hover:bg-slate-950/30"
                    >
                      <td className="px-3 py-2 align-top">
                        <div className="flex items-center gap-2">
                          <div className="font-medium text-slate-100">{fullName}</div>
                          {c?.is_primary ? (
                            <span
                              data-testid="contact-primary-badge"
                              className="inline-flex items-center rounded-full bg-emerald-500/10 px-2 py-0.5 text-[10px] font-medium text-emerald-300 border border-emerald-500/30"
                            >
                              Primary
                            </span>
                          ) : null}
                        </div>
                        <div className="text-[11px] text-slate-500">
                          ID: {String(c?.id || c?._id || "-")}
                        </div>
                      </td>

                      <td className="px-3 py-2 align-top text-slate-200">
                        {c?.position || "-"}
                      </td>

                      <td className="px-3 py-2 align-top text-slate-200 whitespace-nowrap">
                        {c?.phone || "-"}
                      </td>

                      <td className="px-3 py-2 align-top text-slate-200 whitespace-nowrap">
                        {c?.whatsapp || "-"}
                      </td>

                      <td className="px-3 py-2 align-top text-slate-200">
                        {c?.email || "-"}
                      </td>

                      <td className="px-3 py-2 align-top text-slate-400 text-xs max-w-[260px]">
                        <div className="line-clamp-2">{c?.notes || "-"}</div>
                      </td>

                      <td className="px-3 py-2 align-top">
                        <div className="flex flex-wrap gap-1">
                          <Button
                            data-testid="contact-action-call"
                            variant="outline"
                            size="xs"
                            asChild
                            disabled={!phone}
                          >
                            <a href={phone ? `tel:${phone}` : undefined}>Ara</a>
                          </Button>

                          <Button
                            data-testid="contact-action-whatsapp"
                            variant="outline"
                            size="xs"
                            onClick={() => openWhatsApp(c)}
                            disabled={!whatsapp}
                          >
                            WhatsApp
                          </Button>

                          <Button
                            data-testid="contact-action-email"
                            variant="outline"
                            size="xs"
                            asChild
                            disabled={!c?.email}
                          >
                            <a href={c?.email ? `mailto:${c.email}` : undefined}>Mail</a>
                          </Button>

                          <Button
                            data-testid="contact-action-copy"
                            variant="ghost"
                            size="xs"
                            onClick={() => copySummary(c)}
                          >
                            Kopyala
                          </Button>
                        </div>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </Card>

      <div className="text-[11px] text-slate-500">
        Not: Agency tarafı v1’de "Kişiler" read-only. Düzenleme otel tarafında yapılacak.
      </div>
    </div>
  );
}
