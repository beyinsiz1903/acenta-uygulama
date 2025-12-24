import { formatMoney } from "../lib/format";

export function buildBookingShareSummary({ booking, bookingIdFallback, hotelNote }) {
  if (!booking) return "";

  const referenceId = booking.id || bookingIdFallback || "";
  const noteClean = (hotelNote || "").trim();
  const noteLine = noteClean ? `Not: ${noteClean}` : null;

  // AGENCY (rate_snapshot path)
  if (booking.rate_snapshot) {
    const { hotel_name, rate_snapshot, stay, occupancy } = booking;

    const paxTotal = (occupancy?.adults || 0) + (occupancy?.children || 0);

    const dateRangeText =
      stay?.check_in && stay?.check_out
        ? `${stay.check_in} → ${stay.check_out}`
        : "";

    const roomLine = rate_snapshot.room_type_name
      ? `Oda: ${rate_snapshot.room_type_name}`
      : null;

    const planLine = rate_snapshot.rate_plan_name
      ? `Plan: ${rate_snapshot.rate_plan_name}`
      : null;

    const totalLine =
      typeof rate_snapshot?.price?.total === "number"
        ? `Tutar: ${formatMoney(
            rate_snapshot.price.total,
            rate_snapshot.price.currency || "TRY",
          )}`
        : null;

    return [
      "✅ Rezervasyon Özeti",
      referenceId ? `Referans: ${referenceId}` : null,
      hotel_name ? `Otel: ${hotel_name}` : null,
      dateRangeText ? `Tarih: ${dateRangeText}` : null,
      paxTotal ? `Kişi: ${paxTotal}` : null,
      roomLine,
      planLine,
      totalLine,
      noteLine,
    ]
      .filter(Boolean)
      .join("\n");
  }

  // HOTEL (/hotel/bookings path)
  const hotelName = booking.hotel_name;
  const stay = booking.stay || {};
  const occ = booking.occupancy || {};

  const dateRangeText =
    stay.check_in && stay.check_out
      ? `${stay.check_in} → ${stay.check_out}`
      : "";

  const paxTotal =
    (occ.adults || booking.adults || 0) +
    (occ.children || booking.children || 0);

  const roomLine = booking.room_type
    ? `Oda: ${booking.room_type}`
    : null;

  const planLine = booking.board_type
    ? `Plan: ${booking.board_type}`
    : null;

  const totalNum = Number(booking.total_amount);
  const totalLine =
    Number.isFinite(totalNum)
      ? `Tutar: ${formatMoney(totalNum, booking.currency || "TRY")}`
      : null;

  return [
    "✅ Rezervasyon Özeti",
    referenceId ? `Referans: ${referenceId}` : null,
    hotelName ? `Otel: ${hotelName}` : null,
    dateRangeText ? `Tarih: ${dateRangeText}` : null,
    paxTotal ? `Kişi: ${paxTotal}` : null,
    roomLine,
    planLine,
    totalLine,
    noteLine,
  ]
    .filter(Boolean)
    .join("\n");
}
