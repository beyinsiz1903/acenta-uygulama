export const LIMIT_LABELS = {
  "users.active": "Aktif kullanıcı",
  "reservations.monthly": "Aylık rezervasyon",
};

export const USAGE_ALLOWANCE_LABELS = {
  "reservation.created": "Rezervasyon oluşturma",
  "report.generated": "Rapor üretimi",
  "export.generated": "Dışa aktarma",
  "integration.call": "Entegrasyon çağrısı",
  "b2b.match_request": "B2B eşleşme talebi",
};

export function formatEntitlementValue(value, suffix = "") {
  if (value === null || value === undefined) {
    return "Sınırsız";
  }
  return `${value}${suffix}`;
}

export function mapEntitlementEntries(values, labels) {
  return Object.entries(values || {}).map(([key, value]) => ({
    key,
    label: labels[key] || key,
    value,
  }));
}
