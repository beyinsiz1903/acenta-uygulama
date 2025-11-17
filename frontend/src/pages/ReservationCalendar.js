import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { 
  ChevronLeft, 
  ChevronRight, 
  Calendar as CalendarIcon,
  User,
  Building2,
  Clock,
  Plus,
  TrendingUp,
  Info
} from 'lucide-react';

const ReservationCalendar = ({ user, tenant, onLogout }) => {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [rooms, setRooms] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [guests, setGuests] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [loading, setLoading] = useState(true);
  const [daysToShow, setDaysToShow] = useState(14); // 2 weeks view
  
  // Dialog states
  const [showNewBookingDialog, setShowNewBookingDialog] = useState(false);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedRoom, setSelectedRoom] = useState(null);
  
  // Drag & Drop state
  const [draggingBooking, setDraggingBooking] = useState(null);
  const [dragOverCell, setDragOverCell] = useState(null);
  
  // Room Move state
  const [showMoveReasonDialog, setShowMoveReasonDialog] = useState(false);
  const [moveData, setMoveData] = useState(null);
  const [moveReason, setMoveReason] = useState('');
  
  // Find Room state
  const [showFindRoomDialog, setShowFindRoomDialog] = useState(false);
  const [findRoomCriteria, setFindRoomCriteria] = useState({
    check_in: '',
    check_out: '',
    room_type: 'all',
    guests_count: 2
  });
  const [availableRooms, setAvailableRooms] = useState([]);
  
  // New booking form
  const [newBooking, setNewBooking] = useState({
    guest_id: '',
    room_id: '',
    check_in: '',
    check_out: '',
    guests_count: 2,
    adults: 2,
    children: 0,
    children_ages: [],
    total_amount: 0,
    status: 'confirmed'
  });
  
  // Conflicts state
  const [conflicts, setConflicts] = useState([]);

  useEffect(() => {
    loadCalendarData();
  }, [currentDate, daysToShow]);

  const loadCalendarData = async () => {
    setLoading(true);
    try {
      const [roomsRes, bookingsRes, guestsRes, companiesRes] = await Promise.all([
        axios.get('/pms/rooms'),
        axios.get('/pms/bookings'),
        axios.get('/pms/guests').catch(() => ({ data: [] })),
        axios.get('/companies').catch(() => ({ data: [] }))
      ]);

      setRooms(roomsRes.data || []);
      setBookings(bookingsRes.data || []);
      setGuests(guestsRes.data || []);
      setCompanies(companiesRes.data || []);
    } catch (error) {
      console.error('Failed to load calendar data:', error);
      toast.error('Failed to load calendar data');
    } finally {
      setLoading(false);
    }
  };

  // Handle cell click - Open new booking dialog
  const handleCellClick = (roomId, date) => {
    const room = rooms.find(r => r.id === roomId);
    if (!room) return;
    
    setSelectedRoom(room);
    setSelectedDate(date);
    
    const checkInDate = new Date(date);
    const checkOutDate = new Date(date);
    checkOutDate.setDate(checkOutDate.getDate() + 1);
    
    setNewBooking({
      guest_id: '',
      room_id: roomId,
      check_in: checkInDate.toISOString().split('T')[0],
      check_out: checkOutDate.toISOString().split('T')[0],
      guests_count: 2,
      adults: 2,
      children: 0,
      children_ages: [],
      total_amount: room.base_price || 100,
      status: 'confirmed'
    });
    
    setShowNewBookingDialog(true);
  };

  // Handle booking double-click - Show details
  const handleBookingDoubleClick = (booking) => {
    setSelectedBooking(booking);
    setShowDetailsDialog(true);
  };

  // Handle new booking submit
  const handleCreateBooking = async (e) => {
    e.preventDefault();
    
    if (!newBooking.guest_id) {
      toast.error('Please select a guest');
      return;
    }
    
    try {
      await axios.post('/pms/bookings', newBooking);
      toast.success('Booking created successfully!');
      setShowNewBookingDialog(false);
      loadCalendarData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create booking');
    }
  };

  // Drag & Drop handlers
  const handleDragStart = (e, booking) => {
    setDraggingBooking(booking);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e, roomId, date) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverCell({ roomId, date: date.toISOString() });
  };

  const handleDragLeave = () => {
    setDragOverCell(null);
  };

  const handleDrop = async (e, newRoomId, newDate) => {
    e.preventDefault();
    setDragOverCell(null);
    
    if (!draggingBooking) return;
    
    const daysDiff = Math.ceil((new Date(draggingBooking.check_out) - new Date(draggingBooking.check_in)) / (1000 * 60 * 60 * 24));
    
    const newCheckIn = new Date(newDate);
    const newCheckOut = new Date(newDate);
    newCheckOut.setDate(newCheckOut.getDate() + daysDiff);
    
    try {
      await axios.put(`/pms/bookings/${draggingBooking.id}`, {
        ...draggingBooking,
        room_id: newRoomId,
        check_in: newCheckIn.toISOString().split('T')[0],
        check_out: newCheckOut.toISOString().split('T')[0]
      });
      
      toast.success('Booking moved successfully!');
      loadCalendarData();
    } catch (error) {
      toast.error('Failed to move booking');
    }
    
    setDraggingBooking(null);
  };

  const handleDragEnd = () => {
    setDraggingBooking(null);
    setDragOverCell(null);
  };

  // Calculate occupancy for each date
  const getOccupancyForDate = (date) => {
    const occupiedCount = bookings.filter(b => 
      isBookingOnDate(b, date) && b.status === 'checked_in'
    ).length;
    
    return rooms.length > 0 ? Math.round((occupiedCount / rooms.length) * 100) : 0;
  };

  // Calculate forecast occupancy (next 14 days avg)
  const getForecastOccupancy = () => {
    const forecastDates = [];
    const today = new Date();
    
    for (let i = 0; i < 14; i++) {
      const date = new Date(today);
      date.setDate(today.getDate() + i);
      forecastDates.push(date);
    }
    
    const avgOccupancy = forecastDates.reduce((sum, date) => {
      return sum + getOccupancyForDate(date);
    }, 0) / forecastDates.length;
    
    return Math.round(avgOccupancy);
  };

  // Detect conflicts (overbooking, overlaps)
  const detectConflicts = () => {
    const detectedConflicts = [];
    
    rooms.forEach(room => {
      const roomBookings = bookings.filter(b => b.room_id === room.id);
      
      // Check for overlapping bookings
      for (let i = 0; i < roomBookings.length; i++) {
        for (let j = i + 1; j < roomBookings.length; j++) {
          const booking1 = roomBookings[i];
          const booking2 = roomBookings[j];
          
          const start1 = new Date(booking1.check_in);
          const end1 = new Date(booking1.check_out);
          const start2 = new Date(booking2.check_in);
          const end2 = new Date(booking2.check_out);
          
          // Check if dates overlap
          if (start1 < end2 && start2 < end1) {
            detectedConflicts.push({
              type: 'overbooking',
              room_id: room.id,
              room_number: room.room_number,
              booking1_id: booking1.id,
              booking2_id: booking2.id,
              guest1: booking1.guest_name,
              guest2: booking2.guest_name,
              overlap_start: start1 > start2 ? start1 : start2,
              overlap_end: end1 < end2 ? end1 : end2
            });
          }
        }
      }
    });
    
    setConflicts(detectedConflicts);
    return detectedConflicts;
  };

  useEffect(() => {
    detectConflicts();
  }, [bookings]);

  // Check if a room/date has conflict
  const hasConflict = (roomId, date) => {
    return conflicts.some(c => 
      c.room_id === roomId && 
      date >= new Date(c.overlap_start) && 
      date < new Date(c.overlap_end)
    );
  };

  // Find available rooms
  const handleFindRoom = async () => {
    if (!findRoomCriteria.check_in || !findRoomCriteria.check_out) {
      toast.error('Please select check-in and check-out dates');
      return;
    }
    
    const checkIn = new Date(findRoomCriteria.check_in);
    const checkOut = new Date(findRoomCriteria.check_out);
    
    const available = rooms.filter(room => {
      // Filter by room type if specified
      if (findRoomCriteria.room_type !== 'all' && room.room_type !== findRoomCriteria.room_type) {
        return false;
      }
      
      // Filter by capacity
      if (room.capacity < findRoomCriteria.guests_count) {
        return false;
      }
      
      // Check if room is available for the date range
      const roomBookings = bookings.filter(b => b.room_id === room.id);
      const isAvailable = !roomBookings.some(booking => {
        const bStart = new Date(booking.check_in);
        const bEnd = new Date(booking.check_out);
        return checkIn < bEnd && checkOut > bStart;
      });
      
      return isAvailable;
    });
    
    setAvailableRooms(available);
  };

  // Generate date range
  const getDateRange = () => {
    const dates = [];
    const start = new Date(currentDate);
    start.setHours(0, 0, 0, 0);

    for (let i = 0; i < daysToShow; i++) {
      const date = new Date(start);
      date.setDate(start.getDate() + i);
      dates.push(date);
    }
    return dates;
  };

  const dateRange = getDateRange();

  // Check if booking overlaps with date
  const isBookingOnDate = (booking, date) => {
    const checkIn = new Date(booking.check_in);
    const checkOut = new Date(booking.check_out);
    const current = new Date(date);
    
    checkIn.setHours(0, 0, 0, 0);
    checkOut.setHours(0, 0, 0, 0);
    current.setHours(0, 0, 0, 0);

    return current >= checkIn && current < checkOut;
  };

  // Get booking for room on specific date
  const getBookingForRoomOnDate = (roomId, date) => {
    return bookings.find(booking => 
      booking.room_id === roomId && isBookingOnDate(booking, date)
    );
  };

  // Calculate booking span width (how many days)
  const calculateBookingSpan = (booking, startDate) => {
    const checkIn = new Date(booking.check_in);
    const checkOut = new Date(booking.check_out);
    const rangeStart = new Date(startDate);
    const rangeEnd = new Date(startDate);
    rangeEnd.setDate(rangeEnd.getDate() + daysToShow);

    checkIn.setHours(0, 0, 0, 0);
    checkOut.setHours(0, 0, 0, 0);
    rangeStart.setHours(0, 0, 0, 0);
    rangeEnd.setHours(0, 0, 0, 0);

    const effectiveStart = checkIn < rangeStart ? rangeStart : checkIn;
    const effectiveEnd = checkOut > rangeEnd ? rangeEnd : checkOut;

    const nights = Math.ceil((effectiveEnd - effectiveStart) / (1000 * 60 * 60 * 24));
    return Math.max(1, nights);
  };

  // Check if booking starts on this date
  const isBookingStart = (booking, date) => {
    const checkIn = new Date(booking.check_in);
    const current = new Date(date);
    
    checkIn.setHours(0, 0, 0, 0);
    current.setHours(0, 0, 0, 0);

    return checkIn.getTime() === current.getTime();
  };

  const getStatusColor = (status) => {
    const colors = {
      confirmed: 'bg-blue-500',
      checked_in: 'bg-green-500',
      checked_out: 'bg-gray-400',
      cancelled: 'bg-red-500',
      guaranteed: 'bg-purple-500'
    };
    return colors[status] || 'bg-gray-500';
  };

  const getStatusLabel = (status) => {
    const labels = {
      confirmed: 'Confirmed',
      checked_in: 'In-House',
      checked_out: 'Departed',
      cancelled: 'Cancelled',
      guaranteed: 'Guaranteed'
    };
    return labels[status] || status;
  };

  const navigatePrevious = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() - daysToShow);
    setCurrentDate(newDate);
  };

  const navigateNext = () => {
    const newDate = new Date(currentDate);
    newDate.setDate(newDate.getDate() + daysToShow);
    setCurrentDate(newDate);
  };

  const goToToday = () => {
    setCurrentDate(new Date());
  };

  const formatDate = (date) => {
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
  };

  const formatDateWithDay = (date) => {
    return date.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
  };

  const isToday = (date) => {
    const today = new Date();
    return date.toDateString() === today.toDateString();
  };

  if (loading) {
    return (
      <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="pms">
        <div className="flex items-center justify-center h-screen">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="pms">
      <div className="p-6 space-y-4">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold" style={{ fontFamily: 'Space Grotesk' }}>
              Reservation Calendar
            </h1>
            <p className="text-gray-600 mt-1">Timeline view of all bookings</p>
          </div>
          <div className="flex items-center space-x-2">
            <select
              className="border rounded-md px-3 py-2"
              value={daysToShow}
              onChange={(e) => setDaysToShow(Number(e.target.value))}
            >
              <option value={7}>7 Days</option>
              <option value={14}>14 Days</option>
              <option value={30}>30 Days</option>
            </select>
            <Button variant="outline" onClick={goToToday}>
              <CalendarIcon className="w-4 h-4 mr-2" />
              Today
            </Button>
            <Button variant="outline" onClick={navigatePrevious}>
              <ChevronLeft className="w-4 h-4" />
            </Button>
            <Button variant="outline" onClick={navigateNext}>
              <ChevronRight className="w-4 h-4" />
            </Button>
          </div>
        </div>

        {/* Occupancy Bar */}
        <Card>
          <CardContent className="py-4">
            <div className="space-y-3">
              <div className="flex items-center justify-between">
                <div>
                  <h3 className="text-sm font-semibold text-gray-700">Occupancy Overview</h3>
                  <p className="text-xs text-gray-500">Hover over dates to see occupancy %</p>
                </div>
                <div className="flex items-center space-x-4">
                  <div className="text-center">
                    <div className="text-2xl font-bold text-blue-600">{getOccupancyForDate(new Date())}%</div>
                    <div className="text-xs text-gray-600">Today</div>
                  </div>
                  <div className="text-center">
                    <div className="text-2xl font-bold text-green-600">{getForecastOccupancy()}%</div>
                    <div className="text-xs text-gray-600 flex items-center">
                      <TrendingUp className="w-3 h-3 mr-1" />
                      14-Day Forecast
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Occupancy bars for visible dates */}
              <div className="flex space-x-1">
                {dateRange.map((date, idx) => {
                  const occ = getOccupancyForDate(date);
                  const isCurrentDate = isToday(date);
                  
                  return (
                    <div
                      key={idx}
                      className="flex-1 relative group"
                      title={`${formatDate(date)}: ${occ}% occupancy`}
                    >
                      <div className="h-8 bg-gray-200 rounded overflow-hidden">
                        <div
                          className={`h-full transition-all ${
                            occ >= 90 ? 'bg-red-500' :
                            occ >= 75 ? 'bg-orange-500' :
                            occ >= 50 ? 'bg-yellow-500' :
                            'bg-green-500'
                          }`}
                          style={{ width: `${occ}%` }}
                        ></div>
                      </div>
                      {isCurrentDate && (
                        <div className="absolute -bottom-1 left-1/2 transform -translate-x-1/2 w-2 h-2 bg-blue-600 rounded-full"></div>
                      )}
                      <div className="absolute -bottom-6 left-1/2 transform -translate-x-1/2 text-xs text-gray-500 opacity-0 group-hover:opacity-100 whitespace-nowrap">
                        {occ}%
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Legend & Quick Tips */}
        <Card>
          <CardContent className="py-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-6 text-sm">
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 bg-blue-500 rounded"></div>
                  <span>Confirmed</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 bg-green-500 rounded"></div>
                  <span>In-House</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 bg-purple-500 rounded"></div>
                  <span>Guaranteed</span>
                </div>
                <div className="flex items-center space-x-2">
                  <div className="w-4 h-4 bg-gray-400 rounded"></div>
                  <span>Departed</span>
                </div>
              </div>
              <div className="flex items-center space-x-4 text-xs text-gray-600">
                <div className="flex items-center space-x-1">
                  <Plus className="w-3 h-3" />
                  <span>Click cell = New booking</span>
                </div>
                <div className="flex items-center space-x-1">
                  <Info className="w-3 h-3" />
                  <span>Double-click booking = Details</span>
                </div>
                <div className="flex items-center space-x-1">
                  <span>🖱️ Drag & drop = Move booking</span>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Calendar Grid */}
        <Card>
          <CardContent className="p-0 overflow-x-auto">
            <div className="min-w-max">
              {/* Date Header Row */}
              <div className="flex border-b bg-gray-50 sticky top-0 z-10">
                <div className="w-32 flex-shrink-0 p-3 border-r font-semibold">
                  Room
                </div>
                {dateRange.map((date, idx) => (
                  <div
                    key={idx}
                    className={`w-24 flex-shrink-0 p-2 border-r text-center text-sm ${
                      isToday(date) ? 'bg-blue-50 font-bold text-blue-600' : ''
                    }`}
                  >
                    <div>{formatDateWithDay(date)}</div>
                  </div>
                ))}
              </div>

              {/* Room Rows */}
              {rooms.length === 0 ? (
                <div className="p-12 text-center text-gray-500">
                  <CalendarIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No rooms available</p>
                </div>
              ) : (
                rooms.map((room) => (
                  <div key={room.id} className="flex border-b hover:bg-gray-50">
                    {/* Room Cell */}
                    <div className="w-32 flex-shrink-0 p-3 border-r">
                      <div className="font-semibold">{room.room_number}</div>
                      <div className="text-xs text-gray-600 capitalize">{room.room_type}</div>
                      <div className="text-xs text-gray-500">Floor {room.floor}</div>
                    </div>

                    {/* Timeline Cells */}
                    <div className="flex relative" style={{ width: `${daysToShow * 96}px` }}>
                      {dateRange.map((date, idx) => {
                        const booking = getBookingForRoomOnDate(room.id, date);
                        const isStart = booking && isBookingStart(booking, date);
                        const isDragOver = dragOverCell?.roomId === room.id && 
                                          new Date(dragOverCell.date).toDateString() === date.toDateString();

                        return (
                          <div
                            key={idx}
                            className={`w-24 flex-shrink-0 border-r relative cursor-pointer hover:bg-gray-100 transition-colors ${
                              isToday(date) ? 'bg-blue-50' : ''
                            } ${isDragOver ? 'bg-green-100 border-2 border-green-500' : ''}`}
                            style={{ height: '80px' }}
                            onClick={() => !booking && handleCellClick(room.id, date)}
                            onDragOver={(e) => handleDragOver(e, room.id, date)}
                            onDragLeave={handleDragLeave}
                            onDrop={(e) => handleDrop(e, room.id, date)}
                          >
                            {/* Empty cell indicator */}
                            {!booking && (
                              <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                                <Plus className="w-6 h-6 text-gray-400" />
                              </div>
                            )}
                            
                            {/* Booking bar */}
                            {isStart && booking && (
                              <div
                                draggable
                                onDragStart={(e) => handleDragStart(e, booking)}
                                onDragEnd={handleDragEnd}
                                onDoubleClick={() => handleBookingDoubleClick(booking)}
                                className={`absolute top-2 left-1 h-16 rounded ${getStatusColor(
                                  booking.status
                                )} text-white text-xs p-2 overflow-hidden shadow-md hover:shadow-lg transition-all cursor-move z-20 ${
                                  draggingBooking?.id === booking.id ? 'opacity-50' : ''
                                }`}
                                style={{
                                  width: `${calculateBookingSpan(booking, currentDate) * 96 - 8}px`,
                                }}
                                title={`Double-click for details | Drag to move\n${booking.guest_name || 'Guest'} - ${getStatusLabel(booking.status)}`}
                              >
                                <div className="font-semibold truncate">
                                  {booking.guest_name || 'Guest'}
                                </div>
                                <div className="text-xs opacity-90 flex items-center mt-1">
                                  <Clock className="w-3 h-3 mr-1" />
                                  {calculateBookingSpan(booking, currentDate)}n
                                </div>
                                {booking.company_name && (
                                  <div className="text-xs opacity-90 flex items-center mt-1 truncate">
                                    <Building2 className="w-3 h-3 mr-1" />
                                    {booking.company_name}
                                  </div>
                                )}
                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ))
              )}
            </div>
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-gray-600">Total Rooms</div>
              <div className="text-3xl font-bold">{rooms.length}</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-gray-600">Active Bookings</div>
              <div className="text-3xl font-bold text-blue-600">
                {bookings.filter(b => b.status === 'confirmed' || b.status === 'checked_in').length}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-gray-600">In-House</div>
              <div className="text-3xl font-bold text-green-600">
                {bookings.filter(b => b.status === 'checked_in').length}
              </div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="pt-6">
              <div className="text-sm text-gray-600">Occupancy Today</div>
              <div className="text-3xl font-bold text-purple-600">
                {rooms.length > 0
                  ? Math.round(
                      (bookings.filter(b => isBookingOnDate(b, new Date()) && b.status === 'checked_in')
                        .length /
                        rooms.length) *
                        100
                    )
                  : 0}
                %
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* New Booking Dialog */}
      <Dialog open={showNewBookingDialog} onOpenChange={setShowNewBookingDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Quick Booking</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleCreateBooking} className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Room</Label>
                <Input value={selectedRoom?.room_number || ''} disabled />
              </div>
              <div>
                <Label>Guest *</Label>
                <select
                  className="w-full border rounded-md p-2"
                  value={newBooking.guest_id}
                  onChange={(e) => setNewBooking({...newBooking, guest_id: e.target.value})}
                  required
                >
                  <option value="">Select guest...</option>
                  {guests.map(guest => (
                    <option key={guest.id} value={guest.id}>{guest.name}</option>
                  ))}
                </select>
              </div>
            </div>
            
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Check-in</Label>
                <Input
                  type="date"
                  value={newBooking.check_in}
                  onChange={(e) => setNewBooking({...newBooking, check_in: e.target.value})}
                  required
                />
              </div>
              <div>
                <Label>Check-out</Label>
                <Input
                  type="date"
                  value={newBooking.check_out}
                  onChange={(e) => setNewBooking({...newBooking, check_out: e.target.value})}
                  required
                />
              </div>
            </div>

            <div className="grid grid-cols-3 gap-4">
              <div>
                <Label>Adults</Label>
                <Input
                  type="number"
                  min="1"
                  value={newBooking.adults}
                  onChange={(e) => setNewBooking({
                    ...newBooking, 
                    adults: Number(e.target.value),
                    guests_count: Number(e.target.value) + newBooking.children
                  })}
                />
              </div>
              <div>
                <Label>Children</Label>
                <Input
                  type="number"
                  min="0"
                  value={newBooking.children}
                  onChange={(e) => setNewBooking({
                    ...newBooking, 
                    children: Number(e.target.value),
                    guests_count: newBooking.adults + Number(e.target.value)
                  })}
                />
              </div>
              <div>
                <Label>Total Amount</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={newBooking.total_amount}
                  onChange={(e) => setNewBooking({...newBooking, total_amount: Number(e.target.value)})}
                />
              </div>
            </div>

            <div>
              <Label>Status</Label>
              <select
                className="w-full border rounded-md p-2"
                value={newBooking.status}
                onChange={(e) => setNewBooking({...newBooking, status: e.target.value})}
              >
                <option value="confirmed">Confirmed</option>
                <option value="guaranteed">Guaranteed</option>
                <option value="checked_in">Checked-in</option>
              </select>
            </div>

            <div className="flex space-x-2 pt-4">
              <Button type="submit" className="flex-1">Create Booking</Button>
              <Button type="button" variant="outline" onClick={() => setShowNewBookingDialog(false)}>
                Cancel
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Booking Details Dialog */}
      <Dialog open={showDetailsDialog} onOpenChange={setShowDetailsDialog}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Booking Details</DialogTitle>
          </DialogHeader>
          {selectedBooking && (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-600">Guest Name</div>
                  <div className="text-lg font-semibold">{selectedBooking.guest_name}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Status</div>
                  <Badge className={getStatusColor(selectedBooking.status)}>
                    {getStatusLabel(selectedBooking.status)}
                  </Badge>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-600">Check-in</div>
                  <div className="font-semibold">{selectedBooking.check_in}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Check-out</div>
                  <div className="font-semibold">{selectedBooking.check_out}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-600">Room</div>
                  <div className="font-semibold">
                    {rooms.find(r => r.id === selectedBooking.room_id)?.room_number}
                  </div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Total Amount</div>
                  <div className="font-semibold">${selectedBooking.total_amount}</div>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-600">Adults</div>
                  <div className="font-semibold">{selectedBooking.adults}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Children</div>
                  <div className="font-semibold">{selectedBooking.children}</div>
                </div>
              </div>

              {selectedBooking.company_name && (
                <div>
                  <div className="text-sm text-gray-600">Company</div>
                  <div className="font-semibold">{selectedBooking.company_name}</div>
                </div>
              )}

              <div className="flex space-x-2 pt-4">
                <Button variant="outline" onClick={() => setShowDetailsDialog(false)}>
                  Close
                </Button>
                <Button variant="outline" onClick={() => {
                  setShowDetailsDialog(false);
                  // Navigate to booking edit or folio
                }}>
                  Edit Booking
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </Layout>
  );
};

export default ReservationCalendar;
