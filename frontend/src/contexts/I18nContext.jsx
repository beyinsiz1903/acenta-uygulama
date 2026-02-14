import React, { createContext, useContext, useMemo, useState, useEffect } from "react";

const DEFAULT_LANG = "tr";
const STORAGE_KEY = "app_lang";

const translations = {
  tr: {
    common: {
      language_tr: "Türkçe",
      language_en: "İngilizce",
    },
    topbar: {
      partners: "İş Ortakları",
      activity_log: "Aktivite Logu",
      logout: "Çıkış",
      expand: "Genişlet",
      collapse: "Daralt",
    },
    trial: {
      banner_text: "Deneme süreniz: {days} gün kaldı",
      upgrade_cta: "Planı yükselt",
      modal_title: "Plan Yükseltme",
      modal_success_title: "Talep Gönderildi!",
      modal_success_text: "Yöneticiniz talebinizi inceleyecek.",
      modal_close: "Kapat",
      modal_cancel: "İptal",
      modal_submit: "Talep Gönder",
      modal_submitting: "Gönderiliyor...",
      modal_error: "Talep gönderilemedi",
    },
    opsIncidents: {
      title: "Ops Olayları",
      subtitle: "Risk ve tedarikçi kaynaklı ops olaylarınızı tek ekranda görüntüleyin.",
      filters: "Filtreler",
      status: "Durum",
      type: "Tip",
      severity: "Önem Derecesi",
      all: "Tümü",
      open: "Açık",
      resolved: "Çözüldü",
      page: "Sayfa",
      prev: "Önceki",
      next: "Sonraki",
      incidents: "Olaylar",
      no_incidents_title: "Kayıt bulunamadı",
      no_incidents_default_desc: "Şu anda bu ortamda hiç ops olayı yok.",
      no_incidents_filtered_desc: "Seçili filtrelere uyan ops olayı bulunamadı.",
      clear_filters: "Filtreleri temizle",
      created_at: "Oluşturma Tarihi",
      summary: "Özet",
      source: "Kaynak",
      supplier_health: "Tedarikçi Sağlığı",
      id: "ID",
      drawer_badge: "Ops Olayı",
      drawer_fallback_title: "Olay",
      loading: "Olay yükleniyor...",
      detail_not_found: "Olay detayı bulunamadı.",
      meta: "Meta",
      source_block: "Kaynak",
      supplier_health_block: "Tedarikçi Sağlığı",
      success_rate: "Başarı oranı",
      error_rate: "Hata oranı",
      avg_latency: "Ort. gecikme",
      p95_latency: "p95 gecikme",
      last_error_codes: "Son hata kodları",
      notes: "Notlar",
      circuit_open: "Devre: AÇIK",
      circuit_closed: "Devre: KAPALI",
      no_health: "SAĞLIK YOK",
      no_health_tooltip: "Health snapshot bulunamadı (fail-open).",
      summary_label: "Özet",
    },
  },
  en: {
    common: {
      language_tr: "Turkish",
      language_en: "English",
    },
    topbar: {
      partners: "Partners",
      activity_log: "Activity log",
      logout: "Logout",
      expand: "Expand",
      collapse: "Collapse",
    },
    trial: {
      banner_text: "Your trial ends in {days} days",
      upgrade_cta: "Upgrade plan",
      modal_title: "Upgrade Plan",
      modal_success_title: "Request Sent!",
      modal_success_text: "Your administrator will review your request.",
      modal_close: "Close",
      modal_cancel: "Cancel",
      modal_submit: "Send Request",
      modal_submitting: "Sending...",
      modal_error: "Request could not be sent",
    },
    opsIncidents: {
      title: "Ops Incidents",
      subtitle: "View all your ops incidents from risk review and suppliers on a single screen.",
      filters: "Filters",
      status: "Status",
      type: "Type",
      severity: "Severity",
      all: "All",
      open: "Open",
      resolved: "Resolved",
      page: "Page",
      prev: "Prev",
      next: "Next",
      incidents: "Incidents",
      no_incidents_title: "No incidents",
      no_incidents_default_desc: "There are currently no ops incidents in this environment.",
      no_incidents_filtered_desc: "There are no ops incidents for the selected filters.",
      clear_filters: "Clear filters",
      created_at: "Created At",
      summary: "Summary",
      source: "Source",
      supplier_health: "Supplier Health",
      id: "ID",
      drawer_badge: "Ops Incident",
      drawer_fallback_title: "Incident",
      loading: "Loading incident...",
      detail_not_found: "Incident detail not found.",
      meta: "Meta",
      source_block: "Source",
      supplier_health_block: "Supplier Health",
      success_rate: "Success rate",
      error_rate: "Error rate",
      avg_latency: "Avg latency",
      p95_latency: "p95 latency",
      last_error_codes: "Last error codes",
      notes: "Notes",
      circuit_open: "Circuit: OPEN",
      circuit_closed: "Circuit: CLOSED",
      no_health: "NO HEALTH",
      no_health_tooltip: "Health snapshot not found (fail-open).",
      summary_label: "Summary",
    },
  },
};

const I18nContext = createContext({ lang: DEFAULT_LANG, setLang: () => {}, t: (key, vars) => key });

function getStoredLang() {
  if (typeof window === "undefined") return DEFAULT_LANG;
  try {
    const v = localStorage.getItem(STORAGE_KEY);
    return v === "en" ? "en" : DEFAULT_LANG;
  } catch {
    return DEFAULT_LANG;
  }
}

export function I18nProvider({ children }) {
  const [lang, setLangState] = useState(getStoredLang);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, lang);
    } catch {
      // ignore
    }
  }, [lang]);

  const setLang = (next) => {
    setLangState(next === "en" ? "en" : "tr");
  };

  const t = useCallbackLikeTranslator(lang);

  const value = useMemo(() => ({ lang, setLang, t }), [lang, t]);

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

function useCallbackLikeTranslator(lang) {
  const dict = translations[lang] || translations[DEFAULT_LANG];
  return (key, vars) => {
    const parts = key.split(".");
    let current = dict;
    for (const p of parts) {
      current = current?.[p];
      if (current == null) return key;
    }
    if (typeof current === "string" && vars) {
      return current.replace(/\{(\w+)\}/g, (_, k) => (vars[k] != null ? String(vars[k]) : ""));
    }
    return current;
  };
}

export function useI18n() {
  return useContext(I18nContext);
}

export function LanguageSwitcher() {
  const { lang, setLang, t } = useI18n();
  return (
    <div className="inline-flex items-center gap-1 text-2xs border rounded-full px-2 py-0.5 bg-background/60">
      <button
        type="button"
        onClick={() => setLang("tr")}
        className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${lang === "tr" ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}
      >
        TR
      </button>
      <button
        type="button"
        onClick={() => setLang("en")}
        className={`px-1.5 py-0.5 rounded-full text-[10px] font-medium ${lang === "en" ? "bg-primary text-primary-foreground" : "text-muted-foreground"}`}
      >
        EN
      </button>
    </div>
  );
}

export default I18nContext;
