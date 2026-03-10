export const SYROCE_BILLING_CYCLES = {
  monthly: {
    key: "monthly",
    label: "Aylık",
    helper: "Aylık operasyon ücreti",
  },
  yearly: {
    key: "yearly",
    label: "Yıllık",
    helper: "İlk yıl kurulum + kullanım dahil",
  },
};

export const SYROCE_PUBLIC_PACKAGES = [
  {
    key: "giris",
    targetPlan: "starter",
    label: "Giriş",
    audience: "Yeni girişimler için",
    description: "Rezervasyon, teklif ve temel müşteri akışını tek panelde toparlamak isteyen küçük ekipler için hızlı başlangıç paketi.",
    featuredLabel: null,
    pricing: {
      monthly: { label: "₺4.900", period: "/ ay" },
      yearly: { label: "₺49.500", period: "/ yıl", badge: "Kurulum + ilk yıl kullanım dahil" },
    },
    specialOffer: "Aynı gün canlıya geçiş için hızlı onboarding",
    ctaLabel: "14 Gün Deneyin",
    ctaHref: "/signup?plan=trial&selectedPlan=starter",
    accent: "border-[#d6e7ff] bg-white text-slate-900",
    bulletTone: "bg-slate-50 text-slate-700",
    highlights: [
      "Bulut rezervasyon paneli",
      "Temel CRM müşteri kartları",
      "Operasyon notları ve görev takibi",
      "3 kullanıcıya kadar ekip kurulumu",
    ],
    compare: {
      reservationOps: true,
      crm: true,
      finance: "Temel",
      eTable: false,
      b2b: false,
      dedicatedSupport: false,
      customBuild: false,
      userSeats: "3 kullanıcı",
    },
  },
  {
    key: "standart",
    targetPlan: "pro",
    label: "Standart",
    audience: "Büyüyen acenteler için",
    description: "Satış, operasyon ve tahsilatı aynı sistemde koşturmak isteyen ekipler için en dengeli Syroce paketi.",
    featuredLabel: "Önerilen",
    pricing: {
      monthly: { label: "₺6.450", period: "/ ay" },
      yearly: { label: "₺64.500", period: "/ yıl", badge: "Google Sheets / E-Tablo entegrasyonu dahil" },
    },
    specialOffer: "İkinci paketten itibaren E-Tablo entegrasyonu aktif",
    ctaLabel: "Standart ile Başlayın",
    ctaHref: "/signup?plan=trial&selectedPlan=pro",
    accent: "border-[#f4c8ae] bg-[#fff8f2] text-slate-900",
    bulletTone: "bg-white text-slate-700",
    highlights: [
      "Google Sheets / E-Tablo entegrasyonu",
      "Tahsilat, link ile ödeme ve finans görünümü",
      "Ekip bazlı rol ve görev yönetimi",
      "10 kullanıcıya kadar ölçeklenebilir kullanım",
    ],
    compare: {
      reservationOps: true,
      crm: true,
      finance: true,
      eTable: true,
      b2b: false,
      dedicatedSupport: false,
      customBuild: false,
      userSeats: "10 kullanıcı",
    },
  },
  {
    key: "profesyonel",
    targetPlan: "enterprise",
    label: "Profesyonel",
    audience: "Tam hizmet ekipler için",
    description: "Birden fazla satış kanalı, alt acente akışı ve ileri raporlama isteyen operasyonlar için gelişmiş plan.",
    featuredLabel: "Operasyon + B2B",
    pricing: {
      monthly: { label: "₺8.450", period: "/ ay" },
      yearly: { label: "₺84.500", period: "/ yıl", badge: "2 yıllık alımda +3 ay bizden" },
    },
    specialOffer: "B2B ağ, gelişmiş raporlar ve E-Tablo otomasyonları",
    ctaLabel: "Demo ile İnceleyin",
    ctaHref: "/demo",
    accent: "border-slate-950 bg-slate-950 text-white",
    bulletTone: "bg-white/10 text-white/90",
    highlights: [
      "Google Sheets / E-Tablo senkron akışları",
      "B2B acente ağı ve alt acente yönetimi",
      "Gelişmiş raporlar, onay ve audit akışları",
      "Sınırsız kullanıcı ve ekip yapısı",
    ],
    compare: {
      reservationOps: true,
      crm: true,
      finance: true,
      eTable: true,
      b2b: true,
      dedicatedSupport: true,
      customBuild: false,
      userSeats: "Sınırsız",
    },
  },
  {
    key: "platinum",
    targetPlan: null,
    label: "Platinum",
    audience: "Özel projeler için",
    description: "Özel onboarding, adanmış proje yöneticisi, geliştirme saati ve markanıza özel operasyon kurgusu isteyen yapılar için.",
    featuredLabel: "Özel teklif",
    pricing: {
      monthly: { label: "Teklif al", period: "" },
      yearly: { label: "Özel sözleşme", period: "" },
    },
    specialOffer: "Özel temsilci, özel entegrasyon ve geliştirme saatleri",
    ctaLabel: "Teklif Alın",
    ctaHref: "/demo",
    accent: "border-[#dbe8e6] bg-[linear-gradient(180deg,#ffffff,#f7fbfb)] text-slate-900",
    bulletTone: "bg-slate-50 text-slate-700",
    highlights: [
      "Google Sheets / E-Tablo entegrasyon orkestrasyonu",
      "Özel onboarding ve adanmış proje yöneticisi",
      "Çoklu marka / çoklu ekip operasyonları",
      "Özel geliştirme ve entegrasyon planlaması",
    ],
    compare: {
      reservationOps: true,
      crm: true,
      finance: true,
      eTable: true,
      b2b: true,
      dedicatedSupport: true,
      customBuild: true,
      userSeats: "Sınırsız + özel yapı",
    },
  },
];

export const SYROCE_FAQS = [
  {
    question: "Syroce fiyatlarına neler dahildir?",
    answer:
      "Paket fiyatlarına panel erişimi, güvenlik güncellemeleri, bulut altyapı, standart destek ve seçtiğiniz pakette yer alan modüller dahildir. Özel geliştirme ve markaya özel tasarım talepleri ayrıca planlanır.",
  },
  {
    question: "Google Sheets / E-Tablo entegrasyonu hangi paketten itibaren geliyor?",
    answer:
      "E-Tablo entegrasyonu Standart paket ile başlar. Bu paketten itibaren Google Sheets bağlantıları, veri eşleme ve operasyon ekranına veri taşıma akışları aktif edilir.",
  },
  {
    question: "Kurulum ve onboarding süreci nasıl ilerliyor?",
    answer:
      "Trial hesabınızı dakikalar içinde açabilirsiniz. Yıllık paketlerde ilk kurulum ve onboarding planlaması fiyatın içine dahildir; Profesyonel ve Platinum’da canlıya geçiş kurgusu birlikte yapılır.",
  },
  {
    question: "Paketimi daha sonra yükseltebilir miyim?",
    answer:
      "Evet. İhtiyacınız büyüdüğünde Standart’tan Profesyonel’e veya Platinum’a geçebilirsiniz. Verileriniz korunur; geçişte sadece yeni modüller ve destek katmanı açılır.",
  },
  {
    question: "Rezervasyon sınırı var mı?",
    answer:
      "Hayır. Syroce paketlerinde rezervasyon sınırı koymuyoruz. Planlar; ekip yapısı, entegrasyon seviyesi, destek modeli ve operasyon derinliğine göre ayrışır.",
  },
  {
    question: "Özel entegrasyon veya özel geliştirme talep edebilir miyim?",
    answer:
      "Evet. Profesyonel pakette kapsam görüşmesi yapılır, Platinum’da ise özel geliştirme planı, adanmış proje yöneticisi ve roadmap takibi ile ilerlenir.",
  },
  {
    question: "Aylık mı yıllık mı çalışıyorsunuz?",
    answer:
      "Her iki model de mevcut. Yıllık planlar ilk yıl kurulum + kullanım dahil fiyatla gelir; ayrıca dönemsel özel teklif veya çok yıllı alımlarda ek avantaj sunabiliriz.",
  },
];

export const SYROCE_COMPARISON_ROWS = [
  { key: "reservationOps", label: "Rezervasyon ve operasyon paneli" },
  { key: "crm", label: "CRM ve müşteri geçmişi" },
  { key: "finance", label: "Tahsilat ve finans görünümü" },
  { key: "eTable", label: "Google Sheets / E-Tablo entegrasyonu" },
  { key: "b2b", label: "B2B / alt acente ağı" },
  { key: "dedicatedSupport", label: "Öncelikli destek / onboarding" },
  { key: "customBuild", label: "Özel geliştirme planı" },
  { key: "userSeats", label: "Kullanıcı yapısı" },
];

export function getPricingForCycle(pkg, billingCycle) {
  return pkg?.pricing?.[billingCycle] || pkg?.pricing?.monthly || { label: "Teklif al", period: "" };
}

export function formatComparisonValue(value) {
  if (value === true) return "Dahil";
  if (value === false) return "—";
  return value || "—";
}