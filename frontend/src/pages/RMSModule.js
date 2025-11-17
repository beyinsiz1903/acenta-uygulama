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

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="rms">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>
              Revenue Management
            </h1>
            <p className="text-gray-600">AI-powered pricing optimization for maximum revenue</p>
          </div>
          <Dialog open={showGenerateDialog} onOpenChange={setShowGenerateDialog}>
            <DialogTrigger asChild>
              <Button>
                <Sparkles className="w-4 h-4 mr-2" />
                Generate Suggestions
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Generate Pricing Suggestions</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleGenerateSuggestions} className="space-y-4">
                <div>
                  <Label>Start Date</Label>
                  <Input
                    type="date"
                    value={dateRange.start_date}
                    onChange={(e) => setDateRange({...dateRange, start_date: e.target.value})}
                    required
                  />
                </div>
                <div>
                  <Label>End Date</Label>
                  <Input
                    type="date"
                    value={dateRange.end_date}
                    onChange={(e) => setDateRange({...dateRange, end_date: e.target.value})}
                    required
                  />
                </div>
                <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 text-sm text-blue-800">
                  <p className="font-semibold mb-1">How it works:</p>
                  <p>Our AI analyzes occupancy rates, historical data, and market trends to generate optimal pricing for each room type within the selected date range.</p>
                </div>
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? 'Generating...' : 'Generate Suggestions'}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Filter Buttons */}
        <div className="flex space-x-2">
          <Button
            variant={filterStatus === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilterStatus('all')}
          >
            All
          </Button>
          <Button
            variant={filterStatus === 'pending' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilterStatus('pending')}
          >
            <Clock className="w-4 h-4 mr-2" />
            Pending
          </Button>
          <Button
            variant={filterStatus === 'applied' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setFilterStatus('applied')}
          >
            <CheckCircle className="w-4 h-4 mr-2" />
            Applied
          </Button>
          <Button
            variant={filterStatus === 'rejected' ? 'default' ? 'outline'}
            size="sm"
            onClick={() => setFilterStatus('rejected')}
          >
            <XCircle className="w-4 h-4 mr-2" />
            Rejected
          </Button>
        </div>

        {/* Suggestions Grid */}
        {loading ? (
          <div className="text-center py-12">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading suggestions...</p>
          </div>
        ) : suggestions.length === 0 ? (
          <Card>
            <CardContent className="py-12">
              <div className="text-center text-gray-500">
                <Sparkles className="w-16 h-16 mx-auto mb-4 opacity-50" />
                <p className="text-lg font-semibold mb-2">No suggestions available</p>
                <p className="text-sm mb-4">Generate AI-powered pricing suggestions to optimize your revenue</p>
                <Button onClick={() => setShowGenerateDialog(true)}>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Generate Suggestions
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {suggestions.map((suggestion) => {
              const trend = getPriceTrend(suggestion.current_rate, suggestion.suggested_rate);
              const TrendIcon = trend.icon;
              
              return (
                <Card key={suggestion.id} className="hover:shadow-lg transition-shadow">
                  <CardHeader>
                    <div className="flex justify-between items-start">
                      <div>
                        <CardTitle className="text-lg">
                          {suggestion.date}
                        </CardTitle>
                        <p className="text-sm text-gray-600 capitalize mt-1">{suggestion.room_type}</p>
                      </div>
                      {getStatusBadge(suggestion.status)}
                    </div>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Price Comparison */}
                    <div className={`${trend.bgColor} rounded-lg p-4 space-y-2`}>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Current Rate</span>
                        <span className="text-xl font-bold text-gray-800">
                          ${suggestion.current_rate.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-sm text-gray-600">Suggested Rate</span>
                        <div className="flex items-center space-x-2">
                          <span className="text-2xl font-bold text-blue-600">
                            ${suggestion.suggested_rate.toFixed(2)}
                          </span>
                          <TrendIcon className={`w-5 h-5 ${trend.color}`} />
                        </div>
                      </div>
                      <div className={`text-sm font-medium ${trend.color} text-center pt-2 border-t border-gray-200`}>
                        {trend.label}
                      </div>
                    </div>

                    {/* Reasoning */}
                    <div className="space-y-2">
                      <div className="text-sm font-semibold text-gray-700">Reasoning:</div>
                      <p className="text-sm text-gray-600">{suggestion.reason}</p>
                    </div>

                    {/* Metrics */}
                    <div className="pt-3 border-t space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Based On:</span>
                        <span className="font-medium capitalize">{suggestion.based_on}</span>
                      </div>
                      <div className="flex justify-between text-sm items-center">
                        <span className="text-gray-600">Confidence:</span>
                        {getConfidenceBadge(suggestion.confidence_score)}
                      </div>
                    </div>

                    {/* Actions */}
                    {suggestion.status === 'pending' && (
                      <div className="pt-3 border-t flex space-x-2">
                        <Button
                          className="flex-1"
                          size="sm"
                          onClick={() => handleApplySuggestion(suggestion.id)}
                          disabled={loading}
                        >
                          <CheckCircle className="w-4 h-4 mr-2" />
                          Apply
                        </Button>
                        <Button
                          variant="outline"
                          className="flex-1"
                          size="sm"
                          onClick={() => handleRejectSuggestion(suggestion.id)}
                          disabled={loading}
                        >
                          <XCircle className="w-4 h-4 mr-2" />
                          Reject
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              );
            })}
          </div>
        )}
      </div>
    </Layout>
  );
};

export default RMSModule;
