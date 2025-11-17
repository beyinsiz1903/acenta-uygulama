import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { 
  TrendingUp, 
  TrendingDown, 
  Minus, 
  Sparkles, 
  Calendar,
  CheckCircle,
  XCircle,
  Clock,
  Filter
} from 'lucide-react';

const RMSModule = ({ user, tenant, onLogout }) => {
  const { t } = useTranslation();
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState('all');
  const [showGenerateDialog, setShowGenerateDialog] = useState(false);
  const [dateRange, setDateRange] = useState({
    start_date: new Date().toISOString().split('T')[0],
    end_date: new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
  });

  useEffect(() => {
    loadSuggestions();
  }, [filterStatus]);

  const loadSuggestions = async () => {
    setLoading(true);
    try {
      const url = filterStatus === 'all' 
        ? '/rms/suggestions'
        : `/rms/suggestions?status=${filterStatus}`;
      const response = await axios.get(url);
      setSuggestions(response.data || []);
    } catch (error) {
      console.error('Failed to load suggestions:', error);
      setSuggestions([]);
    } finally {
      setLoading(false);
    }
  };

  const handleGenerateSuggestions = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post('/rms/generate-suggestions', null, {
        params: dateRange
      });
      toast.success(`Generated ${response.data.total_count || 0} pricing suggestions!`);
      setShowGenerateDialog(false);
      loadSuggestions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to generate suggestions');
    } finally {
      setLoading(false);
    }
  };

  const handleApplySuggestion = async (suggestionId) => {
    setLoading(true);
    try {
      await axios.post(`/rms/apply-suggestion/${suggestionId}`);
      toast.success('Rate suggestion applied successfully!');
      loadSuggestions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to apply suggestion');
    } finally {
      setLoading(false);
    }
  };

  const handleRejectSuggestion = async (suggestionId) => {
    setLoading(true);
    try {
      await axios.post(`/rms/reject-suggestion/${suggestionId}`);
      toast.success('Suggestion rejected');
      loadSuggestions();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to reject suggestion');
    } finally {
      setLoading(false);
    }
  };

  const getPriceTrend = (current, suggested) => {
    const diff = suggested - current;
    const percentChange = ((diff / current) * 100).toFixed(1);
    if (diff > 0) return { 
      icon: TrendingUp, 
      color: 'text-green-600', 
      bgColor: 'bg-green-50',
      label: `+$${diff.toFixed(2)} (+${percentChange}%)` 
    };
    if (diff < 0) return { 
      icon: TrendingDown, 
      color: 'text-red-600',
      bgColor: 'bg-red-50', 
      label: `-$${Math.abs(diff).toFixed(2)} (${percentChange}%)` 
    };
    return { 
      icon: Minus, 
      color: 'text-gray-600',
      bgColor: 'bg-gray-50', 
      label: '$0.00 (0%)' 
    };
  };

  const getStatusBadge = (status) => {
    const config = {
      pending: { color: 'bg-yellow-500', icon: Clock, label: 'Pending' },
      applied: { color: 'bg-green-500', icon: CheckCircle, label: 'Applied' },
      rejected: { color: 'bg-red-500', icon: XCircle, label: 'Rejected' }
    };
    const { color, icon: Icon, label } = config[status] || config.pending;
    return (
      <Badge className={`${color} flex items-center space-x-1`}>
        <Icon className="w-3 h-3" />
        <span>{label}</span>
      </Badge>
    );
  };

  const getConfidenceBadge = (score) => {
    if (score >= 0.8) return <Badge className="bg-green-500">High Confidence</Badge>;
    if (score >= 0.6) return <Badge className="bg-yellow-500">Medium Confidence</Badge>;
    return <Badge className="bg-gray-500">Low Confidence</Badge>;
  };

  if (loading) {
    return (
      <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="rms">
        <div className="p-6 text-center">Loading...</div>
      </Layout>
    );
  }

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="rms">
      <div className="p-6 space-y-6">
        <div>
          <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>{t('rms.title')}</h1>
          <p className="text-gray-600">{t('rms.subtitle')}</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <Card className="md:col-span-2 lg:col-span-3">
            <CardHeader>
              <CardTitle>Pricing Overview</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-sm text-gray-600 mb-4">
                Our AI analyzes your occupancy rates, historical data, and market trends to suggest optimal pricing strategies.
              </div>
            </CardContent>
          </Card>

          {suggestions.map((suggestion, index) => {
            const trend = getPriceTrend(suggestion.current_price, suggestion.suggested_price);
            const TrendIcon = trend.icon;
            
            return (
              <Card key={index} data-testid={`price-suggestion-${suggestion.room_number}`}>
                <CardHeader>
                  <CardTitle>Room {suggestion.room_number}</CardTitle>
                  <p className="text-sm text-gray-600 capitalize">{suggestion.room_type}</p>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Current Price</span>
                      <span className="text-xl font-bold">${suggestion.current_price.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-sm text-gray-600">Suggested Price</span>
                      <div className="flex items-center space-x-2">
                        <span className="text-xl font-bold text-blue-600">${suggestion.suggested_price.toFixed(2)}</span>
                        <TrendIcon className={`w-5 h-5 ${trend.color}`} />
                      </div>
                    </div>
                  </div>

                  <div className="pt-4 border-t">
                    <div className="space-y-2 text-sm">
                      <div className="flex justify-between">
                        <span className="text-gray-600">Occupancy Rate</span>
                        <span className="font-medium">{suggestion.occupancy_rate.toFixed(1)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span className="text-gray-600">Demand Score</span>
                        <span className="font-medium">{(suggestion.demand_score * 100).toFixed(0)}%</span>
                      </div>
                    </div>
                  </div>

                  <div className="pt-2">
                    <div className={`text-xs px-3 py-2 rounded-lg ${
                      suggestion.occupancy_rate > 80 ? 'bg-red-50 text-red-700' :
                      suggestion.occupancy_rate > 60 ? 'bg-yellow-50 text-yellow-700' :
                      'bg-green-50 text-green-700'
                    }`}>
                      {suggestion.occupancy_rate > 80 ? '🔥 High demand - Increase prices' :
                       suggestion.occupancy_rate > 60 ? '📊 Moderate demand - Maintain prices' :
                       '💡 Low demand - Consider discounts'}
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>

        {suggestions.length === 0 && (
          <Card>
            <CardContent className="py-12 text-center text-gray-500">
              <p>No pricing suggestions available. Add rooms and bookings to get started.</p>
            </CardContent>
          </Card>
        )}
      </div>
    </Layout>
  );
};

export default RMSModule;
