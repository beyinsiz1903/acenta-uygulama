export function buildHotelBookingShareText(booking) {
  if (!booking) return "";

  const stay = booking?.stay || {};
  const guest = booking?.guest || {};
  const customer = booking?.customer || {};
  const snap = booking?.catalog_snapshot || {};
  const commission = snap?.commission?.value;
  const markup = snap?.pricing_policy?.markup_percent;

  const lines = [];

  lines.push(`📌 REZERVASYON TALEBİ`);
  lines.push(
    `Kaynak: ${
      booking?.source === "public_booking" ? "Public Booking" : booking?.source || "-"
    }`,
  );
  lines.push(`Durum: ${booking?.status || "-"}`);
  lines.push("");

  lines.push(`🏨 Otel: ${booking?.hotel_name || "-"}`);
  lines.push(`📅 Tarih: ${stay?.check_in || "-"} → ${stay?.check_out || "-"}`);
  lines.push(
    `👤 Pax: ${booking?.adults ?? "-"} yetişkin / ${booking?.children ?? 0} çocuk`,
  );
  lines.push("");

  if (booking?.source === "public_booking") {
    lines.push(`🙋 Müşteri: ${customer?.name || "-"}`);
    lines.push(`📞 Telefon: ${customer?.phone || "-"}`);
    if (customer?.email) lines.push(`✉️ E-posta: ${customer.email}`);
    lines.push("");

    lines.push(`🧾 Katalog Koşulları`);
    lines.push(`• Min gece: ${snap?.min_nights ?? "-"}`);
    lines.push(
      `• Komisyon: ${
        commission != null && commission !== "" ? `%${commission}` : "-"
      }`,
    );
    lines.push(
      `• Markup: ${
        markup != null && markup !== "" ? `%${markup}` : "-"
      }`,
    );
    lines.push("");
  } else {
    lines.push(`🙋 Misafir: ${guest?.full_name || "-"}`);
    if (guest?.email) lines.push(`✉️ E-posta: ${guest.email}`);
    lines.push("");
  }

  if (booking?.note) {
    lines.push(`📝 Not: ${booking.note}`);
    lines.push("");
  }

  lines.push(`— Syroce Otel Paneli`);

  return lines.join("\n");
}
