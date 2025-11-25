import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Star, TrendingUp, TrendingDown, AlertTriangle } from 'lucide-react';

const ReputationCenter = () => {
  const [overview, setOverview] = useState(null);
  const [trends, setTrends] = useState(null);
  const [alerts, setAlerts] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [overviewRes, trendsRes, alertsRes] = await Promise.all([
        axios.get('/reputation/overview'),
        axios.get('/reputation/trends'),
        axios.get('/reputation/negative-alerts')
      ]);
      
      setOverview(overviewRes.data);
      setTrends(trendsRes.data);
      setAlerts(alertsRes.data.negative_reviews || []);
    } catch (error) {
      console.error('Reputation data yüklenemedi');
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-8">
        ⭐ Online Reputation Center
      </h1>

      {overview && (
        <>
          {/* Overall Score */}
          <Card className="mb-6 bg-gradient-to-r from-yellow-50 to-orange-50 border-2 border-yellow-200">
            <CardContent className="pt-8 pb-8 text-center">
              <p className="text-sm text-gray-600 mb-2">Genel Değerlendirme</p>
              <div className="flex items-center justify-center gap-2 mb-4">
                <Star className="w-12 h-12 text-yellow-500 fill-yellow-500" />
                <p className="text-6xl font-bold text-gray-900">{overview.overall_rating}</p>
                <span className="text-2xl text-gray-500">/5.0</span>
              </div>
              <p className="text-gray-600">{overview.total_reviews.toLocaleString()} toplam değerlendirme</p>
            </CardContent>
          </Card>

          {/* Platform Breakdown */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
            {Object.entries(overview.platforms).map(([platform, data]) => (
              <Card key={platform}>
                <CardContent className="pt-6">
                  <p className="text-sm font-semibold text-gray-700 mb-2 capitalize">
                    {platform === 'booking_com' ? 'Booking.com' : platform}
                  </p>
                  <div className="flex items-baseline gap-2 mb-2">
                    <p className="text-3xl font-bold">{data.rating}</p>
                    <Star className="w-5 h-5 text-yellow-500 fill-yellow-500" />
                  </div>
                  <p className="text-xs text-gray-500">{data.total_reviews} reviews</p>
                  <p className="text-xs text-blue-600 mt-1">+{data.recent_reviews} bu ay</p>
                </CardContent>
              </Card>
            ))}
          </div>
        </>
      )}

      {/* Trends */}
      {trends && (
        <Card className="mb-6">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {trends.trend === 'improving' ? (
                <TrendingUp className="w-6 h-6 text-green-600" />
              ) : trends.trend === 'declining' ? (
                <TrendingDown className="w-6 h-6 text-red-600" />
              ) : null}
              Trend Analizi (Son {30} Gün)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-3 gap-4">
              <div className="text-center">
                <p className="text-sm text-gray-600">Ortalama Rating</p>
                <p className="text-2xl font-bold">{trends.avg_rating}</p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-600">Trend</p>
                <p className={`text-xl font-bold capitalize ${
                  trends.trend === 'improving' ? 'text-green-600' :
                  trends.trend === 'declining' ? 'text-red-600' :
                  'text-gray-600'
                }`}>
                  {trends.trend === 'improving' ? '↑ Yükseliyor' :
                   trends.trend === 'declining' ? '↓ Düşüyor' :
                   '= Stabil'}
                </p>
              </div>
              <div className="text-center">
                <p className="text-sm text-gray-600">Toplam Review</p>
                <p className="text-2xl font-bold">{trends.total_reviews}</p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Negative Alerts */}
      {alerts.length > 0 && (
        <Card className="border-2 border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-800">
              <AlertTriangle className="w-6 h-6" />
              Negatif Review Uyarıları (Son 24 Saat)
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {alerts.map((alert) => (
                <div key={alert.id} className="bg-white p-4 rounded-lg border border-red-200">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-semibold mb-1">Rating: {alert.rating}/5</p>
                      <p className="text-sm text-gray-700">{alert.comment}</p>
                      <p className="text-xs text-gray-500 mt-2">
                        {new Date(alert.created_at).toLocaleString('tr-TR')}
                      </p>
                    </div>
                    <Button size="sm" variant="outline">
                      Yanıtla
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default DynamicPricing;