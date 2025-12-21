import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";

export default function HotelHelpPage() {
  return (
    <div className="space-y-6">
      <Card className="border-sky-500/40 bg-sky-500/5">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-sky-900 dark:text-sky-200">
            <span>Syroce Acenta – Gelen Rezervasyonlar Kılavuzu</span>
            <Badge variant="secondary" className="text-xs">Pilot</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-sky-900/90 dark:text-sky-100/90">
          <p>
            Bu rehber, acentalardan gelen <strong>rezervasyon taleplerini</strong> tek ekrandan yönetmeniz için
            hazırlanmıştır.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>1️⃣ Giriş</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <p>
            Size verilen otel kullanıcı adı ve şifresi ile giriş yapın. Menüden
            <strong> Gelen Rezervasyonlar</strong> ekranına geçin.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>2️⃣ Gelen Rezervasyonlar</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <ul className="list-disc list-inside space-y-1">
            <li>Acentalardan gelen tüm rezervasyon taleplerini görürsünüz.</li>
            <li>Her talepte tarih, oda/plan, misafir, kişi sayısı ve tutar bilgisi yer alır.</li>
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>3️⃣ Onay / Ret</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <ul className="list-disc list-inside space-y-1">
            <li>
              <strong>Onayla</strong> butonu ile rezervasyon kesinleşir ve acenta tarafında durum
              <strong> Onaylandı</strong> olarak görünür.
            </li>
            <li>
              <strong>Reddet</strong> butonu ile talep iptal edilir ve acenta bilgilendirilir.
            </li>
          </ul>
          <p className="text-xs text-muted-foreground mt-2">
            Kontrol her zaman <strong>oteldedir</strong>; acenta sizin onayınız olmadan rezervasyonu kesinleştiremez.
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>4️⃣ Satış Kontrolleri (Opsiyonel)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <ul className="list-disc list-inside space-y-1">
            <li>
              <strong>Satışa Kapat</strong>: Belirli tarih/oda tipi için satışları durdurmak için kullanılır
              (stop‑sell mantığı).
            </li>
            <li>
              <strong>Acenta Kotası</strong>: Acentalara özel oda/adet limiti tanımlamanızı sağlar.
            </li>
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>5️⃣ Mutabakat</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <ul className="list-disc list-inside space-y-1">
            <li>Ay sonunda satılan rezervasyonları, komisyon ve net tutarları görebilirsiniz.</li>
            <li>Hem acenta hem otel tarafında aynı rakamları görmek için kullanılır.</li>
          </ul>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Önemli Notlar (Pilot)</CardTitle>
        </CardHeader>
        <CardContent className="space-y-2 text-sm text-muted-foreground">
          <ul className="list-disc list-inside space-y-1">
            <li>Syroce Acenta sizin için bir <strong>acenta extranet&apos;i</strong> gibi çalışır; kontrol sizdedir.</li>
            <li>Acenta sadece talep gönderir; siz <strong>Onayla / Reddet</strong> kararı verirsiniz.</li>
            <li>
              Pilot hedefi: Gelen taleplerin mümkün olduğunca <strong>sistem üzerinden</strong> onaylanması / reddedilmesi.
            </li>
          </ul>
        </CardContent>
      </Card>
    </div>
  );
}
