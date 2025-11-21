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
  FileText
} from 'lucide-react';

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
                      <Badge className={getStatusColor(task.status)}>
                        {task.status}
                      </Badge>
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
        <Card className="bg-gradient-to-r from-purple-50 to-indigo-50">
          <CardContent className="p-4">
            <Button
              className="w-full h-16 flex items-center justify-center space-x-2 bg-purple-600 hover:bg-purple-700"
              onClick={() => setNewTaskModalOpen(true)}
            >
              <Wrench className="w-6 h-6" />
              <span>Yeni Bakım Görevi Oluştur</span>
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* New Task Modal */}
      <Dialog open={newTaskModalOpen} onOpenChange={setNewTaskModalOpen}>
        <DialogContent className="max-w-full w-[95vw]">
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
    </div>
  );
};

export default MobileMaintenance;
