import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  ArrowLeft, 
  Users, 
  CheckCircle, 
  XCircle,
  Clock,
  Bed,
  RefreshCw,
  UserPlus,
  Calendar
} from 'lucide-react';

const MobileFrontDesk = ({ user }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [todayArrivals, setTodayArrivals] = useState([]);
  const [todayDepartures, setTodayDepartures] = useState([]);
  const [inHouse, setInHouse] = useState([]);
  const [roomAvailability, setRoomAvailability] = useState(null);
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      const today = new Date().toISOString().split('T')[0];
      
      const [bookingsRes, roomsRes] = await Promise.all([
        axios.get('/pms/bookings'),
        axios.get('/housekeeping/room-status')
      ]);

      const allBookings = bookingsRes.data.bookings || [];
      
      // Filter arrivals
      const arrivals = allBookings.filter(b => 
        b.check_in?.startsWith(today) && 
        ['confirmed', 'guaranteed'].includes(b.status)
      );
      
      // Filter departures
      const departures = allBookings.filter(b => 
        b.check_out?.startsWith(today) && 
        b.status === 'checked_in'
      );
      
      // In-house guests
      const inHouseGuests = allBookings.filter(b => b.status === 'checked_in');

      setTodayArrivals(arrivals);
      setTodayDepartures(departures);
      setInHouse(inHouseGuests);
      setRoomAvailability(roomsRes.data);
    } catch (error) {
      console.error('Failed to load front desk data:', error);
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

  const handleCheckIn = async (bookingId) => {
    try {
      await axios.post(`/frontdesk/checkin/${bookingId}`);
      toast.success('Check-in başarılı!');
      loadData();
    } catch (error) {
      toast.error('Check-in başarısız: ' + (error.response?.data?.detail || 'Hata'));
    }
  };

  const handleCheckOut = async (bookingId) => {
    try {
      await axios.post(`/frontdesk/checkout/${bookingId}`);
      toast.success('Check-out başarılı!');
      loadData();
    } catch (error) {
      toast.error('Check-out başarısız: ' + (error.response?.data?.detail || 'Hata'));
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <RefreshCw className="w-8 h-8 animate-spin text-green-600 mx-auto mb-2" />
          <p className="text-gray-600">Yükleniyor...</p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20">
      {/* Header */}
      <div className="bg-gradient-to-r from-green-600 to-green-500 text-white p-4 sticky top-0 z-50 shadow-lg">
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
              <h1 className="text-xl font-bold">Ön Büro</h1>
              <p className="text-xs text-green-100">Front Desk Dashboard</p>
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
          <Card className="bg-gradient-to-br from-blue-50 to-blue-100 border-blue-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-blue-600 font-medium">BUGÜN GELİŞ</p>
                  <p className="text-3xl font-bold text-blue-700">{todayArrivals.length}</p>
                </div>
                <UserPlus className="w-10 h-10 text-blue-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-orange-50 to-orange-100 border-orange-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-orange-600 font-medium">BUGÜN ÇIKIŞ</p>
                  <p className="text-3xl font-bold text-orange-700">{todayDepartures.length}</p>
                </div>
                <XCircle className="w-10 h-10 text-orange-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-green-50 to-green-100 border-green-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-green-600 font-medium">KONAKLAYANLAR</p>
                  <p className="text-3xl font-bold text-green-700">{inHouse.length}</p>
                </div>
                <Users className="w-10 h-10 text-green-300" />
              </div>
            </CardContent>
          </Card>

          <Card className="bg-gradient-to-br from-purple-50 to-purple-100 border-purple-200">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-xs text-purple-600 font-medium">BOŞ ODALAR</p>
                  <p className="text-3xl font-bold text-purple-700">{roomAvailability?.status_counts?.available || 0}</p>
                </div>
                <Bed className="w-10 h-10 text-purple-300" />
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Today's Arrivals */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center">
              <UserPlus className="w-5 h-5 mr-2 text-blue-600" />
              Bugün Geliş Yapacaklar ({todayArrivals.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {todayArrivals.length === 0 ? (
              <p className="text-gray-500 text-center py-4">Bugün geliş yok</p>
            ) : (
              todayArrivals.map((booking) => (
                <div key={booking.id} className="flex items-center justify-between p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <div className="flex-1">
                    <p className="font-bold text-gray-900">{booking.guest_name || 'Misafir'}</p>
                    <p className="text-sm text-gray-600">Oda {booking.room_number || 'TBA'}</p>
                    <p className="text-xs text-gray-500">
                      {booking.guests_count || 1} kişi • {booking.nights || 0} gece
                    </p>
                  </div>
                  <div className="flex flex-col items-end space-y-2">
                    <Badge className="bg-blue-500">{booking.status}</Badge>
                    <Button
                      size="sm"
                      onClick={() => handleCheckIn(booking.id)}
                      className="bg-green-600 hover:bg-green-700"
                    >
                      <CheckCircle className="w-4 h-4 mr-1" />
                      Check-In
                    </Button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* Today's Departures */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center">
              <XCircle className="w-5 h-5 mr-2 text-orange-600" />
              Bugün Çıkış Yapacaklar ({todayDepartures.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {todayDepartures.length === 0 ? (
              <p className="text-gray-500 text-center py-4">Bugün çıkış yok</p>
            ) : (
              todayDepartures.map((booking) => (
                <div key={booking.id} className="flex items-center justify-between p-3 bg-orange-50 rounded-lg border border-orange-200">
                  <div className="flex-1">
                    <p className="font-bold text-gray-900">{booking.guest_name || 'Misafir'}</p>
                    <p className="text-sm text-gray-600">Oda {booking.room_number || 'N/A'}</p>
                    <p className="text-xs text-gray-500">
                      {booking.guests_count || 1} kişi • Toplam: ₺{booking.total_amount || 0}
                    </p>
                  </div>
                  <div className="flex flex-col items-end space-y-2">
                    <Badge className="bg-orange-500">Konaklıyor</Badge>
                    <Button
                      size="sm"
                      onClick={() => handleCheckOut(booking.id)}
                      className="bg-red-600 hover:bg-red-700"
                    >
                      <CheckCircle className="w-4 h-4 mr-1" />
                      Check-Out
                    </Button>
                  </div>
                </div>
              ))
            )}
          </CardContent>
        </Card>

        {/* In-House Guests */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-lg flex items-center">
              <Users className="w-5 h-5 mr-2 text-green-600" />
              Konaklayanlar ({inHouse.length})
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {inHouse.slice(0, 10).map((booking) => (
              <div key={booking.id} className="flex items-center justify-between p-3 bg-green-50 rounded-lg border border-green-200">
                <div className="flex-1">
                  <p className="font-bold text-gray-900">{booking.guest_name || 'Misafir'}</p>
                  <p className="text-sm text-gray-600">Oda {booking.room_number || 'N/A'}</p>
                  <p className="text-xs text-gray-500">
                    Çıkış: {booking.check_out ? new Date(booking.check_out).toLocaleDateString('tr-TR') : 'N/A'}
                  </p>
                </div>
                <Badge className="bg-green-500">Konaklıyor</Badge>
              </div>
            ))}
          </CardContent>
        </Card>

        {/* Quick Actions */}
        <Card className="bg-gradient-to-r from-green-50 to-blue-50">
          <CardContent className="p-4">
            <div className="grid grid-cols-2 gap-3">
              <Button
                className="h-20 flex flex-col items-center justify-center"
                onClick={() => navigate('/pms')}
              >
                <Calendar className="w-6 h-6 mb-1" />
                <span className="text-xs">Rezervasyonlar</span>
              </Button>
              <Button
                className="h-20 flex flex-col items-center justify-center"
                variant="outline"
                onClick={() => navigate('/dashboard')}
              >
                <Bed className="w-6 h-6 mb-1" />
                <span className="text-xs">Oda Durumu</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default MobileFrontDesk;