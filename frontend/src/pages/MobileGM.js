import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { 
  ArrowLeft, 
  BarChart3, 
  TrendingUp, 
  Users,
  DollarSign,
  Bed,
  AlertCircle,
  RefreshCw,
  CheckCircle,
  Clock,
  Target,
  Calendar
} from 'lucide-react';

const MobileGM = ({ user }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dailyFlash, setDailyFlash] = useState(null);
  const [financeSnapshot, setFinanceSnapshot] = useState(null);
  const [roomStatus, setRoomStatus] = useState(null);
  const [staffTasks, setStaffTasks] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [dashboardModalOpen, setDashboardModalOpen] = useState(false);
  const [reportsModalOpen, setReportsModalOpen] = useState(false);
  const [pickupModalOpen, setPickupModalOpen] = useState(false);
  const [anomalyModalOpen, setAnomalyModalOpen] = useState(false);
  const [forecastModalOpen, setForecastModalOpen] = useState(false);
  const [pickupData, setPickupData] = useState(null);
  const [anomalies, setAnomalies] = useState([]);
  const [weeklyForecast, setWeeklyForecast] = useState([]);
  const [monthlyForecast, setMonthlyForecast] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      const [flashRes, financeRes, roomsRes, tasksRes] = await Promise.all([
        axios.get('/reports/daily-flash'),
        axios.get('/reports/finance-snapshot'),
        axios.get('/housekeeping/room-status'),
        axios.get('/pms/staff-tasks?limit=5')
      ]);

      setDailyFlash(flashRes.data);
      setFinanceSnapshot(financeRes.data);
      setRoomStatus(roomsRes.data);
      setStaffTasks(tasksRes.data);
    } catch (error) {
      console.error('Failed to load GM data:', error);
      toast.error('Veri yüklenemedi');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const loadPickupAnalysis = async () => {
    try {
      const res = await axios.get('/dashboard/gm/pickup-analysis');
      setPickupData(res.data);
      setPickupModalOpen(true);
    } catch (error) {
      toast.error('Pickup analizi yüklenemedi');
    }
  };

  const loadAnomalyDetection = async () => {
    try {
      const res = await axios.get('/dashboard/gm/anomaly-detection');
      setAnomalies(res.data.anomalies || []);
      setAnomalyModalOpen(true);
    } catch (error) {
      toast.error('Anomali tespiti yüklenemedi');
    }
  };

  const loadForecast = async () => {
    try {
      const [weeklyRes, monthlyRes] = await Promise.all([
        axios.get('/dashboard/gm/forecast-weekly'),
        axios.get('/dashboard/gm/forecast-monthly')
      ]);
      setWeeklyForecast(weeklyRes.data.weeks || []);
      setMonthlyForecast(monthlyRes.data.months || []);
      setForecastModalOpen(true);
    } catch (error) {
      toast.error('Tahmin verileri yüklenemedi');
    }
  };

  const formatCurrency = (amount) => {
    return `₺${parseFloat(amount || 0).toFixed(2)}`;
  };

  const formatPercent = (value) => {
    return `${parseFloat(value || 0).toFixed(1)}%`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-red-600 mx-auto mb-2" />
          <p className="text-gray-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-gradient-to-r from-red-600 to-red-500 text-white p-4 sticky top-0 z-50 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate('/mobile')}
              className="text-white hover:bg-white/20 p-2"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-xl font-bold">Genel Müdür Dashboard</h1>
              <p className="text-xs text-red-100">GM Executive Dashboard</p>
            </div>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
            className="text-white hover:bg-white/20 p-2"
          >
            <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
          </Button>
        </div>
      </div>

      <div className="p-4 space-y-4">
        {/* Date Badge */}
        <Card className="bg-gradient-to-r from-red-50 to-pink-50">
          <CardContent className="p-3">
            <div className="text-center">
              <p className="text-xs text-gray-600">Bugün</p>
              <p className="text-lg font-bold text-gray-900">
                {new Date().toLocaleDateString('tr-TR', { 
                  weekday: 'long', 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                })}
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Key Performance Indicators */}
        <div className="grid grid-cols-2 gap-3">
          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-blue-600 font-medium">DOLULUK</p>
                  <p className="text-3xl font-bold text-blue-700">
                    {formatPercent(dailyFlash?.occupancy?.occupancy_pct || 0)}
                  </p>
                  <p className="text-xs text-blue-600 mt-1">
                    {dailyFlash?.occupancy?.occupied_rooms || 0}/{dailyFlash?.occupancy?.total_rooms || 0} oda
                  </p>
                </div>
                <Bed className="w-10 h-10 text-blue-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-green-600 font-medium">GÜN GELİRİ</p>
                  <p className="text-2xl font-bold text-green-700">
                    {formatCurrency(dailyFlash?.revenue?.total_revenue || 0)}
                  </p>
                  <p className="text-xs text-green-600 mt-1">
                    ADR: {formatCurrency(dailyFlash?.revenue?.adr || 0)}
                  </p>
                </div>
                <DollarSign className="w-10 h-10 text-green-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-purple-600 font-medium">RevPAR</p>
                  <p className="text-2xl font-bold text-purple-700">
                    {formatCurrency(dailyFlash?.revenue?.revpar || 0)}
                  </p>
                </div>
                <Target className="w-10 h-10 text-purple-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-orange-600 font-medium">BEKLEYEN AR</p>
                  <p className="text-2xl font-bold text-orange-700">
                    {formatCurrency(financeSnapshot?.pending_ar?.total_pending || 0)}
                  </p>
                </div>
                <AlertCircle className="w-10 h-10 text-orange-300" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Today's Movements */}
        {dailyFlash?.movements && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <Users className="w-5 h-5 mr-2 text-blue-600" />
                Bugünkü Hareketler
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-3">
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <p className="text-xs text-green-600 mb-1">Geliş</p>
                  <p className="text-3xl font-bold text-green-700">
                    {dailyFlash.movements.arrivals || 0}
                  </p>
                </div>
                <div className="text-center p-3 bg-red-50 rounded-lg">
                  <p className="text-xs text-red-600 mb-1">Gidiş</p>
                  <p className="text-3xl font-bold text-red-700">
                    {dailyFlash.movements.departures || 0}
                  </p>
                </div>
                <div className="text-center p-3 bg-blue-50 rounded-lg">
                  <p className="text-xs text-blue-600 mb-1">Konaklayan</p>
                  <p className="text-3xl font-bold text-blue-700">
                    {dailyFlash.movements.in_house || 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Room Status Overview */}
        {roomStatus?.status_counts && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <Bed className="w-5 h-5 mr-2 text-purple-600" />
                Oda Durumu Özeti
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-3 gap-2">
                <div className="text-center p-2 bg-green-50 rounded border border-green-200">
                  <p className="text-2xl font-bold text-green-700">{roomStatus.status_counts.available || 0}</p>
                  <p className="text-xs text-green-600">Hazır</p>
                </div>
                <div className="text-center p-2 bg-red-50 rounded border border-red-200">
                  <p className="text-2xl font-bold text-red-700">{roomStatus.status_counts.dirty || 0}</p>
                  <p className="text-xs text-red-600">Kirli</p>
                </div>
                <div className="text-center p-2 bg-purple-50 rounded border border-purple-200">
                  <p className="text-2xl font-bold text-purple-700">{roomStatus.status_counts.occupied || 0}</p>
                  <p className="text-xs text-purple-600">Dolu</p>
                </div>
                <div className="text-center p-2 bg-blue-50 rounded border border-blue-200">
                  <p className="text-2xl font-bold text-blue-700">{roomStatus.status_counts.inspected || 0}</p>
                  <p className="text-xs text-blue-600">Kontrol</p>
                </div>
                <div className="text-center p-2 bg-yellow-50 rounded border border-yellow-200">
                  <p className="text-2xl font-bold text-yellow-700">{roomStatus.status_counts.cleaning || 0}</p>
                  <p className="text-xs text-yellow-600">Temizlik</p>
                </div>
                <div className="text-center p-2 bg-orange-50 rounded border border-orange-200">
                  <p className="text-2xl font-bold text-orange-700">{roomStatus.status_counts.maintenance || 0}</p>
                  <p className="text-xs text-orange-600">Bakım</p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Financial Summary */}
        {financeSnapshot && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <DollarSign className="w-5 h-5 mr-2 text-green-600" />
                Finansal Özet
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-3">
              <div className="flex items-center justify-between p-3 bg-green-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-700">Bugünkü Tahsilat</p>
                  <p className="text-xs text-gray-500">
                    {financeSnapshot.todays_collections?.payment_count || 0} işlem
                  </p>
                </div>
                <p className="text-xl font-bold text-green-700">
                  {formatCurrency(financeSnapshot.todays_collections?.total_collected || 0)}
                </p>
              </div>
              <div className="flex items-center justify-between p-3 bg-blue-50 rounded-lg">
                <div>
                  <p className="text-sm font-medium text-gray-700">Aylık Tahsilat</p>
                  <p className="text-xs text-gray-500">
                    Oran: {formatPercent(financeSnapshot.mtd_collections?.collection_rate || 0)}
                  </p>
                </div>
                <p className="text-xl font-bold text-blue-700">
                  {formatCurrency(financeSnapshot.mtd_collections?.total_collected || 0)}
                </p>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Recent Tasks */}
        {staffTasks?.tasks && staffTasks.tasks.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <CheckCircle className="w-5 h-5 mr-2 text-indigo-600" />
                Son Görevler
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {staffTasks.tasks.slice(0, 5).map((task, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg border">
                  <div className="flex-1">
                    <p className="font-medium text-gray-900 text-sm">{task.title || 'Görev'}</p>
                    <p className="text-xs text-gray-500">{task.department || 'Genel'}</p>
                  </div>
                  <Badge variant={task.status === 'completed' ? 'success' : 'default'}>
                    {task.status || 'pending'}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Quick Actions */}
        <Card className="bg-gradient-to-r from-red-50 to-orange-50">
          <CardContent className="p-4">
            <div className="grid grid-cols-2 gap-3">
              <Button
                className="h-20 flex flex-col items-center justify-center bg-red-600 hover:bg-red-700"
                onClick={() => setDashboardModalOpen(true)}
              >
                <BarChart3 className="w-6 h-6 mb-1" />
                <span className="text-xs">Tam Dashboard</span>
              </Button>
              <Button
                className="h-20 flex flex-col items-center justify-center"
                variant="outline"
                onClick={() => setReportsModalOpen(true)}
              >
                <TrendingUp className="w-6 h-6 mb-1" />
                <span className="text-xs">Raporlar</span>
              </Button>
              <Button
                className="h-20 flex flex-col items-center justify-center bg-blue-600 hover:bg-blue-700"
                onClick={loadPickupAnalysis}
              >
                <Target className="w-6 h-6 mb-1" />
                <span className="text-xs">Pickup Analizi</span>
              </Button>
              <Button
                className="h-20 flex flex-col items-center justify-center bg-orange-600 hover:bg-orange-700"
                onClick={loadAnomalyDetection}
              >
                <AlertCircle className="w-6 h-6 mb-1" />
                <span className="text-xs">Anomali Tespiti</span>
              </Button>
              <Button
                className="h-20 flex flex-col items-center justify-center bg-purple-600 hover:bg-purple-700"
                onClick={loadForecast}
              >
                <Calendar className="w-6 h-6 mb-1" />
                <span className="text-xs">Tahminler</span>
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Info Banner */}
        <Card className="bg-gradient-to-r from-indigo-50 to-purple-50">
          <CardContent className="p-4">
            <div className="flex items-start space-x-3">
              <div className="bg-indigo-100 p-2 rounded-full">
                <Target className="w-5 h-5 text-indigo-600" />
              </div>
              <div className="flex-1">
                <h4 className="font-semibold text-gray-900 mb-1">📊 Executive Snapshot</h4>
                <p className="text-sm text-gray-600">
                  Tüm operasyonlarınızın özeti mobil cihazınızda. 
                  Detaylı analizler için tam dashboard'u ziyaret edin.
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Dashboard Modal */}
      <Dialog open={dashboardModalOpen} onOpenChange={setDashboardModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Executive Dashboard - Detaylı Görünüm</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Günlük Performans</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 gap-3">
                  <div className="p-3 bg-blue-50 rounded-lg">
                    <p className="text-xs text-blue-600 mb-1">Doluluk Oranı</p>
                    <p className="text-2xl font-bold text-blue-700">
                      {dailyFlash?.occupancy_rate?.toFixed(1) || 0}%
                    </p>
                  </div>
                  <div className="p-3 bg-green-50 rounded-lg">
                    <p className="text-xs text-green-600 mb-1">RevPAR</p>
                    <p className="text-2xl font-bold text-green-700">
                      ₺{dailyFlash?.revpar?.toFixed(0) || 0}
                    </p>
                  </div>
                  <div className="p-3 bg-purple-50 rounded-lg">
                    <p className="text-xs text-purple-600 mb-1">ADR</p>
                    <p className="text-2xl font-bold text-purple-700">
                      ₺{dailyFlash?.adr?.toFixed(0) || 0}
                    </p>
                  </div>
                  <div className="p-3 bg-orange-50 rounded-lg">
                    <p className="text-xs text-orange-600 mb-1">Günlük Gelir</p>
                    <p className="text-2xl font-bold text-orange-700">
                      ₺{dailyFlash?.total_revenue?.toFixed(0) || 0}
                    </p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Operasyonel Durum</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Toplam Oda:</span>
                  <span className="font-bold">{roomStatus?.total_rooms || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Dolu Odalar:</span>
                  <span className="font-bold text-blue-700">{roomStatus?.status_counts?.occupied || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Müsait Odalar:</span>
                  <span className="font-bold text-green-700">{roomStatus?.status_counts?.available || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Temizlik Bekleyen:</span>
                  <span className="font-bold text-red-700">{roomStatus?.status_counts?.dirty || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Bakımda:</span>
                  <span className="font-bold text-orange-700">{roomStatus?.status_counts?.maintenance || 0}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Finansal Özet</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Bugünkü Tahsilat:</span>
                  <span className="font-bold text-green-700">₺{financeSnapshot?.today_collections?.toFixed(0) || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Bekleyen Alacaklar:</span>
                  <span className="font-bold text-orange-700">₺{financeSnapshot?.pending_receivables?.toFixed(0) || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Aylık Toplam Gelir:</span>
                  <span className="font-bold text-blue-700">₺{financeSnapshot?.monthly_revenue?.toFixed(0) || 0}</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </DialogContent>
      </Dialog>

      {/* Reports Modal */}
      <Dialog open={reportsModalOpen} onOpenChange={setReportsModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Executive Raporlar</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Bugünkü Flash Rapor</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div>
                    <p className="text-gray-500">Doluluk:</p>
                    <p className="font-bold">{dailyFlash?.occupancy_rate?.toFixed(1) || 0}%</p>
                  </div>
                  <div>
                    <p className="text-gray-500">RevPAR:</p>
                    <p className="font-bold">₺{dailyFlash?.revpar?.toFixed(0) || 0}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">ADR:</p>
                    <p className="font-bold">₺{dailyFlash?.adr?.toFixed(0) || 0}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Günlük Gelir:</p>
                    <p className="font-bold">₺{dailyFlash?.total_revenue?.toFixed(0) || 0}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Gelen Misafir:</p>
                    <p className="font-bold">{dailyFlash?.arrivals || 0}</p>
                  </div>
                  <div>
                    <p className="text-gray-500">Çıkan Misafir:</p>
                    <p className="font-bold">{dailyFlash?.departures || 0}</p>
                  </div>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Departman Durumu</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex items-center justify-between p-2 bg-green-50 rounded">
                  <span className="text-sm">Ön Büro</span>
                  <Badge className="bg-green-500">Operasyonel</Badge>
                </div>
                <div className="flex items-center justify-between p-2 bg-green-50 rounded">
                  <span className="text-sm">Housekeeping</span>
                  <Badge className="bg-green-500">
                    {roomStatus?.status_counts?.dirty || 0} kirli oda
                  </Badge>
                </div>
                <div className="flex items-center justify-between p-2 bg-green-50 rounded">
                  <span className="text-sm">Teknik Servis</span>
                  <Badge className="bg-green-500">
                    {roomStatus?.status_counts?.maintenance || 0} bakımda
                  </Badge>
                </div>
                <div className="flex items-center justify-between p-2 bg-green-50 rounded">
                  <span className="text-sm">F&B</span>
                  <Badge className="bg-green-500">Operasyonel</Badge>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Performans Göstergeleri</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Ortalama Konaklama Süresi:</span>
                  <span className="font-bold">{dailyFlash?.avg_stay_duration || 0} gece</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Rezervasyon Kaynağı (OTA):</span>
                  <span className="font-bold">{dailyFlash?.ota_percentage || 0}%</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Direkt Rezervasyon:</span>
                  <span className="font-bold">{dailyFlash?.direct_percentage || 0}%</span>
                </div>
              </CardContent>
            </Card>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MobileGM;
