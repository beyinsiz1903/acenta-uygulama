import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  ArrowLeft, 
  DollarSign, 
  TrendingUp, 
  TrendingDown,
  Clock,
  AlertCircle,
  RefreshCw,
  FileText,
  CreditCard,
  BarChart3
} from 'lucide-react';

const MobileFinance = ({ user }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [financeSnapshot, setFinanceSnapshot] = useState(null);
  const [costSummary, setCostSummary] = useState(null);
  const [pendingAR, setPendingAR] = useState([]);
  const [recentInvoices, setRecentInvoices] = useState([]);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      const [snapshotRes, costRes, invoicesRes] = await Promise.all([
        axios.get('/reports/finance-snapshot'),
        axios.get('/reports/cost-summary'),
        axios.get('/accounting/invoices?limit=10')
      ]);

      setFinanceSnapshot(snapshotRes.data);
      setCostSummary(costRes.data);
      setRecentInvoices(invoicesRes.data.invoices || []);

      // Try to get pending AR
      try {
        const arRes = await axios.get('/reports/company-aging');
        setPendingAR(arRes.data.companies || []);
      } catch (error) {
        console.log('AR data not available');
      }
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

  const formatCurrency = (amount) => {
    return `₺${parseFloat(amount || 0).toFixed(2)}`;
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-teal-600 mx-auto mb-2" />
          <p className="text-gray-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-gradient-to-r from-teal-600 to-teal-500 text-white p-4 sticky top-0 z-50 shadow-lg">
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
              <h1 className="text-xl font-bold">Finans Yönetimi</h1>
              <p className="text-xs text-teal-100">Finance Dashboard</p>
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
                  <p className="text-xs text-green-600 font-medium">BUGÜNKÜ TAH.</p>
                  <p className="text-2xl font-bold text-green-700">
                    {formatCurrency(financeSnapshot?.todays_collections?.total_collected || 0)}
                  </p>
                </div>
                <TrendingUp className="w-10 h-10 text-green-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-red-50 to-red-100 border-red-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-red-600 font-medium">BEKLEYEN ALACAK</p>
                  <p className="text-2xl font-bold text-red-700">
                    {formatCurrency(financeSnapshot?.pending_ar?.total_pending || 0)}
                  </p>
                </div>
                <Clock className="w-10 h-10 text-red-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-blue-600 font-medium">AYLIK TAH.</p>
                  <p className="text-2xl font-bold text-blue-700">
                    {formatCurrency(financeSnapshot?.mtd_collections?.total_collected || 0)}
                  </p>
                </div>
                <BarChart3 className="w-10 h-10 text-blue-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-purple-600 font-medium">AYLIK MALİYET</p>
                  <p className="text-2xl font-bold text-purple-700">
                    {formatCurrency(costSummary?.total_mtd_costs || 0)}
                  </p>
                </div>
                <TrendingDown className="w-10 h-10 text-purple-300" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Financial Metrics */}
        {costSummary?.financial_metrics && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <TrendingUp className="w-5 h-5 mr-2 text-green-600" />
                Finansal Metrikler
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3">
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <p className="text-xs text-green-600 mb-1">Gelir</p>
                  <p className="text-xl font-bold text-green-700">
                    {formatCurrency(costSummary.financial_metrics.revenue)}
                  </p>
                </div>
                <div className="text-center p-3 bg-red-50 rounded-lg">
                  <p className="text-xs text-red-600 mb-1">Maliyet</p>
                  <p className="text-xl font-bold text-red-700">
                    {formatCurrency(costSummary.financial_metrics.costs)}
                  </p>
                </div>
                <div className="text-center p-3 bg-blue-50 rounded-lg">
                  <p className="text-xs text-blue-600 mb-1">Brüt Kar</p>
                  <p className="text-xl font-bold text-blue-700">
                    {formatCurrency(costSummary.financial_metrics.gross_profit)}
                  </p>
                </div>
                <div className="text-center p-3 bg-purple-50 rounded-lg">
                  <p className="text-xs text-purple-600 mb-1">Kar Marjı</p>
                  <p className="text-xl font-bold text-purple-700">
                    {costSummary.financial_metrics.profit_margin?.toFixed(1)}%
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Recent Invoices */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center">
              <FileText className="w-5 h-5 mr-2 text-blue-600" />
              Son Faturalar
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {recentInvoices.length === 0 ? (
              <p className="text-gray-500 text-center py-4">Henüz fatura yok</p>
            ) : (
              recentInvoices.slice(0, 5).map((invoice) => (
                <div key={invoice.id} className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex-1">
                    <p className="font-bold text-gray-900">{invoice.invoice_number || 'N/A'}</p>
                    <p className="text-sm text-gray-600">{invoice.customer_name || 'Müşteri'}</p>
                    <p className="text-xs text-gray-500">
                      {new Date(invoice.invoice_date).toLocaleDateString('tr-TR')}
                    </p>
                  </div>
                  <div className="text-right">
                    <p className="font-bold text-blue-700">{formatCurrency(invoice.total_amount)}</p>
                    <Badge variant="outline" className="mt-1">
                      {invoice.status || 'pending'}
                    </Badge>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card className="bg-gradient-to-r from-teal-50 to-blue-50">
          <CardContent className="p-4">
            <div className="grid grid-cols-2 gap-3">
              <Button
                className="h-20 flex flex-col items-center justify-center bg-teal-600 hover:bg-teal-700"
                onClick={() => navigate('/invoice')}
              >
                <FileText className="w-6 h-6 mb-1" />
                <span className="text-xs">Faturalar</span>
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

export default MobileFinance;
