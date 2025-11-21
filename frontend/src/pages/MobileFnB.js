import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { 
  ArrowLeft, 
  UtensilsCrossed, 
  DollarSign, 
  TrendingUp,
  Clock,
  Users,
  RefreshCw,
  ShoppingBag,
  BarChart3,
  Plus,
  Minus,
  FileText,
  XCircle,
  MenuIcon,
  Calculator,
  Download
} from 'lucide-react';

const MobileFnB = ({ user }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dailySummary, setDailySummary] = useState(null);
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [outlets, setOutlets] = useState([]);
  const [topItems, setTopItems] = useState([]);
  const [menuItems, setMenuItems] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [orderModalOpen, setOrderModalOpen] = useState(false);
  const [reportsModalOpen, setReportsModalOpen] = useState(false);
  const [selectedOutlet, setSelectedOutlet] = useState(null);
  const [orderItems, setOrderItems] = useState([]);
  const [tableNumber, setTableNumber] = useState('');
  const [zReportModalOpen, setZReportModalOpen] = useState(false);
  const [voidReportModalOpen, setVoidReportModalOpen] = useState(false);
  const [menuManagementModalOpen, setMenuManagementModalOpen] = useState(false);
  const [zReportData, setZReportData] = useState(null);
  const [voidTransactions, setVoidTransactions] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const today = new Date().toISOString().split('T')[0];
      
      const [summaryRes, transactionsRes, outletsRes, menuRes] = await Promise.all([
        axios.get(`/pos/daily-summary?date=${today}`),
        axios.get('/pos/transactions?limit=10'),
        axios.get('/pos/outlets'),
        axios.get('/pos/menu-items')
      ]);

      setDailySummary(summaryRes.data);
      setRecentTransactions(transactionsRes.data.transactions || []);
      setOutlets(outletsRes.data.outlets || []);
      setMenuItems(menuRes.data.menu_items || []);
      setTopItems((menuRes.data.menu_items || []).slice(0, 5));
    } catch (error) {
      console.error('Failed to load F&B data:', error);
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

  const handleAddItem = (item) => {
    const existing = orderItems.find(i => i.item_id === item.id);
    if (existing) {
      setOrderItems(orderItems.map(i => 
        i.item_id === item.id ? {...i, quantity: i.quantity + 1} : i
      ));
    } else {
      setOrderItems([...orderItems, { item_id: item.id, name: item.name, price: item.price, quantity: 1 }]);
    }
  };

  const handleRemoveItem = (itemId) => {
    const existing = orderItems.find(i => i.item_id === itemId);
    if (existing && existing.quantity > 1) {
      setOrderItems(orderItems.map(i => 
        i.item_id === itemId ? {...i, quantity: i.quantity - 1} : i
      ));
    } else {
      setOrderItems(orderItems.filter(i => i.item_id !== itemId));
    }
  };

  const calculateTotal = () => {
    return orderItems.reduce((sum, item) => sum + (item.price * item.quantity), 0);
  };

  const handleSubmitOrder = async () => {
    try {
      if (!selectedOutlet) {
        toast.error('Lütfen outlet seçin');
        return;
      }
      if (orderItems.length === 0) {
        toast.error('Lütfen ürün ekleyin');
        return;
      }

      await axios.post('/pos/mobile/quick-order', {
        outlet_id: selectedOutlet,
        table_number: tableNumber,
        items: orderItems,
        notes: ''
      });

      toast.success('Sipariş başarıyla oluşturuldu!');
      setOrderModalOpen(false);
      setOrderItems([]);
      setTableNumber('');
      loadData();
    } catch (error) {
      toast.error('Sipariş oluşturulamadı: ' + (error.response?.data?.detail || 'Hata'));
    }
  };

  const formatCurrency = (amount) => {
    return `₺${parseFloat(amount || 0).toFixed(2)}`;
  };

  const loadZReport = async () => {
    try {
      const today = new Date().toISOString().split('T')[0];
      const res = await axios.get(`/pos/z-report?date=${today}`);
      setZReportData(res.data);
      setZReportModalOpen(true);
    } catch (error) {
      toast.error('Z raporu yüklenemedi');
    }
  };

  const loadVoidReport = async () => {
    try {
      const today = new Date().toISOString().split('T')[0];
      const res = await axios.get(`/pos/void-transactions?start_date=${today}&end_date=${today}`);
      setVoidTransactions(res.data.void_transactions || []);
      setVoidReportModalOpen(true);
    } catch (error) {
      toast.error('İptal raporu yüklenemedi');
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-orange-600 mx-auto mb-2" />
          <p className="text-gray-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-gradient-to-r from-orange-600 to-orange-500 text-white p-4 sticky top-0 z-50 shadow-lg">
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
              <h1 className="text-xl font-bold">F&B Yönetimi</h1>
              <p className="text-xs text-orange-100">Food & Beverage Dashboard</p>
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
        {/* Quick Stats */}
        <div className="grid grid-cols-2 gap-3">
          <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-green-600 font-medium">BUGÜN SATIŞ</p>
                  <p className="text-2xl font-bold text-green-700">
                    {formatCurrency(dailySummary?.total_sales || 0)}
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
                  <p className="text-xs text-blue-600 font-medium">TOPLAM İŞLEM</p>
                  <p className="text-3xl font-bold text-blue-700">
                    {dailySummary?.transaction_count || 0}
                  </p>
                </div>
                <ShoppingBag className="w-10 h-10 text-blue-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-purple-600 font-medium">ORT. SEPET</p>
                  <p className="text-2xl font-bold text-purple-700">
                    {formatCurrency(dailySummary?.average_transaction || 0)}
                  </p>
                </div>
                <BarChart3 className="w-10 h-10 text-purple-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-orange-600 font-medium">OUTLET SAYISI</p>
                  <p className="text-3xl font-bold text-orange-700">
                    {outlets.length}
                  </p>
                </div>
                <UtensilsCrossed className="w-10 h-10 text-orange-300" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Outlets */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center">
              <UtensilsCrossed className="w-5 h-5 mr-2 text-orange-600" />
              Outlet'ler ({outlets.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {outlets.length === 0 ? (
              <p className="text-gray-500 text-center py-4">Outlet bulunamadı</p>
            ) : (
              outlets.map((outlet) => (
                <div key={outlet.id} className="flex items-center justify-between p-3 bg-orange-50 rounded-lg border border-orange-200">
                  <div className="flex-1">
                    <p className="font-bold text-gray-900">{outlet.name}</p>
                    <p className="text-sm text-gray-600">{outlet.location}</p>
                    <p className="text-xs text-gray-500">
                      Kapasite: {outlet.capacity} • {outlet.type}
                    </p>
                  </div>
                  <div className="text-right">
                    <Badge className={outlet.status === 'active' ? 'bg-green-500' : 'bg-gray-500'}>
                      {outlet.status === 'active' ? 'Açık' : 'Kapalı'}
                    </Badge>
                    <p className="text-xs text-gray-500 mt-1">{outlet.operating_hours}</p>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Recent Transactions */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center">
              <Clock className="w-5 h-5 mr-2 text-blue-600" />
              Son İşlemler
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {recentTransactions.length === 0 ? (
              <p className="text-gray-500 text-center py-4">Henüz işlem yok</p>
            ) : (
              recentTransactions.map((transaction) => (
                <div key={transaction.id} className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex-1">
                    <p className="font-bold text-gray-900">
                      {transaction.outlet_name || 'Outlet'}
                    </p>
                    <p className="text-sm text-gray-600">
                      Masa {transaction.table_number || 'N/A'}
                    </p>
                    <p className="text-xs text-gray-500">
                      {new Date(transaction.created_at).toLocaleTimeString('tr-TR')}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-green-700">{formatCurrency(transaction.total_amount)}</p>
                    <Badge variant="outline" className="mt-1">
                      {transaction.payment_method || 'Cash'}
                    </Badge>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-3">
          <Button
            className="h-20 flex flex-col items-center justify-center bg-orange-600 hover:bg-orange-700"
            onClick={() => setOrderModalOpen(true)}
          >
            <ShoppingBag className="w-6 h-6 mb-1" />
            <span className="text-xs">Yeni Sipariş</span>
          </Button>
          
          <Button
            className="h-20 flex flex-col items-center justify-center bg-green-600 hover:bg-green-700"
            onClick={loadZReport}
          >
            <Calculator className="w-6 h-6 mb-1" />
            <span className="text-xs">Z Raporu</span>
          </Button>
          
          <Button
            className="h-20 flex flex-col items-center justify-center bg-red-600 hover:bg-red-700"
            onClick={loadVoidReport}
          >
            <XCircle className="w-6 h-6 mb-1" />
            <span className="text-xs">İptal Raporu</span>
          </Button>
          
          <Button
            className="h-20 flex flex-col items-center justify-center bg-purple-600 hover:bg-purple-700"
            onClick={() => setMenuManagementModalOpen(true)}
          >
            <MenuIcon className="w-6 h-6 mb-1" />
            <span className="text-xs">Menü Yönetimi</span>
          </Button>
        </div>
      </div>

      {/* Order Modal */}
      <Dialog open={orderModalOpen} onOpenChange={setOrderModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Yeni Sipariş Oluştur</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Outlet Seçin</Label>
              <select 
                className="w-full p-2 border rounded mt-1"
                value={selectedOutlet || ''}
                onChange={(e) => setSelectedOutlet(e.target.value)}
              >
                <option value="">Seçin...</option>
                {outlets.filter(o => o.status === 'active').map(outlet => (
                  <option key={outlet.id} value={outlet.id}>{outlet.name}</option>
                ))}
              </select>
            </div>

            <div>
              <Label>Masa Numarası</Label>
              <Input 
                value={tableNumber}
                onChange={(e) => setTableNumber(e.target.value)}
                placeholder="Örn: 12"
              />
            </div>

            <div>
              <Label>Ürünler</Label>
              <div className="space-y-2 mt-2 max-h-60 overflow-y-auto">
                {menuItems.map(item => (
                  <div key={item.id} className="flex items-center justify-between p-2 border rounded">
                    <div className="flex-1">
                      <p className="font-medium text-sm">{item.name}</p>
                      <p className="text-xs text-gray-500">{formatCurrency(item.price)}</p>
                    </div>
                    <div className="flex items-center space-x-2">
                      {orderItems.find(i => i.item_id === item.id) && (
                        <>
                          <Button size="sm" variant="outline" onClick={() => handleRemoveItem(item.id)}>
                            <Minus className="w-3 h-3" />
                          </Button>
                          <span className="text-sm font-bold">
                            {orderItems.find(i => i.item_id === item.id)?.quantity || 0}
                          </span>
                        </>
                      )}
                      <Button size="sm" onClick={() => handleAddItem(item)}>
                        <Plus className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {orderItems.length > 0 && (
              <div className="border-t pt-3">
                <div className="space-y-1">
                  {orderItems.map(item => (
                    <div key={item.item_id} className="flex justify-between text-sm">
                      <span>{item.name} x{item.quantity}</span>
                      <span>{formatCurrency(item.price * item.quantity)}</span>
                    </div>
                  ))}
                  <div className="flex justify-between font-bold text-lg border-t pt-2">
                    <span>TOPLAM:</span>
                    <span>{formatCurrency(calculateTotal())}</span>
                  </div>
                </div>
              </div>
            )}

            <Button 
              className="w-full bg-orange-600 hover:bg-orange-700"
              onClick={handleSubmitOrder}
              disabled={!selectedOutlet || orderItems.length === 0}
            >
              Sipariş Oluştur
            </Button>
          </div>
        </DialogContent>
      </Dialog>

      {/* Reports Modal */}
      <Dialog open={reportsModalOpen} onOpenChange={setReportsModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>F&B Raporları</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Bugünkü Özet</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                <div className="flex justify-between">
                  <span className="text-gray-600">Toplam Satış:</span>
                  <span className="font-bold">{formatCurrency(dailySummary?.total_sales || 0)}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">İşlem Sayısı:</span>
                  <span className="font-bold">{dailySummary?.transaction_count || 0}</span>
                </div>
                <div className="flex justify-between">
                  <span className="text-gray-600">Ortalama Sepet:</span>
                  <span className="font-bold">{formatCurrency(dailySummary?.average_transaction || 0)}</span>
                </div>
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">Popüler Ürünler</CardTitle>
              </CardHeader>
              <CardContent className="space-y-2">
                {topItems.map((item, idx) => (
                  <div key={item.id} className="flex items-center justify-between p-2 bg-gray-50 rounded">
                    <div className="flex items-center space-x-2">
                      <span className="font-bold text-orange-600">{idx + 1}.</span>
                      <span className="text-sm">{item.name}</span>
                    </div>
                    <span className="text-sm font-bold">{formatCurrency(item.price)}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MobileFnB;
