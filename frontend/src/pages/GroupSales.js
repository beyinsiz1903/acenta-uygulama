import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Users, Plus, FileText, DollarSign, Calendar, TrendingUp, Mail, Phone } from 'lucide-react';

const GroupSales = () => {
  const [loading, setLoading] = useState(false);
  const [groups, setGroups] = useState([]);
  const [selectedGroup, setSelectedGroup] = useState(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [groupDetails, setGroupDetails] = useState(null);

  const [newGroup, setNewGroup] = useState({
    group_name: '',
    organization: '',
    contact_name: '',
    contact_email: '',
    contact_phone: '',
    check_in: '',
    check_out: '',
    total_rooms: 10,
    group_rate: 100,
    room_type: 'Standard',
    cutoff_date: '',
    billing_type: 'master_account',
    special_requirements: ''
  });

  useEffect(() => {
    loadGroups();
  }, []);

  const loadGroups = async () => {
    try {
      const response = await axios.get('/groups/blocks');
      setGroups(response.data.blocks || []);
    } catch (error) {
      toast.error('Grup listesi yüklenemedi');
    }
  };

  const handleCreateGroup = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post('/groups/create-block', newGroup);
      toast.success('Grup bloğu başarıyla oluşturuldu!');
      setShowCreateDialog(false);
      loadGroups();
      setNewGroup({
        group_name: '',
        organization: '',
        contact_name: '',
        contact_email: '',
        contact_phone: '',
        check_in: '',
        check_out: '',
        total_rooms: 10,
        group_rate: 100,
        room_type: 'Standard',
        cutoff_date: '',
        billing_type: 'master_account',
        special_requirements: ''
      });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Grup oluşturulamadı');
    } finally {
      setLoading(false);
    }
  };

  const loadGroupDetails = async (blockId) => {
    try {
      const response = await axios.get(`/groups/block/${blockId}`);
      setGroupDetails(response.data);
      setSelectedGroup(blockId);
    } catch (error) {
      toast.error('Grup detayları yüklenemedi');
    }
  };

  const StatusBadge = ({ status }) => {
    const colors = {
      tentative: 'bg-yellow-100 text-yellow-800',
      definite: 'bg-green-100 text-green-800',
      released: 'bg-gray-100 text-gray-800',
      completed: 'bg-blue-100 text-blue-800',
      cancelled: 'bg-red-100 text-red-800'
    };

    const labels = {
      tentative: 'Opsiyonel',
      definite: 'Kesin',
      released: 'Serbest Bırakıldı',
      completed: 'Tamamlandı',
      cancelled: 'İptal'
    };

    return (
      <span className={`px-3 py-1 rounded-full text-xs font-semibold ${colors[status] || 'bg-gray-100'}`}>
        {labels[status] || status}
      </span>
    );
  };

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            👥 Grup Satış Yönetimi
          </h1>
          <p className="text-gray-600">
            Grup rezervasyonları, bloklar ve rooming list yönetimi
          </p>
        </div>
        
        <Dialog open={showCreateDialog} onOpenChange={setShowCreateDialog}>
          <DialogTrigger asChild>
            <Button size="lg" className="bg-purple-600 hover:bg-purple-700">
              <Plus className="w-5 h-5 mr-2" />
              Yeni Grup Bloğu
            </Button>
          </DialogTrigger>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Yeni Grup Bloğu Oluştur</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateGroup} className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Grup Adı *</Label>
                  <Input
                    value={newGroup.group_name}
                    onChange={(e) => setNewGroup({...newGroup, group_name: e.target.value})}
                    required
                    placeholder="ABC Şirketi Toplantısı"
                  />
                </div>
                <div>
                  <Label>Organizasyon *</Label>
                  <Input
                    value={newGroup.organization}
                    onChange={(e) => setNewGroup({...newGroup, organization: e.target.value})}
                    required
                    placeholder="ABC Şirketi"
                  />
                </div>
                <div>
                  <Label>İlgili Kişi *</Label>
                  <Input
                    value={newGroup.contact_name}
                    onChange={(e) => setNewGroup({...newGroup, contact_name: e.target.value})}
                    required
                    placeholder="Ahmet Yılmaz"
                  />
                </div>
                <div>
                  <Label>E-posta *</Label>
                  <Input
                    type="email"
                    value={newGroup.contact_email}
                    onChange={(e) => setNewGroup({...newGroup, contact_email: e.target.value})}
                    required
                    placeholder="ahmet@abc.com"
                  />
                </div>
                <div>
                  <Label>Telefon *</Label>
                  <Input
                    value={newGroup.contact_phone}
                    onChange={(e) => setNewGroup({...newGroup, contact_phone: e.target.value})}
                    required
                    placeholder="+90 555 123 45 67"
                  />
                </div>
                <div>
                  <Label>Toplam Oda Sayısı *</Label>
                  <Input
                    type="number"
                    min="1"
                    value={newGroup.total_rooms}
                    onChange={(e) => setNewGroup({...newGroup, total_rooms: parseInt(e.target.value)})}
                    required
                  />
                </div>
                <div>
                  <Label>Check-in Tarihi *</Label>
                  <Input
                    type="date"
                    value={newGroup.check_in}
                    onChange={(e) => setNewGroup({...newGroup, check_in: e.target.value})}
                    required
                  />
                </div>
                <div>
                  <Label>Check-out Tarihi *</Label>
                  <Input
                    type="date"
                    value={newGroup.check_out}
                    onChange={(e) => setNewGroup({...newGroup, check_out: e.target.value})}
                    required
                  />
                </div>
                <div>
                  <Label>Cutoff Tarihi *</Label>
                  <Input
                    type="date"
                    value={newGroup.cutoff_date}
                    onChange={(e) => setNewGroup({...newGroup, cutoff_date: e.target.value})}
                    required
                  />
                  <p className="text-xs text-gray-500 mt-1">Rezervasyon kapanış tarihi</p>
                </div>
                <div>
                  <Label>Grup Fiyatı (€) *</Label>
                  <Input
                    type="number"
                    min="0"
                    value={newGroup.group_rate}
                    onChange={(e) => setNewGroup({...newGroup, group_rate: parseFloat(e.target.value)})}
                    required
                  />
                </div>
                <div>
                  <Label>Oda Tipi</Label>
                  <Select 
                    value={newGroup.room_type}
                    onValueChange={(val) => setNewGroup({...newGroup, room_type: val})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="Standard">Standard</SelectItem>
                      <SelectItem value="Deluxe">Deluxe</SelectItem>
                      <SelectItem value="Suite">Suite</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Fatura Tipi</Label>
                  <Select 
                    value={newGroup.billing_type}
                    onValueChange={(val) => setNewGroup({...newGroup, billing_type: val})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="master_account">Master Hesap</SelectItem>
                      <SelectItem value="individual">Bireysel Fatura</SelectItem>
                      <SelectItem value="split">Karma (Split)</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              <div>
                <Label>Özel Gereksinimler</Label>
                <Textarea
                  value={newGroup.special_requirements}
                  onChange={(e) => setNewGroup({...newGroup, special_requirements: e.target.value})}
                  placeholder="Meeting room, catering, özel istekler..."
                  rows={3}
                />
              </div>

              <div className="flex gap-3">
                <Button type="button" variant="outline" onClick={() => setShowCreateDialog(false)} className="flex-1">
                  İptal
                </Button>
                <Button type="submit" disabled={loading} className="flex-1 bg-purple-600 hover:bg-purple-700">
                  {loading ? 'Oluşturuluyor...' : 'Grup Bloğu Oluştur'}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Group List */}
      <div className="grid grid-cols-1 gap-4">
        {groups.length === 0 ? (
          <Card>
            <CardContent className="pt-12 pb-12 text-center">
              <Users className="w-16 h-16 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 mb-4">Henüz grup rezervasyonu yok</p>
              <Button onClick={() => setShowCreateDialog(true)}>
                İlk Grup Bloğunu Oluştur
              </Button>
            </CardContent>
          </Card>
        ) : (
          groups.map((group) => (
            <Card 
              key={group.id} 
              className="cursor-pointer hover:shadow-lg transition-shadow"
              onClick={() => loadGroupDetails(group.id)}
            >
              <CardContent className="pt-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-xl font-bold text-gray-900">{group.group_name}</h3>
                      <StatusBadge status={group.status} />
                    </div>
                    <p className="text-gray-600 mb-3">{group.organization}</p>
                    
                    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mt-4">
                      <div>
                        <p className="text-xs text-gray-500">Check-in</p>
                        <p className="font-semibold">{new Date(group.check_in).toLocaleDateString('tr-TR')}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Toplam Oda</p>
                        <p className="font-semibold">{group.total_rooms} oda</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Pickup</p>
                        <p className="font-semibold">{group.rooms_picked_up} / {group.total_rooms}</p>
                      </div>
                      <div>
                        <p className="text-xs text-gray-500">Grup Fiyatı</p>
                        <p className="font-semibold">€{group.group_rate}</p>
                      </div>
                    </div>
                  </div>
                  
                  <div className="text-right">
                    <div className="text-3xl font-bold text-purple-600">
                      {Math.round((group.rooms_picked_up / group.total_rooms) * 100)}%
                    </div>
                    <div className="text-xs text-gray-500">Pickup Oranı</div>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))
        )}
      </div>

      {/* Group Details Modal */}
      {selectedGroup && groupDetails && (
        <Dialog open={!!selectedGroup} onOpenChange={() => setSelectedGroup(null)}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-2xl">
                {groupDetails.block.group_name}
              </DialogTitle>
            </DialogHeader>

            <Tabs defaultValue="overview" className="mt-4">
              <TabsList className="grid w-full grid-cols-3">
                <TabsTrigger value="overview">Genel Bakış</TabsTrigger>
                <TabsTrigger value="bookings">Rezervasyonlar ({groupDetails.bookings_count})</TabsTrigger>
                <TabsTrigger value="folio">Master Folio</TabsTrigger>
              </TabsList>

              <TabsContent value="overview" className="space-y-4">
                <Card>
                  <CardHeader>
                    <CardTitle>Pickup Durumu</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex items-center justify-between">
                        <span>Toplam Oda:</span>
                        <span className="font-bold">{groupDetails.pickup.total_rooms}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Alınan Oda:</span>
                        <span className="font-bold text-green-600">{groupDetails.pickup.rooms_picked_up}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span>Kalan Oda:</span>
                        <span className="font-bold text-orange-600">{groupDetails.pickup.rooms_remaining}</span>
                      </div>
                      
                      <div className="pt-4 border-t">
                        <div className="flex items-center justify-between mb-2">
                          <span className="text-sm font-medium">Pickup Oranı</span>
                          <span className="text-lg font-bold text-purple-600">
                            {groupDetails.pickup.pickup_percentage}%
                          </span>
                        </div>
                        <div className="w-full bg-gray-200 rounded-full h-3">
                          <div 
                            className="bg-purple-600 h-3 rounded-full transition-all duration-500"
                            style={{ width: `${groupDetails.pickup.pickup_percentage}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>İletişim Bilgileri</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-2">
                    <div className="flex items-center gap-2">
                      <Users className="w-4 h-4 text-gray-500" />
                      <span>{groupDetails.block.contact_name}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Mail className="w-4 h-4 text-gray-500" />
                      <span>{groupDetails.block.contact_email}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <Phone className="w-4 h-4 text-gray-500" />
                      <span>{groupDetails.block.contact_phone}</span>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>

              <TabsContent value="bookings">
                <div className="space-y-3">
                  {groupDetails.bookings.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      Henüz rezervasyon oluşturulmamış
                    </div>
                  ) : (
                    groupDetails.bookings.map((booking, idx) => (
                      <Card key={booking.id}>
                        <CardContent className="pt-4">
                          <div className="flex items-center justify-between">
                            <div>
                              <p className="font-semibold">#{idx + 1} - Misafir ID: {booking.guest_id.substring(0, 8)}</p>
                              <p className="text-sm text-gray-600">
                                {new Date(booking.check_in).toLocaleDateString('tr-TR')} - 
                                {new Date(booking.check_out).toLocaleDateString('tr-TR')}
                              </p>
                            </div>
                            <div className="text-right">
                              <p className="text-sm text-gray-500">Tutar</p>
                              <p className="text-lg font-bold">€{booking.total_amount}</p>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))
                  )}
                </div>
              </TabsContent>

              <TabsContent value="folio">
                <Card>
                  <CardHeader>
                    <CardTitle>Master Folio Özeti</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-center py-8">
                      <DollarSign className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                      <p className="text-gray-600">
                        Master folio özelliği yakında aktif olacak
                      </p>
                    </div>
                  </CardContent>
                </Card>
              </TabsContent>
            </Tabs>
          </DialogContent>
        </Dialog>
      )}

      {/* Statistics Summary */}
      {groups.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mt-6">
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-sm text-gray-500">Toplam Grup</p>
                <p className="text-3xl font-bold text-purple-600">{groups.length}</p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-sm text-gray-500">Toplam Oda</p>
                <p className="text-3xl font-bold text-blue-600">
                  {groups.reduce((sum, g) => sum + g.total_rooms, 0)}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-sm text-gray-500">Alınan Oda</p>
                <p className="text-3xl font-bold text-green-600">
                  {groups.reduce((sum, g) => sum + (g.rooms_picked_up || 0), 0)}
                </p>
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-center">
                <p className="text-sm text-gray-500">Ort. Pickup</p>
                <p className="text-3xl font-bold text-orange-600">
                  {groups.length > 0 
                    ? Math.round(groups.reduce((sum, g) => sum + ((g.rooms_picked_up || 0) / g.total_rooms * 100), 0) / groups.length)
                    : 0}%
                </p>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};

export default GroupSales;
