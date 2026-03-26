# Persona Bilgi Mimarisi (Faz 3)

## Amaç
Her persona için ürün yüzeyini günlük iş akışına göre 5-7 ana işe indirmek;
menü karmaşasını azaltmak; ekranları "modül mantığına göre" değil
"iş yapma mantığına göre" organize etmek.

---

## A. Admin

**Kim:** Sistemin sahibi / operasyon yöneticisi.

**Günlük Top 5 Görev:**
1. Genel operasyon sağlığını görmek
2. Kullanıcı / rol / tenant yönetmek
3. Rezervasyon, satış, iptal, hata akışlarını izlemek
4. Sistem ayarları, entegrasyonlar, fiyat/komisyon kurallarını kontrol etmek
5. Rapor ve audit görünümüne bakmak

**Sidebar Grupları (max 7):**
| # | Grup           | Birincil Öğeler                                          |
|---|----------------|----------------------------------------------------------|
| 1 | Dashboard      | Genel Bakış                                              |
| 2 | Operasyon      | Siparişler, Onay Kutusu, Misafir Vakaları, Görevler      |
| 3 | Rezervasyonlar | Tüm Rezervasyonlar, İadeler, Açık Bakiye                 |
| 4 | Müşteri&Acenta | Müşteriler, Acentalar, İş Ortakları, B2B Kanal           |
| 5 | Fiyatlandırma  | Fiyat Yönetimi, Kurallar, Kampanyalar, Kuponlar           |
| 6 | Raporlar       | Gelir Analizi, Raporlama, Mutabakat, Dışa Aktarma        |
| 7 | Ayarlar        | Kullanıcılar, Entegrasyonlar, Tenant, Branding, API Key  |

---

## B. Agency

**Kim:** Acenta operasyon kullanıcısı. Satış yapar, rezervasyon yönetir.

**Günlük Top 5 Görev:**
1. Yeni rezervasyon / arama oluşturmak
2. Mevcut rezervasyonu görüntülemek / değiştirmek / iptal etmek
3. Teklif hazırlamak ve satışa dönüştürmek
4. Müşteri / kurumsal cari bilgisine erişmek
5. Günlük satış ve operasyon durumunu izlemek

**Sidebar Grupları (max 7):**
| # | Grup             | Birincil Öğeler                                     |
|---|------------------|-----------------------------------------------------|
| 1 | Dashboard        | Ana Panel                                           |
| 2 | Arama & Satış    | Otel Arama, Çoklu Arama, Müsaitlik, Turlar          |
| 3 | Rezervasyonlar   | Rezervasyonlarım                                    |
| 4 | Teklifler        | Pipeline, CRM Görevleri                              |
| 5 | Müşteriler       | Müşteri Listesi                                     |
| 6 | Hesap / Finans   | Mutabakat, PMS Paneli, Muhasebe, Faturalar            |
| 7 | Destek           | Yardım, Google Sheets                                |

---

## C. Hotel

**Kim:** Otel operasyon veya kontrat/yükleme kullanıcısı.

**Günlük Top 5 Görev:**
1. Oda / fiyat / envanter güncellemek
2. Allotment ve availability kontrol etmek
3. Gelen rezervasyonları görmek
4. Stop-sale / restriction yönetmek
5. Performans ve doluluk görünümünü izlemek

**Sidebar Grupları (max 7):**
| # | Grup           | Birincil Öğeler                              |
|---|----------------|----------------------------------------------|
| 1 | Dashboard      | Genel Bakış                                  |
| 2 | Envanter       | Kontenjan Yönetimi                           |
| 3 | Fiyatlandırma  | (Gelecek sprint)                             |
| 4 | Rezervasyonlar | Gelen Talepler                               |
| 5 | Kısıtlar       | Stop Sell                                    |
| 6 | Performans     | (Gelecek sprint)                             |
| 7 | Ayarlar        | Entegrasyonlar, Mutabakat, Yardım             |

---

## D. B2B

**Kim:** Bayi / partner / kurumsal satış tarafı.

**Günlük Top 5 Görev:**
1. Ürün aramak ve fiyat karşılaştırmak
2. Hızlı rezervasyon oluşturmak
3. Mevcut rezervasyonlarını yönetmek
4. Voucher / dokümanlara erişmek
5. Kendi satış / hesap özetini görmek

**Sidebar Grupları (max 6):**
| # | Grup            | Birincil Öğeler                    |
|---|-----------------|------------------------------------|
| 1 | Dashboard       | B2B Ana Panel                      |
| 2 | Arama           | Ürün Arama                         |
| 3 | Rezervasyonlarım| Rezervasyon Listesi, Detay          |
| 4 | Dokümanlar      | Voucher, Proforma                   |
| 5 | Hesap Özeti     | Cari Hesap                         |
| 6 | Destek          | Yardım, Talepler                    |

---

## Navigasyon Prensipleri

1. **Modül değil görev odaklı** - Backend domain adları kullanıcıya gösterilmez
2. **Her persona için farklı sidebar** - Tek mega-sidebar yerine role-aware sidebar
3. **Dashboard = karar ekranı** - Bugün aksiyon gerektiren öğeler, kısa yollar
4. **Primary / Secondary ayrımı** - Sık işler sidebar'da, seyrek işler "Gelişmiş" altında
5. **Standart iskelet** - Filtre bar → sonuç listesi → detay → hızlı aksiyon

## Metadata Modeli

Her navigasyon öğesi aşağıdaki metadata'yı taşır:
- `visibleInSidebar` — sidebar'da görünür mü
- `visibleInSearch` — arama/command palette'de görünür mü
- `allowedRoles` — hangi roller erişebilir
- `legacy` — eski/deprecated öğe mi
- `directAccessOnly` — sadece URL ile erişilebilir (sidebar/search dışı)
