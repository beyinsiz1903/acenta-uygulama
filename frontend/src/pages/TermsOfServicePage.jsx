import React from "react";

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-bold mb-2" data-testid="terms-title">Kullanım Koşulları</h1>
        <p className="text-sm text-muted-foreground mb-8">Son güncelleme: 25 Şubat 2026</p>

        <div className="prose prose-sm max-w-none space-y-6 text-foreground/90">
          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">1. Genel Hükümler</h2>
            <p>Bu kullanım koşulları, Syroce hizmetlerini kullanan tüm kullanıcılar için geçerlidir. Uygulamayı kullanarak bu koşulları kabul etmiş sayılırsınız.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">2. Hizmet Tanımı</h2>
            <p>Syroce, turizm sektörü için geliştirilmiş bir operasyon yönetim platformudur. Aşağıdaki hizmetleri kapsar:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Rezervasyon yönetimi</li>
              <li>B2B ağ yönetimi ve iş ortağı portalı</li>
              <li>Tur ve ürün yönetimi</li>
              <li>Finansal mutabakat ve raporlama</li>
              <li>CRM ve müşteri ilişkileri yönetimi</li>
              <li>Operasyon ekipleri için destek araçları</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">3. Hesap Sorumluluğu</h2>
            <p>Kullanıcılar:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Hesap bilgilerinin doğru ve güncel olmasından sorumludur</li>
              <li>Şifre güvenliğini korumakla yükümlüdür</li>
              <li>Hesap üzerinden yapılan işlemlerden sorumludur</li>
              <li>Yetkisiz erişim durumlarını gecikmeden bildirmelidir</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">4. Kabul Edilebilir Kullanım</h2>
            <p>Kullanıcılar aşağıdaki davranışlardan kaçınmalıdır:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Yasal olmayan amaçlarla kullanım</li>
              <li>Sisteme yetkisiz erişim girişimi</li>
              <li>Diğer kullanıcıların hizmetini aksatacak eylemler</li>
              <li>Yanıltıcı veya sahte bilgi girişi</li>
              <li>Fikri mülkiyet haklarının ihlali</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">5. Ödeme ve Abonelik</h2>
            <p>Hizmet bedelleri seçilen plana göre belirlenir. Ödemeler plan periyoduna göre faturalandırılır. İptal talepleri, mevcut dönemin sonunda yürürlüğe alınabilir.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">6. Fikri Mülkiyet</h2>
            <p>Uygulamanın içerikleri, tasarımı, yazılımı ve markası Syroce’ye aittir. Kullanıcılar bu içerikleri izinsiz kopyalayamaz, dağıtamaz veya ticari amaçla kullanamaz.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">7. Hizmet Seviyesi</h2>
            <p>Sistemimiz yüksek erişilebilirlik hedefiyle çalışır. Planlı bakım çalışmaları önceden duyurulur. Beklenmedik kesintilerde sorunu en kısa sürede gidermek için çalışırız.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">8. Sorumluluğun Sınırları</h2>
            <p>Syroce, hizmet kullanımından doğan dolaylı zararlar için sorumlu tutulamaz. Toplam sorumluluk, ilgili kullanıcının son 12 ayda ödediği hizmet bedeli ile sınırlıdır.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">9. Fesih</h2>
            <p>Her iki taraf da yazılı bildirimle hizmet ilişkisini sona erdirebilir. Kullanım koşullarının ihlali halinde Syroce hesabı askıya alma veya kapatma hakkını saklı tutar.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">10. Uygulanacak Hukuk</h2>
            <p>Bu koşullar Türkiye Cumhuriyeti kanunlarına tabidir. Uyuşmazlıklarda İstanbul Mahkemeleri ve İcra Daireleri yetkilidir.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">11. İletişim</h2>
            <p>Kullanım koşulları hakkında sorularınız için:</p>
            <p className="mt-2">E-posta: <a href="mailto:info@syroce.com" className="text-primary underline">info@syroce.com</a></p>
          </section>
        </div>

        <div className="mt-12 pt-6 border-t text-center text-xs text-muted-foreground">
          &copy; 2026 Syroce. Tüm hakları saklıdır.
        </div>
      </div>
    </div>
  );
}
