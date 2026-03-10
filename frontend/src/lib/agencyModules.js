const AGENCY_MODULE_ALIASES = {
  dashboard: ["genel_bakis"],
  rezervasyonlar: [],
  musteriler: [],
  mutabakat: ["finans"],
  raporlar: [],
  oteller: ["otellerim", "urunler"],
  musaitlik: ["musaitlik_takibi"],
  turlar: ["turlarimiz"],
  sheet_baglantilari: ["google_sheets", "google_sheet_baglantisi", "google_sheet_baglantilari"],
};

const AGENCY_MODULE_ALIAS_LOOKUP = Object.entries(AGENCY_MODULE_ALIASES).reduce((acc, [canonicalKey, aliases]) => {
  acc[canonicalKey] = canonicalKey;
  aliases.forEach((alias) => {
    acc[alias] = canonicalKey;
  });
  return acc;
}, {});

export const AGENCY_MODULE_GROUPS = [
  {
    group: "TEMEL",
    items: [
      { key: "dashboard", label: "Dashboard" },
      { key: "rezervasyonlar", label: "Rezervasyonlar" },
      { key: "musteriler", label: "Müşteriler" },
      { key: "mutabakat", label: "Finans / Mutabakat" },
      { key: "raporlar", label: "Raporlar" },
    ],
  },
  {
    group: "SATIŞ & ENVANTER",
    items: [
      { key: "oteller", label: "Oteller" },
      { key: "musaitlik", label: "Müsaitlik" },
      { key: "turlar", label: "Turlar" },
    ],
  },
  {
    group: "ENTEGRASYONLAR",
    items: [
      { key: "sheet_baglantilari", label: "Google Sheets Bağlantıları" },
    ],
  },
];

function slugifyModuleKey(value) {
  return String(value || "")
    .normalize("NFKD")
    .replace(/[\u0300-\u036f]/g, "")
    .trim()
    .toLowerCase()
    .replace(/-/g, "_")
    .replace(/\s+/g, "_");
}

export function normalizeAgencyModuleKey(value) {
  const normalizedKey = slugifyModuleKey(value);
  return AGENCY_MODULE_ALIAS_LOOKUP[normalizedKey] || normalizedKey;
}

export function normalizeAgencyModuleKeys(values = []) {
  const unique = new Set();

  values.forEach((value) => {
    const key = normalizeAgencyModuleKey(value);
    if (key) {
      unique.add(key);
    }
  });

  return Array.from(unique);
}