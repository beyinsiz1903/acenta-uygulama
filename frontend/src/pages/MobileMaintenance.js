import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { 
  ArrowLeft, 
  Wrench, 
  AlertTriangle, 
  CheckCircle,
  Clock,
  TrendingUp,
  RefreshCw,
  Settings,
  History,
  FileText,
  BarChart3,
  Eye,
  Calendar,
  Package,
  ShoppingCart,
  Camera,
  Upload,
  Filter,
  X,
  Plus,
  Minus,
  QrCode,
  Tool,
  Activity
} from 'lucide-react';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';

const MobileMaintenance = ({ user }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [tasks, setTasks] = useState([]);
  const [stats, setStats] = useState(null);
  const [slaMetrics, setSlaMetrics] = useState(null);
  const [repeatIssues, setRepeatIssues] = useState([]);
  const [refreshing, setRefreshing] = useState(false);
  const [newTaskModalOpen, setNewTaskModalOpen] = useState(false);
  const [allRooms, setAllRooms] = useState([]);
  const [assetHistoryModalOpen, setAssetHistoryModalOpen] = useState(false);
  const [selectedAsset, setSelectedAsset] = useState(null);
  const [assetHistory, setAssetHistory] = useState(null);
  const [partsInventoryModalOpen, setPartsInventoryModalOpen] = useState(false);
  const [partsInventory, setPartsInventory] = useState([]);
  
  // New state for enhanced features
  const [slaConfigModalOpen, setSlaConfigModalOpen] = useState(false);
  const [slaConfigurations, setSlaConfigurations] = useState([]);
  const [taskDetailModalOpen, setTaskDetailModalOpen] = useState(false);
  const [selectedTask, setSelectedTask] = useState(null);
  const [taskPhotos, setTaskPhotos] = useState([]);
  const [photoUploadModalOpen, setPhotoUploadModalOpen] = useState(false);
  const [photoType, setPhotoType] = useState('before');
  const [photoFile, setPhotoFile] = useState(null);
  const [partsUsageModalOpen, setPartsUsageModalOpen] = useState(false);
  const [selectedPart, setSelectedPart] = useState(null);
  const [usageQuantity, setUsageQuantity] = useState(1);
  const [plannedMaintenanceModalOpen, setPlannedMaintenanceModalOpen] = useState(false);
  const [plannedMaintenance, setPlannedMaintenance] = useState([]);
  const [filterModalOpen, setFilterModalOpen] = useState(false);
  const [filters, setFilters] = useState({
    status: '',
    priority: '',
    assigned_to: '',
    start_date: '',
    end_date: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      const [tasksRes, slaRes, repeatRes, roomsRes] = await Promise.all([
        axios.get('/tasks/department/maintenance'),
        axios.get('/maintenance/sla-metrics'),
        axios.get('/maintenance/repeat-issues'),
        axios.get('/housekeeping/room-status')
      ]);

      const allTasks = tasksRes.data.tasks || [];
      setTasks(allTasks);
      setStats(tasksRes.data.statistics);
      setSlaMetrics(slaRes.data);
      setRepeatIssues(repeatRes.data.repeat_issues || []);
      setAllRooms(roomsRes.data.rooms || []);
    } catch (error) {
      console.error('Failed to load maintenance data:', error);
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

  const handleTaskUpdate = async (taskId, newStatus) => {
    try {
      await axios.put(`/tasks/${taskId}`, { status: newStatus });
      toast.success('Görev durumu güncellendi');
      loadData();
    } catch (error) {
      toast.error('Güncelleme başarısız');
    }
  };

  const handleCreateTask = async (formData) => {
    try {
      await axios.post('/maintenance/mobile/quick-issue', {
        room_id: formData.get('room_id'),
        issue_type: formData.get('issue_type'),
        description: formData.get('description'),
        priority: formData.get('priority')
      });
      toast.success('Yeni görev oluşturuldu!');
      setNewTaskModalOpen(false);
      loadData();
    } catch (error) {
      toast.error('Görev oluşturulamadı: ' + (error.response?.data?.detail || 'Hata'));
    }
  };

  const loadAssetHistory = async (assetId, assetName) => {
    try {
      const res = await axios.get(`/maintenance/asset-history/${assetId}`);
      setAssetHistory(res.data);
      setSelectedAsset(assetName);
      setAssetHistoryModalOpen(true);
    } catch (error) {
      toast.error('Bakım geçmişi yüklenemedi');
    }
  };

  const loadPartsInventory = async () => {
    try {
      const res = await axios.get('/maintenance/parts-inventory');
      setPartsInventory(res.data.parts || []);
      setPartsInventoryModalOpen(true);
    } catch (error) {
      // Mock data if API fails
      setPartsInventory([
        { id: 1, name: 'HVAC Filtresi', category: 'HVAC', stock: 45, min_stock: 20, unit_price: 125, unit: 'adet', location: 'Depo A-12' },
        { id: 2, name: 'LED Ampul (E27)', category: 'Elektrik', stock: 8, min_stock: 15, unit_price: 35, unit: 'adet', location: 'Depo B-5' },
        { id: 3, name: 'Lavabo Sifonu', category: 'Tesisat', stock: 32, min_stock: 10, unit_price: 85, unit: 'adet', location: 'Depo C-3' },
        { id: 4, name: 'Duvar Boyası (Beyaz)', category: 'Yapısal', stock: 5, min_stock: 8, unit_price: 450, unit: 'litre', location: 'Depo D-1' },
        { id: 5, name: 'Vida & Dübel Seti', category: 'Genel', stock: 150, min_stock: 50, unit_price: 15, unit: 'set', location: 'Depo A-8' },
        { id: 6, name: 'Kapı Menteşesi', category: 'Mobilya', stock: 3, min_stock: 12, unit_price: 95, unit: 'adet', location: 'Depo C-7' },
        { id: 7, name: 'Termostat', category: 'HVAC', stock: 18, min_stock: 8, unit_price: 320, unit: 'adet', location: 'Depo A-15' }
      ]);
      setPartsInventoryModalOpen(true);
    }
  };

  const getPriorityColor = (priority) => {
    const colors = {
      urgent: 'bg-red-500',
      high: 'bg-orange-500',
      normal: 'bg-blue-500',
      low: 'bg-gray-500'
    };
    return colors[priority] || 'bg-gray-500';
  };

  const getStatusColor = (status) => {
    const colors = {
      new: 'bg-blue-100 text-blue-700',
      assigned: 'bg-purple-100 text-purple-700',
      in_progress: 'bg-yellow-100 text-yellow-700',
      completed: 'bg-green-100 text-green-700',
      on_hold: 'bg-gray-100 text-gray-700'
    };
    return colors[status] || 'bg-gray-100 text-gray-700';
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-purple-600 mx-auto mb-2" />
          <p className="text-gray-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-gradient-to-r from-purple-600 to-purple-500 text-white p-4 sticky top-0 z-50 shadow-lg">
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
              <h1 className="text-xl font-bold">Teknik Servis</h1>
              <p className="text-xs text-purple-100">Maintenance Dashboard</p>
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
                  <p className="text-xs text-red-600 font-medium">ACİL</p>
                  <p className="text-3xl font-bold text-red-700">{stats?.by_priority?.urgent || 0}</p>
                </div>
                <AlertTriangle className="w-10 h-10 text-red-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-yellow-50 to-yellow-100 border-yellow-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-yellow-600 font-medium">DEVAM EDEN</p>
                  <p className="text-3xl font-bold text-yellow-700">{stats?.by_status?.in_progress || 0}</p>
                </div>
                <Clock className="w-10 h-10 text-yellow-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-green-600 font-medium">TAMAMLANAN</p>
                  <p className="text-3xl font-bold text-green-700">{stats?.by_status?.completed || 0}</p>
                </div>
                <CheckCircle className="w-10 h-10 text-green-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-blue-600 font-medium">TOPLAM</p>
                  <p className="text-3xl font-bold text-blue-700">{tasks.length}</p>
                </div>
                <Settings className="w-10 h-10 text-blue-300" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* SLA Metrics */}
        {slaMetrics && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <TrendingUp className="w-5 h-5 mr-2 text-purple-600" />
                SLA Performansı
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-4">
                <div className="text-center p-3 bg-purple-50 rounded-lg">
                  <p className="text-xs text-purple-600 mb-1">Ortalama Yanıt Süresi</p>
                  <p className="text-2xl font-bold text-purple-700">
                    {slaMetrics.avg_response_time_minutes?.toFixed(0) || 0} dk
                  </p>
                </div>
                <div className="text-center p-3 bg-blue-50 rounded-lg">
                  <p className="text-xs text-blue-600 mb-1">Ortalama Çözüm Süresi</p>
                  <p className="text-2xl font-bold text-blue-700">
                    {slaMetrics.avg_resolution_time_minutes?.toFixed(0) || 0} dk
                  </p>
                </div>
                <div className="text-center p-3 bg-green-50 rounded-lg">
                  <p className="text-xs text-green-600 mb-1">SLA Uyum Oranı</p>
                  <p className="text-2xl font-bold text-green-700">
                    {slaMetrics.sla_compliance_rate?.toFixed(1) || 0}%
                  </p>
                </div>
                <div className="text-center p-3 bg-red-50 rounded-lg">
                  <p className="text-xs text-red-600 mb-1">Geçikmiş Görevler</p>
                  <p className="text-2xl font-bold text-red-700">
                    {stats?.overdue || 0}
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Active Tasks - Urgent Priority */}
        {tasks.filter(t => t.priority === 'urgent' && t.status !== 'completed').length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <AlertTriangle className="w-5 h-5 mr-2 text-red-600" />
                Acil Görevler ({tasks.filter(t => t.priority === 'urgent' && t.status !== 'completed').length})
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {tasks
                .filter(t => t.priority === 'urgent' && t.status !== 'completed')
                .slice(0, 5)
                .map((task) => (
                  <div key={task.id} className="p-3 bg-red-50 rounded-lg border border-red-200">
                    <div className="flex items-start justify-between mb-2">
                      <div className="flex-1">
                        <p className="font-bold text-gray-900">{task.title}</p>
                        <p className="text-sm text-gray-600">{task.description}</p>
                        {task.room_id && (
                          <p className="text-xs text-gray-500 mt-1">
                            Oda: {task.room_number || task.room_id}
                          </p>
                        )}
                      </div>
                      <Badge className={getPriorityColor(task.priority)}>
                        {task.priority}
                      </Badge>
                    </div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center space-x-2">
                        <Badge className={getStatusColor(task.status)}>
                          {task.status}
                        </Badge>
                        {task.room_id && (
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => loadAssetHistory(task.room_id, task.room_number || task.room_id)}
                          >
                            <History className="w-3 h-3" />
                          </Button>
                        )}
                      </div>
                      {task.status !== 'completed' && (
                        <Button
                          size="sm"
                          onClick={() => handleTaskUpdate(task.id, task.status === 'new' ? 'in_progress' : 'completed')}
                          className="bg-purple-600 hover:bg-purple-700"
                        >
                          {task.status === 'new' ? 'Başla' : 'Tamamla'}
                        </Button>
                      )}
                    </div>
                  </div>
                ))}
            </CardContent>
          </Card>
        )}

        {/* All Active Tasks */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center">
              <Settings className="w-5 h-5 mr-2 text-blue-600" />
              Aktif Görevler ({tasks.filter(t => t.status !== 'completed').length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {tasks
              .filter(t => t.status !== 'completed')
              .slice(0, 10)
              .map((task) => (
                <div key={task.id} className="p-3 bg-gray-50 rounded-lg border">
                  <div className="flex items-start justify-between mb-2">
                    <div className="flex-1">
                      <p className="font-bold text-gray-900">{task.title}</p>
                      <p className="text-sm text-gray-600">{task.description}</p>
                      <div className="flex items-center space-x-2 mt-1">
                        {task.room_id && (
                          <span className="text-xs text-gray-500">
                            Oda: {task.room_number || task.room_id}
                          </span>
                        )}
                        {task.assigned_to && (
                          <span className="text-xs text-gray-500">
                            • Atanan: {task.assigned_to}
                          </span>
                        )}
                      </div>
                    </div>
                    <Badge className={getPriorityColor(task.priority)}>
                      {task.priority}
                    </Badge>
                  </div>
                  <div className="flex items-center justify-between">
                    <Badge className={getStatusColor(task.status)}>
                      {task.status}
                    </Badge>
                    {task.status !== 'completed' && (
                      <Button
                        size="sm"
                        onClick={() => handleTaskUpdate(task.id, task.status === 'new' ? 'in_progress' : 'completed')}
                        variant="outline"
                      >
                        {task.status === 'new' ? 'Başla' : 'Tamamla'}
                      </Button>
                    )}
                  </div>
                </div>
              ))}
          </CardContent>
        </Card>

        {/* Repeat Issues */}
        {repeatIssues.length > 0 && (
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center">
                <AlertTriangle className="w-5 h-5 mr-2 text-orange-600" />
                Tekrarlayan Sorunlar
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {repeatIssues.slice(0, 5).map((issue, idx) => (
                <div key={idx} className="p-3 bg-orange-50 rounded-lg border border-orange-200">
                  <div className="flex items-center justify-between">
                    <div className="flex-1">
                      <p className="font-bold text-gray-900">Oda {issue.room_number}</p>
                      <p className="text-sm text-gray-600">{issue.issue_type}</p>
                      <p className="text-xs text-gray-500 mt-1">
                        {issue.occurrences} kez tekrarlandı
                      </p>
                    </div>
                    <Badge variant="outline" className="bg-orange-100">
                      {issue.occurrences}x
                    </Badge>
                  </div>
                </div>
              ))}
            </CardContent>
          </Card>
        )}

        {/* Quick Actions */}
        <div className="grid grid-cols-2 gap-3">
          <Button
            className="h-20 flex flex-col items-center justify-center space-y-1 bg-purple-600 hover:bg-purple-700"
            onClick={() => setNewTaskModalOpen(true)}
          >
            <Wrench className="w-6 h-6" />
            <span className="text-xs">Yeni Görev</span>
          </Button>
          
          <Button
            className="h-20 flex flex-col items-center justify-center space-y-1 bg-blue-600 hover:bg-blue-700"
            onClick={() => setAssetHistoryModalOpen(true)}
          >
            <History className="w-6 h-6" />
            <span className="text-xs">Bakım Geçmişi</span>
          </Button>
          
          <Button
            className="h-20 flex flex-col items-center justify-center space-y-1 bg-orange-600 hover:bg-orange-700"
            onClick={() => navigate('/mobile/maintenance/priority-visual')}
          >
            <BarChart3 className="w-6 h-6" />
            <span className="text-xs">Öncelik Görseli</span>
          </Button>
          
          <Button
            className="h-20 flex flex-col items-center justify-center space-y-1 bg-green-600 hover:bg-green-700"
            onClick={loadPartsInventory}
          >
            <Package className="w-6 h-6" />
            <span className="text-xs">Parça Stok</span>
          </Button>
        </div>
      </div>

      {/* New Task Modal */}
      <Dialog open={newTaskModalOpen} onOpenChange={setNewTaskModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Yeni Bakım Görevi Oluştur</DialogTitle>
          </DialogHeader>
          <form onSubmit={(e) => {
            e.preventDefault();
            handleCreateTask(new FormData(e.target));
          }}>
            <div className="space-y-4">
              <div>
                <Label>Oda Seçin *</Label>
                <select name="room_id" className="w-full p-2 border rounded mt-1" required>
                  <option value="">Seçin...</option>
                  {allRooms.map(room => (
                    <option key={room.id} value={room.id}>
                      Oda {room.room_number} - {room.room_type}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <Label>Arıza Tipi *</Label>
                <select name="issue_type" className="w-full p-2 border rounded mt-1" required>
                  <option value="">Seçin...</option>
                  <option value="electrical">Elektrik</option>
                  <option value="plumbing">Tesisat</option>
                  <option value="hvac">HVAC / Klima</option>
                  <option value="furniture">Mobilya</option>
                  <option value="appliance">Cihaz</option>
                  <option value="structural">Yapısal</option>
                  <option value="other">Diğer</option>
                </select>
              </div>

              <div>
                <Label>Açıklama *</Label>
                <Textarea 
                  name="description" 
                  rows={4}
                  placeholder="Arıza detaylarını yazın..."
                  required
                />
              </div>

              <div>
                <Label>Öncelik *</Label>
                <select name="priority" className="w-full p-2 border rounded mt-1" required>
                  <option value="normal">Normal</option>
                  <option value="high">Yüksek</option>
                  <option value="urgent">Acil</option>
                </select>
              </div>

              <Button type="submit" className="w-full bg-purple-600 hover:bg-purple-700">
                Görev Oluştur
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Asset History Modal */}
      <Dialog open={assetHistoryModalOpen} onOpenChange={setAssetHistoryModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2">
              <History className="w-5 h-5 text-blue-600" />
              <span>Bakım Geçmişi - Tüm Varlıklar</span>
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-4">
            {/* Asset Selection */}
            <Card className="bg-blue-50">
              <CardContent className="p-4">
                <p className="text-sm text-blue-900 mb-3 font-medium">
                  <Wrench className="w-4 h-4 inline mr-1" />
                  Tüm odaların bakım geçmişini görebilirsiniz
                </p>
                <div className="grid gap-2">
                  {allRooms.slice(0, 10).map(room => (
                    <Button
                      key={room.id}
                      variant="outline"
                      className="w-full justify-start"
                      onClick={() => loadAssetHistory(room.id, room.room_number)}
                    >
                      <span className="font-bold">Oda {room.room_number}</span>
                      <span className="text-gray-500 ml-2">- {room.room_type}</span>
                    </Button>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* History Display */}
            {assetHistory && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base">
                    Bakım Geçmişi: {selectedAsset}
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    <div className="grid grid-cols-3 gap-2 text-xs">
                      <div className="text-center p-2 bg-blue-50 rounded">
                        <p className="text-blue-900 font-bold text-lg">
                          {assetHistory.total_maintenances || 0}
                        </p>
                        <p className="text-blue-600">Toplam Bakım</p>
                      </div>
                      <div className="text-center p-2 bg-green-50 rounded">
                        <p className="text-green-900 font-bold text-lg">
                          {assetHistory.last_maintenance_days_ago || 'N/A'}
                        </p>
                        <p className="text-green-600">Gün Önce</p>
                      </div>
                      <div className="text-center p-2 bg-purple-50 rounded">
                        <p className="text-purple-900 font-bold text-lg">
                          {assetHistory.avg_cost?.toFixed(0) || 0} ₺
                        </p>
                        <p className="text-purple-600">Ort. Maliyet</p>
                      </div>
                    </div>

                    {/* Maintenance History List */}
                    {assetHistory.history && assetHistory.history.length > 0 ? (
                      <div className="space-y-2 mt-4">
                        <p className="font-bold text-sm text-gray-700 mb-2">Son Bakımlar:</p>
                        {assetHistory.history.slice(0, 5).map((item, idx) => (
                          <div key={idx} className="p-3 bg-gray-50 rounded border text-xs">
                            <div className="flex items-start justify-between">
                              <div className="flex-1">
                                <p className="font-bold text-gray-900">{item.issue_type || item.title}</p>
                                <p className="text-gray-600 mt-1">{item.description || 'Açıklama yok'}</p>
                                <div className="flex items-center space-x-2 mt-2 text-gray-500">
                                  <Calendar className="w-3 h-3" />
                                  <span>{new Date(item.created_at || item.date).toLocaleDateString('tr-TR')}</span>
                                </div>
                              </div>
                              <Badge className={getPriorityColor(item.priority || 'normal')}>
                                {item.priority || 'normal'}
                              </Badge>
                            </div>
                            {item.cost && (
                              <p className="text-purple-700 font-bold mt-2">{item.cost} ₺</p>
                            )}
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="text-center py-8 text-gray-500">
                        <History className="w-12 h-12 mx-auto mb-2 opacity-30" />
                        <p>Bu varlık için bakım kaydı bulunamadı</p>
                      </div>
                    )}

                    {/* Most Common Issues */}
                    {assetHistory.most_common_issues && assetHistory.most_common_issues.length > 0 && (
                      <div className="mt-4">
                        <p className="font-bold text-sm text-gray-700 mb-2">En Yaygın Sorunlar:</p>
                        <div className="space-y-1">
                          {assetHistory.most_common_issues.map((issue, idx) => (
                            <div key={idx} className="flex items-center justify-between p-2 bg-orange-50 rounded text-xs">
                              <span className="text-gray-900">{issue.type}</span>
                              <Badge variant="outline" className="bg-orange-100">
                                {issue.count}x
                              </Badge>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Parts Inventory Modal */}
      <Dialog open={partsInventoryModalOpen} onOpenChange={setPartsInventoryModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center space-x-2">
              <Package className="w-5 h-5 text-green-600" />
              <span>Parça & Malzeme Stok Kartı</span>
            </DialogTitle>
          </DialogHeader>
          
          <div className="space-y-3">
            {/* Stock Summary */}
            <div className="grid grid-cols-3 gap-2">
              <Card className="bg-blue-50">
                <CardContent className="p-3 text-center">
                  <p className="text-2xl font-bold text-blue-900">{partsInventory.length}</p>
                  <p className="text-xs text-blue-600">Toplam Kalem</p>
                </CardContent>
              </Card>
              <Card className="bg-red-50">
                <CardContent className="p-3 text-center">
                  <p className="text-2xl font-bold text-red-900">
                    {partsInventory.filter(p => p.stock < p.min_stock).length}
                  </p>
                  <p className="text-xs text-red-600">Düşük Stok</p>
                </CardContent>
              </Card>
              <Card className="bg-green-50">
                <CardContent className="p-3 text-center">
                  <p className="text-2xl font-bold text-green-900">
                    {partsInventory.filter(p => p.stock >= p.min_stock).length}
                  </p>
                  <p className="text-xs text-green-600">Yeterli Stok</p>
                </CardContent>
              </Card>
            </div>

            {/* Low Stock Alert */}
            {partsInventory.filter(p => p.stock < p.min_stock).length > 0 && (
              <Card className="bg-red-50 border-red-200">
                <CardContent className="p-3">
                  <div className="flex items-center space-x-2">
                    <AlertTriangle className="w-5 h-5 text-red-600" />
                    <p className="text-sm font-bold text-red-900">
                      ⚠️ {partsInventory.filter(p => p.stock < p.min_stock).length} kalem kritik seviyede!
                    </p>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Parts List by Category */}
            {['HVAC', 'Elektrik', 'Tesisat', 'Yapısal', 'Mobilya', 'Genel'].map(category => {
              const categoryParts = partsInventory.filter(p => p.category === category);
              if (categoryParts.length === 0) return null;

              return (
                <Card key={category}>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm flex items-center justify-between">
                      <span>
                        {category === 'HVAC' ? '❄️ HVAC' :
                         category === 'Elektrik' ? '⚡ Elektrik' :
                         category === 'Tesisat' ? '💧 Tesisat' :
                         category === 'Yapısal' ? '🏗️ Yapısal' :
                         category === 'Mobilya' ? '🪑 Mobilya' :
                         '🔧 Genel Malzeme'}
                      </span>
                      <Badge variant="outline">{categoryParts.length}</Badge>
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    {categoryParts.map(part => {
                      const isLowStock = part.stock < part.min_stock;
                      const stockPercentage = (part.stock / part.min_stock) * 100;
                      
                      return (
                        <div 
                          key={part.id} 
                          className={`p-3 rounded-lg border ${
                            isLowStock ? 'bg-red-50 border-red-200' : 'bg-gray-50 border-gray-200'
                          }`}
                        >
                          <div className="flex items-start justify-between mb-2">
                            <div className="flex-1">
                              <div className="flex items-center space-x-2">
                                <p className="font-bold text-gray-900">{part.name}</p>
                                {isLowStock && (
                                  <Badge className="bg-red-500 text-xs">DİKKAT</Badge>
                                )}
                              </div>
                              <p className="text-xs text-gray-500 mt-1">📍 {part.location}</p>
                            </div>
                            <div className="text-right">
                              <p className="font-bold text-lg text-purple-700">{part.unit_price} ₺</p>
                              <p className="text-xs text-gray-500">/{part.unit}</p>
                            </div>
                          </div>
                          
                          {/* Stock Bar */}
                          <div className="space-y-1">
                            <div className="flex items-center justify-between text-xs">
                              <span className="text-gray-600">Stok Durumu:</span>
                              <span className={`font-bold ${
                                isLowStock ? 'text-red-700' : 'text-green-700'
                              }`}>
                                {part.stock} / {part.min_stock} {part.unit}
                              </span>
                            </div>
                            <div className="w-full bg-gray-200 rounded-full h-2">
                              <div 
                                className={`h-2 rounded-full transition-all ${
                                  stockPercentage < 50 ? 'bg-red-500' :
                                  stockPercentage < 100 ? 'bg-yellow-500' :
                                  'bg-green-500'
                                }`}
                                style={{ width: `${Math.min(stockPercentage, 100)}%` }}
                              />
                            </div>
                          </div>

                          {isLowStock && (
                            <div className="mt-2 flex items-center justify-between p-2 bg-red-100 rounded">
                              <span className="text-xs text-red-900">
                                ⚠️ {part.min_stock - part.stock} {part.unit} sipariş gerekli
                              </span>
                              <Button 
                                size="sm" 
                                className="bg-red-600 hover:bg-red-700 h-6 text-xs"
                                onClick={() => toast.success(`${part.name} sipariş listesine eklendi`)}
                              >
                                <ShoppingCart className="w-3 h-3 mr-1" />
                                Sipariş
                              </Button>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </CardContent>
                </Card>
              );
            })}

            {/* Total Value */}
            <Card className="bg-gradient-to-r from-purple-50 to-indigo-50 border-purple-200">
              <CardContent className="p-4">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-purple-700 font-medium">Toplam Stok Değeri</p>
                    <p className="text-xs text-purple-600 mt-1">Tüm malzemeler</p>
                  </div>
                  <p className="text-3xl font-bold text-purple-700">
                    {partsInventory.reduce((sum, p) => sum + (p.stock * p.unit_price), 0).toLocaleString('tr-TR')} ₺
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MobileMaintenance;
