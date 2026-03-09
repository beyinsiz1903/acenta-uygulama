import React from "react";

export default function PrivacyPolicyPage() {
  return (
    <div className="min-h-screen bg-background">
      <div className="max-w-3xl mx-auto px-4 py-12">
        <h1 className="text-3xl font-bold mb-2" data-testid="privacy-title">Gizlilik Politikası</h1>
        <p className="text-sm text-muted-foreground mb-8">Son güncelleme: 25 Şubat 2026</p>

        <div className="prose prose-sm max-w-none space-y-6 text-foreground/90">
          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">1. Genel Bakış</h2>
            <p>Syroce olarak kullanıcılarımızın gizliliğini korumaya önem veriyoruz. Bu politika; hangi verileri topladığımızı, bu verileri neden kullandığımızı ve nasıl koruduğumuzu açık bir dille anlatır.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">2. Toplanan Veriler</h2>
            <p>Hizmeti sunabilmek için aşağıdaki bilgileri işleyebiliriz:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li><strong>Hesap bilgileri:</strong> ad, soyad, e-posta adresi, telefon numarası</li>
              <li><strong>İşletme bilgileri:</strong> şirket adı, vergi bilgileri, acenta bilgileri</li>
              <li><strong>İşlem kayıtları:</strong> rezervasyon detayları, ödeme bilgileri, fatura kayıtları</li>
              <li><strong>Kullanım verileri:</strong> oturum bilgileri, giriş zamanları, kullanılan özellikler</li>
              <li><strong>Cihaz bilgileri:</strong> IP adresi, tarayıcı türü, işletim sistemi</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">3. Verileri Neden Kullanıyoruz?</h2>
            <p>Toplanan verileri şu amaçlarla kullanırız:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Hizmeti sunmak ve hesabınızı yönetmek</li>
              <li>Rezervasyon ve ödeme işlemlerini tamamlamak</li>
              <li>Müşteri desteği vermek</li>
              <li>Ürün deneyimini iyileştirmek</li>
              <li>Yasal yükümlülükleri yerine getirmek</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">4. Verileri Kimlerle Paylaşabiliriz?</h2>
            <p>Kişisel verileriniz, yalnızca aşağıdaki durumlarda ve gereken ölçüde paylaşılır:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Açık onayınız olduğunda</li>
              <li>Ödeme, barındırma ve teknik altyapı sağlayıcılarımızla</li>
              <li>Yasal zorunluluk doğduğunda</li>
              <li>B2B operasyonlar için gerekli olan sınırlı iş ortağı verilerinde</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">5. Verileri Nasıl Koruyoruz?</h2>
            <p>Veri güvenliği için aşağıdaki önlemleri uygularız:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>SSL/TLS ile güvenli veri aktarımı</li>
              <li>Şifrelenmiş veri depolama</li>
              <li>Rol bazlı erişim kontrolü</li>
              <li>Düzenli güvenlik kontrolleri</li>
              <li>İki adımlı doğrulama desteği</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">6. Çerezler</h2>
            <p>Syroce, oturum yönetimi ve tercihlerinizi hatırlamak için çerezlerden yararlanır. Çerez tercihlerinizi tarayıcı ayarlarınızdan değiştirebilirsiniz.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">7. Haklarınız</h2>
            <p>KVKK ve ilgili veri koruma düzenlemeleri kapsamında şu haklara sahipsiniz:</p>
            <ul className="list-disc pl-6 space-y-1">
              <li>Verilerinize erişim isteme</li>
              <li>Hatalı bilgilerin düzeltilmesini talep etme</li>
              <li>Verilerinizin silinmesini isteme</li>
              <li>İşleme faaliyetlerine itiraz etme</li>
              <li>Veri taşınabilirliği talebinde bulunma</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">8. Veri Saklama Süresi</h2>
            <p>Verileriniz, hizmet ilişkisi sürdüğü sürece ve ilgili mevzuatın zorunlu kıldığı süre boyunca saklanır. Hesabınız kapandıktan sonra verileriniz yasal süre sonunda silinir ya da anonimleştirilir.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">9. Değişiklikler</h2>
            <p>Bu politika zaman zaman güncellenebilir. Önemli değişikliklerde uygulama içinden veya e-posta ile bilgilendirme yapabiliriz.</p>
          </section>

          <section>
            <h2 className="text-xl font-semibold mt-6 mb-3">10. İletişim</h2>
            <p>Gizlilik politikamızla ilgili sorularınız için bizimle iletişime geçebilirsiniz:</p>
            <p className="mt-2">E-posta: <a href="mailto:privacy@syroce.com" className="text-primary underline">privacy@syroce.com</a></p>
          </section>
        </div>

        <div className="mt-12 pt-6 border-t text-center text-xs text-muted-foreground">
          &copy; 2026 Syroce. Tüm hakları saklıdır.
        </div>
      </div>
    </div>
  );
}
