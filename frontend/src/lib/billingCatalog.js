export const BILLING_PLAN_OPTIONS = {
  starter: {
    key: "starter",
    label: "Starter",
    description: "Küçük acenteler için sıcak başlangıç paketi.",
    pricing: {
      monthly: { amount: 990, label: "₺990", period: "/ ay" },
      yearly: { amount: 9900, label: "₺9.900", period: "/ yıl", badge: "2 ay ücretsiz" },
    },
    features: ["100 rezervasyon", "3 kullanıcı", "Temel raporlar"],
  },
  pro: {
    key: "pro",
    label: "Pro",
    description: "Büyüyen acenteler için satış ve operasyonu tek panelde toplayan ana plan.",
    pricing: {
      monthly: { amount: 2490, label: "₺2.490", period: "/ ay" },
      yearly: { amount: 24900, label: "₺24.900", period: "/ yıl", badge: "2 ay ücretsiz" },
    },
    features: ["500 rezervasyon", "10 kullanıcı", "Tüm raporlar"],
    isPopular: true,
  },
  enterprise: {
    key: "enterprise",
    label: "Enterprise",
    description: "Yüksek hacim, özel entegrasyon ve sözleşmeli destek gerektiren ekipler için.",
    pricing: {
      monthly: { amount: 6990, label: "₺6.990", period: "/ ay" },
      yearly: { amount: 69900, label: "Özel teklif", period: "" },
    },
    features: ["Sınırsız rezervasyon", "Sınırsız kullanıcı", "Özel entegrasyon"],
  },
};

export const BILLING_PLAN_ORDER = ["starter", "pro", "enterprise"];

export function formatBillingDate(value) {
  if (!value) {
    return "—";
  }

  try {
    return new Date(value).toLocaleDateString("tr-TR", {
      day: "2-digit",
      month: "long",
      year: "numeric",
    });
  } catch {
    return value;
  }
}

export function getIntervalText(interval) {
  return interval === "yearly" ? "Yıllık" : "Aylık";
}