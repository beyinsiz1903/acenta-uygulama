import React from "react";
import { Card, CardContent, CardHeader, CardTitle } from "../components/ui/card";
import { Badge } from "../components/ui/badge";
import { Separator } from "../components/ui/separator";
import { AlertCircle, Clock, CheckCircle2, MessageCircle, TrendingUp } from "lucide-react";

// NOTE: Şu an tüm veriler mock. Pilot sonrası gerçek API entegrasyonuna dönüştürülebilir.
// Expected API shape (örnek):
// {
//   range: { from: "2025-12-14", to: "2025-12-21" },
//   kpis: {
//     totalRequests,
//     avgRequestsPerAgency,
//     whatsappShareRate,
//     hotelPanelActionRate,
//     avgApprovalMinutes,
//     agenciesViewedSettlements,
//     hotelsViewedSettlements,
//     flowCompletionRate,
//   },
//   breakdown: {
//     dailyRequests: [
//       { date: "2025-12-14", count: 3 },
//       { date: "2025-12-15", count: 5 },
//     ],
//     statusCounts: { confirmed: 8, cancelled: 2, pending: 2 },
//   },
// }
const MOCK_KPIS = {
  totalRequests: 12,
  avgRequestsPerAgency: 2.4,
  whatsappShareRate: 0.75,
  hotelPanelActionRate: 0.82,
  avgApprovalMinutes: 47,
  agenciesViewedSettlements: 0.5,
  hotelsViewedSettlements: 1.0,
  flowCompletionRate: 0.73,
};

export default function AdminPilotDashboardPage() {
  const {
    totalRequests,
    avgRequestsPerAgency,
    whatsappShareRate,
    hotelPanelActionRate,
    avgApprovalMinutes,
    agenciesViewedSettlements,
    hotelsViewedSettlements,
    flowCompletionRate,
  } = MOCK_KPIS;

  return (
    <div className="space-y-6">
      <div className="flex flex-col gap-2">
        <div className="flex items-center gap-3">
          <h1 className="text-2xl font-bold text-foreground">Pilot Dashboard</h1>
          <Badge variant="outline" className="text-xs border-amber-500/50 text-amber-700 dark:text-amber-300">
            Mock Veri · Son 7 Gün
          </Badge>
        </div>
        <p className="text-sm text-muted-foreground max-w-2xl">
          Syroce Acenta pilotunun ilk 7 günündeki <strong>davranışsal KPI&apos;larını</strong> özetler.
          Şu anda metrikler örnek/mock değerlerdir; pilot sonrasında gerçek verilere bağlanabilir.
        </p>
      </div>

      {/* Üst satır: Aktivasyon & hacim */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Deneme Rezervasyonları</CardTitle>
            <TrendingUp className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{totalRequests}</div>
            <p className="text-xs text-muted-foreground mt-1">
              Toplam talep · Hedef: ≥ 10 (7 günde)
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Acenta başına ortalama <strong>{avgRequestsPerAgency.toFixed(1)}</strong> talep
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">WhatsApp Kullanımı</CardTitle>
            <MessageCircle className="h-4 w-4 text-emerald-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.round(whatsappShareRate * 100)}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              Confirmed ekranda <strong>WhatsApp&apos;a Gönder</strong> kullanımı · Hedef: ≥ 70%
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Otel Panel Aksiyonu</CardTitle>
            <CheckCircle2 className="h-4 w-4 text-sky-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.round(hotelPanelActionRate * 100)}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              Taleplerin panelden <strong>Onayla / Reddet</strong> ile işlem görme oranı · Hedef: ≥ 80%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Orta satır: Hız & güven */}
      <div className="grid gap-4 md:grid-cols-3">
        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Ortalama Onay Süresi</CardTitle>
            <Clock className="h-4 w-4 text-orange-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{avgApprovalMinutes} dk</div>
            <p className="text-xs text-muted-foreground mt-1">
              Talep → Otel onayı ortalama süresi · Hedef: &lt; 120 dk (ideal: &lt; 30 dk)
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm font-medium">Mutabakat Ekranı Kullanımı</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-muted-foreground">Acentalar</span>
              <span className="font-semibold">{Math.round(agenciesViewedSettlements * 100)}%</span>
            </div>
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-muted-foreground">Oteller</span>
              <span className="font-semibold">{Math.round(hotelsViewedSettlements * 100)}%</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              En az bir kez <strong>Mutabakat</strong> ekranına giren aktif kullanıcı oranı.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2 flex flex-row items-center justify-between space-y-0">
            <CardTitle className="text-sm font-medium">Akış Tamamlama Oranı</CardTitle>
            <AlertCircle className="h-4 w-4 text-purple-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">{Math.round(flowCompletionRate * 100)}%</div>
            <p className="text-xs text-muted-foreground mt-1">
              Hızlı Rezervasyon akışını <strong>BookingConfirmed</strong> ile bitirenlerin oranı · Hedef: ≥ 70%
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Alt: Yorum / karar matrisi */}
      <Card>
        <CardHeader>
          <CardTitle>Pilot Sonu Yorum Matrisi</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4 text-sm text-muted-foreground">
          <p>
            Bu tablo, ilk 7 gün sonunda <strong>"pilot çalışıyor mu?"</strong> sorusuna net cevap vermek için
            kullanılabilir. Rakamları gerçek verilerle değiştirdiğinizde hangi alana odaklanmanız gerektiği
            hemen ortaya çıkar.
          </p>
          <Separator />
          <div className="grid gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <p className="font-medium text-foreground">KPI yorumu</p>
              <ul className="list-disc list-inside space-y-1">
                <li>KPI-1 &amp; KPI-2 yüksekse → Acenta ürünü benimsemiş demektir.</li>
                <li>KPI-3 düşükse → Otel UI / bildirim / alışkanlık tarafına odaklanın.</li>
                <li>KPI-4 yüksekse → Otel onay süreçleri yavaş; hız için görüşme yapın.</li>
                <li>KPI-5 açılıyorsa → Mutabakat güven veriyor; parasal ilişki kuruluyor.</li>
                <li>KPI-6 düşükse → Akıştaki sürtünme noktasını (özellikle Adım 2 &amp; 3) inceleyin.</li>
              </ul>
            </div>
            <div className="space-y-1">
              <p className="font-medium text-foreground">Sonraki adım önerileri</p>
              <ul className="list-disc list-inside space-y-1">
                <li>Acenta güçlü, otel zayıfsa → <strong>Gelen Rezervasyonlar</strong> ekranını parlatın.</li>
                <li>Her iki taraf da düşükse → Pilot iletişimi ve onboarding&apos;i gözden geçirin.</li>
                <li>Metrix iyi, ama kullanım azsa → Fiyatlama / ticari model konuşma zamanı gelmiş demektir.</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
