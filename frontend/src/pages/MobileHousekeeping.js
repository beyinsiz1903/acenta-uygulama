import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog';
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from '@/components/ui/collapsible';
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
  Plus,
  ChevronDown,
  ChevronRight
} from 'lucide-react';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
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
  const [filterStatus, setFilterStatus] = useState('all');
  const [allRooms, setAllRooms] = useState([]);
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [pendingStatusChange, setPendingStatusChange] = useState(null);
  const [openCategories, setOpenCategories] = useState({
    dirty: false,
    cleaning: false,
    inspected: false,
    available: false,
    dueOut: false,
    arrivals: false
  });
  const [selectedRooms, setSelectedRooms] = useState([]);
  const [bulkUpdateMode, setBulkUpdateMode] = useState(false);
  const [filterStaff, setFilterStaff] = useState('all');
  const [cleaningRequests, setCleaningRequests] = useState([]);
  const [cleaningRequestsExpanded, setCleaningRequestsExpanded] = useState(true);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const [statusRes, dueOutRes, stayoverRes, arrivalRes, perfRes, cleaningReqRes] = await Promise.all([
        axios.get('/housekeeping/room-status'),
        axios.get('/housekeeping/due-out'),
        axios.get('/housekeeping/stayovers'),
        axios.get('/housekeeping/arrivals'),
        axios.get('/housekeeping/staff-performance-table'),
        axios.get('/housekeeping/cleaning-requests?status=pending').catch(() => ({ data: { requests: [] } }))
      ]);

      setRoomStatus(statusRes.data);
      setDueOut(dueOutRes.data.due_out_rooms || []);
      setStayovers(stayoverRes.data.stayover_rooms || []);
      setArrivals(arrivalRes.data.arrival_rooms || []);
      setStaffPerformance(perfRes.data);
      setCleaningRequests(cleaningReqRes.data.categories?.pending || []);
      
      // Get all rooms for filtering
      const roomsRes = await axios.get('/pms/rooms');
      setAllRooms(roomsRes.data || []);
    } catch (error) {
      console.error('Failed to load housekeeping data:', error);
      toast.error('✗ Yükleme');
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleCleaningRequestStatus = async (requestId, newStatus) => {
    try {
      await axios.put(`/housekeeping/cleaning-request/${requestId}/status`, null, {
        params: { status: newStatus }
      });
      toast.success(`Talep ${newStatus === 'in_progress' ? 'başlatıldı' : 'tamamlandı'}`);
      loadData(); // Reload data
    } catch (error) {
      toast.error('İşlem başarısız');
    }
  };

  const getFilteredRooms = () => {
    if (filterStatus === 'all') return allRooms;
    return allRooms.filter(room => room.status === filterStatus);
  };

  const toggleCategory = (category) => {
    setOpenCategories(prev => ({
      ...prev,
      [category]: !prev[category]
    }));
  };

  const getRoomsByStatus = (status) => {
    return allRooms.filter(room => room.status === status);
  };

  const handleRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const handleQuickStatusUpdate = async (roomId, newStatus) => {
    try {
      await axios.put(`/housekeeping/room/${roomId}/status`, { new_status: newStatus });
      toast.success('✓ Güncellendi');
      loadData();
    } catch (error) {
      toast.error('✗ Hata');
    }
  };

  const loadLostFound = async () => {
    try {
      const res = await axios.get('/housekeeping/lost-found/items');
      setLostFoundItems(res.data.items || []);
      setLostFoundModalOpen(true);
    } catch (error) {
      toast.error('✗ Kayıp Eşya');
    }
  };

  const loadInventory = async () => {
    try {
      const res = await axios.get('/housekeeping/inventory');
      setInventoryItems(res.data.inventory_items || []);
      setInventoryModalOpen(true);
    } catch (error) {
      toast.error('✗ Envanter');
    }
  };

  const loadTaskAssignments = async () => {
    try {
      const res = await axios.get('/housekeeping/task-assignments');
      setTaskAssignments(res.data.assignments || []);
      setTaskAssignmentsModalOpen(true);
    } catch (error) {
      toast.error('✗ Görev');
    }
  };

  const loadStatusLogs = async () => {
    try {
      const res = await axios.get('/housekeeping/status-change-logs');
      setStatusLogs(res.data.logs || []);
      setStatusLogsModalOpen(true);
    } catch (error) {
      toast.error('✗ Kayıt');
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
      toast.success('✓ Kaydedildi');
      loadLostFound();
    } catch (error) {
      toast.error('✗ Hata');
    }
  };

  const handleStatusChangeRequest = (roomId, roomNumber, currentStatus, newStatus) => {
    setPendingStatusChange({ roomId, roomNumber, currentStatus, newStatus });
    setConfirmDialogOpen(true);
  };

  const confirmStatusChange = async () => {
    if (!pendingStatusChange) return;
    
    try {
      await axios.put(`/housekeeping/room/${pendingStatusChange.roomId}/status?new_status=${pendingStatusChange.newStatus}`);
      toast.success(`✓ Oda ${pendingStatusChange.roomNumber}`);
      loadData(); // Reload data
      setConfirmDialogOpen(false);
      setPendingStatusChange(null);
    } catch (error) {
      console.error('Status update error:', error);
      toast.error('✗ Hata');
      setConfirmDialogOpen(false);
    }
  };

  const cancelStatusChange = () => {
    setConfirmDialogOpen(false);
    setPendingStatusChange(null);
  };

  const toggleRoomSelection = (roomId) => {
    setSelectedRooms(prev => 
      prev.includes(roomId) ? prev.filter(id => id !== roomId) : [...prev, roomId]
    );
  };

  const handleBulkStatusUpdate = async (newStatus) => {
    if (selectedRooms.length === 0) {
      toast.error('⚠️ Oda seçin');
      return;
    }

    try {
      await Promise.all(
        selectedRooms.map(roomId => 
          axios.put(`/housekeeping/room/${roomId}/status?new_status=${newStatus}`)
        )
      );
      toast.success(`✓ ${selectedRooms.length} oda güncellendi`);
      setSelectedRooms([]);
      setBulkUpdateMode(false);
      loadData();
    } catch (error) {
      toast.error('✗ Toplu güncelleme hatası');
    }
  };

  const getActionText = (currentStatus, newStatus) => {
    if (currentStatus === 'dirty' && newStatus === 'cleaning') {
      return 'Başla';
    } else if (currentStatus === 'cleaning' && newStatus === 'inspected') {
      return 'Tamamla';
    } else if (currentStatus === 'inspected' && newStatus === 'available') {
      return 'Müsait';
    } else if (currentStatus === 'available' && newStatus === 'dirty') {
      return 'Kirli';
    }
    return 'Onayla';
  };

  const getActionDescription = (roomNumber, currentStatus, newStatus) => {
    if (currentStatus === 'available' && newStatus === 'dirty') {
      return `${roomNumber} → Kirli`;
    } else if (currentStatus === 'dirty' && newStatus === 'cleaning') {
      return `${roomNumber} → Temizleniyor`;
    } else if (currentStatus === 'cleaning' && newStatus === 'inspected') {
      return `${roomNumber} → Kontrol`;
    } else if (currentStatus === 'inspected' && newStatus === 'available') {
      return `${roomNumber} → Müsait`;
    }
    return `Oda ${roomNumber}`;
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
        {/* Bulk Action Controls */}
        {bulkUpdateMode ? (
          <Card className="bg-purple-50 border-purple-200">
            <CardContent className="p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-bold text-purple-700">
                  {selectedRooms.length} oda seçildi
                </span>
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => {
                    setBulkUpdateMode(false);
                    setSelectedRooms([]);
                  }}
                  className="h-7 text-xs"
                >
                  İptal
                </Button>
              </div>
              <div className="grid grid-cols-4 gap-2">
                <Button
                  size="sm"
                  className="h-8 text-xs bg-yellow-600 hover:bg-yellow-700"
                  onClick={() => handleBulkStatusUpdate('cleaning')}
                >
                  🧹 Başla
                </Button>
                <Button
                  size="sm"
                  className="h-8 text-xs bg-blue-600 hover:bg-blue-700"
                  onClick={() => handleBulkStatusUpdate('inspected')}
                >
                  ✓ Kontrol
                </Button>
                <Button
                  size="sm"
                  className="h-8 text-xs bg-green-600 hover:bg-green-700"
                  onClick={() => handleBulkStatusUpdate('available')}
                >
                  ✓ Müsait
                </Button>
                <Button
                  size="sm"
                  className="h-8 text-xs bg-red-600 hover:bg-red-700"
                  onClick={() => handleBulkStatusUpdate('dirty')}
                >
                  🔴 Kirli
                </Button>
              </div>
            </CardContent>
          </Card>
        ) : (
          <Button
            size="sm"
            className="w-full h-10 bg-purple-600 hover:bg-purple-700"
            onClick={() => setBulkUpdateMode(true)}
          >
            📋 Toplu İşlem Modu
          </Button>
        )}

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

        {/* Due Out Today - Collapsible */}
        {dueOut.length > 0 && (
          <Collapsible open={openCategories.dueOut} onOpenChange={() => setOpenCategories({...openCategories, dueOut: !openCategories.dueOut})}>
            <Card>
              <CollapsibleTrigger className="w-full">
                <CardHeader className="pb-3 cursor-pointer hover:bg-gray-50 transition-colors">
                  <CardTitle className="text-lg flex items-center justify-between">
                    <div className="flex items-center">
                      <AlertCircle className="w-5 h-5 mr-2 text-orange-600" />
                      Bugün Çıkış Yapacaklar ({dueOut.filter(r => r.is_today).length})
                    </div>
                    {openCategories.dueOut ? (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    )}
                  </CardTitle>
                </CardHeader>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <CardContent className="space-y-2">
                  {dueOut.filter(r => r.is_today).map((room) => (
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
              </CollapsibleContent>
            </Card>
          </Collapsible>
        )}

        {/* Arrivals Today - Collapsible */}
        {arrivals.length > 0 && (
          <Collapsible open={openCategories.arrivals} onOpenChange={() => setOpenCategories({...openCategories, arrivals: !openCategories.arrivals})}>
            <Card>
              <CollapsibleTrigger className="w-full">
                <CardHeader className="pb-3 cursor-pointer hover:bg-gray-50 transition-colors">
                  <CardTitle className="text-lg flex items-center justify-between">
                    <div className="flex items-center">
                      <Users className="w-5 h-5 mr-2 text-green-600" />
                      Bugün Gelenler - Hazır Odalar ({arrivals.filter(r => r.ready).length}/{arrivals.length})
                    </div>
                    {openCategories.arrivals ? (
                      <ChevronDown className="w-5 h-5 text-gray-400" />
                    ) : (
                      <ChevronRight className="w-5 h-5 text-gray-400" />
                    )}
                  </CardTitle>
                </CardHeader>
              </CollapsibleTrigger>
              <CollapsibleContent>
                <CardContent className="space-y-2">
                  {arrivals.map((room) => (
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
              </CollapsibleContent>
            </Card>
          </Collapsible>
        )}

        {/* All Rooms - Categorized with Collapsible */}
        <div className="space-y-3">
          {/* Dirty Rooms */}
          {getRoomsByStatus('dirty').length > 0 && (
            <Collapsible open={openCategories.dirty} onOpenChange={() => toggleCategory('dirty')}>
              <Card>
                <CollapsibleTrigger className="w-full">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between w-full">
                      <div className="flex items-center">
                        <span className="text-2xl mr-2">🔴</span>
                        <div className="text-left">
                          <p className="font-bold text-gray-900">Kirli Odalar</p>
                          <p className="text-xs text-gray-500">{getRoomsByStatus('dirty').length} oda</p>
                        </div>
                      </div>
                      {openCategories.dirty ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                    </div>
                  </CardHeader>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <CardContent className="space-y-2 pt-0">
                    {getRoomsByStatus('dirty').map((room) => (
                      <div key={room.id} className="p-2 bg-red-50 rounded-lg border border-red-200">
                        <div className="flex items-center justify-between">
                          {bulkUpdateMode && (
                            <input
                              type="checkbox"
                              checked={selectedRooms.includes(room.id)}
                              onChange={() => toggleRoomSelection(room.id)}
                              className="mr-2 w-5 h-5"
                            />
                          )}
                          <div className="flex-1">
                            <p className="font-bold text-sm">Oda {room.room_number}</p>
                            <p className="text-xs text-gray-500">{room.room_type}</p>
                          </div>
                          {!bulkUpdateMode && (
                            <Button
                              size="sm"
                              className="h-7 text-xs px-3 bg-yellow-600 hover:bg-yellow-700"
                              onClick={() => handleStatusChangeRequest(room.id, room.room_number, room.status, getNextStatus(room.status))}
                            >
                              🧹 Başla
                            </Button>
                          )}
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </CollapsibleContent>
              </Card>
            </Collapsible>
          )}

          {/* Cleaning Rooms */}
          {getRoomsByStatus('cleaning').length > 0 && (
            <Collapsible open={openCategories.cleaning} onOpenChange={() => toggleCategory('cleaning')}>
              <Card>
                <CollapsibleTrigger className="w-full">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between w-full">
                      <div className="flex items-center">
                        <span className="text-2xl mr-2">🟡</span>
                        <div className="text-left">
                          <p className="font-bold text-gray-900">Temizleniyor</p>
                          <p className="text-xs text-gray-500">{getRoomsByStatus('cleaning').length} oda</p>
                        </div>
                      </div>
                      {openCategories.cleaning ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                    </div>
                  </CardHeader>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <CardContent className="space-y-2 pt-0">
                    {getRoomsByStatus('cleaning').map((room) => (
                      <div key={room.id} className="p-2 bg-yellow-50 rounded-lg border border-yellow-200">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <p className="font-bold text-sm">Oda {room.room_number}</p>
                            <p className="text-xs text-gray-500">{room.room_type}</p>
                          </div>
                          <Button
                            size="sm"
                            className="h-7 text-xs px-3 bg-green-600 hover:bg-green-700"
                            onClick={() => handleStatusChangeRequest(room.id, room.room_number, room.status, getNextStatus(room.status))}
                          >
                            ✓ Temizlendi
                          </Button>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </CollapsibleContent>
              </Card>
            </Collapsible>
          )}

          {/* Inspected Rooms */}
          {getRoomsByStatus('inspected').length > 0 && (
            <Collapsible open={openCategories.inspected} onOpenChange={() => toggleCategory('inspected')}>
              <Card>
                <CollapsibleTrigger className="w-full">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between w-full">
                      <div className="flex items-center">
                        <span className="text-2xl mr-2">🔵</span>
                        <div className="text-left">
                          <p className="font-bold text-gray-900">Kontrol Edildi</p>
                          <p className="text-xs text-gray-500">{getRoomsByStatus('inspected').length} oda</p>
                        </div>
                      </div>
                      {openCategories.inspected ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                    </div>
                  </CardHeader>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <CardContent className="space-y-2 pt-0">
                    {getRoomsByStatus('inspected').map((room) => (
                      <div key={room.id} className="p-2 bg-blue-50 rounded-lg border border-blue-200">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <p className="font-bold text-sm">Oda {room.room_number}</p>
                            <p className="text-xs text-gray-500">{room.room_type}</p>
                          </div>
                          <Button
                            size="sm"
                            className="h-7 text-xs px-3 bg-blue-600 hover:bg-blue-700"
                            onClick={() => handleStatusChangeRequest(room.id, room.room_number, room.status, getNextStatus(room.status))}
                          >
                            ✓ Müsait Yap
                          </Button>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </CollapsibleContent>
              </Card>
            </Collapsible>
          )}

          {/* Available Rooms */}
          {getRoomsByStatus('available').length > 0 && (
            <Collapsible open={openCategories.available} onOpenChange={() => toggleCategory('available')}>
              <Card>
                <CollapsibleTrigger className="w-full">
                  <CardHeader className="pb-3">
                    <div className="flex items-center justify-between w-full">
                      <div className="flex items-center">
                        <span className="text-2xl mr-2">🟢</span>
                        <div className="text-left">
                          <p className="font-bold text-gray-900">Müsait Odalar</p>
                          <p className="text-xs text-gray-500">{getRoomsByStatus('available').length} oda</p>
                        </div>
                      </div>
                      {openCategories.available ? <ChevronDown className="w-5 h-5" /> : <ChevronRight className="w-5 h-5" />}
                    </div>
                  </CardHeader>
                </CollapsibleTrigger>
                <CollapsibleContent>
                  <CardContent className="space-y-2 pt-0">
                    {getRoomsByStatus('available').map((room) => (
                      <div key={room.id} className="p-2 bg-green-50 rounded-lg border border-green-200">
                        <div className="flex items-center justify-between">
                          <div className="flex-1">
                            <p className="font-bold text-sm">Oda {room.room_number}</p>
                            <p className="text-xs text-gray-500">{room.room_type}</p>
                          </div>
                          <Button
                            size="sm"
                            className="h-7 text-xs px-3 bg-red-600 hover:bg-red-700"
                            onClick={() => handleStatusChangeRequest(room.id, room.room_number, room.status, getNextStatus(room.status))}
                          >
                            🧹 Kirli
                          </Button>
                        </div>
                      </div>
                    ))}
                  </CardContent>
                </CollapsibleContent>
              </Card>
            </Collapsible>
          )}
        </div>

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

        {/* Quick Actions - Compact */}
        <div className="grid grid-cols-4 gap-2">
          <Button
            size="sm"
            className="h-16 flex flex-col items-center justify-center bg-orange-600 hover:bg-orange-700 p-1"
            onClick={loadLostFound}
          >
            <Search className="w-4 h-4 mb-1" />
            <span className="text-[10px]">Kayıp Eşya</span>
          </Button>
          <Button
            size="sm"
            className="h-16 flex flex-col items-center justify-center bg-green-600 hover:bg-green-700 p-1"
            onClick={loadInventory}
          >
            <Package className="w-4 h-4 mb-1" />
            <span className="text-[10px]">Envanter</span>
          </Button>
          <Button
            size="sm"
            className="h-16 flex flex-col items-center justify-center bg-purple-600 hover:bg-purple-700 p-1"
            onClick={loadTaskAssignments}
          >
            <MapPin className="w-4 h-4 mb-1" />
            <span className="text-[10px]">Görev</span>
          </Button>
          <Button
            size="sm"
            className="h-16 flex flex-col items-center justify-center bg-blue-600 hover:bg-blue-700 p-1"
            onClick={loadStatusLogs}
          >
            <History className="w-4 h-4 mb-1" />
            <span className="text-[10px]">Kayıt</span>
          </Button>
        </div>
      </div>

      {/* Lost & Found Modal */}
      <Dialog open={lostFoundModalOpen} onOpenChange={setLostFoundModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center justify-between">
              <span>🔍 Kayıp Eşya ({lostFoundItems.length})</span>
              <Dialog>
                <DialogTrigger asChild>
                  <Button size="sm" className="bg-orange-600">
                    <Plus className="w-4 h-4 mr-1" />
                    Yeni Kayıt
                  </Button>
                </DialogTrigger>
                <DialogContent>
                  <DialogHeader>
                    <DialogTitle>Kayıp Eşya Kaydı</DialogTitle>
                  </DialogHeader>
                  <form onSubmit={(e) => {
                    e.preventDefault();
                    handleCreateLostFound(new FormData(e.target));
                  }}>
                    <div className="space-y-3">
                      <div>
                        <Label>Eşya Tanımı *</Label>
                        <Input name="item_description" required />
                      </div>
                      <div>
                        <Label>Bulunduğu Yer *</Label>
                        <Input name="location_found" required />
                      </div>
                      <div>
                        <Label>Bulan Kişi *</Label>
                        <Input name="found_by" required />
                      </div>
                      <div>
                        <Label>Kategori</Label>
                        <select name="category" className="w-full p-2 border rounded">
                          <option value="electronics">Elektronik</option>
                          <option value="jewelry">Takı</option>
                          <option value="clothing">Giysi</option>
                          <option value="documents">Evrak</option>
                          <option value="other">Diğer</option>
                        </select>
                      </div>
                      <div>
                        <Label>Oda Numarası</Label>
                        <Input name="room_number" />
                      </div>
                      <div>
                        <Label>Notlar</Label>
                        <Textarea name="notes" rows={3} />
                      </div>
                      <Button type="submit" className="w-full">Kaydet</Button>
                    </div>
                  </form>
                </DialogContent>
              </Dialog>
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            {lostFoundItems.map((item) => (
              <Card key={item.id} className="border">
                <CardContent className="p-3">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <p className="font-bold text-gray-900">{item.item_description}</p>
                      <p className="text-sm text-gray-600">
                        📍 {item.location_found} • Oda {item.room_number || 'N/A'}
                      </p>
                      <p className="text-xs text-gray-500">
                        Bulan: {item.found_by} • {new Date(item.found_date).toLocaleDateString('tr-TR')}
                      </p>
                    </div>
                    <Badge className={{
                      'unclaimed': 'bg-orange-500',
                      'claimed': 'bg-green-500',
                      'disposed': 'bg-gray-500'
                    }[item.status]}>
                      {item.status}
                    </Badge>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* Inventory Modal */}
      <Dialog open={inventoryModalOpen} onOpenChange={setInventoryModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>📦 Envanter ({inventoryItems.length})</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            {inventoryItems.map((item) => (
              <Card key={item.id} className={`border ${item.is_low_stock ? 'border-red-300 bg-red-50' : ''}`}>
                <CardContent className="p-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-bold text-gray-900">{item.name}</p>
                    <Badge>{item.category}</Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-2 text-sm">
                    <div>
                      <p className="text-gray-600">Stok:</p>
                      <p className={`font-bold ${item.is_low_stock ? 'text-red-600' : 'text-green-600'}`}>
                        {item.current_stock} {item.unit}
                      </p>
                    </div>
                    <div>
                      <p className="text-gray-600">Minimum:</p>
                      <p className="font-bold">{item.minimum_stock}</p>
                    </div>
                    <div>
                      <p className="text-gray-600">Birim Fiyat:</p>
                      <p className="font-bold">₺{item.unit_cost}</p>
                    </div>
                  </div>
                  {item.is_low_stock && (
                    <div className="mt-2 p-2 bg-red-100 rounded text-xs text-red-700">
                      ⚠️ Düşük stok uyarısı! Yeniden sipariş gerekli.
                    </div>
                  )}
                </CardContent>
              </Card>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* Task Assignments Modal */}
      <Dialog open={taskAssignmentsModalOpen} onOpenChange={setTaskAssignmentsModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>🗺️ Görev Dağılımı ({taskAssignments.length} Personel)</DialogTitle>
          </DialogHeader>
          <div className="space-y-3">
            {taskAssignments.map((staff, idx) => (
              <Card key={idx} className="border">
                <CardContent className="p-3">
                  <div className="flex items-center justify-between mb-2">
                    <p className="font-bold text-gray-900">{staff.staff_name}</p>
                    <div className="flex space-x-2">
                      <Badge className="bg-green-500">{staff.completed} ✓</Badge>
                      <Badge className="bg-yellow-500">{staff.in_progress} ⏳</Badge>
                      <Badge className="bg-gray-500">{staff.pending} ⏸</Badge>
                    </div>
                  </div>
                  <div className="text-xs text-gray-600 mb-2">
                    Rota: {staff.route.join(' → ')}
                  </div>
                  <div className="space-y-1">
                    {staff.tasks.slice(0, 3).map((task, tidx) => (
                      <div key={tidx} className="flex items-center justify-between text-xs p-1 bg-gray-50 rounded">
                        <span>Oda {task.room_number}</span>
                        <Badge variant="outline" className="text-xs">{task.status}</Badge>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* Status Change Logs Modal */}
      <Dialog open={statusLogsModalOpen} onOpenChange={setStatusLogsModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>📝 Durum Değişim Kayıtları ({statusLogs.length})</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            {statusLogs.map((log) => (
              <Card key={log.log_id} className="border">
                <CardContent className="p-3">
                  <div className="flex items-center justify-between mb-1">
                    <p className="font-bold text-gray-900">Oda {log.room_number}</p>
                    <p className="text-xs text-gray-500">{new Date(log.timestamp).toLocaleString('tr-TR')}</p>
                  </div>
                  <div className="flex items-center space-x-2 text-sm">
                    <Badge variant="outline">{log.old_status}</Badge>
                    <span>→</span>
                    <Badge className="bg-blue-500">{log.new_status}</Badge>
                  </div>
                  <p className="text-xs text-gray-600 mt-1">
                    Değiştiren: {log.changed_by}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* Confirmation Dialog - Compact Mobile Design */}
      <AlertDialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <AlertDialogContent className="max-w-[85vw] p-4">
          <AlertDialogHeader className="space-y-2">
            <AlertDialogTitle className="text-base font-bold flex items-center space-x-2">
              <span className="text-2xl">
                {pendingStatusChange && (
                  pendingStatusChange.currentStatus === 'dirty' ? '🧹' :
                  pendingStatusChange.currentStatus === 'cleaning' ? '✓' :
                  pendingStatusChange.currentStatus === 'inspected' ? '🟢' : '🔴'
                )}
              </span>
              <span>
                {pendingStatusChange && getActionText(
                  pendingStatusChange.currentStatus, 
                  pendingStatusChange.newStatus
                )}
              </span>
            </AlertDialogTitle>
            <AlertDialogDescription className="text-sm font-medium text-gray-700">
              {pendingStatusChange && getActionDescription(
                pendingStatusChange.roomNumber,
                pendingStatusChange.currentStatus,
                pendingStatusChange.newStatus
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter className="flex flex-row space-x-2 mt-4">
            <AlertDialogCancel 
              onClick={cancelStatusChange} 
              className="flex-1 h-10 bg-gray-100 hover:bg-gray-200 text-gray-700 font-medium"
            >
              İptal
            </AlertDialogCancel>
            <AlertDialogAction 
              onClick={confirmStatusChange}
              className="flex-1 h-10 bg-green-600 hover:bg-green-700 text-white font-medium"
            >
              Onayla
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
};

export default MobileHousekeeping;
