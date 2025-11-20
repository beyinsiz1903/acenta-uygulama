import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  ArrowLeft, 
  UtensilsCrossed, 
  DollarSign, 
  TrendingUp,
  Clock,
  Users,
  RefreshCw,
  ShoppingBag,
  BarChart3
} from 'lucide-react';

const MobileFnB = ({ user }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [dailySummary, setDailySummary] = useState(null);
  const [recentTransactions, setRecentTransactions] = useState([]);
  const [outlets, setOutlets] = useState([]);
  const [topItems, setTopItems] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const today = new Date().toISOString().split('T')[0];
      
      const [summaryRes, transactionsRes, outletsRes] = await Promise.all([
        axios.get(`/pos/daily-summary?date=${today}`),
        axios.get('/pos/transactions?limit=10'),
        axios.get('/pos/outlets')
      ]);

      setDailySummary(summaryRes.data);
      setRecentTransactions(transactionsRes.data.transactions || []);
      setOutlets(outletsRes.data.outlets || []);

      // Try to get top items from menu
      try {
        const menuRes = await axios.get('/pos/menu-items');
        const items = menuRes.data.items || [];
        setTopItems(items.slice(0, 5));
      } catch (error) {
        console.log('Menu items not available');
      }
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

  const formatCurrency = (amount) => {
    return `₺${parseFloat(amount || 0).toFixed(2)}`;
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

        {/* Top Menu Items */}
        {topItems.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <TrendingUp className="w-5 h-5 mr-2 text-green-600" />
                Popüler Menü Öğeleri
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {topItems.map((item, idx) => (
                <div key={item.id} className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                  <div className="flex items-center space-x-3 flex-1">
                    <div className="bg-green-600 text-white w-8 h-8 rounded-full flex items-center justify-center font-bold">
                      {idx + 1}
                    </div>
                    <div>
                      <p className="font-bold text-gray-900">{item.name}</p>
                      <p className="text-sm text-gray-600">{item.category}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-green-700">{formatCurrency(item.price)}</p>
                    <Badge variant="outline" className="mt-1">
                      {item.outlet_id || 'Genel'}
                    </Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Quick Actions */}
        <Card className="bg-gradient-to-r from-orange-50 to-red-50">
          <CardContent className="p-4">
            <div className="grid grid-cols-2 gap-3">
              <Button
                className="h-20 flex flex-col items-center justify-center bg-orange-600 hover:bg-orange-700"
                onClick={() => toast.info('POS ekranı açılıyor...')}
              >
                <ShoppingBag className="w-6 h-6 mb-1" />
                <span className="text-xs">Yeni Sipariş</span>
              </Button>
              <Button
                className="h-20 flex flex-col items-center justify-center"
                variant="outline"
                onClick={() => navigate('/reports')}
              >
                <BarChart3 className="w-6 h-6 mb-1" />
                <span className="text-xs">Raporlar</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default MobileFnB;