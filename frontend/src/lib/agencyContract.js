export const paymentStatusMeta = {
  paid: {
    label: "Ödendi",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  pending: {
    label: "Bekliyor",
    className: "border-amber-200 bg-amber-50 text-amber-700",
  },
  overdue: {
    label: "Gecikmiş",
    className: "border-rose-200 bg-rose-50 text-rose-700",
  },
};

export const contractStatusMeta = {
  active: {
    label: "Aktif",
    className: "border-emerald-200 bg-emerald-50 text-emerald-700",
  },
  expiring_soon: {
    label: "Süresi Doluyor",
    className: "border-amber-200 bg-amber-50 text-amber-700",
  },
  expired: {
    label: "Kısıtlı",
    className: "border-rose-200 bg-rose-50 text-rose-700",
  },
  not_configured: {
    label: "Tanımsız",
    className: "border-slate-200 bg-slate-50 text-slate-600",
  },
};

export function getPaymentStatusMeta(status) {
  return paymentStatusMeta[status] || {
    label: "Tanımsız",
    className: "border-slate-200 bg-slate-50 text-slate-600",
  };
}

export function getContractStatusMeta(status) {
  return contractStatusMeta[status] || contractStatusMeta.not_configured;
}

export function formatContractWindow(summary) {
  if (!summary) return "Süre tanımlanmadı";
  const start = summary.contract_start_date || "-";
  const end = summary.contract_end_date || "-";
  if (start === "-" && end === "-") return "Süre tanımlanmadı";
  return `${start} → ${end}`;
}

export function formatSeatUsage(summary) {
  if (!summary || summary.user_limit == null) return "Sınırsız kullanıcı";
  return `${summary.active_user_count || 0} / ${summary.user_limit} kullanıcı`;
}