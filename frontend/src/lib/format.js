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

// Kısaltılmış para formatı: ₺9.4K, ₺1.2M gibi.
export function formatMoneyCompact(amount, currency = "TRY") {
  const n = Number(amount || 0);
  const abs = Math.abs(n);

  const suffix = abs >= 1_000_000_000 ? "B" : abs >= 1_000_000 ? "M" : abs >= 1_000 ? "K" : "";
  const div = abs >= 1_000_000_000 ? 1_000_000_000 : abs >= 1_000_000 ? 1_000_000 : abs >= 1_000 ? 1_000 : 1;
  const base = div === 1 ? n : n / div;

  const number = new Intl.NumberFormat("tr-TR", {
    maximumFractionDigits: div === 1 ? 0 : 1,
  }).format(base);

  const symMap = { TRY: "₺", USD: "$", EUR: "€" };
  const sym = symMap[currency] || `${currency} `;

  return `${sym}${number}${suffix}`;
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
