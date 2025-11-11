import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { TrendingUp, TrendingDown, Minus } from 'lucide-react';

const RMSModule = ({ user, tenant, onLogout }) => {
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadSuggestions();
  }, []);

  const loadSuggestions = async () => {
    try {
      const response = await axios.get('/rms/suggestions');
      setSuggestions(response.data);
    } catch (error) {
      toast.error('Failed to load price suggestions');
    } finally {
      setLoading(false);
    }
  };

  const getPriceTrend = (current, suggested) => {
    const diff = suggested - current;
    if (diff > 0) return { icon: TrendingUp, color: 'text-green-600', label: '+' + diff.toFixed(2) };
    if (diff < 0) return { icon: TrendingDown, color: 'text-red-600', label: diff.toFixed(2) };
    return { icon: Minus, color: 'text-gray-600', label: '0.00' };
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
          <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>Revenue Management</h1>
          <p className="text-gray-600">AI-powered price optimization and analysis</p>
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
