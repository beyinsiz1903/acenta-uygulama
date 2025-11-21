import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  ArrowLeft, 
  Bed, 
  CheckCircle, 
  Clock, 
  Users,
  AlertCircle,
  TrendingUp,
  BarChart3,
  RefreshCw,
  Package,
  Search,
  MapPin,
  History,
  Plus
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';

const MobileHousekeeping = ({ user }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [roomStatus, setRoomStatus] = useState(null);
  const [dueOut, setDueOut] = useState([]);
  const [stayovers, setStayovers] = useState([]);
  const [arrivals, setArrivals] = useState([]);
  const [staffPerformance, setStaffPerformance] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [lostFoundModalOpen, setLostFoundModalOpen] = useState(false);
  const [inventoryModalOpen, setInventoryModalOpen] = useState(false);
  const [taskAssignmentsModalOpen, setTaskAssignmentsModalOpen] = useState(false);
  const [statusLogsModalOpen, setStatusLogsModalOpen] = useState(false);
  const [lostFoundItems, setLostFoundItems] = useState([]);
  const [inventoryItems, setInventoryItems] = useState([]);
  const [taskAssignments, setTaskAssignments] = useState([]);
  const [statusLogs, setStatusLogs] = useState([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statusRes, dueOutRes, stayoverRes, arrivalRes, perfRes] = await Promise.all([
        axios.get('/housekeeping/room-status'),
        axios.get('/housekeeping/due-out'),
        axios.get('/housekeeping/stayovers'),
        axios.get('/housekeeping/arrivals'),
        axios.get('/housekeeping/staff-performance-table')
      ]);

      setRoomStatus(statusRes.data);
      setDueOut(dueOutRes.data.due_out_rooms || []);
      setStayovers(stayoverRes.data.stayover_rooms || []);
      setArrivals(arrivalRes.data.arrival_rooms || []);
      setStaffPerformance(perfRes.data);
    } catch (error) {
      console.error('Failed to load housekeeping data:', error);
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

  const handleQuickStatusUpdate = async (roomId, newStatus) => {
    try {
      await axios.put(`/housekeeping/room/${roomId}/status`, { new_status: newStatus });
      toast.success(`Oda durumu güncellendi: ${newStatus}`);
      loadData();
    } catch (error) {
      toast.error('Durum güncellenemedi');
    }
  };

  const loadLostFound = async () => {
    try {
      const res = await axios.get('/housekeeping/lost-found/items');
      setLostFoundItems(res.data.items || []);
      setLostFoundModalOpen(true);
    } catch (error) {
      toast.error('Kayıp eşya listesi yüklenemedi');
    }
  };

  const loadInventory = async () => {
    try {
      const res = await axios.get('/housekeeping/inventory');
      setInventoryItems(res.data.inventory_items || []);
      setInventoryModalOpen(true);
    } catch (error) {
      toast.error('Envanter yüklenemedi');
    }
  };

  const loadTaskAssignments = async () => {
    try {
      const res = await axios.get('/housekeeping/task-assignments');
      setTaskAssignments(res.data.assignments || []);
      setTaskAssignmentsModalOpen(true);
    } catch (error) {
      toast.error('Görev dağılımı yüklenemedi');
    }
  };

  const loadStatusLogs = async () => {
    try {
      const res = await axios.get('/housekeeping/status-change-logs');
      setStatusLogs(res.data.logs || []);
      setStatusLogsModalOpen(true);
    } catch (error) {
      toast.error('Durum kayıtları yüklenemedi');
    }
  };

  const handleCreateLostFound = async (formData) => {
    try {
      await axios.post('/housekeeping/lost-found/item', {
        item_description: formData.get('item_description'),
        location_found: formData.get('location_found'),
        found_by: formData.get('found_by'),
        category: formData.get('category'),
        room_number: formData.get('room_number'),
        notes: formData.get('notes')
      });
      toast.success('Kayıp eşya kaydedildi!');
      loadLostFound();
    } catch (error) {
      toast.error('Kayıt oluşturulamadı');
    }
  };

  const getStatusColor = (status) => {
    const colors = {
      dirty: 'bg-red-100 text-red-700 border-red-300',
      cleaning: 'bg-yellow-100 text-yellow-700 border-yellow-300',
      inspected: 'bg-blue-100 text-blue-700 border-blue-300',
      available: 'bg-green-100 text-green-700 border-green-300',
      occupied: 'bg-purple-100 text-purple-700 border-purple-300',
      maintenance: 'bg-orange-100 text-orange-700 border-orange-300'
    };
    return colors[status] || 'bg-gray-100 text-gray-700 border-gray-300';
  };

  const getNextStatus = (currentStatus) => {
    const statusFlow = {
      dirty: 'cleaning',
      cleaning: 'inspected',
      inspected: 'available',
      available: 'dirty',
      occupied: 'dirty'
    };
    return statusFlow[currentStatus] || 'available';
  };

  const getStatusIcon = (status) => {
    switch(status) {
      case 'dirty': return '🟥';
      case 'cleaning': return '🟨';
      case 'inspected': return '🟦';
      case 'available': return '✅';
      case 'occupied': return '🟪';
      default: return '⬜';
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-600 mx-auto mb-2" />
          <p className="text-gray-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-gradient-to-r from-blue-600 to-blue-500 text-white p-4 sticky top-0 z-50 shadow-lg">
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
              <h1 className="text-xl font-bold">Temizlik Yönetimi</h1>
              <p className="text-xs text-blue-100">Housekeeping Dashboard</p>
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
          <Card className="bg-gradient-to-br from-red-50 to-red-100 border-red-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-red-600 font-medium">KİRLİ</p>
                  <p className="text-3xl font-bold text-red-700">{roomStatus?.status_counts?.dirty || 0}</p>
                </div>
                <AlertCircle className="w-10 h-10 text-red-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-green-600 font-medium">HAZIR</p>
                  <p className="text-3xl font-bold text-green-700">{roomStatus?.status_counts?.available || 0}</p>
                </div>
                <CheckCircle className="w-10 h-10 text-green-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-blue-600 font-medium">KONTROL EDİLDİ</p>
                  <p className="text-3xl font-bold text-blue-700">{roomStatus?.status_counts?.inspected || 0}</p>
                </div>
                <Bed className="w-10 h-10 text-blue-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-yellow-50 to-yellow-100 border-yellow-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-yellow-600 font-medium">TEMİZLENİYOR</p>
                  <p className="text-3xl font-bold text-yellow-700">{roomStatus?.status_counts?.cleaning || 0}</p>
                </div>
                <Clock className="w-10 h-10 text-yellow-300" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Due Out Today */}
        {dueOut.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <AlertCircle className="w-5 h-5 mr-2 text-orange-600" />
                Bugün Çıkış Yapacaklar ({dueOut.filter(r => r.is_today).length})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {dueOut.filter(r => r.is_today).slice(0, 5).map((room) => (
                <div key={room.booking_id} className="flex items-center justify-between p-3 bg-orange-50 rounded-lg border border-orange-200">
                  <div>
                    <p className="font-bold text-gray-900">Oda {room.room_number}</p>
                    <p className="text-sm text-gray-600">{room.guest_name}</p>
                  </div>
                  <Badge variant="outline" className="bg-white">
                    {new Date(room.checkout_date).toLocaleTimeString('tr-TR', { hour: '2-digit', minute: '2-digit' })}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Arrivals Today */}
        {arrivals.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <Users className="w-5 h-5 mr-2 text-green-600" />
                Bugün Gelenler - Hazır Odalar ({arrivals.filter(r => r.ready).length}/{arrivals.length})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {arrivals.slice(0, 5).map((room) => (
                <div key={room.booking_id} className={`flex items-center justify-between p-3 rounded-lg border ${
                  room.ready ? 'bg-green-50 border-green-200' : 'bg-red-50 border-red-200'
                }`}>
                  <div>
                    <p className="font-bold text-gray-900">Oda {room.room_number}</p>
                    <p className="text-sm text-gray-600">{room.guest_name}</p>
                  </div>
                  <Badge className={room.ready ? 'bg-green-500' : 'bg-red-500'}>
                    {room.ready ? '✓ Hazır' : '✗ Hazır Değil'}
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* All Rooms List with Quick Status Change */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center">
              <BarChart3 className="w-5 h-5 mr-2 text-gray-600" />
              Tüm Odalar - Durum Değiştir ({roomStatus?.total_rooms || 0})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {roomStatus?.rooms?.map((room) => (
              <div key={room.id} className="p-3 bg-gray-50 rounded-lg border">
                <div className="flex items-center justify-between mb-2">
                  <div className="flex-1">
                    <p className="font-bold text-gray-900 flex items-center">
                      <span className="text-xl mr-2">{getStatusIcon(room.status)}</span>
                      Oda {room.room_number}
                    </p>
                    <p className="text-sm text-gray-600">{room.room_type}</p>
                  </div>
                  <Badge className={getStatusColor(room.status)}>
                    {room.status}
                  </Badge>
                </div>
                {room.status !== 'occupied' && (
                  <Button
                    size="sm"
                    className="w-full mt-2"
                    onClick={() => handleQuickStatusUpdate(room.id, getNextStatus(room.status))}
                  >
                    {room.status === 'dirty' && '🧹 Temizliğe Başla'}
                    {room.status === 'cleaning' && '✅ Kontrol için Hazır'}
                    {room.status === 'inspected' && '✅ Müsaite Aç'}
                    {room.status === 'available' && '🧹 Kirliye Çevir'}
                  </Button>
                )}
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Staff Performance */}
        {staffPerformance?.staff_performance && staffPerformance.staff_performance.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <TrendingUp className="w-5 h-5 mr-2 text-blue-600" />
                Personel Performansı
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {staffPerformance.staff_performance.slice(0, 5).map((staff, idx) => (
                <div key={idx} className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex-1">
                    <p className="font-bold text-gray-900">{staff.staff_name}</p>
                    <p className="text-sm text-gray-600">
                      {staff.total_tasks_completed} görev • Ortalama {staff.avg_duration_minutes.toFixed(0)} dk
                    </p>
                  </div>
                  <Badge variant="outline" className="bg-white">
                    {staff.performance_rating}⭐
                  </Badge>
                </div>
              ))}
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  );
};

export default MobileHousekeeping;
