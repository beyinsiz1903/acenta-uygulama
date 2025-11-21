import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { 
  ArrowLeft, 
  DollarSign, 
  TrendingUp, 
  Calendar,
  AlertCircle,
  Receipt,
  CreditCard,
  RefreshCw,
  Plus,
  BarChart3,
  User,
  FileText,
  Clock,
  CheckCircle
} from 'lucide-react';

const MobileFinance = ({ user }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dailyCollections, setDailyCollections] = useState(null);
  const [monthlyCollections, setMonthlyCollections] = useState(null);
  const [pendingReceivables, setPendingReceivables] = useState(null);
  const [monthlyCosts, setMonthlyCosts] = useState(null);
  const [notifications, setNotifications] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [paymentModalOpen, setPaymentModalOpen] = useState(false);
  const [selectedFolio, setSelectedFolio] = useState(null);
  const [reportsModalOpen, setReportsModalOpen] = useState(false);
  const [invoicesModalOpen, setInvoicesModalOpen] = useState(false);
  const [allInvoices, setAllInvoices] = useState([]);
  const [plDetailModalOpen, setPlDetailModalOpen] = useState(false);
  const [cashierShiftModalOpen, setCashierShiftModalOpen] = useState(false);
  const [plData, setPlData] = useState(null);
  const [shiftReportData, setShiftReportData] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      const [dailyRes, monthlyRes, receivablesRes, costsRes, notifRes, invoicesRes] = await Promise.all([
        axios.get('/finance/mobile/daily-collections'),
        axios.get('/finance/mobile/monthly-collections'),
        axios.get('/finance/mobile/pending-receivables'),
        axios.get('/finance/mobile/monthly-costs'),
        axios.get('/notifications/mobile/finance'),
        axios.get('/invoice/list').catch(() => ({ data: { invoices: [] } }))
      ]);

      setDailyCollections(dailyRes.data);
      setMonthlyCollections(monthlyRes.data);
      setPendingReceivables(receivablesRes.data);
      setMonthlyCosts(costsRes.data);
      setNotifications(notifRes.data.notifications || []);
      setAllInvoices(invoicesRes.data.invoices || []);
    } catch (error) {
      console.error('Failed to load finance data:', error);
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

  const handleRecordPayment = async (formData) => {
    try {
      await axios.post('/finance/mobile/record-payment', formData);
      toast.success('Ödeme kaydedildi!');
      setPaymentModalOpen(false);
      loadData();
    } catch (error) {
      toast.error('Ödeme kaydedilemedi: ' + (error.response?.data?.detail || 'Hata'));
    }
  };

  const formatCurrency = (amount) => {
    return `₺${parseFloat(amount || 0).toFixed(2)}`;
  };

  const formatPercent = (value) => {
    return `${parseFloat(value || 0).toFixed(1)}%`;
  };

  const loadPLDetail = async () => {
    try {
      const currentMonth = new Date().toISOString().slice(0, 7); // YYYY-MM
      const res = await axios.get(`/finance/pl-detail?month=${currentMonth}`);
      setPlData(res.data);
      setPlDetailModalOpen(true);
    } catch (error) {
      toast.error('P&L raporu yüklenemedi');
    }
  };

  const loadCashierShiftReport = async () => {
    try {
      const res = await axios.get('/finance/cashier-shift-report');
      setShiftReportData(res.data);
      setCashierShiftModalOpen(true);
    } catch (error) {
      toast.error('Vardiya raporu yüklenemedi');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-indigo-600 mx-auto mb-2" />
          <p className="text-gray-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-gradient-to-r from-indigo-600 to-indigo-500 text-white p-4 sticky top-0 z-50 shadow-lg">
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
              <h1 className="text-xl font-bold">Finans Dashboard</h1>
              <p className="text-xs text-indigo-100">Finance & AR/AP</p>
            </div>
          </div>
          <div className="flex items-center space-x-2">
            {notifications.length > 0 && (
              <div className="relative">
                <Badge className="bg-red-500 text-white">{notifications.length}</Badge>
              </div>
            )}
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
      </div>

      <div className="p-4 space-y-4">
        {/* Notifications */}
        {notifications.length > 0 && (
          <Card className="bg-gradient-to-r from-red-50 to-orange-50 border-red-200">
            <CardContent className="p-3">
              <div className="flex items-start space-x-2">
                <AlertCircle className="w-5 h-5 text-red-600 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <p className="text-sm font-semibold text-gray-900">Bildirimler ({notifications.length})</p>
                  {notifications.slice(0, 3).map((notif, idx) => (
                    <p key={idx} className="text-xs text-gray-700 mt-1">
                      • {notif.title}: {notif.message}
                    </p>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-3">
          <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-green-600 font-medium">BUGÜN TAHSİLAT</p>
                  <p className="text-2xl font-bold text-green-700">
                    {formatCurrency(dailyCollections?.total_collected || 0)}
                  </p>
                  <p className="text-xs text-green-600 mt-1">
                    {dailyCollections?.payment_count || 0} işlem
                  </p>
                </div>
                <DollarSign className="w-10 h-10 text-green-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-blue-600 font-medium">AYLIK TAHSİLAT</p>
                  <p className="text-2xl font-bold text-blue-700">
                    {formatCurrency(monthlyCollections?.total_collected || 0)}
                  </p>
                  <p className="text-xs text-blue-600 mt-1">
                    Oran: {formatPercent(monthlyCollections?.collection_rate || 0)}
                  </p>
                </div>
                <TrendingUp className="w-10 h-10 text-blue-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-orange-600 font-medium">BEKLEYEN ALACAK</p>
                  <p className="text-2xl font-bold text-orange-700">
                    {formatCurrency(pendingReceivables?.total_pending || 0)}
                  </p>
                  <p className="text-xs text-orange-600 mt-1">
                    {pendingReceivables?.receivables_count || 0} fatura
                  </p>
                </div>
                <Receipt className="w-10 h-10 text-orange-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-purple-600 font-medium">AYIN MALİYETİ</p>
                  <p className="text-2xl font-bold text-purple-700">
                    {formatCurrency(monthlyCosts?.total_costs || 0)}
                  </p>
                </div>
                <Calendar className="w-10 h-10 text-purple-300" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Pending Receivables */}
        {pendingReceivables?.receivables && pendingReceivables.receivables.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <Receipt className="w-5 h-5 mr-2 text-orange-600" />
                Bekleyen Alacaklar ({pendingReceivables.receivables_count})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {pendingReceivables.receivables.slice(0, 10).map((receivable) => (
                <div 
                  key={receivable.folio_id} 
                  className={`flex items-center justify-between p-3 rounded-lg border ${
                    receivable.is_overdue ? 'bg-red-50 border-red-200' : 'bg-gray-50 border-gray-200'
                  }`}
                >
                  <div className="flex-1">
                    <p className="font-bold text-gray-900">{receivable.guest_name}</p>
                    <p className="text-sm text-gray-600">Folio: {receivable.folio_number}</p>
                    {receivable.is_overdue && (
                      <Badge className="bg-red-500 text-xs mt-1">Vadesi Geçmiş</Badge>
                    )}
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-orange-700">{formatCurrency(receivable.balance)}</p>
                    <Button
                      size="sm"
                      onClick={() => {
                        setSelectedFolio(receivable);
                        setPaymentModalOpen(true);
                      }}
                      className="bg-green-600 hover:bg-green-700 mt-1"
                    >
                      <CreditCard className="w-3 h-3 mr-1" />
                      Tahsilat
                    </Button>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Payment Methods Summary */}
        {dailyCollections?.payment_methods && Object.keys(dailyCollections.payment_methods).length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <CreditCard className="w-5 h-5 mr-2 text-green-600" />
                Bugün Ödeme Yöntemleri
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Object.entries(dailyCollections.payment_methods).map(([method, amount]) => (
                  <div key={method} className="flex items-center justify-between p-2 bg-green-50 rounded-lg">
                    <span className="text-sm font-medium text-gray-700 capitalize">{method}</span>
                    <span className="text-sm font-bold text-green-700">{formatCurrency(amount)}</span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Quick Actions */}
        <Card className="bg-gradient-to-r from-indigo-50 to-purple-50">
          <CardContent className="p-4">
            <div className="grid grid-cols-2 gap-3">
              <Button
                className="h-20 flex flex-col items-center justify-center bg-indigo-600 hover:bg-indigo-700"
                onClick={() => setReportsModalOpen(true)}
              >
                <TrendingUp className="w-6 h-6 mb-1" />
                <span className="text-xs">Finansal Raporlar</span>
              </Button>
              <Button
                className="h-20 flex flex-col items-center justify-center"
                variant="outline"
                onClick={() => setInvoicesModalOpen(true)}
              >
                <Receipt className="w-6 h-6 mb-1" />
                <span className="text-xs">Faturalar</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Payment Modal */}
      <Dialog open={paymentModalOpen} onOpenChange={setPaymentModalOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Tahsilat Kaydı</DialogTitle>
          </DialogHeader>
          {selectedFolio && (
            <form onSubmit={(e) => {
              e.preventDefault();
              const formData = new FormData(e.target);
              handleRecordPayment({
                folio_id: selectedFolio.folio_id,
                amount: parseFloat(formData.get('amount')),
                payment_method: formData.get('payment_method'),
                notes: formData.get('notes')
              });
            }}>
              <div className="space-y-4">
                <div>
                  <Label>Misafir</Label>
                  <Input value={selectedFolio.guest_name} disabled />
                </div>
                <div>
                  <Label>Kalan Bakiye</Label>
                  <Input value={formatCurrency(selectedFolio.balance)} disabled />
                </div>
                <div>
                  <Label>Tahsilat Tutarı *</Label>
                  <Input 
                    name="amount" 
                    type="number" 
                    step="0.01" 
                    max={selectedFolio.balance}
                    required 
                  />
                </div>
                <div>
                  <Label>Ödeme Yöntemi *</Label>
                  <select name="payment_method" className="w-full p-2 border rounded" required>
                    <option value="cash">Nakit</option>
                    <option value="card">Kredi Kartı</option>
                    <option value="transfer">Havale</option>
                    <option value="check">Çek</option>
                  </select>
                </div>
                <div>
                  <Label>Notlar</Label>
                  <Textarea name="notes" rows={3} />
                </div>
                <Button type="submit" className="w-full bg-green-600 hover:bg-green-700">
                  Tahsilat Kaydet
                </Button>
              </div>
            </form>
          )}
        </DialogContent>
      </Dialog>

      {/* Reports Modal */}
      <Dialog open={reportsModalOpen} onOpenChange={setReportsModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Finansal Raporlar</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Günlük Özet</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Bugün Tahsilat:</span>
                  <span className="font-bold text-green-700">{formatCurrency(dailyCollections?.total_collected || 0)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">İşlem Sayısı:</span>
                  <span className="font-bold">{dailyCollections?.payment_count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Ortalama İşlem:</span>
                  <span className="font-bold">{formatCurrency(dailyCollections?.average_transaction || 0)}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Aylık Özet</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Toplam Tahsilat:</span>
                  <span className="font-bold text-green-700">{formatCurrency(monthlyCollections?.total_collected || 0)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Beklenen Tutar:</span>
                  <span className="font-bold">{formatCurrency(monthlyCollections?.total_expected || 0)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Tahsilat Oranı:</span>
                  <span className="font-bold text-blue-700">{formatPercent(monthlyCollections?.collection_rate || 0)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Kalan Alacak:</span>
                  <span className="font-bold text-orange-700">{formatCurrency(monthlyCollections?.outstanding || 0)}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Maliyet Özeti</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Aylık Maliyet:</span>
                  <span className="font-bold text-red-700">{formatCurrency(monthlyCosts?.total_costs || 0)}</span>
                </div>
                {monthlyCosts?.costs_by_category && Object.entries(monthlyCosts.costs_by_category).map(([category, amount]) => (
                  <div key={category} className="flex justify-between pl-4">
                    <span className="text-sm text-gray-500 capitalize">{category}:</span>
                    <span className="text-sm">{formatCurrency(amount)}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </DialogContent>
      </Dialog>

      {/* Invoices Modal */}
      <Dialog open={invoicesModalOpen} onOpenChange={setInvoicesModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Faturalar ({allInvoices.length})</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            {allInvoices.length === 0 ? (
              <p className="text-center text-gray-500 py-8">Henüz fatura yok</p>
            ) : (
              allInvoices.map((invoice) => (
                <div key={invoice.id} className="p-3 bg-gray-50 rounded-lg border">
                  <div className="flex items-center justify-between mb-2">
                    <div>
                      <p className="font-bold text-gray-900">Fatura #{invoice.invoice_number}</p>
                      <p className="text-sm text-gray-600">{invoice.guest_name || invoice.company_name}</p>
                    </div>
                    <Badge className={{
                      'paid': 'bg-green-500',
                      'pending': 'bg-yellow-500',
                      'overdue': 'bg-red-500',
                      'cancelled': 'bg-gray-500'
                    }[invoice.status] || 'bg-gray-500'}>
                      {invoice.status}
                    </Badge>
                  </div>
                  <div className="text-sm text-gray-600">
                    <p>Tutar: {formatCurrency(invoice.total_amount)}</p>
                    <p>Tarih: {invoice.invoice_date ? new Date(invoice.invoice_date).toLocaleDateString('tr-TR') : 'N/A'}</p>
                    {invoice.due_date && (
                      <p>Vade: {new Date(invoice.due_date).toLocaleDateString('tr-TR')}</p>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MobileFinance;