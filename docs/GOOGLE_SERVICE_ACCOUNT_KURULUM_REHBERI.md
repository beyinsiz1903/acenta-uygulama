# Google Service Account Kurulum Rehberi — Syroce

Bu rehber, Syroce sisteminin Google E-Tablolar (Google Sheets) ile entegrasyonu icin gerekli olan **Google Service Account** olusturma adimlarini anlatmaktadir.

---

## Neden Service Account Gerekli?

Syroce, otel envanteri ve rezervasyon verilerini Google E-Tablolar uzerinden senkronize eder. Bunun icin Google'in API'sine erisim gerekir. **Service Account**, bir "robot kullanici" gibi calisir — sizin adinizdaki islemleri otomatik olarak yapar.

**Onemli:** Tek bir Service Account tum acentelerin e-tablolarina erisebilir. Her acentenin kendi e-tablosunu bu hesaba paylasmasi yeterlidir. **Acenteler birbirlerinin verilerine erisemez** — sistem kiracı (tenant) izolasyonu ile bunu garanti eder.

---

## Adim 1: Google Cloud Console'a Giris

1. Tarayicinizda su adrese gidin: **https://console.cloud.google.com**
2. Google hesabinizla giris yapin (sirket e-postaniz ile)
3. Ust barda "Agree" / "Kabul Et" tusuna basarak sartlari onaylayin

> **Not:** Daha once hic Google Cloud kullanmadiysaniz, ucretsiz deneme hesabi acilacaktir. Bu islem icin kredi karti gerekmez.

---

## Adim 2: Yeni Proje Olusturma

1. Sol ust kosedeki proje seciciye tiklayin (genellikle "Select a project" veya "My First Project" yazar)
2. Acilan pencerede **"NEW PROJECT"** (Yeni Proje) butonuna tiklayin
3. Proje bilgilerini girin:
   - **Project name:** `Syroce Sheets` (veya istediginiz bir isim)
   - **Organization:** Bos birakin veya mevcut organizasyonunuzu secin
4. **"CREATE"** (Olustur) butonuna tiklayin
5. Proje olusturulduktan sonra, ust bardaki bildirimden **"SELECT PROJECT"** ile yeni projeyi secin

---

## Adim 3: Google Sheets API'yi Etkinlestirme

1. Sol menuden **"APIs & Services"** > **"Library"** (Kutuphane) yolunu izleyin
2. Arama kutusuna **"Google Sheets API"** yazin
3. Cikan sonucta **"Google Sheets API"** kartina tiklayin
4. **"ENABLE"** (Etkinlestir) butonuna tiklayin
5. Ayni sekilde **"Google Drive API"** arayin ve onu da etkinlestirin

> **Her iki API'nin de etkin olmasi gerekir:** Sheets API veri okuma/yazma, Drive API dosya erisimi icin kullanilir.

---

## Adim 4: Service Account Olusturma

1. Sol menuden **"APIs & Services"** > **"Credentials"** (Kimlik Bilgileri) yolunu izleyin
2. Ust kisimda **"+ CREATE CREDENTIALS"** butonuna tiklayin
3. Acilan menuden **"Service account"** secin
4. Service account bilgilerini girin:
   - **Service account name:** `syroce-sheets` (veya istediginiz bir isim)
   - **Service account ID:** Otomatik doldurulur (ornek: `syroce-sheets@syroce-sheets.iam.gserviceaccount.com`)
   - **Description:** `Syroce E-Tablo entegrasyonu` (istege bagli)
5. **"CREATE AND CONTINUE"** (Olustur ve Devam Et) butonuna tiklayin
6. "Grant this service account access" adimlari icin:
   - **Rol secimi atlayabilirsiniz** — "CONTINUE" butonuna tiklayin
   - Son adimda da "DONE" butonuna tiklayin

---

## Adim 5: JSON Anahtar Dosyasini Indirme

1. **"Credentials"** sayfasinda, az once olusturdugumuz service account'u bulun (alt kisimda "Service Accounts" bolumunde listelenir)
2. Service account'un **email adresine** tiklayin (ornek: `syroce-sheets@syroce-sheets.iam.gserviceaccount.com`)
3. Ust kisimda **"KEYS"** (Anahtarlar) sekmesine gecin
4. **"ADD KEY"** > **"Create new key"** secin
5. Anahtar turunu **"JSON"** olarak secin
6. **"CREATE"** butonuna tiklayin
7. Tarayiciniz otomatik olarak bir `.json` dosyasi indirecektir

> **ONEMLI:** Bu dosyayi guvenli bir yerde saklayin. Bu dosya hesabiniza erisim saglar. Kaybederseniz yenisini olusturabilirsiniz, ancak baskalarinin erisim saglamasina izin vermeyin.

---

## Adim 6: JSON'u Syroce'a Yukleme

1. Syroce admin paneline **superadmin** olarak giris yapin
2. Sol menuden **"E-Tablo Senkron"** veya **"Portfolio Sync"** sayfasina gidin
3. Sayfanin ust kisminda **"Service Account Yukle"** veya **"Yapilandirma"** bolumunu bulun
4. Indirdiginiz JSON dosyasinin **tum icerigini kopyalayin** (dosyayi bir metin editoruyle acin, Ctrl+A ile tumunu secin, Ctrl+C ile kopyalayin)
5. Syroce'daki metin alanina **yapistirin** (Ctrl+V)
6. **"Kaydet"** butonuna tiklayin

Basarili oldugunda, ekranda service account'un email adresi gorunecektir.

---

## Adim 7: E-Tablolari Paylasma

Service account yuklendiginde, Syroce size bir **email adresi** gosterecektir (ornek: `syroce-sheets@syroce-sheets.iam.gserviceaccount.com`).

### Her acentenin yapmasi gereken:

1. Google Sheets'te ilgili e-tabloyu acin
2. Sag ustteki **"Paylas"** (Share) butonuna tiklayin
3. **Service account email adresini** yapistirin
4. Yetki olarak **"Duzenleyici"** (Editor) secin
   - Sadece okuma yeterliyse "Goruntuleyici" (Viewer) de olabilir
   - Ancak sisteme geri yazma (write-back) icin "Duzenleyici" gerekir
5. **"Gonder"** (Send) butonuna tiklayin

> **Not:** Acenteler bu email adresini Syroce admin panelinden gorebilir veya siz onlara iletebilirsiniz.

---

## E-Tablo Format Gereksinimleri

Syroce'un e-tabloyu dogru okuyabilmesi icin, ilk satirin **baslik satiri** olmasi gerekir. Beklenen kolonlar:

### Ana Veri Sekmesi (Envanter)
| Kolon | Aciklama | Ornek |
|-------|----------|-------|
| Tarih | Tarih bilgisi | 2026-03-15 |
| Oda Tipi | Oda kategorisi | Standart, Deluxe, Suite |
| Fiyat | Gecelik fiyat | 150 |
| Kontenjan | Musait oda sayisi | 10 |

### Rezervasyonlar Sekmesi (Write-back)
Sistem otomatik olarak bir **"Rezervasyonlar"** sekmesi olusturabilir. Bu sekme uzerinden:
- Sistemden sheet'e rezervasyon yazilabilir
- Sheet'ten sisteme `incoming_reservation` veya `external_reservation` satiri ile rezervasyon aktarilabilir

---

## Sorun Giderme

| Sorun | Cozum |
|-------|-------|
| "Sheet bulunamadi" hatasi | Sheet URL'sindeki ID'yi kontrol edin. URL'deki `/d/` ile `/edit` arasindaki kisim sheet ID'sidir |
| "Sheet erisimi yok" hatasi | Sheet'in service account email'ine paylasimi kontrol edin |
| "API etkin degil" hatasi | Google Cloud Console'da Sheets API ve Drive API'nin etkin oldugunu kontrol edin |
| JSON hatasi | JSON dosyasinin tamamin kopyaladiginizdan emin olun (bas ve son suslu parantezler dahil) |

---

## Ozet Kontrol Listesi

- [ ] Google Cloud Console'da proje olusturuldu
- [ ] Google Sheets API etkinlestirildi
- [ ] Google Drive API etkinlestirildi
- [ ] Service Account olusturuldu
- [ ] JSON anahtar dosyasi indirildi
- [ ] JSON, Syroce admin paneline yuklendi
- [ ] Service account email adresi gorunuyor
- [ ] En az bir e-tablo bu email adresine paylasıldı
- [ ] E-tabloda baslik satiri dogru formatta

---

## Guvenlik Notu

- Service Account JSON dosyasi **ozel bir anahtardir**. Baskalarıyla paylasmayın.
- Her acenta **sadece kendi verilerine** erisebilir. Sistem tenant izolasyonu ile bunu garanti eder.
- Service Account'un eristigi sheet'ler **yalnizca kendisine acikca paylasilan** sheet'lerdir.
- Istediginiz zaman admin panelinden service account'u silebilir ve yenisiyle degistirebilirsiniz.

---

*Bu rehber Syroce Travel Agency Operating System icin hazirlanmistir.*
