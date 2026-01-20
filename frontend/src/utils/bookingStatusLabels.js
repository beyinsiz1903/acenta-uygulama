export const BOOKING_STATUS_LABELS_TR = {
  confirmed: "Onaylandı",
  cancelled: "İptal edildi",
  completed: "Tamamlandı",
  voucher_issued: "Voucher kesildi",
  pending: "Beklemede",
};

export function bookingStatusLabelTr(status) {
  if (!status) return "-";
  const key = String(status).toLowerCase();
  return BOOKING_STATUS_LABELS_TR[key] || status;
}
