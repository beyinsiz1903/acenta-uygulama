export function buildBookingCopyText(booking) {
  if (!booking) return "";

  const safe = (v) => (v === null || v === undefined || v === "" ? "-" : String(v));

  const {
    hotel_name,
    destination,
    guest_name,
    check_in_date,
    check_out_date,
    nights,
    room_type,
    board_type,
    adults,
    children,
    total_amount,
    currency,
    status_tr,
    status_en,
    code,
    special_requests,
    confirmed_at,
  } = booking;

  const paxLine = () => {
    const a = typeof adults === "number" ? adults : null;
    const c = typeof children === "number" ? children : null;
    if (a === null && c === null) return "-";
    if (c === null || c === 0) return `${a} yetişkin / ${a} adult`;
    return `${a} yetişkin, ${c} çocuk / ${a} adult, ${c} child`;
  };

  const nightsLine = () => {
    if (!nights || nights <= 0) return "-";
    return `${nights} gece / ${nights} nights`;
  };

  const totalLine = () => {
    if (total_amount == null) return "-";
    const amt = Number(total_amount).toLocaleString("tr-TR", {
      minimumFractionDigits: 0,
      maximumFractionDigits: 2,
    });
    return `${amt} ${currency || ""}`.trim();
  };

  const lines = [
    "Rezervasyon Bilgisi / Booking Details",
    `Otel / Hotel: ${safe(hotel_name)}${destination ? ` (${destination})` : ""}`,
    `Misafir / Guest: ${safe(guest_name)}`,
    `Check-in: ${safe(check_in_date)}`,
    `Check-out: ${safe(check_out_date)}`,
    `Gece / Nights: ${nightsLine()}`,
    `Oda / Room: ${safe(room_type)}`,
    `Pansiyon / Board: ${safe(board_type)}`,
    `Kişi / Pax: ${paxLine()}`,
    `Tutar / Total: ${totalLine()}`,
    `Durum / Status: ${safe(status_tr)} / ${safe(status_en)}`,
    `PNR / Booking ID: ${safe(code)}`,
  ];

  if (special_requests) {
    lines.push(`Özel İstekler / Special Requests: ${special_requests}`);
  }

  if (confirmed_at) {
    lines.push(`Onay Zamanı / Confirmed At: ${confirmed_at}`);
  }

  return lines.join("\n");
}
