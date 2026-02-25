import React from "react";

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-bold mb-2" data-testid="privacy-title">Gizlilik Politikasi</h1>
        <p className="text-sm text-muted-foreground mb-8">Son guncelleme: 25 Subat 2026</p>

        <div className="prose prose-sm max-w-none space-y-6 text-foreground/90">
          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">1. Genel Bakis</h2>
            <p>Syroce / Acenta Master ("Uygulama") olarak kullanicilarimizin gizliligini korumaya onem veriyoruz. Bu gizlilik politikasi, uygulamamizi kullandiginizda hangi verileri topladigimizi, nasil kullandigimizi ve nasil korudugumuzu aciklamaktadir.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">2. Toplanan Veriler</h2>
            <p>Uygulamamiz asagidaki verileri toplar:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Hesap Bilgileri:</strong> Ad, soyad, e-posta adresi, telefon numarasi</li>
              <li><strong>Is Bilgileri:</strong> Sirket adi, vergi numarasi, acenta bilgileri</li>
              <li><strong>Islem Verileri:</strong> Rezervasyon detaylari, odeme bilgileri, fatura verileri</li>
              <li><strong>Kullanim Verileri:</strong> Oturum bilgileri, erisim zamanlari, kullanilan ozellikler</li>
              <li><strong>Cihaz Bilgileri:</strong> IP adresi, tarayici turu, isletim sistemi</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">3. Verilerin Kullanim Amaci</h2>
            <p>Toplanan veriler asagidaki amaclarla kullanilir:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Hizmetlerimizi sunmak ve yonetmek</li>
              <li>Kullanici hesaplarini olusturmak ve dogrulamak</li>
              <li>Rezervasyon ve odeme islemlerini gerceklestirmek</li>
              <li>Musteri destegi saglamak</li>
              <li>Hizmet kalitesini iyilestirmek</li>
              <li>Yasal yukumlulukleri yerine getirmek</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">4. Verilerin Paylasilmasi</h2>
            <p>Kisisel verileriniz asagidaki durumlar disinda ucuncu taraflarla paylasilmaz:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Acik rizaniz oldugunda</li>
              <li>Hizmet saglayicilarimizla (odeme islemcileri, sunucu hizmetleri)</li>
              <li>Yasal zorunluluk durumlarinda</li>
              <li>Is ortaklari kapsaminda (B2B operasyonlari icin gerekli minimum veri)</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">5. Veri Guvenligi</h2>
            <p>Verilerinizi korumak icin asagidaki onlemleri aliyoruz:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>SSL/TLS sifreleme ile veri iletimi</li>
              <li>Sifrelenmis veritabani depolama</li>
              <li>Rol bazli erisim kontrolu (RBAC)</li>
              <li>Duzenli guvenlik denetimleri</li>
              <li>Iki faktorlu kimlik dogrulama (2FA) destegi</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">6. Cerezler</h2>
            <p>Uygulamamiz oturum yonetimi ve kullanici tercihlerini hatirlamak icin cerezler kullanir. Cerezler tarayici ayarlarinizdan yonetebilirsiniz.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">7. Kullanici Haklari</h2>
            <p>KVKK ve GDPR kapsaminda asagidaki haklara sahipsiniz:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Verilerinize erisim talep etme</li>
              <li>Verilerinizin duzeltilmesini isteme</li>
              <li>Verilerinizin silinmesini talep etme</li>
              <li>Veri islemesine itiraz etme</li>
              <li>Veri tasinabilirligi talep etme</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">8. Veri Saklama Suresi</h2>
            <p>Kisisel verileriniz, hizmet iliskisi devam ettigi surece ve yasal zorunluluklarin gerektirdigi sure boyunca saklanir. Hesabinizi kapattiktan sonra verileriniz yasal saklama suresi sonunda silinir.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">9. Degisiklikler</h2>
            <p>Bu gizlilik politikasi zaman zaman guncellenebilir. Onemli degisiklikler yapildiginda sizi bilgilendiririz.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">10. Iletisim</h2>
            <p>Gizlilik politikamiz hakkinda sorulariniz icin bizimle iletisime gecebilirsiniz:</p>
            <p className="mt-2">E-posta: <a href="mailto:privacy@syroce.com" className="text-primary underline">privacy@syroce.com</a></p>
          </section>
        </div>

        <div className="mt-12 pt-6 border-t text-center text-xs text-muted-foreground">
          &copy; 2026 Syroce. Tum haklari saklidir.
        </div>
      </div>
    </div>
  );
}
