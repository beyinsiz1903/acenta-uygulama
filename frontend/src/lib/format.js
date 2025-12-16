export function formatMoney(amount, currency = "TRY") {
  const n = Number(amount || 0);
  try {
    return new Intl.NumberFormat("tr-TR", {
      style: "currency",
      currency,
      maximumFractionDigits: 2,
    }).format(n);
  } catch {
    return `${n.toFixed(2)} ${currency}`;
  }
}

export function formatDateTR(isoOrYmd) {
  if (!isoOrYmd) return "-";
  try {
    const d = new Date(isoOrYmd);
    return new Intl.DateTimeFormat("tr-TR").format(d);
  } catch {
    return isoOrYmd;
  }
}

export function statusBadge(status) {
  const s = status || "-";
  const map = {
    pending: { label: "Beklemede", tone: "warn" },
    confirmed: { label: "Onaylandı", tone: "info" },
    cancelled: { label: "İptal", tone: "danger" },
    paid: { label: "Ödendi", tone: "success" },
  };
  return map[s] || { label: s, tone: "neutral" };
}
