import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { ArrowLeft, Cpu, HardDrive, Activity, Zap, Clock, RefreshCw, TrendingUp, Server } from 'lucide-react';

const SystemPerformanceMonitor = ({ user }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [performance, setPerformance] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const loadData = async () => {
    try {
      const res = await axios.get('/api/system/performance');
      setPerformance(res.data);
      setLoading(false);
      setRefreshing(false);
    } catch (error) {
      console.error('Failed to load performance data:', error);
      if (!loading) toast.error('Performans verileri yüklenemedi');
      setRefreshing(false);
    }
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <RefreshCw className="w-8 h-8 animate-spin text-blue-600" />
      </div>
    );
  }

  const { system, api_metrics, timeline, health_status } = performance || {};

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white p-4 sticky top-0 z-50 shadow-lg">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => navigate(-1)}
              className="text-white hover:bg-white/20 p-2"
            >
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <div>
              <h1 className="text-xl font-bold">Sistem Performansı</h1>
              <p className="text-xs text-blue-100">Real-time Monitoring</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Badge className={health_status === 'healthy' ? 'bg-green-500' : 'bg-orange-500'}>
              {health_status === 'healthy' ? 'Sağlıklı' : 'Dikkat'}
            </Badge>
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
        {/* System Resources */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Cpu className="w-4 h-4 text-blue-600" />
                CPU Kullanımı
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-blue-600">{system?.cpu_percent}%</div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div
                  className={`h-2 rounded-full ${
                    system?.cpu_percent > 80 ? 'bg-red-500' :
                    system?.cpu_percent > 60 ? 'bg-orange-500' : 'bg-green-500'
                  }`}
                  style={{ width: `${system?.cpu_percent}%` }}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Activity className="w-4 h-4 text-purple-600" />
                RAM Kullanımı
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-purple-600">{system?.memory_percent}%</div>
              <div className="text-xs text-gray-500 mt-1">
                {system?.memory_used_gb}GB / {system?.memory_total_gb}GB
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div
                  className={`h-2 rounded-full ${
                    system?.memory_percent > 80 ? 'bg-red-500' :
                    system?.memory_percent > 60 ? 'bg-orange-500' : 'bg-purple-500'
                  }`}
                  style={{ width: `${system?.memory_percent}%` }}
                />
              </div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <HardDrive className="w-4 h-4 text-green-600" />
                Disk Kullanımı
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-green-600">{system?.disk_percent}%</div>
              <div className="text-xs text-gray-500 mt-1">
                {system?.disk_used_gb}GB / {system?.disk_total_gb}GB
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                <div
                  className="h-2 rounded-full bg-green-500"
                  style={{ width: `${system?.disk_percent}%` }}
                />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* API Metrics */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Zap className="w-4 h-4 text-yellow-600" />
                Ortalama Yanıt Süresi
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-yellow-600">
                {api_metrics?.avg_response_time_ms}ms
              </div>
              <div className="text-xs text-gray-500 mt-1">API Response Time</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <TrendingUp className="w-4 h-4 text-cyan-600" />
                İstek Oranı
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-cyan-600">
                {api_metrics?.requests_per_minute}
              </div>
              <div className="text-xs text-gray-500 mt-1">Requests/Minute</div>
            </CardContent>
          </Card>

          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-sm flex items-center gap-2">
                <Server className="w-4 h-4 text-indigo-600" />
                Toplam İstek
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-3xl font-bold text-indigo-600">
                {api_metrics?.total_requests_tracked}
              </div>
              <div className="text-xs text-gray-500 mt-1">Tracked Requests</div>
            </CardContent>
          </Card>
        </div>

        {/* Timeline Chart */}
        {timeline && timeline.length > 0 && (
          <Card>
            <CardHeader>
              <CardTitle className="text-sm">İstek Grafiği (Son 10 Dakika)</CardTitle>
            </CardHeader>
            <CardContent>
              <ResponsiveContainer width="100%" height={200}>
                <LineChart data={timeline}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="timestamp" tick={{ fontSize: 10 }} />
                  <YAxis tick={{ fontSize: 10 }} />
                  <Tooltip />
                  <Legend />
                  <Line type="monotone" dataKey="requests" stroke="#3b82f6" name="İstek Sayısı" />
                  <Line type="monotone" dataKey="avg_response_time" stroke="#f59e0b" name="Ort. Yanıt (ms)" />
                </LineChart>
              </ResponsiveContainer>
            </CardContent>
          </Card>
        )}

        {/* Endpoint Performance Table */}
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">En Yavaş Endpoint'ler</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {api_metrics?.endpoints?.map((endpoint, idx) => (
                <div key={idx} className="flex justify-between items-center p-2 bg-gray-50 rounded">
                  <div className="flex-1">
                    <div className="font-mono text-xs truncate">{endpoint.endpoint}</div>
                    <div className="text-xs text-gray-500">{endpoint.count} requests</div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-sm">{endpoint.avg_duration_ms}ms</div>
                    <div className="text-xs text-gray-500">
                      {endpoint.fastest_ms}ms - {endpoint.slowest_ms}ms
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default SystemPerformanceMonitor;