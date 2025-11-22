import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { 
  ArrowLeft, 
  Users, 
  CheckCircle, 
  XCircle,
  Clock,
  Bed,
  RefreshCw,
  UserPlus,
  Calendar,
  Search,
  AlertCircle,
  DollarSign,
  Filter,
  Star,
  Home,
  Camera,
  CreditCard,
  QrCode,
  Key,
  ChevronDown,
  ChevronUp
} from 'lucide-react';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';

const MobileFrontDesk = ({ user }) => {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [todayArrivals, setTodayArrivals] = useState([]);
  const [todayDepartures, setTodayDepartures] = useState([]);
  const [inHouse, setInHouse] = useState([]);
  const [roomAvailability, setRoomAvailability] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [reservationsModalOpen, setReservationsModalOpen] = useState(false);
  const [roomStatusModalOpen, setRoomStatusModalOpen] = useState(false);
  const [allBookings, setAllBookings] = useState([]);
  const [allRooms, setAllRooms] = useState([]);
  const [guestAlertsModalOpen, setGuestAlertsModalOpen] = useState(false);
  const [feeCalculatorModalOpen, setFeeCalculatorModalOpen] = useState(false);
  const [roomFilterModalOpen, setRoomFilterModalOpen] = useState(false);
  const [guestAlerts, setGuestAlerts] = useState([]);
  const [selectedBookingForFee, setSelectedBookingForFee] = useState(null);
  const [calculatedFees, setCalculatedFees] = useState(null);
  const [roomFilters, setRoomFilters] = useState({ bed_type: '', floor: '', status: '' });
  const [filteredRooms, setFilteredRooms] = useState([]);
  
  // NEW FEATURES STATE
  const [searchModalOpen, setSearchModalOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState([]);
  const [roomAssignModalOpen, setRoomAssignModalOpen] = useState(false);
  const [selectedBookingForRoom, setSelectedBookingForRoom] = useState(null);
  const [availableRooms, setAvailableRooms] = useState([]);
  const [passportScanModalOpen, setPassportScanModalOpen] = useState(false);
  const [selectedBookingForPassport, setSelectedBookingForPassport] = useState(null);
  const [passportImage, setPassportImage] = useState(null);
  const [keycardModalOpen, setKeycardModalOpen] = useState(false);
  const [selectedBookingForKeycard, setSelectedBookingForKeycard] = useState(null);
  const [keycardType, setKeycardType] = useState('physical');
  
  // COLLAPSIBLE STATE
  const [arrivalsExpanded, setArrivalsExpanded] = useState(false);
  const [departuresExpanded, setDeparturesExpanded] = useState(false);
  
  console.log('🔍 Collapsible States:', { arrivalsExpanded, departuresExpanded });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      setLoading(true);
      
      const [arrivalsRes, departuresRes, inHouseRes, roomsRes, bookingsRes] = await Promise.all([
        axios.get('/unified/today-arrivals'),
        axios.get('/unified/today-departures'),
        axios.get('/unified/in-house'),
        axios.get('/housekeeping/room-status'),
        axios.get('/pms/bookings').catch(() => ({ data: { bookings: [] } }))
      ]);

      const allBookings = bookingsRes.data.bookings || [];
      setAllBookings(allBookings);
      
      // Use unified endpoints
      setTodayArrivals(arrivalsRes.data.arrivals || []);
      setTodayDepartures(departuresRes.data.departures || []);
      setInHouse(inHouseRes.data.in_house || []);
      setRoomAvailability(roomsRes.data);
      setAllRooms(roomsRes.data.rooms || []);
      
      console.log('🔍 Front Desk Data Loaded:', {
        arrivals: arrivalsRes.data.count,
        departures: departuresRes.data.count,
        inHouse: inHouseRes.data.count
      });
    } catch (error) {
      console.error('Failed to load front desk data:', error);
      toast.error('✗ Yükleme');
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
      toast.success('✓ Check-in');
      loadData();
    } catch (error) {
      toast.error('✗ Check-in');
    }
  };

  const handleCheckOut = async (bookingId) => {
    try {
      await axios.post(`/frontdesk/checkout/${bookingId}`);
      toast.success('✓ Check-out');
      loadData();
    } catch (error) {
      toast.error('✗ Check-out');
    }
  };

  const loadGuestAlerts = async () => {
    try {
      const res = await axios.get('/frontdesk/guest-alerts');
      setGuestAlerts(res.data.alerts || []);
      setGuestAlertsModalOpen(true);
    } catch (error) {
      toast.error('✗ Uyarılar');
    }
  };

  const calculateFees = async (booking, earlyTime, lateTime) => {
    try {
      const res = await axios.post('/frontdesk/calculate-early-late-fees', {
        booking_id: booking.id,
        early_checkin_time: earlyTime,
        late_checkout_time: lateTime
      });
      setCalculatedFees(res.data);
    } catch (error) {
      toast.error('✗ Hesaplama');
    }
  };

  const loadFilteredRooms = async (filters) => {
    try {
      const params = new URLSearchParams();
      if (filters.bed_type) params.append('bed_type', filters.bed_type);
      if (filters.floor) params.append('floor', filters.floor);
      if (filters.status) params.append('status', filters.status);
      
      const res = await axios.get(`/frontdesk/rooms-with-filters?${params.toString()}`);
      setFilteredRooms(res.data.rooms || []);
    } catch (error) {
      toast.error('✗ Filtre');
    }
  };

  // NEW FEATURE 1: RESERVATION SEARCH
  const handleSearch = async () => {
    try {
      const params = new URLSearchParams();
      if (searchQuery) params.append('query', searchQuery);
      
      const res = await axios.get(`/reservations/search?${params.toString()}`);
      setSearchResults(res.data.bookings || []);
      toast.success(`${res.data.count} rezervasyon bulundu`);
    } catch (error) {
      toast.error('✗ Arama başarısız');
    }
  };

  // NEW FEATURE 2: ROOM ASSIGNMENT
  const openRoomAssignment = async (booking) => {
    try {
      setSelectedBookingForRoom(booking);
      // Load available rooms
      const res = await axios.get(`/frontdesk/available-rooms-for-assignment?check_in=${booking.check_in}&check_out=${booking.check_out}`);
      setAvailableRooms(res.data.rooms || []);
      setRoomAssignModalOpen(true);
    } catch (error) {
      toast.error('✗ Müsait odalar yüklenemedi');
    }
  };

  const assignRoom = async (roomId) => {
    try {
      await axios.post('/frontdesk/assign-room', {
        booking_id: selectedBookingForRoom.id,
        room_id: roomId
      });
      toast.success('✓ Oda atandı');
      setRoomAssignModalOpen(false);
      loadData();
    } catch (error) {
      toast.error('✗ Oda atanamadı');
    }
  };

  // NEW FEATURE 3: PASSPORT SCAN
  const openPassportScan = (booking) => {
    setSelectedBookingForPassport(booking);
    setPassportScanModalOpen(true);
  };

  const handlePassportScan = async (imageData) => {
    try {
      const res = await axios.post('/frontdesk/passport-scan', {
        image_data: imageData
      });
      toast.success('✓ Kimlik okundu');
      // Auto-fill guest data
      if (res.data.extracted_data) {
        toast.info(`${res.data.extracted_data.name} ${res.data.extracted_data.surname}`);
      }
      setPassportScanModalOpen(false);
    } catch (error) {
      toast.error('✗ Kimlik okunamadı');
    }
  };

  const handleImageUpload = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        const base64String = reader.result.split(',')[1];
        setPassportImage(base64String);
      };
      reader.readAsDataURL(file);
    }
  };

  // NEW FEATURE 4: KEYCARD ISSUE
  const openKeycardModal = (booking) => {
    setSelectedBookingForKeycard(booking);
    setKeycardModalOpen(true);
  };

  const issueKeycard = async () => {
    try {
      const res = await axios.post('/keycard/issue', {
        booking_id: selectedBookingForKeycard.id,
        card_type: keycardType,
        validity_hours: 48
      });
      toast.success(`✓ ${keycardType === 'physical' ? 'Fiziksel' : keycardType === 'mobile' ? 'Mobil' : 'QR'} kart basıldı`);
      toast.info(`Kart No: ${res.data.card_data}`);
      setKeycardModalOpen(false);
    } catch (error) {
      toast.error('✗ Kart basılamadı');
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
        {/* Quick Action Buttons - Row 1 */}
        <div className="grid grid-cols-4 gap-2">
          <Button
            size="sm"
            className="h-16 flex flex-col items-center justify-center bg-green-600 hover:bg-green-700 text-white p-1"
            onClick={() => {
              const arrivals = todayArrivals.filter(b => b.status === 'confirmed');
              if (arrivals.length > 0) {
                handleCheckIn(arrivals[0].id);
              } else {
                toast.error('⚠️ Giriş yapacak rezervasyon yok');
              }
            }}
          >
            <CheckCircle className="w-5 h-5 mb-1" />
            <span className="text-[10px] font-medium">Check-In</span>
          </Button>
          
          <Button
            size="sm"
            className="h-16 flex flex-col items-center justify-center bg-orange-600 hover:bg-orange-700 text-white p-1"
            onClick={() => {
              const departures = todayDepartures.filter(b => b.status === 'checked_in');
              if (departures.length > 0) {
                handleCheckOut(departures[0].id);
              } else {
                toast.error('⚠️ Çıkış yapacak rezervasyon yok');
              }
            }}
          >
            <XCircle className="w-5 h-5 mb-1" />
            <span className="text-[10px] font-medium">Check-Out</span>
          </Button>
          
          <Button
            size="sm"
            className="h-16 flex flex-col items-center justify-center bg-blue-600 hover:bg-blue-700 text-white p-1"
            onClick={() => navigate('/walk-in-booking')}
          >
            <UserPlus className="w-5 h-5 mb-1" />
            <span className="text-[10px] font-medium">Walk-In</span>
          </Button>
          
          <Button
            size="sm"
            className="h-16 flex flex-col items-center justify-center bg-red-600 hover:bg-red-700 text-white p-1"
            onClick={() => {
              // Mark no-show functionality
              const noShows = todayArrivals.filter(b => b.status === 'confirmed');
              if (noShows.length > 0) {
                toast.info('🔄 No-show işlemi hazırlanıyor...');
              } else {
                toast.error('⚠️ İşaretlenecek rezervasyon yok');
              }
            }}
          >
            <AlertCircle className="w-5 h-5 mb-1" />
            <span className="text-[10px] font-medium">No-Show</span>
          </Button>
        </div>

        {/* NEW FEATURES - Row 2 */}
        <div className="grid grid-cols-4 gap-2">
          <Button
            size="sm"
            className="h-16 flex flex-col items-center justify-center bg-purple-600 hover:bg-purple-700 text-white p-1"
            onClick={() => setSearchModalOpen(true)}
          >
            <Search className="w-5 h-5 mb-1" />
            <span className="text-[10px] font-medium">Arama</span>
          </Button>
          
          <Button
            size="sm"
            className="h-16 flex flex-col items-center justify-center bg-indigo-600 hover:bg-indigo-700 text-white p-1"
            onClick={() => {
              const confirmed = todayArrivals.filter(b => b.status === 'confirmed')[0];
              if (confirmed) openRoomAssignment(confirmed);
              else toast.error('⚠️ Oda atanacak rezervasyon yok');
            }}
          >
            <Home className="w-5 h-5 mb-1" />
            <span className="text-[10px] font-medium">Oda Ata</span>
          </Button>
          
          <Button
            size="sm"
            className="h-16 flex flex-col items-center justify-center bg-teal-600 hover:bg-teal-700 text-white p-1"
            onClick={() => {
              const confirmed = todayArrivals.filter(b => b.status === 'confirmed')[0];
              if (confirmed) openPassportScan(confirmed);
              else toast.error('⚠️ Kimlik okunacak rezervasyon yok');
            }}
          >
            <Camera className="w-5 h-5 mb-1" />
            <span className="text-[10px] font-medium">Kimlik</span>
          </Button>
          
          <Button
            size="sm"
            className="h-16 flex flex-col items-center justify-center bg-cyan-600 hover:bg-cyan-700 text-white p-1"
            onClick={() => {
              const checkedIn = inHouse[0];
              if (checkedIn) openKeycardModal(checkedIn);
              else toast.error('⚠️ Kart basılacak rezervasyon yok');
            }}
          >
            <Key className="w-5 h-5 mb-1" />
            <span className="text-[10px] font-medium">Kart Bas</span>
          </Button>
        </div>

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

        {/* Today's Arrivals - Collapsible */}
        <Card>
          <CardHeader 
            className="pb-3 cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => setArrivalsExpanded(!arrivalsExpanded)}
          >
            <CardTitle className="text-lg flex items-center justify-between">
              <div className="flex items-center">
                <UserPlus className="w-5 h-5 mr-2 text-blue-600" />
                Bugün Geliş Yapacaklar ({todayArrivals.length})
              </div>
              {arrivalsExpanded ? (
                <ChevronUp className="w-5 h-5 text-gray-400" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-400" />
              )}
            </CardTitle>
          </CardHeader>
          {arrivalsExpanded && (
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
                        {booking.guests_count || 1} kişi • {booking.check_out}
                      </p>
                    </div>
                    <div className="flex flex-col items-end space-y-2">
                      <Badge className="bg-blue-500 text-xs">{booking.source}</Badge>
                      <Button
                        size="sm"
                        onClick={() => handleCheckIn(booking.id)}
                        className="bg-green-600 hover:bg-green-700 text-xs px-2 py-1"
                      >
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Check-In
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          )}
        </Card>

        {/* Today's Departures - Collapsible */}
        <Card>
          <CardHeader 
            className="pb-3 cursor-pointer hover:bg-gray-50 transition-colors"
            onClick={() => setDeparturesExpanded(!departuresExpanded)}
          >
            <CardTitle className="text-lg flex items-center justify-between">
              <div className="flex items-center">
                <XCircle className="w-5 h-5 mr-2 text-orange-600" />
                Bugün Çıkış Yapacaklar ({todayDepartures.length})
              </div>
              {departuresExpanded ? (
                <ChevronUp className="w-5 h-5 text-gray-400" />
              ) : (
                <ChevronDown className="w-5 h-5 text-gray-400" />
              )}
            </CardTitle>
          </CardHeader>
          {departuresExpanded && (
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
                        {booking.guests_count || 1} kişi • ₺{booking.total_amount || 0}
                      </p>
                    </div>
                    <div className="flex flex-col items-end space-y-2">
                      <Badge className="bg-orange-500 text-xs">Konaklıyor</Badge>
                      <Button
                        size="sm"
                        onClick={() => handleCheckOut(booking.id)}
                        className="bg-red-600 hover:bg-red-700 text-xs px-2 py-1"
                      >
                        <CheckCircle className="w-3 h-3 mr-1" />
                        Check-Out
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          )}
        </Card>

        {/* Quick Actions */}
        <Card className="bg-gradient-to-r from-green-50 to-blue-50">
          <CardContent className="p-4">
            <div className="grid grid-cols-2 gap-3">
              <Button
                className="h-20 flex flex-col items-center justify-center bg-green-600 hover:bg-green-700"
                onClick={() => setReservationsModalOpen(true)}
              >
                <Calendar className="w-6 h-6 mb-1" />
                <span className="text-xs">Rezervasyonlar</span>
              </Button>
              <Button
                className="h-20 flex flex-col items-center justify-center"
                variant="outline"
                onClick={() => setRoomStatusModalOpen(true)}
              >
                <Bed className="w-6 h-6 mb-1" />
                <span className="text-xs">Oda Durumu</span>
              </Button>
              <Button
                className="h-20 flex flex-col items-center justify-center bg-orange-600 hover:bg-orange-700"
                onClick={loadGuestAlerts}
              >
                <Star className="w-6 h-6 mb-1" />
                <span className="text-xs">Misafir Uyarıları</span>
              </Button>
              <Button
                className="h-20 flex flex-col items-center justify-center bg-blue-600 hover:bg-blue-700"
                onClick={() => setFeeCalculatorModalOpen(true)}
              >
                <DollarSign className="w-6 h-6 mb-1" />
                <span className="text-xs">Ücret Hesapla</span>
              </Button>
              <Button
                className="h-20 flex flex-col items-center justify-center bg-purple-600 hover:bg-purple-700"
                onClick={() => {
                  setRoomFilterModalOpen(true);
                  loadFilteredRooms(roomFilters);
                }}
              >
                <Filter className="w-6 h-6 mb-1" />
                <span className="text-xs">Oda Filtrele</span>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Reservations Modal */}
      <Dialog open={reservationsModalOpen} onOpenChange={setReservationsModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center">
              <Calendar className="w-5 h-5 mr-2" />
              Tüm Rezervasyonlar ({allBookings.length})
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            {allBookings.map((booking) => (
              <div key={booking.id} className="p-3 bg-gray-50 rounded-lg border">
                <div className="flex items-center justify-between mb-2">
                  <p className="font-bold text-gray-900">{booking.guest_name}</p>
                  <Badge className={{
                    'confirmed': 'bg-blue-500',
                    'checked_in': 'bg-green-500',
                    'checked_out': 'bg-gray-500',
                    'cancelled': 'bg-red-500'
                  }[booking.status] || 'bg-gray-500'}>
                    {booking.status}
                  </Badge>
                </div>
                <div className="text-sm text-gray-600">
                  <p>Oda: {booking.room_number || 'TBA'}</p>
                  <p>Giriş: {booking.check_in ? new Date(booking.check_in).toLocaleDateString('tr-TR') : 'N/A'}</p>
                  <p>Çıkış: {booking.check_out ? new Date(booking.check_out).toLocaleDateString('tr-TR') : 'N/A'}</p>
                  <p>Tutar: ₺{booking.total_amount || 0}</p>
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* Room Status Modal */}
      <Dialog open={roomStatusModalOpen} onOpenChange={setRoomStatusModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center">
              <Bed className="w-5 h-5 mr-2" />
              Oda Durumu ({allRooms.length})
            </DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            {allRooms.map((room) => (
              <div key={room.id} className="p-3 bg-gray-50 rounded-lg border">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="font-bold text-gray-900">Oda {room.room_number}</p>
                    <p className="text-sm text-gray-600">{room.room_type}</p>
                  </div>
                  <Badge className={{
                    'available': 'bg-green-500',
                    'occupied': 'bg-blue-500',
                    'dirty': 'bg-red-500',
                    'cleaning': 'bg-yellow-500',
                    'inspected': 'bg-purple-500',
                    'maintenance': 'bg-orange-500'
                  }[room.status] || 'bg-gray-500'}>
                    {room.status}
                  </Badge>
                </div>
              </div>
            ))}
          </div>
        </DialogContent>
      </Dialog>

      {/* Guest Alerts Modal */}
      <Dialog open={guestAlertsModalOpen} onOpenChange={setGuestAlertsModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>⭐ Misafir Uyarıları ({guestAlerts.length})</DialogTitle>
          </DialogHeader>
          <div className="space-y-2">
            {guestAlerts.length === 0 ? (
              <p className="text-center text-gray-500 py-8">Uyarı yok</p>
            ) : (
              guestAlerts.map((alert, idx) => (
                <Card key={idx} className={`border-2 ${
                  alert.priority === 'high' ? 'border-red-300 bg-red-50' :
                  alert.priority === 'medium' ? 'border-yellow-300 bg-yellow-50' :
                  'border-blue-300 bg-blue-50'
                }`}>
                  <CardContent className="p-3">
                    <div className="flex items-start space-x-2">
                      <span className="text-2xl">{alert.icon}</span>
                      <div className="flex-1">
                        <div className="flex items-center justify-between mb-1">
                          <p className="font-bold text-gray-900">{alert.guest_name}</p>
                          <Badge>{alert.type}</Badge>
                        </div>
                        <p className="text-sm text-gray-700 mb-1">{alert.message}</p>
                        <p className="text-xs text-gray-600">Oda: {alert.room_number}</p>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Fee Calculator Modal */}
      <Dialog open={feeCalculatorModalOpen} onOpenChange={setFeeCalculatorModalOpen}>
        <DialogContent className="max-w-full w-[95vw]">
          <DialogHeader>
            <DialogTitle>💰 Ücret Hesaplayıcı</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Rezervasyon Seçin</Label>
              <select 
                className="w-full p-2 border rounded mt-1"
                onChange={(e) => {
                  const booking = [...todayArrivals, ...todayDepartures].find(b => b.id === e.target.value);
                  setSelectedBookingForFee(booking);
                  setCalculatedFees(null);
                }}
              >
                <option value="">Seçin...</option>
                {[...todayArrivals, ...todayDepartures].map(booking => (
                  <option key={booking.id} value={booking.id}>
                    {booking.guest_name} - Oda {booking.room_number}
                  </option>
                ))}
              </select>
            </div>

            {selectedBookingForFee && (
              <>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <Label>Erken Check-in Saati</Label>
                    <Input 
                      type="time" 
                      onChange={(e) => calculateFees(selectedBookingForFee, e.target.value, null)}
                    />
                  </div>
                  <div>
                    <Label>Geç Check-out Saati</Label>
                    <Input 
                      type="time" 
                      onChange={(e) => calculateFees(selectedBookingForFee, null, e.target.value)}
                    />
                  </div>
                </div>

                {calculatedFees && (
                  <Card className="bg-green-50 border-green-200">
                    <CardContent className="p-4">
                      <p className="font-bold text-lg mb-2">Hesaplanan Ücretler:</p>
                      {calculatedFees.early_checkin_fee > 0 && (
                        <div className="mb-2">
                          <p className="text-sm text-gray-700">Erken Check-in:</p>
                          <p className="text-lg font-bold text-green-700">₺{calculatedFees.early_checkin_fee}</p>
                          <p className="text-xs text-gray-600">{calculatedFees.early_checkin_reason}</p>
                        </div>
                      )}
                      {calculatedFees.late_checkout_fee > 0 && (
                        <div className="mb-2">
                          <p className="text-sm text-gray-700">Geç Check-out:</p>
                          <p className="text-lg font-bold text-green-700">₺{calculatedFees.late_checkout_fee}</p>
                          <p className="text-xs text-gray-600">{calculatedFees.late_checkout_reason}</p>
                        </div>
                      )}
                      <div className="border-t pt-2 mt-2">
                        <p className="text-sm text-gray-700">Toplam Ek Ücret:</p>
                        <p className="text-2xl font-bold text-green-700">₺{calculatedFees.total_additional_fees}</p>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Room Filter Modal */}
      <Dialog open={roomFilterModalOpen} onOpenChange={setRoomFilterModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>🔍 Oda Filtrele</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-3 gap-3">
              <div>
                <Label>Yatak Tipi</Label>
                <select 
                  className="w-full p-2 border rounded mt-1"
                  value={roomFilters.bed_type}
                  onChange={(e) => {
                    const newFilters = {...roomFilters, bed_type: e.target.value};
                    setRoomFilters(newFilters);
                    loadFilteredRooms(newFilters);
                  }}
                >
                  <option value="">Tümü</option>
                  <option value="single">Tek</option>
                  <option value="double">Çift</option>
                  <option value="twin">İkiz</option>
                  <option value="king">King</option>
                  <option value="queen">Queen</option>
                </select>
              </div>
              <div>
                <Label>Kat</Label>
                <Input 
                  type="number"
                  value={roomFilters.floor}
                  onChange={(e) => {
                    const newFilters = {...roomFilters, floor: e.target.value};
                    setRoomFilters(newFilters);
                    loadFilteredRooms(newFilters);
                  }}
                />
              </div>
              <div>
                <Label>Durum</Label>
                <select 
                  className="w-full p-2 border rounded mt-1"
                  value={roomFilters.status}
                  onChange={(e) => {
                    const newFilters = {...roomFilters, status: e.target.value};
                    setRoomFilters(newFilters);
                    loadFilteredRooms(newFilters);
                  }}
                >
                  <option value="">Tümü</option>
                  <option value="available">Müsait</option>
                  <option value="occupied">Dolu</option>
                  <option value="dirty">Kirli</option>
                  <option value="cleaning">Temizleniyor</option>
                </select>
              </div>
            </div>

            <div className="space-y-2">
              <p className="font-bold">Sonuçlar ({filteredRooms.length})</p>
              {filteredRooms.map((room) => (
                <div key={room.id} className="p-3 bg-gray-50 rounded-lg border">
                  <div className="flex items-center justify-between">
                    <div>
                      <p className="font-bold text-gray-900">Oda {room.room_number}</p>
                      <p className="text-sm text-gray-600">{room.room_type} • {room.bed_type} • Kat {room.floor}</p>
                    </div>
                    <Badge className={{
                      'available': 'bg-green-500',
                      'occupied': 'bg-blue-500',
                      'dirty': 'bg-red-500',
                      'cleaning': 'bg-yellow-500'
                    }[room.status] || 'bg-gray-500'}>
                      {room.status}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* NEW FEATURE 1: SEARCH MODAL */}
      <Dialog open={searchModalOpen} onOpenChange={setSearchModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>🔍 Rezervasyon Ara</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="Ad, Soyad, Tel, Email veya Rezervasyon No"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
              />
              <Button onClick={handleSearch} className="bg-purple-600">
                <Search className="w-4 h-4" />
              </Button>
            </div>
            
            <div className="space-y-2">
              {searchResults.length === 0 ? (
                <p className="text-center text-gray-500 py-4">Arama yapın veya sonuç bulunamadı</p>
              ) : (
                searchResults.map(booking => (
                  <Card key={booking.id} className="border-l-4 border-purple-500">
                    <CardContent className="p-3">
                      <div className="flex justify-between items-start">
                        <div>
                          <p className="font-bold">{booking.guest_name}</p>
                          <p className="text-sm text-gray-600">
                            {booking.check_in} - {booking.check_out}
                          </p>
                          <p className="text-xs text-gray-500">
                            {booking.guest_phone} • {booking.guest_email}
                          </p>
                        </div>
                        <Badge className={
                          booking.status === 'checked_in' ? 'bg-green-500' :
                          booking.status === 'confirmed' ? 'bg-blue-500' :
                          'bg-gray-500'
                        }>
                          {booking.status}
                        </Badge>
                      </div>
                      <div className="flex gap-2 mt-2">
                        {booking.status === 'confirmed' && (
                          <>
                            <Button size="sm" onClick={() => {openRoomAssignment(booking); setSearchModalOpen(false);}}>
                              Oda Ata
                            </Button>
                            <Button size="sm" onClick={() => {openPassportScan(booking); setSearchModalOpen(false);}}>
                              Kimlik Oku
                            </Button>
                          </>
                        )}
                        {booking.status === 'checked_in' && (
                          <Button size="sm" onClick={() => {openKeycardModal(booking); setSearchModalOpen(false);}}>
                            Kart Bas
                          </Button>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* NEW FEATURE 2: ROOM ASSIGNMENT MODAL */}
      <Dialog open={roomAssignModalOpen} onOpenChange={setRoomAssignModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>🏠 Oda Atama</DialogTitle>
          </DialogHeader>
          {selectedBookingForRoom && (
            <div className="space-y-4">
              <Card className="bg-blue-50">
                <CardContent className="p-3">
                  <p className="font-bold">{selectedBookingForRoom.guest_name}</p>
                  <p className="text-sm text-gray-600">
                    {selectedBookingForRoom.check_in} - {selectedBookingForRoom.check_out}
                  </p>
                </CardContent>
              </Card>
              
              <div className="space-y-2">
                <p className="font-semibold">Müsait Odalar:</p>
                {availableRooms.length === 0 ? (
                  <p className="text-center text-gray-500 py-4">Müsait oda bulunamadı</p>
                ) : (
                  availableRooms.map(room => (
                    <Card key={room.id} className="border hover:border-indigo-500 cursor-pointer" onClick={() => assignRoom(room.id)}>
                      <CardContent className="p-3">
                        <div className="flex justify-between items-center">
                          <div>
                            <p className="font-bold text-lg">{room.room_number}</p>
                            <p className="text-sm text-gray-600">{room.room_type}</p>
                            <p className="text-xs text-gray-500">{room.bed_type} • {room.floor}. Kat</p>
                          </div>
                          <div className="text-right">
                            <p className="text-xl font-bold text-green-600">₺{room.base_rate}</p>
                            <Badge className="bg-green-500">Müsait</Badge>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))
                )}
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* NEW FEATURE 3: PASSPORT SCAN MODAL */}
      <Dialog open={passportScanModalOpen} onOpenChange={setPassportScanModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>📷 Kimlik Okuma</DialogTitle>
          </DialogHeader>
          {selectedBookingForPassport && (
            <div className="space-y-4">
              <Card className="bg-teal-50">
                <CardContent className="p-3">
                  <p className="font-bold">{selectedBookingForPassport.guest_name}</p>
                  <p className="text-sm text-gray-600">
                    {selectedBookingForPassport.check_in}
                  </p>
                </CardContent>
              </Card>
              
              <div className="space-y-3">
                <Label>Kimlik/Pasaport Fotoğrafı</Label>
                <Input 
                  type="file" 
                  accept="image/*" 
                  capture="environment"
                  onChange={handleImageUpload}
                  className="cursor-pointer"
                />
                
                {passportImage && (
                  <div className="relative">
                    <img 
                      src={`data:image/jpeg;base64,${passportImage}`} 
                      alt="Passport" 
                      className="w-full rounded border"
                    />
                  </div>
                )}
                
                <Button 
                  className="w-full bg-teal-600 hover:bg-teal-700"
                  disabled={!passportImage}
                  onClick={() => handlePassportScan(passportImage)}
                >
                  <Camera className="w-4 h-4 mr-2" />
                  Kimlik Oku
                </Button>
                
                <p className="text-xs text-gray-500 text-center">
                  * OCR teknolojisi ile otomatik bilgi çıkarma
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* NEW FEATURE 4: KEYCARD MODAL */}
      <Dialog open={keycardModalOpen} onOpenChange={setKeycardModalOpen}>
        <DialogContent className="max-w-full w-[95vw] max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>🔑 Kart Basma</DialogTitle>
          </DialogHeader>
          {selectedBookingForKeycard && (
            <div className="space-y-4">
              <Card className="bg-cyan-50">
                <CardContent className="p-3">
                  <p className="font-bold">{selectedBookingForKeycard.guest_name}</p>
                  <p className="text-sm text-gray-600">
                    Oda: {selectedBookingForKeycard.room_number || 'Atanmadı'}
                  </p>
                </CardContent>
              </Card>
              
              <div className="space-y-3">
                <Label>Kart Tipi Seçin</Label>
                <div className="grid grid-cols-3 gap-2">
                  <Card 
                    className={`cursor-pointer border-2 ${keycardType === 'physical' ? 'border-cyan-600 bg-cyan-50' : 'border-gray-200'}`}
                    onClick={() => setKeycardType('physical')}
                  >
                    <CardContent className="p-4 text-center">
                      <CreditCard className="w-8 h-8 mx-auto mb-2 text-cyan-600" />
                      <p className="text-sm font-semibold">Fiziksel Kart</p>
                      <p className="text-xs text-gray-500">RFID</p>
                    </CardContent>
                  </Card>
                  
                  <Card 
                    className={`cursor-pointer border-2 ${keycardType === 'mobile' ? 'border-cyan-600 bg-cyan-50' : 'border-gray-200'}`}
                    onClick={() => setKeycardType('mobile')}
                  >
                    <CardContent className="p-4 text-center">
                      <Key className="w-8 h-8 mx-auto mb-2 text-cyan-600" />
                      <p className="text-sm font-semibold">Mobil Anahtar</p>
                      <p className="text-xs text-gray-500">Bluetooth</p>
                    </CardContent>
                  </Card>
                  
                  <Card 
                    className={`cursor-pointer border-2 ${keycardType === 'qr' ? 'border-cyan-600 bg-cyan-50' : 'border-gray-200'}`}
                    onClick={() => setKeycardType('qr')}
                  >
                    <CardContent className="p-4 text-center">
                      <QrCode className="w-8 h-8 mx-auto mb-2 text-cyan-600" />
                      <p className="text-sm font-semibold">QR Kod</p>
                      <p className="text-xs text-gray-500">Geçici</p>
                    </CardContent>
                  </Card>
                </div>
                
                <Button 
                  className="w-full bg-cyan-600 hover:bg-cyan-700"
                  onClick={issueKeycard}
                >
                  <Key className="w-4 h-4 mr-2" />
                  Kart Bas (48 saat geçerli)
                </Button>
                
                <div className="bg-yellow-50 border border-yellow-200 rounded p-3">
                  <p className="text-xs text-yellow-800">
                    <strong>Not:</strong> Kartlar otomatik olarak check-out zamanına kadar geçerlidir. 
                    Erken çıkış durumunda kart manuel olarak iptal edilmelidir.
                  </p>
                </div>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default MobileFrontDesk;