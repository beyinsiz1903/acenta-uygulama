import React from "react";

export default function TermsOfServicePage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-bold mb-2" data-testid="terms-title">Kullanim Kosullari</h1>
        <p className="text-sm text-muted-foreground mb-8">Son guncelleme: 25 Subat 2026</p>

        <div className="prose prose-sm max-w-none space-y-6 text-foreground/90">
          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">1. Genel Hukumler</h2>
            <p>Bu kullanim kosullari, Syroce / Acenta Master ("Uygulama") hizmetlerini kullanan tum kullanicilar icin gecerlidir. Uygulamayi kullanarak bu kosullari kabul etmis sayilirsiniz.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">2. Hizmet Tanimi</h2>
            <p>Acenta Master, turizm sektoru icin gelistirilmis bir operasyon yonetim platformudur. Asagidaki hizmetleri kapsar:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Rezervasyon yonetimi</li>
              <li>B2B ag yonetimi ve is ortagi portali</li>
              <li>Tur ve urun yonetimi</li>
              <li>Finansal mutabakat ve raporlama</li>
              <li>CRM ve musteri iliskileri yonetimi</li>
              <li>Operasyonel araclar</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">3. Hesap Sorumlulugu</h2>
            <p>Kullanicilar:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Hesap bilgilerinin dogrulugu ve guncelliginden sorumludur</li>
              <li>Sifre gizliligini korumakla yukumludur</li>
              <li>Hesap uzerinden yapilan tum islemlerden sorumludur</li>
              <li>Yetkisiz erisim durumlarini derhal bildirmelidir</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">4. Kabul Edilebilir Kullanim</h2>
            <p>Kullanicilar asagidaki davranislardan kacinmalidir:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Yasal olmayan amaclarla kullanim</li>
              <li>Sisteme yetkisiz erisim girisimi</li>
              <li>Diger kullanicilarin hizmetini engelleyecek eylemler</li>
              <li>Yaniltici veya sahte bilgi girisi</li>
              <li>Fikri mulkiyet haklarinin ihlali</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">5. Odeme ve Abonelik</h2>
            <p>Hizmet bedelleri secilen plana gore belirlenir. Odemeler duzenli olarak faturalandirilir. Iptal talepleri cari donem sonunda islem gorur.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">6. Fikri Mulkiyet</h2>
            <p>Uygulamanin tum icerik, tasarim, kod ve markasi Syroce'ye aittir. Kullanicilar, uygulama icerigini kopyalayamaz, dagitamaz veya ticari amacla kullanamazlar.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">7. Hizmet Seviyesi</h2>
            <p>Sistemimiz %99.9 kullanilabilirlik hedefler. Planli bakim calismalari onceden duyurulur. Beklenmedik kesintilerde en kisa surede cozum saglanir.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">8. Sorumluluk Sinirlamasi</h2>
            <p>Syroce, hizmet kullanamindan kaynaklanan dolayli zararlardan sorumlu tutulamaz. Toplam sorumluluk, kullanicinin son 12 ayda odedigi hizmet bedeli ile sinirlidir.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">9. Fesih</h2>
            <p>Her iki taraf da 30 gun onceden yazili bildirimde bulunarak hizmet sozlesmesini feshedebilir. Kullanim kosullarinin ihlali halinde Syroce hesabi askiya alabilir veya feshedebilir.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">10. Uygulanacak Hukuk</h2>
            <p>Bu kosullar Turkiye Cumhuriyeti kanunlarina tabidir. Uyusmazliklarda Istanbul Mahkemeleri ve Icra Daireleri yetkilidir.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">11. Iletisim</h2>
            <p>Kullanim kosullari hakkinda sorulariniz icin:</p>
            <p className="mt-2">E-posta: <a href="mailto:info@syroce.com" className="text-primary underline">info@syroce.com</a></p>
          </section>
        </div>

        <div className="mt-12 pt-6 border-t text-center text-xs text-muted-foreground">
          &copy; 2026 Syroce. Tum haklari saklidir.
        </div>
      </div>
    </div>
  );
}
