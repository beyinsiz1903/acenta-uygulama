import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Star, TrendingUp, AlertTriangle, MessageCircle } from 'lucide-react';

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
      console.error('Reputation yüklenemedi');
    }
  };

  return (
    <div className="p-6">
      <h1 className="text-3xl font-bold mb-8">
        ⭐ Online Reputation Center
      </h1>

      {overview && (
        <Card className="mb-6 bg-gradient-to-r from-yellow-50 to-orange-50">
          <CardContent className="pt-8 text-center">
            <div className="flex items-center justify-center gap-2 mb-4">
              <Star className="w-12 h-12 text-yellow-500 fill-yellow-500" />
              <p className="text-6xl font-bold">{overview.overall_rating}</p>
              <span className="text-2xl text-gray-500">/5.0</span>
            </div>
            <p className="text-gray-600">{overview.total_reviews.toLocaleString()} toplam değerlendirme</p>
          </CardContent>
        </Card>
      )}

      {overview && (
        <div className="grid grid-cols-4 gap-4 mb-6">
          {Object.entries(overview.platforms).map(([platform, data]) => (
            <Card key={platform}>
              <CardContent className="pt-6">
                <p className="text-sm font-semibold capitalize mb-2">
                  {platform === 'booking_com' ? 'Booking.com' : platform}
                </p>
                <p className="text-3xl font-bold">{data.rating}</p>
                <p className="text-xs text-gray-500">{data.total_reviews} reviews</p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {alerts.length > 0 && (
        <Card className="border-red-200 bg-red-50">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-red-800">
              <AlertTriangle className="w-6 h-6" />
              Negatif Review Uyarıları
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-red-700">Son 24 saatte {alerts.length} negatif review</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default ReputationCenter;