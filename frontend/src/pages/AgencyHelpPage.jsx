import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";

export default function AgencyHelpPage() {
  return (
    <div className="space-y-6">
      <Card className="border-emerald-500/40 bg-emerald-500/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-emerald-900 dark:text-emerald-200">
            <span>Syroce Acenta – Hızlı Rezervasyon Kılavuzu</span>
            <Badge variant="secondary" className="text-xs">Pilot</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-emerald-900/90 dark:text-emerald-100/90">
          <p>
            Bu rehber, anlaşmalı oteller için <strong>5 dakikada rezervasyon talebi</strong> göndermeniz
            için hazırlanmıştır. Aşağıdaki 3 adımı izleyin.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>1️⃣ Giriş</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            Kullanıcı adı ve şifreniz ile giriş yaptığınızda açılan ilk ekran <strong>Hızlı Rezervasyon</strong>
            ekranıdır.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>2️⃣ Hızlı Rezervasyon (Adım 1/3 – Otel)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <ul className="list-disc list-inside space-y-1">
            <li>Satış yapabileceğiniz oteller listelenir.</li>
            <li>Bir otel seçin.</li>
            <li>Tarih ve kişi (yetişkin/çocuk) bilgilerini girin.</li>
          </ul>
          <p className="text-xs text-muted-foreground mt-2">
            Bu adımda sadece <strong>otel + tarih + kişi</strong> seçersiniz; henüz fiyat/rezervasyon yoktur.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>3️⃣ Fiyat Seçimi (Adım 2/3 – Fiyat)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <ul className="list-disc list-inside space-y-1">
            <li>Müsait oda ve fiyatları görürsünüz.</li>
            <li>Her satırda brüt fiyat, <strong>net kazancınız</strong> ve komisyon bilgisi yer alır.</li>
            <li>Satmak istediğiniz seçeneğin yanındaki <strong>Rezervasyon Oluştur</strong> butonuna tıklayın.</li>
          </ul>
          <p className="text-xs text-muted-foreground mt-2">
            NET kazancınız ekranda görünür; görünmediği durumlarda net/komisyon detayı
            <strong> mutabakat ekranında netleşir</strong>.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>4️⃣ Misafir Bilgisi (Adım 3/3 – Misafir)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <ul className="list-disc list-inside space-y-1">
            <li>Misafir adı soyadı ve telefon bilgisini girin.</li>
            <li>İsterseniz e‑posta ve özel istek notu ekleyebilirsiniz.</li>
            <li><strong>Rezervasyonu Gönder</strong> butonuna basın.</li>
          </ul>
          <p className="text-xs text-muted-foreground mt-2">
            Rezervasyon talebiniz <strong>otele iletilir</strong> ve sistemde kayıt altına alınır.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>5️⃣ Paylaşım &amp; Takip</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <ul className="list-disc list-inside space-y-1">
            <li>
              Onay ekranında <strong>WhatsApp&apos;a Gönder</strong> butonu ile detayı misafire veya otele hızlıca
              iletebilirsiniz.
            </li>
            <li>
              <strong>Rezervasyonlarım</strong> ekranından her rezervasyonun durumunu görebilirsiniz:
              <span className="block ml-4 mt-1">
                • Otel onayı bekleniyor<br />• Onaylandı<br />• İptal edildi
              </span>
            </li>
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Önemli Notlar (Pilot)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <ul className="list-disc list-inside space-y-1">
            <li>Syroce Acenta bir <strong>OTA değildir</strong>; satış kontrolü oteldedir.</li>
            <li>WhatsApp entegrasyonu süreci hızlandırmak içindir; resmi kayıt sistemdedir.</li>
            <li>
              Pilot hedefi: <strong>1 rezervasyonu 5 dakikadan kısa sürede</strong> sisteme girmek ve paylaşmak.
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
