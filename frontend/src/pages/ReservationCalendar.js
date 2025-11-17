import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  ChevronLeft, 
  ChevronRight, 
  Calendar as CalendarIcon,
  User,
  Building2,
  Clock
} from 'lucide-react';

const ReservationCalendar = ({ user, tenant, onLogout }) => {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [rooms, setRooms] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [daysToShow, setDaysToShow] = useState(14); // 2 weeks view

  useEffect(() => {
    loadCalendarData();
  }, [currentDate, daysToShow]);

  const loadCalendarData = async () => {
    setLoading(true);
    try {
      const [roomsRes, bookingsRes] = await Promise.all([
        axios.get('/pms/rooms'),
        axios.get('/pms/bookings')
      ]);

      setRooms(roomsRes.data || []);
      setBookings(bookingsRes.data || []);
    } catch (error) {
      console.error('Failed to load calendar data:', error);
      toast.error('Failed to load calendar data');
    } finally {
      setLoading(false);
    }
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

        {/* Legend */}
        <Card>
          <CardContent className="py-3">
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

                        return (
                          <div
                            key={idx}
                            className={`w-24 flex-shrink-0 border-r relative ${
                              isToday(date) ? 'bg-blue-50' : ''
                            }`}
                            style={{ height: '80px' }}
                          >
                            {isStart && booking && (
                              <div
                                className={`absolute top-2 left-1 h-16 rounded ${getStatusColor(
                                  booking.status
                                )} text-white text-xs p-2 overflow-hidden shadow-md hover:shadow-lg transition-shadow cursor-pointer z-20`}
                                style={{
                                  width: `${calculateBookingSpan(booking, currentDate) * 96 - 8}px`,
                                }}
                                title={`${booking.guest_name || 'Guest'} - ${getStatusLabel(booking.status)}`}
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
    </Layout>
  );
};

export default ReservationCalendar;
