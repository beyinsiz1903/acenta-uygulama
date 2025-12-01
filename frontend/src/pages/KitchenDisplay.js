import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  Home,
  Clock,
  CheckCircle,
  AlertTriangle,
  RefreshCw,
  PlugZap,
  Filter
} from 'lucide-react';
import { toast } from 'sonner';
import { useWebSocket, websocket } from '@/lib/websocket';

const KitchenDisplay = () => {
  const navigate = useNavigate();
  const [orders, setOrders] = useState([]);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [stationFilter, setStationFilter] = useState('all');
  const [statusFilter, setStatusFilter] = useState('active');
  const [lastUpdate, setLastUpdate] = useState(null);
  const { isConnected } = useWebSocket('kitchen');

  useEffect(() => {
    loadOrders();
    if (autoRefresh) {
      const interval = setInterval(loadOrders, 5000);
      return () => clearInterval(interval);
    }
  }, [autoRefresh]);

  useEffect(() => {
    const unsubscribe = websocket.on('kitchen_orders', (payload) => {
      if (!payload) return;
      setOrders(payload.orders || []);
      setLastUpdate(payload.timestamp || new Date().toISOString());
    });
    return () => {
      if (unsubscribe) unsubscribe();
    };
  }, []);

  const loadOrders = async () => {
    try {
      const response = await axios.get('/fnb/kitchen-display');
      setOrders(response.data.orders || []);
      setLastUpdate(new Date().toISOString());
    } catch (error) {
      console.error('Orders yüklenemedi');
    }
  };

  const updateOrderStatus = async (orderId, status) => {
    try {
      await axios.put(`/fnb/kitchen-order/${orderId}/status`, null, {
        params: { status },
      });
      toast.success(`✓ Sipariş ${status}`);
    } catch (error) {
      toast.error('Hata');
    }
  };

  const completeOrder = async (orderId) => {
    try {
      await axios.post(`/fnb/kitchen-order/${orderId}/complete`);
      toast.success('✓ Sipariş hazır!');
      loadOrders();
    } catch (error) {
      toast.error('Hata');
    }
  };

  const getElapsedTime = (orderedAt) => {
    const now = new Date();
    const ordered = new Date(orderedAt);
    const diff = Math.floor((now - ordered) / 1000 / 60);
    return diff;
  };

  const getPriorityColor = (priority) => {
    return priority === 'urgent' ? 'from-red-500 to-red-600' :
           priority === 'high' ? 'from-orange-500 to-orange-600' :
           'from-blue-500 to-blue-600';
  };

  const stationOptions = useMemo(() => {
    const stations = new Set();
    orders.forEach((order) =>
      order.items?.forEach((item) => item.station && stations.add(item.station))
    );
    return Array.from(stations);
  }, [orders]);

  const filteredOrders = useMemo(() => {
    return orders.filter((order) => {
      const stationMatch =
        stationFilter === 'all' ||
        order.items?.some((item) => item.station === stationFilter);
      const statusMatch =
        statusFilter === 'active'
          ? ['pending', 'preparing'].includes(order.status || 'pending')
          : statusFilter === 'ready'
          ? order.status === 'ready'
          : true;
      return stationMatch && statusMatch;
    });
  }, [orders, stationFilter, statusFilter]);

  const urgentOrders = useMemo(() => {
    return orders
      .filter((order) => {
        const elapsed = getElapsedTime(order.ordered_at);
        return elapsed > 12 || order.priority === 'urgent';
      })
      .slice(0, 4);
  }, [orders]);

  return (
    <div className="min-h-screen bg-gray-900 text-white">
      {/* Header */}
      <div className="bg-gradient-to-r from-orange-600 to-red-600 p-6 sticky top-0 z-50 shadow-2xl">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Button variant="ghost" size="icon" onClick={() => navigate('/')} className="text-white hover:bg-white/20">
              <Home className="w-6 h-6" />
            </Button>
            <div>
              <h1 className="text-3xl font-bold">🍳 Kitchen Display</h1>
              <p className="text-sm text-orange-100">Real-time Order Management</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <div className="text-right">
              <p className="text-sm text-orange-100">Aktif Sipariş</p>
              <p className="text-3xl font-bold">{filteredOrders.length}</p>
              <p className="text-xs text-orange-100">
                Güncelleme: {lastUpdate ? new Date(lastUpdate).toLocaleTimeString('tr-TR') : '--'}
              </p>
            </div>
            <Badge className={isConnected ? 'bg-green-500' : 'bg-gray-500'}>
              <PlugZap className="w-3 h-3 mr-1" />
              {isConnected ? 'Live' : 'Polling'}
            </Badge>
            <Button 
              variant="ghost" 
              size="icon"
              onClick={() => setAutoRefresh(!autoRefresh)}
              className="text-white hover:bg-white/20"
            >
              <RefreshCw className={`w-6 h-6 ${autoRefresh ? 'animate-spin' : ''}`} />
            </Button>
          </div>
        </div>
      </div>

      {/* Filters */}
      <div className="p-6 pt-0 flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2">
          <Filter className="w-4 h-4 text-gray-400" />
          <Button
            variant={statusFilter === 'active' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter('active')}
          >
            Aktif
          </Button>
          <Button
            variant={statusFilter === 'ready' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter('ready')}
          >
            Ready
          </Button>
          <Button
            variant={statusFilter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStatusFilter('all')}
          >
            Tümü
          </Button>
        </div>
        <div className="flex items-center gap-2">
          <p className="text-xs uppercase tracking-wide text-gray-400">Station</p>
          <Button
            variant={stationFilter === 'all' ? 'default' : 'outline'}
            size="sm"
            onClick={() => setStationFilter('all')}
          >
            Hepsi
          </Button>
          {stationOptions.map((station) => (
            <Button
              key={station}
              variant={stationFilter === station ? 'default' : 'outline'}
              size="sm"
              onClick={() => setStationFilter(station)}
            >
              {station}
            </Button>
          ))}
        </div>
      </div>

      {/* Urgent Rail */}
      {urgentOrders.length > 0 && (
        <div className="px-6">
          <div className="bg-red-900/30 border border-red-700 rounded-xl p-4 mb-4">
            <div className="flex items-center gap-2 mb-3">
              <AlertTriangle className="w-5 h-5 text-red-400" />
              <p className="font-semibold text-red-100">Acil Siparişler</p>
            </div>
            <div className="flex gap-3 overflow-x-auto pb-2">
              {urgentOrders.map((order) => (
                <div
                  key={order.id}
                  className="min-w-[180px] bg-red-700/50 rounded-lg p-3 text-sm"
                >
                  <p className="font-bold text-white text-lg">#{order.order_number}</p>
                  <p className="text-xs text-red-100">
                    {getElapsedTime(order.ordered_at)} dk
                  </p>
                  <p className="text-xs text-red-200 mt-1">
                    {order.table_number ? `Masa ${order.table_number}` : `Oda ${order.room_number}`}
                  </p>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Orders Grid */}
      <div className="p-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {filteredOrders.length === 0 ? (
          <div className="col-span-full text-center py-20">
            <CheckCircle className="w-24 h-24 text-green-500 mx-auto mb-4" />
            <p className="text-2xl text-gray-400">Tüm siparişler tamamlandı!</p>
          </div>
        ) : (
          filteredOrders.map((order) => {
            const elapsed = getElapsedTime(order.ordered_at);
            const isUrgent = elapsed > 15 || order.priority === 'urgent';
            
            return (
              <Card 
                key={order.id} 
                className={`bg-gradient-to-br ${getPriorityColor(order.priority)} border-4 ${
                  isUrgent ? 'border-red-500 animate-pulse' : 'border-gray-700'
                } transform hover:scale-105 transition-all`}
              >
                <CardContent className="p-6">
                  {/* Order Header */}
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-4xl font-bold">#{order.order_number}</p>
                      <p className="text-sm text-white/80">
                        {order.table_number ? `Masa ${order.table_number}` : `Oda ${order.room_number}`}
                      </p>
                    </div>
                    <div className="text-right">
                      <div className="flex items-center gap-2">
                        <Clock className="w-5 h-5" />
                        <span className="text-3xl font-bold">{elapsed}dk</span>
                      </div>
                      {isUrgent && (
                        <Badge className="mt-1 bg-red-600 text-white border-0">
                          ACİL!
                        </Badge>
                      )}
                    </div>
                  </div>

                  {/* Order Items */}
                  <div className="space-y-3 mb-4">
                    {order.items?.map((item, idx) => (
                      <div key={idx} className="bg-white/10 backdrop-blur-sm rounded-lg p-3">
                        <div className="flex items-center justify-between">
                          <div>
                            <p className="text-xl font-bold">{item.quantity}x {item.name}</p>
                            {item.notes && (
                              <p className="text-sm text-yellow-200 mt-1">⚠️ {item.notes}</p>
                            )}
                            {item.modifications && item.modifications.length > 0 && (
                              <div className="mt-1 space-y-1">
                                {item.modifications.map((mod, i) => (
                                  <p key={i} className="text-xs text-orange-200">+ {mod}</p>
                                ))}
                              </div>
                            )}
                          </div>
                          <div className="flex flex-col items-end gap-1">
                            {item.station && (
                              <Badge className="bg-white/20 text-white border-0">
                                {item.station}
                              </Badge>
                            )}
                            {order.status === 'pending' && (
                              <Button
                                size="sm"
                                variant="secondary"
                                className="text-xs px-2 py-1"
                                onClick={() => updateOrderStatus(order.id, 'preparing')}
                              >
                                Başlat
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Complete Button */}
                  {order.status !== 'ready' ? (
                    <Button 
                      className="w-full h-16 text-xl font-bold bg-green-600 hover:bg-green-700"
                      onClick={() => completeOrder(order.id)}
                    >
                      ✓ SİPARİŞ HAZIR
                    </Button>
                  ) : (
                    <Button 
                      className="w-full h-16 text-xl font-bold bg-blue-600 hover:bg-blue-700"
                      onClick={() => updateOrderStatus(order.id, 'served')}
                    >
                      SERVİS EDİLDİ
                    </Button>
                  )}
                </CardContent>
              </Card>
            );
          })
        )}
      </div>
    </div>
  );
};

export default KitchenDisplay;