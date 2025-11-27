import { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '@/components/Layout';
import ReservationSidebar from '@/components/ReservationSidebar';
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
  Info,
  Search,
  AlertCircle,
  CheckCircle
} from 'lucide-react';

const ReservationCalendar = ({ user, tenant, onLogout }) => {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [rooms, setRooms] = useState([]);
  const [bookings, setBookings] = useState([]);
  const [guests, setGuests] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [roomBlocks, setRoomBlocks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [daysToShow, setDaysToShow] = useState(14); // 2 weeks view
  
  // Dialog states
  const [showNewBookingDialog, setShowNewBookingDialog] = useState(false);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [showSidebar, setShowSidebar] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [selectedBookingFolio, setSelectedBookingFolio] = useState(null);
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedRoom, setSelectedRoom] = useState(null);
  
  // Drag & Drop state
  const [draggingBooking, setDraggingBooking] = useState(null);
  const [dragOverCell, setDragOverCell] = useState(null);
  
  // Hover tooltip state for ADR/BAR display
  const [hoveredCell, setHoveredCell] = useState(null);
  const [cellRates, setCellRates] = useState({});
  
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
  
  // Enterprise Mode states
  const [rateLeakages, setRateLeakages] = useState([]);
  const [availabilityHeatmap, setAvailabilityHeatmap] = useState([]);
  const [showEnterprisePanel, setShowEnterprisePanel] = useState(false);
  
  // AI Mode states
  const [showAIPanel, setShowAIPanel] = useState(false);
  const [aiOverbookingSolutions, setAiOverbookingSolutions] = useState([]);
  const [aiRoomMoves, setAiRoomMoves] = useState([]);
  const [aiRateRecommendations, setAiRateRecommendations] = useState([]);
  const [aiNoShowPredictions, setAiNoShowPredictions] = useState([]);
  
  // Deluxe+ states
  const [showDeluxePanel, setShowDeluxePanel] = useState(false);
  const [groupBookings, setGroupBookings] = useState([]);
  const [pickupPaceData, setPickupPaceData] = useState(null);
  const [leadTimeData, setLeadTimeData] = useState(null);
  const [oversellProtection, setOversellProtection] = useState([]);
  const [channelMixData, setChannelMixData] = useState(null);
  
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
      const [roomsRes, bookingsRes, guestsRes, companiesRes, blocksRes] = await Promise.all([
        axios.get('/api/pms/rooms'),
        axios.get('/api/pms/bookings'),
        axios.get('/api/pms/guests').catch(() => ({ data: [] })),
        axios.get('/api/companies').catch(() => ({ data: [] })),
        axios.get('/api/pms/room-blocks?status=active').catch(() => ({ data: { blocks: [] } }))
      ]);

      setRooms(roomsRes.data || []);
      setBookings(bookingsRes.data || []);
      setGuests(guestsRes.data || []);
      setCompanies(companiesRes.data || []);
      setRoomBlocks(blocksRes.data.blocks || []);
      
      // Load Enterprise Mode data
      loadEnterpriseData();
    } catch (error) {
      console.error('Failed to load calendar data:', error);
      toast.error('Failed to load calendar data');
    } finally {
      setLoading(false);
    }
  };

  const loadEnterpriseData = async () => {
    try {
      const startDate = currentDate.toISOString().split('T')[0];
      const endDate = new Date(currentDate.getTime() + daysToShow * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      
      const [leakageRes, heatmapRes] = await Promise.all([
        axios.get(`/enterprise/rate-leakage?start_date=${startDate}&end_date=${endDate}`).catch(() => ({ data: { leakages: [] } })),
        axios.get(`/enterprise/availability-heatmap?start_date=${startDate}&end_date=${endDate}`).catch(() => ({ data: { heatmap: [] } }))
      ]);
      
      setRateLeakages(leakageRes.data.leakages || []);
      setAvailabilityHeatmap(heatmapRes.data.heatmap || []);
    } catch (error) {
      console.error('Failed to load enterprise data:', error);
    }
  };

  const loadAIRecommendations = async () => {
    try {
      const today = new Date().toISOString().split('T')[0];
      const startDate = currentDate.toISOString().split('T')[0];
      const endDate = new Date(currentDate.getTime() + daysToShow * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      
      const [overbookingRes, roomMovesRes, ratesRes, noShowRes] = await Promise.all([
        axios.post(`/ai/solve-overbooking`, { date: today }).catch(() => ({ data: { solutions: [] } })),
        axios.post(`/ai/recommend-room-moves`, { date: today }).catch(() => ({ data: { recommendations: [] } })),
        axios.post(`/ai/recommend-rates`, { start_date: startDate, end_date: endDate }).catch(() => ({ data: { recommendations: [] } })),
        axios.post(`/ai/predict-no-shows`, { date: today }).catch(() => ({ data: { predictions: [] } }))
      ]);
      
      setAiOverbookingSolutions(overbookingRes.data.solutions || []);
      setAiRoomMoves(roomMovesRes.data.recommendations || []);
      setAiRateRecommendations(ratesRes.data.recommendations || []);
      setAiNoShowPredictions(noShowRes.data.predictions || []);
    } catch (error) {
      console.error('Failed to load AI recommendations:', error);
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

  // Handle booking double-click - Show sidebar
  const handleBookingDoubleClick = async (booking) => {
    setSelectedBooking(booking);
    
    // Load folio data
    try {
      const folioRes = await axios.get(`/folio/booking/${booking.id}`);
      if (folioRes.data && folioRes.data.length > 0) {
        setSelectedBookingFolio(folioRes.data[0]);
      }
    } catch (error) {
      console.log('No folio found for this booking');
      setSelectedBookingFolio(null);
    }
    
    setShowSidebar(true);
  };

  // Handle new booking submit
  const handleCreateBooking = async (e) => {
    e.preventDefault();
    
    if (!newBooking.guest_id) {
      toast.error('Please select a guest');
      return;
    }
    
    try {
      await axios.post('/api/pms/bookings', newBooking);
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
    
    // Check if room is blocked
    const roomBlock = getRoomBlockForDate(newRoomId, newDate);
    if (roomBlock && !roomBlock.allow_sell) {
      toast.error(`Cannot move booking: Room is ${roomBlock.type.replace('_', ' ')} (${roomBlock.reason})`);
      setDraggingBooking(null);
      return;
    }
    
    // Check if actually moving to different room or date
    const oldRoomId = draggingBooking.room_id;
    const oldDate = new Date(draggingBooking.check_in);
    const isSameRoom = oldRoomId === newRoomId;
    const isSameDate = oldDate.toDateString() === newDate.toDateString();
    
    if (isSameRoom && isSameDate) {
      setDraggingBooking(null);
      return;
    }
    
    const daysDiff = Math.ceil((new Date(draggingBooking.check_out) - new Date(draggingBooking.check_in)) / (1000 * 60 * 60 * 24));
    
    const newCheckIn = new Date(newDate);
    const newCheckOut = new Date(newDate);
    newCheckOut.setDate(newCheckOut.getDate() + daysDiff);
    
    // Store move data and show reason dialog
    const oldRoom = rooms.find(r => r.id === oldRoomId);
    const newRoom = rooms.find(r => r.id === newRoomId);
    
    setMoveData({
      booking: draggingBooking,
      oldRoom: oldRoom?.room_number,
      newRoom: newRoom?.room_number,
      oldCheckIn: draggingBooking.check_in,
      newCheckIn: newCheckIn.toISOString().split('T')[0],
      newCheckOut: newCheckOut.toISOString().split('T')[0],
      newRoomId: newRoomId
    });
    
    setShowMoveReasonDialog(true);
    setDraggingBooking(null);
  };

  const handleConfirmMove = async () => {
    if (!moveReason.trim()) {
      toast.error('Please provide a reason for the room move');
      return;
    }
    
    console.log('🔄 Moving booking:', {
      bookingId: moveData.booking.id,
      from: `${moveData.oldRoom} (${moveData.oldCheckIn})`,
      to: `${moveData.newRoom} (${moveData.newCheckIn})`,
      currentDateView: currentDate.toISOString().split('T')[0]
    });
    
    try {
      // Update booking with new room and dates
      const updateResponse = await axios.put(`/pms/bookings/${moveData.booking.id}`, {
        ...moveData.booking,
        room_id: moveData.newRoomId,
        check_in: moveData.newCheckIn,
        check_out: moveData.newCheckOut
      });
      
      console.log('✅ Booking updated:', updateResponse.data);
      
      // Log room move history
      await axios.post('/api/pms/room-move-history', {
        booking_id: moveData.booking.id,
        old_room: moveData.oldRoom,
        new_room: moveData.newRoom,
        old_check_in: moveData.oldCheckIn,
        new_check_in: moveData.newCheckIn,
        reason: moveReason,
        moved_by: user.name,
        timestamp: new Date().toISOString()
      }).catch(err => console.log('History logging failed:', err));
      
      // Always navigate to the new booking date to ensure it's visible
      const newCheckIn = new Date(moveData.newCheckIn);
      console.log('📅 Navigating timeline to:', newCheckIn.toISOString().split('T')[0]);
      
      setShowMoveReasonDialog(false);
      setMoveReason('');
      setMoveData(null);
      
      // Set the new date FIRST, then reload data
      setCurrentDate(newCheckIn);
      
      toast.success(`Booking moved to ${moveData.newRoom} on ${newCheckIn.toLocaleDateString()}!`);
      
      // Small delay to ensure state update completes before reload
      setTimeout(() => {
        loadCalendarData();
      }, 100);
    } catch (error) {
      toast.error('Failed to move booking');
      console.error('Move booking error:', error);
    }
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

  // Get room block for room on specific date
  const getRoomBlockForDate = (roomId, date) => {
    return roomBlocks.find(block => {
      if (block.room_id !== roomId || block.status !== 'active') return false;
      
      const blockStart = new Date(block.start_date);
      const blockEnd = block.end_date ? new Date(block.end_date) : new Date('9999-12-31');
      const current = new Date(date);
      
      blockStart.setHours(0, 0, 0, 0);
      blockEnd.setHours(0, 0, 0, 0);
      current.setHours(0, 0, 0, 0);
      
      return current >= blockStart && current <= blockEnd;
    });
  };

  // Check if block starts on this date
  const isBlockStart = (block, date) => {
    const blockStart = new Date(block.start_date);
    const current = new Date(date);
    blockStart.setHours(0, 0, 0, 0);
    current.setHours(0, 0, 0, 0);
    return blockStart.getTime() === current.getTime();
  };

  // Calculate block span (how many days visible)
  const calculateBlockSpan = (block, startDate) => {
    const blockStart = new Date(block.start_date);
    const blockEnd = block.end_date ? new Date(block.end_date) : null;
    const rangeStart = new Date(startDate);
    const rangeEnd = new Date(rangeStart);
    rangeEnd.setDate(rangeEnd.getDate() + daysToShow);
    
    const visibleStart = blockStart > rangeStart ? blockStart : rangeStart;
    const visibleEnd = blockEnd && blockEnd < rangeEnd ? blockEnd : rangeEnd;
    
    const days = Math.ceil((visibleEnd - visibleStart) / (1000 * 60 * 60 * 24));
    return Math.max(1, Math.min(days, daysToShow));
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

  // Get color by market segment (more important for revenue management)
  const getSegmentColor = (segment) => {
    const colors = {
      corporate: 'bg-blue-600',      // Corporate → Blue
      'ota': 'bg-purple-600',        // OTA → Purple
      'walk_in': 'bg-orange-500',    // Walk-in → Orange
      'walk-in': 'bg-orange-500',    // Walk-in → Orange
      group: 'bg-green-600',         // Group → Green
      leisure: 'bg-pink-500',        // Leisure → Pink
      government: 'bg-indigo-600',   // Government → Indigo
      default: 'bg-blue-500'
    };
    return colors[segment?.toLowerCase()] || colors.default;
  };

  // Get rate type label with styling
  const getRateTypeInfo = (booking) => {
    const rateTypes = {
      'corp_std': { label: 'CORP-STD', color: 'text-blue-300' },
      'corp_pref': { label: 'CORP-PREF', color: 'text-blue-200' },
      'gov': { label: 'GOV', color: 'text-indigo-300' },
      'leisure': { label: 'RACK', color: 'text-pink-300' },
      'ota': { label: 'OTA', color: 'text-purple-300' },
      'group': { label: 'GROUP', color: 'text-green-300' }
    };
    
    return rateTypes[booking.rate_type] || { label: booking.rate_type?.toUpperCase() || 'STD', color: 'text-gray-300' };
  };

  // Check if booking is arrival/stayover/departure for current date
  const getBookingStatus = (booking, date) => {
    const checkIn = new Date(booking.check_in);
    const checkOut = new Date(booking.check_out);
    const current = new Date(date);
    
    checkIn.setHours(0, 0, 0, 0);
    checkOut.setHours(0, 0, 0, 0);
    current.setHours(0, 0, 0, 0);
    
    if (checkIn.getTime() === current.getTime()) return 'arrival';
    if (checkOut.getTime() === current.getTime()) return 'departure';
    if (current > checkIn && current < checkOut) return 'stayover';
    return null;
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

  // OTA Helper Functions
  const getOTAInfo = (channel) => {
    const otaData = {
      'booking_com': { label: 'BKG', name: 'Booking.com', color: 'bg-indigo-600' },
      'expedia': { label: 'EXP', name: 'Expedia', color: 'bg-blue-600' },
      'airbnb': { label: 'ABNB', name: 'Airbnb', color: 'bg-red-600' },
      'agoda': { label: 'AGD', name: 'Agoda', color: 'bg-purple-600' },
      'hotels_com': { label: 'HTL', name: 'Hotels.com', color: 'bg-rose-600' },
      'direct': { label: 'DIR', name: 'Direct', color: 'bg-green-600' },
      'phone': { label: 'TEL', name: 'Phone', color: 'bg-gray-600' },
      'walk_in': { label: 'WLK', name: 'Walk-in', color: 'bg-orange-600' }
    };
    return otaData[channel] || { label: 'OTA', name: 'OTA', color: 'bg-gray-600' };
  };

  // Enterprise Mode: Check if booking has rate leakage
  const hasRateLeakage = (bookingId) => {
    return rateLeakages.find(l => l.booking_id === bookingId);
  };

  // Enterprise Mode: Get heatmap intensity for date
  const getHeatmapIntensity = (date) => {
    const dateStr = date.toISOString().split('T')[0];
    const heatmapDay = availabilityHeatmap.find(h => h.date === dateStr);
    return heatmapDay?.intensity || 'low';
  };

  const getHeatmapColor = (intensity) => {
    const colors = {
      'critical': 'bg-red-100 border-red-300',
      'high': 'bg-orange-100 border-orange-300',
      'moderate': 'bg-yellow-100 border-yellow-300',
      'medium': 'bg-green-100 border-green-300',
      'low': 'bg-white'
    };
    return colors[intensity] || colors.low;
  };

  // AI Mode: Check if booking has AI recommendation
  const getAIRecommendation = (bookingId) => {
    const roomMove = aiRoomMoves.find(r => r.booking_id === bookingId);
    const overbooking = aiOverbookingSolutions.find(s => s.booking_id === bookingId);
    return roomMove || overbooking;
  };

  // AI Mode: Check no-show risk
  const getNoShowRisk = (bookingId) => {
    return aiNoShowPredictions.find(p => p.booking_id === bookingId);
  };

  const toggleAIMode = () => {
    const newState = !showAIPanel;
    setShowAIPanel(newState);
    if (newState) {
      loadAIRecommendations();
    }
  };

  const toggleDeluxeMode = () => {
    const newState = !showDeluxePanel;
    setShowDeluxePanel(newState);
    if (newState) {
      loadDeluxeFeatures();
    }
  };

  const loadDeluxeFeatures = async () => {
    try {
      const startDate = currentDate.toISOString().split('T')[0];
      const endDate = new Date(currentDate.getTime() + daysToShow * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      const today = new Date().toISOString().split('T')[0];
      
      const [groupsRes, oversellRes, channelRes] = await Promise.all([
        axios.get(`/deluxe/group-bookings?start_date=${startDate}&end_date=${endDate}&min_rooms=5`).catch(() => ({ data: { groups: [] } })),
        axios.get(`/deluxe/oversell-protection?start_date=${startDate}&end_date=${endDate}`).catch(() => ({ data: { protection_map: [] } })),
        axios.post(`/deluxe/optimize-channel-mix`, { start_date: startDate, end_date: endDate }).catch(() => ({ data: null }))
      ]);
      
      setGroupBookings(groupsRes.data.groups || []);
      setOversellProtection(oversellRes.data.protection_map || []);
      setChannelMixData(channelRes.data);
    } catch (error) {
      console.error('Failed to load deluxe features:', error);
    }
  };

  // Check if booking is part of a group
  const isGroupBooking = (bookingId) => {
    return groupBookings.some(g => g.booking_ids.includes(bookingId));
  };

  const getGroupInfo = (bookingId) => {
    return groupBookings.find(g => g.booking_ids.includes(bookingId));
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
      <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="calendar">
        <div className="flex items-center justify-center h-screen">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600"></div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="calendar">
      <div className="p-6 space-y-4">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <div className="flex items-center space-x-3">
              <h1 className="text-4xl font-bold" style={{ fontFamily: 'Space Grotesk' }}>
                Reservation Calendar
              </h1>
              {conflicts.length > 0 && (
                <Badge className="bg-red-500 animate-pulse">
                  ⚠️ {conflicts.length} Conflict{conflicts.length > 1 ? 's' : ''}
                </Badge>
              )}
            </div>
            <p className="text-gray-600 mt-1">Timeline view of all bookings</p>
          </div>
          <div className="flex items-center space-x-2">
            <Button onClick={() => setShowFindRoomDialog(true)}>
              <Search className="w-4 h-4 mr-2" />
              Find Room
            </Button>
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

        {/* Conflict Alert */}
        {conflicts.length > 0 && (
          <Card className="border-red-500 bg-red-50">
            <CardContent className="py-4">
              <div className="flex items-start space-x-3">
                <AlertCircle className="w-6 h-6 text-red-600 flex-shrink-0" />
                <div className="flex-1">
                  <h3 className="font-bold text-red-900 mb-2">⚠️ Overbooking Detected!</h3>
                  <div className="space-y-2">
                    {conflicts.map((conflict, idx) => (
                      <div key={idx} className="text-sm text-red-800 bg-white rounded p-2">
                        <strong>Room {conflict.room_number}:</strong> {conflict.guest1} and {conflict.guest2} 
                        {' '}have overlapping reservations from{' '}
                        {new Date(conflict.overlap_start).toLocaleDateString()} to{' '}
                        {new Date(conflict.overlap_end).toLocaleDateString()}
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

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
                  <Button
                    size="sm"
                    variant={showEnterprisePanel ? "default" : "outline"}
                    onClick={() => setShowEnterprisePanel(!showEnterprisePanel)}
                    className="flex items-center gap-2"
                  >
                    <TrendingUp className="w-4 h-4" />
                    Enterprise
                  </Button>
                  <Button
                    size="sm"
                    variant={showAIPanel ? "default" : "outline"}
                    onClick={toggleAIMode}
                    className="flex items-center gap-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white hover:from-purple-700 hover:to-blue-700"
                  >
                    🤖 AI
                  </Button>
                  <Button
                    size="sm"
                    variant={showDeluxePanel ? "default" : "outline"}
                    onClick={toggleDeluxeMode}
                    className="flex items-center gap-2 bg-gradient-to-r from-amber-500 to-orange-600 text-white hover:from-amber-600 hover:to-orange-700"
                  >
                    💎 Deluxe+
                  </Button>
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

        {/* Deluxe+ Panel */}
        {showDeluxePanel && (
          <Card className="border-2 border-amber-500 bg-gradient-to-br from-amber-50 to-orange-50">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                💎 Deluxe+ Features
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Group Bookings */}
              {groupBookings.length > 0 && (
                <div className="bg-white p-3 rounded-lg border-2 border-amber-300">
                  <div className="text-sm font-semibold text-amber-700 mb-2">
                    👥 Group Bookings ({groupBookings.length})
                  </div>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {groupBookings.slice(0, 5).map((group, idx) => (
                      <div key={idx} className="bg-amber-50 p-2 rounded border border-amber-200 text-xs">
                        <div className="flex justify-between items-start mb-1">
                          <div>
                            <span className="font-semibold">{group.company_name}</span>
                            {group.is_large_group && (
                              <Badge className="ml-2 bg-orange-600 text-white text-[8px]">LARGE</Badge>
                            )}
                          </div>
                          <Badge className="bg-amber-600 text-white text-[9px]">
                            {group.room_count} rooms
                          </Badge>
                        </div>
                        <div className="text-gray-600">
                          {new Date(group.check_in).toLocaleDateString()} - {new Date(group.check_out).toLocaleDateString()}
                        </div>
                        <div className="flex justify-between mt-1">
                          <span className="text-gray-500">Revenue:</span>
                          <span className="font-semibold text-green-600">${group.total_revenue}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Oversell Protection Map */}
              {oversellProtection.length > 0 && (
                <div className="bg-white p-3 rounded-lg border-2 border-red-300">
                  <div className="text-sm font-semibold text-red-700 mb-2">
                    🛡️ Oversell Protection Status
                  </div>
                  <div className="grid grid-cols-4 gap-2">
                    <div className="text-center">
                      <div className="text-xl font-bold text-red-600">
                        {oversellProtection.filter(d => d.risk_level === 'danger').length}
                      </div>
                      <div className="text-[10px] text-gray-600">DANGER</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-yellow-600">
                        {oversellProtection.filter(d => d.risk_level === 'caution').length}
                      </div>
                      <div className="text-[10px] text-gray-600">CAUTION</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-blue-600">
                        {oversellProtection.filter(d => d.risk_level === 'moderate').length}
                      </div>
                      <div className="text-[10px] text-gray-600">MODERATE</div>
                    </div>
                    <div className="text-center">
                      <div className="text-xl font-bold text-green-600">
                        {oversellProtection.filter(d => d.risk_level === 'safe').length}
                      </div>
                      <div className="text-[10px] text-gray-600">SAFE</div>
                    </div>
                  </div>
                  <div className="mt-2 text-xs text-gray-600 space-y-1">
                    {oversellProtection.filter(d => d.risk_level === 'danger').slice(0, 2).map((day, idx) => (
                      <div key={idx} className="flex justify-between bg-red-50 p-1 rounded">
                        <span>{new Date(day.date).toLocaleDateString()}</span>
                        <span className="font-semibold text-red-600">{day.recommendation}</span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Channel Mix Optimization */}
              {channelMixData && (
                <div className="bg-white p-3 rounded-lg border-2 border-blue-300">
                  <div className="text-sm font-semibold text-blue-700 mb-2">
                    📊 Channel Mix Analysis
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-600">Direct Booking Gap:</span>
                      <span className="font-bold text-orange-600">
                        {channelMixData.analysis?.direct_booking_gap}%
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-600">Commission Rate:</span>
                      <span className="font-bold text-red-600">
                        {channelMixData.analysis?.current_commission_rate}%
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-600">Potential Annual Savings:</span>
                      <span className="font-bold text-green-600">
                        ${Math.round(channelMixData.analysis?.potential_annual_savings || 0)}
                      </span>
                    </div>
                  </div>
                  <div className="mt-2 pt-2 border-t">
                    <div className="text-xs font-semibold text-gray-700 mb-1">Top Recommendation:</div>
                    <div className="text-xs text-gray-600 bg-blue-50 p-2 rounded">
                      {channelMixData.recommendations?.[0]}
                    </div>
                  </div>
                </div>
              )}

              {/* Empty State */}
              {groupBookings.length === 0 && oversellProtection.length === 0 && !channelMixData && (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-4xl mb-2">💎</div>
                  <div className="text-sm">Deluxe+ analytics loading...</div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* AI Mode Panel */}
        {showAIPanel && (
          <Card className="border-2 border-purple-500 bg-gradient-to-br from-purple-50 to-blue-50">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                🤖 AI Operations Intelligence
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Overbooking Solutions */}
              {aiOverbookingSolutions.length > 0 && (
                <div className="bg-white p-3 rounded-lg border-2 border-red-300">
                  <div className="text-sm font-semibold text-red-700 mb-2 flex items-center gap-2">
                    <span>🚨 Overbooking Conflicts ({aiOverbookingSolutions.length})</span>
                  </div>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {aiOverbookingSolutions.map((solution, idx) => (
                      <div key={idx} className="bg-red-50 p-2 rounded border border-red-200 text-xs">
                        <div className="flex justify-between items-start mb-1">
                          <div>
                            <span className="font-semibold">{solution.guest_name}</span>
                            <span className="mx-1">•</span>
                            <span>Room {solution.current_room}</span>
                          </div>
                          <Badge className="bg-purple-600 text-white text-[9px]">
                            {Math.round(solution.confidence * 100)}% confident
                          </Badge>
                        </div>
                        <div className="text-green-600 font-semibold">
                          ✓ Move to Room {solution.recommended_room}
                        </div>
                        <div className="text-gray-600 mt-1">{solution.reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Room Move Recommendations */}
              {aiRoomMoves.length > 0 && (
                <div className="bg-white p-3 rounded-lg border-2 border-blue-300">
                  <div className="text-sm font-semibold text-blue-700 mb-2">
                    💎 Smart Room Moves ({aiRoomMoves.length})
                  </div>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {aiRoomMoves.slice(0, 5).map((move, idx) => (
                      <div key={idx} className="bg-blue-50 p-2 rounded border border-blue-200 text-xs">
                        <div className="flex justify-between items-start mb-1">
                          <div>
                            <span className="font-semibold">{move.guest_name}</span>
                            {move.loyalty_tier && (
                              <Badge className="ml-2 bg-yellow-500 text-white text-[8px]">
                                {move.loyalty_tier.toUpperCase()}
                              </Badge>
                            )}
                          </div>
                          <Badge className={`text-white text-[9px] ${
                            move.priority === 'urgent' ? 'bg-red-600' :
                            move.priority === 'high' ? 'bg-orange-600' : 'bg-blue-600'
                          }`}>
                            {move.priority.toUpperCase()}
                          </Badge>
                        </div>
                        <div className="text-green-600 font-semibold">
                          {move.type === 'upgrade' ? '⬆️' : '🔄'} {move.current_room} → {move.recommended_room}
                        </div>
                        <div className="text-gray-600 mt-1">{move.reason}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* No-Show Risk Predictions */}
              {aiNoShowPredictions.filter(p => p.risk_level !== 'low').length > 0 && (
                <div className="bg-white p-3 rounded-lg border-2 border-yellow-300">
                  <div className="text-sm font-semibold text-yellow-700 mb-2">
                    ⚠️ High No-Show Risk ({aiNoShowPredictions.filter(p => p.risk_level === 'high').length})
                  </div>
                  <div className="space-y-2 max-h-48 overflow-y-auto">
                    {aiNoShowPredictions.filter(p => p.risk_level !== 'low').slice(0, 5).map((pred, idx) => (
                      <div key={idx} className="bg-yellow-50 p-2 rounded border border-yellow-200 text-xs">
                        <div className="flex justify-between items-start mb-1">
                          <div>
                            <span className="font-semibold">{pred.guest_name}</span>
                            <span className="mx-1">•</span>
                            <span>Room {pred.room_number}</span>
                          </div>
                          <Badge className={`text-white text-[9px] ${
                            pred.risk_level === 'high' ? 'bg-red-600' : 'bg-yellow-600'
                          }`}>
                            {pred.risk_score}% RISK
                          </Badge>
                        </div>
                        <div className="text-gray-600">
                          Factors: {pred.risk_factors.slice(0, 2).join(', ')}
                        </div>
                        <div className="text-blue-600 mt-1 font-semibold">
                          💡 {pred.recommendation}
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Rate Recommendations Summary */}
              {aiRateRecommendations.length > 0 && (
                <div className="bg-white p-3 rounded-lg border-2 border-green-300">
                  <div className="text-sm font-semibold text-green-700 mb-2">
                    💰 Dynamic Rate Recommendations
                  </div>
                  <div className="grid grid-cols-3 gap-3">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">
                        {aiRateRecommendations.filter(r => r.strategy === 'demand_surge').length}
                      </div>
                      <div className="text-xs text-gray-600">Surge Pricing</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">
                        {aiRateRecommendations.filter(r => r.strategy === 'optimize').length}
                      </div>
                      <div className="text-xs text-gray-600">Optimize</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-orange-600">
                        {aiRateRecommendations.filter(r => r.strategy === 'attract').length}
                      </div>
                      <div className="text-xs text-gray-600">Attract</div>
                    </div>
                  </div>
                  <div className="mt-2 text-center">
                    <div className="text-xl font-bold text-purple-600">
                      ${Math.round(aiRateRecommendations.reduce((sum, r) => sum + (r.revenue_impact || 0), 0))}
                    </div>
                    <div className="text-xs text-gray-600">Potential Revenue Increase</div>
                  </div>
                </div>
              )}

              {/* No AI recommendations */}
              {aiOverbookingSolutions.length === 0 && aiRoomMoves.length === 0 && 
               aiNoShowPredictions.filter(p => p.risk_level !== 'low').length === 0 && (
                <div className="text-center py-8 text-gray-500">
                  <div className="text-4xl mb-2">🤖</div>
                  <div className="text-sm">All systems optimal - No urgent AI recommendations</div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Enterprise Mode Panel */}
        {showEnterprisePanel && (
          <Card className="border-2 border-purple-300 bg-purple-50">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <TrendingUp className="w-5 h-5 text-purple-600" />
                Enterprise Intelligence
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Rate Leakage Alerts */}
              {rateLeakages.length > 0 && (
                <div>
                  <div className="text-sm font-semibold text-red-700 mb-2">
                    💸 Rate Leakage Detected ({rateLeakages.length} instances)
                  </div>
                  <div className="space-y-2 max-h-40 overflow-y-auto">
                    {rateLeakages.slice(0, 5).map((leak, idx) => (
                      <div key={idx} className="bg-white p-2 rounded border border-red-200 text-xs">
                        <div className="flex justify-between items-start">
                          <div>
                            <span className="font-semibold">{leak.guest_name}</span>
                            <span className="mx-2">•</span>
                            <Badge className={getOTAInfo(leak.ota_channel).color + " text-white text-[9px]"}>
                              {getOTAInfo(leak.ota_channel).label}
                            </Badge>
                          </div>
                          <div className="text-red-600 font-bold">
                            -${leak.difference_per_night}/nt
                          </div>
                        </div>
                        <div className="text-gray-600 mt-1">
                          {leak.room_type} • {new Date(leak.check_in).toLocaleDateString()} - {new Date(leak.check_out).toLocaleDateString()}
                        </div>
                      </div>
                    ))}
                  </div>
                  {rateLeakages.length > 5 && (
                    <div className="text-xs text-gray-500 mt-2">
                      +{rateLeakages.length - 5} more leakages
                    </div>
                  )}
                </div>
              )}

              {/* Heatmap Legend */}
              <div>
                <div className="text-sm font-semibold text-gray-700 mb-2">
                  📊 Availability Heatmap Legend
                </div>
                <div className="flex items-center gap-3 flex-wrap">
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-4 bg-red-100 border border-red-300 rounded"></div>
                    <span className="text-xs">Critical (95%+)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-4 bg-orange-100 border border-orange-300 rounded"></div>
                    <span className="text-xs">High (85-94%)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-4 bg-yellow-100 border border-yellow-300 rounded"></div>
                    <span className="text-xs">Moderate (70-84%)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-4 bg-green-100 border border-green-300 rounded"></div>
                    <span className="text-xs">Medium (50-69%)</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="w-6 h-4 bg-white border border-gray-300 rounded"></div>
                    <span className="text-xs">Low (&lt;50%)</span>
                  </div>
                </div>
              </div>

              {/* Quick Stats */}
              {availabilityHeatmap.length > 0 && (
                <div className="grid grid-cols-3 gap-4 pt-3 border-t">
                  <div className="text-center">
                    <div className="text-xl font-bold text-red-600">
                      {availabilityHeatmap.filter(h => h.intensity === 'critical').length}
                    </div>
                    <div className="text-xs text-gray-600">Critical Days</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xl font-bold text-orange-600">
                      {availabilityHeatmap.filter(h => h.intensity === 'high').length}
                    </div>
                    <div className="text-xs text-gray-600">High Demand</div>
                  </div>
                  <div className="text-center">
                    <div className="text-xl font-bold text-purple-600">
                      {Math.round(availabilityHeatmap.reduce((sum, h) => sum + h.occupancy_pct, 0) / availabilityHeatmap.length)}%
                    </div>
                    <div className="text-xs text-gray-600">Avg Occupancy</div>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* Legend - Market Segments & Quick Tips */}
        <Card>
          <CardContent className="py-3">
            <div className="space-y-3">
              {/* Market Segment Colors */}
              <div>
                <div className="text-xs font-semibold text-gray-700 mb-2">Market Segments (by color):</div>
                <div className="flex items-center space-x-4 text-sm">
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 bg-blue-600 rounded"></div>
                    <span>Corporate</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 bg-purple-600 rounded"></div>
                    <span>OTA</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 bg-orange-500 rounded"></div>
                    <span>Walk-in</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 bg-green-600 rounded"></div>
                    <span>Group</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 bg-pink-500 rounded"></div>
                    <span>Leisure</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 bg-indigo-600 rounded"></div>
                    <span>Government</span>
                  </div>
                </div>
              </div>

              {/* Status Indicators */}
              <div>
                <div className="text-xs font-semibold text-gray-700 mb-2">Status Indicators:</div>
                <div className="flex items-center space-x-4 text-sm">
                  <div className="flex items-center space-x-2">
                    <div className="bg-white border-2 border-green-600 text-green-600 rounded-full w-5 h-5 flex items-center justify-center text-xs font-bold">↓</div>
                    <span>Arrival</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="bg-white border-2 border-red-600 text-red-600 rounded-full w-5 h-5 flex items-center justify-center text-xs font-bold">↑</div>
                    <span>Departure</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="bg-white border-2 border-blue-600 text-blue-600 rounded-full w-5 h-5 flex items-center justify-center text-xs font-bold">•</div>
                    <span>Stayover</span>
                  </div>
                </div>
              </div>

              {/* Room Blocks */}
              <div>
                <div className="text-xs font-semibold text-gray-700 mb-2">Room Blocks:</div>
                <div className="flex items-center space-x-4 text-sm">
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 bg-red-600 rounded opacity-60" style={{ backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 2px, rgba(255,255,255,.3) 2px, rgba(255,255,255,.3) 4px)' }}></div>
                    <span>Out of Order</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 bg-orange-500 rounded opacity-60" style={{ backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 2px, rgba(255,255,255,.3) 2px, rgba(255,255,255,.3) 4px)' }}></div>
                    <span>Out of Service</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-4 h-4 bg-yellow-600 rounded opacity-60" style={{ backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 2px, rgba(255,255,255,.3) 2px, rgba(255,255,255,.3) 4px)' }}></div>
                    <span>Maintenance</span>
                  </div>
                </div>
              </div>

              {/* OTA Channels */}
              <div>
                <div className="text-xs font-semibold text-gray-700 mb-2">OTA Channels:</div>
                <div className="flex items-center space-x-3 text-sm flex-wrap gap-y-1">
                  <div className="flex items-center space-x-1">
                    <Badge className="bg-indigo-600 text-white text-[9px] px-1.5">BKG</Badge>
                    <span className="text-xs">Booking.com</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Badge className="bg-blue-600 text-white text-[9px] px-1.5">EXP</Badge>
                    <span className="text-xs">Expedia</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Badge className="bg-red-600 text-white text-[9px] px-1.5">ABNB</Badge>
                    <span className="text-xs">Airbnb</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Badge className="bg-purple-600 text-white text-[9px] px-1.5">AGD</Badge>
                    <span className="text-xs">Agoda</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Badge className="bg-rose-600 text-white text-[9px] px-1.5">HTL</Badge>
                    <span className="text-xs">Hotels.com</span>
                  </div>
                </div>
              </div>

              {/* Quick Tips */}
              <div className="flex items-center justify-between pt-2 border-t">
                <div className="flex items-center space-x-4 text-xs text-gray-600">
                  <div className="flex items-center space-x-1">
                    <Plus className="w-3 h-3" />
                    <span>Click cell = New booking</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <Info className="w-3 h-3" />
                    <span>Double-click = Details</span>
                  </div>
                  <div className="flex items-center space-x-1">
                    <span>🖱️ Drag & drop = Move</span>
                  </div>
                </div>
                <div className="text-xs text-gray-600">
                  <span className="font-semibold">💡 Hover</span> over booking bars to see ADR & rate codes
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
                {dateRange.map((date, idx) => {
                  const intensity = getHeatmapIntensity(date);
                  return (
                  <div
                    key={idx}
                    className={`w-24 flex-shrink-0 p-2 border-r text-center text-sm ${
                      isToday(date) ? 'bg-blue-50 font-bold text-blue-600' : getHeatmapColor(intensity)
                    }`}
                    title={`Occupancy intensity: ${intensity}`}
                  >
                    <div>{formatDateWithDay(date)}</div>
                  </div>
                  );
                })}
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
                        const roomBlock = getRoomBlockForDate(room.id, date);
                        const isBlockStart = roomBlock && isBlockStart(roomBlock, date);
                        const isDragOver = dragOverCell?.roomId === room.id && 
                                          new Date(dragOverCell.date).toDateString() === date.toDateString();

                        return (
                          <div
                            key={idx}
                            className={`w-24 flex-shrink-0 border-r relative cursor-pointer hover:bg-gray-100 transition-colors ${
                              isToday(date) ? 'bg-blue-50' : ''
                            } ${isDragOver ? 'bg-green-100 border-2 border-green-500' : ''}
                            ${roomBlock ? 'bg-gray-200 bg-opacity-50' : ''}`}
                            style={{ height: '80px' }}
                            onClick={() => !booking && !roomBlock && handleCellClick(room.id, date)}
                            onDragOver={(e) => handleDragOver(e, room.id, date)}
                            onDragLeave={handleDragLeave}
                            onDrop={(e) => handleDrop(e, room.id, date)}
                            title={roomBlock ? `${roomBlock.type.toUpperCase()}: ${roomBlock.reason}` : ''}
                          >
                            {/* Room Block Indicator */}
                            {isBlockStart && roomBlock && (
                              <div 
                                className={`absolute top-0 left-0 h-full opacity-60 border-2 ${
                                  roomBlock.type === 'out_of_order' ? 'bg-red-600 border-red-700' :
                                  roomBlock.type === 'out_of_service' ? 'bg-orange-500 border-orange-600' :
                                  'bg-yellow-600 border-yellow-700'
                                }`}
                                style={{
                                  width: `${calculateBlockSpan(roomBlock, currentDate) * 96 - 4}px`,
                                  backgroundImage: 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(255,255,255,.1) 10px, rgba(255,255,255,.1) 20px)',
                                  zIndex: 5
                                }}
                                title={`${roomBlock.type.replace('_', ' ').toUpperCase()}: ${roomBlock.reason}\n${roomBlock.start_date} - ${roomBlock.end_date || 'Open-ended'}`}
                              >
                                <div className="p-1 text-white text-[10px] font-bold">
                                  {roomBlock.type === 'out_of_order' ? 'OOO' :
                                   roomBlock.type === 'out_of_service' ? 'OOS' : 'MNT'}
                                </div>
                              </div>
                            )}

                            {/* Empty cell indicator */}
                            {!booking && !roomBlock && (
                              <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                                <Plus className="w-6 h-6 text-gray-400" />
                              </div>
                            )}
                            
                            {/* Booking bar - segment color coded */}
                            {isStart && booking && (
                              <div
                                draggable
                                onDragStart={(e) => handleDragStart(e, booking)}
                                onDragEnd={handleDragEnd}
                                onDoubleClick={() => handleBookingDoubleClick(booking)}
                                className={`absolute top-2 left-1 rounded ${getSegmentColor(
                                  booking.market_segment || booking.rate_type
                                )} text-white text-xs overflow-hidden shadow-md hover:shadow-xl transition-all cursor-move z-20 group ${
                                  draggingBooking?.id === booking.id ? 'opacity-50' : ''
                                } ${hasConflict(room.id, date) ? 'border-4 border-red-500 animate-pulse' : ''}
                                ${showDeluxePanel && isGroupBooking(booking.id) ? 'border-2 border-amber-500' : ''}`}
                                style={{
                                  width: `${calculateBookingSpan(booking, currentDate) * 96 - 8}px`,
                                  height: '70px',
                                  backgroundImage: showDeluxePanel && isGroupBooking(booking.id) 
                                    ? 'repeating-linear-gradient(45deg, transparent, transparent 10px, rgba(251, 191, 36, 0.2) 10px, rgba(251, 191, 36, 0.2) 20px)' 
                                    : 'none'
                                }}
                                title={`Double-click for details | Drag to move\n${booking.guest_name || 'Guest'} - ${booking.market_segment || 'Standard'}${showDeluxePanel && isGroupBooking(booking.id) ? `\n👥 GROUP: ${getGroupInfo(booking.id)?.company_name}` : ''}`}
                              >
                                {/* Main booking info */}
                                <div className="p-2 h-[48px] relative">
                                  <div className="font-semibold truncate pr-8">
                                    {booking.guest_name || 'Guest'}
                                  </div>
                                  <div className="text-xs opacity-90 flex items-center mt-1">
                                    <Clock className="w-3 h-3 mr-1" />
                                    {calculateBookingSpan(booking, currentDate)}n
                                  </div>
                                  {booking.company_name && (
                                    <div className="text-xs opacity-90 flex items-center truncate">
                                      <Building2 className="w-3 h-3 mr-1" />
                                      {booking.company_name}
                                    </div>
                                  )}
                                  
                                  {/* Status indicators - top right */}
                                  <div className="absolute top-1 right-1 flex flex-col space-y-1 items-end">
                                    {/* AI Recommendation Badge */}
                                    {showAIPanel && getAIRecommendation(booking.id) && (
                                      <div className="bg-gradient-to-r from-purple-600 to-blue-600 text-white text-[8px] font-bold px-1 py-0.5 rounded animate-pulse" title="AI Recommendation Available">
                                        🤖 AI
                                      </div>
                                    )}
                                    
                                    {/* No-Show Risk Badge */}
                                    {showAIPanel && getNoShowRisk(booking.id) && getNoShowRisk(booking.id).risk_level === 'high' && (
                                      <div className="bg-red-600 text-white text-[8px] font-bold px-1 py-0.5 rounded" title={`High No-Show Risk: ${getNoShowRisk(booking.id).risk_score}%`}>
                                        ⚠️ RISK
                                      </div>
                                    )}
                                    
                                    {/* Group Badge - Deluxe+ */}
                                    {showDeluxePanel && isGroupBooking(booking.id) && (
                                      <div className="bg-gradient-to-r from-amber-500 to-orange-600 text-white text-[8px] font-bold px-1 py-0.5 rounded" title={`Group: ${getGroupInfo(booking.id)?.company_name} (${getGroupInfo(booking.id)?.room_count} rooms)`}>
                                        👥 GRP
                                      </div>
                                    )}
                                    
                                    {/* OTA Badge */}
                                    {booking.ota_channel && (
                                      <div className={`${getOTAInfo(booking.ota_channel).color} text-white text-[9px] font-bold px-1.5 py-0.5 rounded`} title={getOTAInfo(booking.ota_channel).name}>
                                        {getOTAInfo(booking.ota_channel).label}
                                      </div>
                                    )}
                                    
                                    <div className="flex space-x-1">
                                      {getBookingStatus(booking, date) === 'arrival' && (
                                        <div className="bg-white text-green-600 rounded-full w-5 h-5 flex items-center justify-center text-[10px] font-bold" title="Arrival">
                                          ↓
                                        </div>
                                      )}
                                      {getBookingStatus(booking, date) === 'departure' && (
                                        <div className="bg-white text-red-600 rounded-full w-5 h-5 flex items-center justify-center text-[10px] font-bold" title="Departure">
                                          ↑
                                        </div>
                                      )}
                                      {getBookingStatus(booking, date) === 'stayover' && (
                                        <div className="bg-white text-blue-600 rounded-full w-5 h-5 flex items-center justify-center text-[10px] font-bold" title="Stayover">
                                          •
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                </div>
                                
                                {/* Enhanced Rate overlay - shown on hover */}
                                <div className="absolute bottom-0 left-0 right-0 bg-black bg-opacity-90 text-white text-[10px] px-2 py-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                                  <div className="flex justify-between items-center">
                                    <div className="flex items-baseline space-x-2">
                                      <div>
                                        <span className="font-bold text-lg text-yellow-300">
                                          ${booking.total_amount ? (booking.total_amount / calculateBookingSpan(booking, currentDate)).toFixed(0) : '0'}
                                        </span>
                                        <span className="opacity-75 ml-1 text-[9px]">ADR</span>
                                      </div>
                                      {booking.base_rate && booking.base_rate !== booking.total_amount && (
                                        <div className="text-red-300 line-through text-[9px]">
                                          ${(booking.base_rate / calculateBookingSpan(booking, currentDate)).toFixed(0)}
                                        </div>
                                      )}
                                    </div>
                                    <div className="flex flex-col items-end space-y-0.5">
                                      {booking.rate_type && (
                                        <div className={`${getRateTypeInfo(booking).color} font-bold text-[9px]`}>
                                          {getRateTypeInfo(booking).label}
                                        </div>
                                      )}
                                      {booking.market_segment && (
                                        <div className="text-blue-200 text-[8px] uppercase">
                                          {booking.market_segment}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                  {/* OTA Info */}
                                  {booking.ota_channel && (
                                    <div className="text-[8px] text-indigo-300 mt-0.5 flex items-center justify-between">
                                      <span>{getOTAInfo(booking.ota_channel).name}</span>
                                      {booking.commission_pct && (
                                        <span>({booking.commission_pct}% comm.)</span>
                                      )}
                                    </div>
                                  )}
                                  {booking.ota_confirmation && (
                                    <div className="text-[8px] text-gray-400 mt-0.5">
                                      Conf: {booking.ota_confirmation}
                                    </div>
                                  )}
                                  {booking.virtual_card_provided && (
                                    <div className="text-[8px] text-green-300 mt-0.5">
                                      ✓ Virtual Card
                                    </div>
                                  )}
                                  {booking.contracted_rate && (
                                    <div className="text-[8px] text-green-300 mt-0.5">
                                      ✓ Contracted Rate
                                    </div>
                                  )}
                                </div>
                                
                                {/* Left border - segment indicator */}
                                <div className="absolute left-0 top-0 bottom-0 w-1 bg-white opacity-30"></div>
                                
                                {/* Rate Leakage Warning - Enterprise Mode */}
                                {hasRateLeakage(booking.id) && (
                                  <div className="absolute top-0 left-0 bg-red-600 text-white text-[8px] px-1 py-0.5 rounded-br font-bold" title={`Rate Leakage: -$${hasRateLeakage(booking.id).difference_per_night}/night`}>
                                    💸 LEAK
                                  </div>
                                )}
                                
                                {/* Conflict indicator */}
                                {hasConflict(room.id, date) && (
                                  <div className="absolute top-0 right-0 bg-red-600 text-white text-[8px] px-1 py-0.5 rounded-bl font-bold animate-pulse">
                                    ⚠️ CONFLICT
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
        <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Booking Details</DialogTitle>
          </DialogHeader>
          {selectedBooking && (
            <div className="space-y-4">
              {/* Main Details */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-sm text-gray-600">Guest Name</div>
                  <div className="text-lg font-semibold">{selectedBooking.guest_name}</div>
                </div>
                <div>
                  <div className="text-sm text-gray-600">Status</div>
                  <div className="flex items-center space-x-2">
                    <Badge className={getSegmentColor(selectedBooking.market_segment)}>
                      {selectedBooking.market_segment || 'Standard'}
                    </Badge>
                    <Badge className={getStatusColor(selectedBooking.status)}>
                      {getStatusLabel(selectedBooking.status)}
                    </Badge>
                  </div>
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

              {/* Rate Details */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <div className="text-sm font-semibold text-blue-900 mb-2">Rate Details</div>
                <div className="grid grid-cols-3 gap-4 text-sm">
                  <div>
                    <div className="text-gray-600">ADR</div>
                    <div className="font-bold text-lg">
                      ${selectedBooking.total_amount ? 
                        (selectedBooking.total_amount / 
                        Math.ceil((new Date(selectedBooking.check_out) - new Date(selectedBooking.check_in)) / (1000 * 60 * 60 * 24))).toFixed(2) 
                        : '0.00'}
                    </div>
                  </div>
                  {selectedBooking.rate_type && (
                    <div>
                      <div className="text-gray-600">Rate Code</div>
                      <div className="font-semibold text-blue-600 uppercase">
                        {selectedBooking.rate_type}
                      </div>
                    </div>
                  )}
                  {selectedBooking.market_segment && (
                    <div>
                      <div className="text-gray-600">Segment</div>
                      <div className="font-semibold text-blue-600 capitalize">
                        {selectedBooking.market_segment}
                      </div>
                    </div>
                  )}
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

              {/* Room Move History */}
              <div className="border-t pt-4">
                <div className="text-sm font-semibold text-gray-700 mb-3 flex items-center">
                  <Clock className="w-4 h-4 mr-2" />
                  Room Move History
                </div>
                {selectedBooking.room_moves && selectedBooking.room_moves.length > 0 ? (
                  <div className="space-y-2">
                    {selectedBooking.room_moves.map((move, idx) => (
                      <div key={idx} className="bg-gray-50 border border-gray-200 rounded p-3 text-sm">
                        <div className="flex items-center justify-between">
                          <div>
                            <span className="font-semibold">Room {move.old_room}</span>
                            <span className="mx-2 text-gray-400">→</span>
                            <span className="font-semibold">Room {move.new_room}</span>
                          </div>
                          <div className="text-xs text-gray-500">
                            {new Date(move.timestamp).toLocaleString()}
                          </div>
                        </div>
                        <div className="mt-1 text-xs text-gray-600">
                          <strong>Reason:</strong> {move.reason}
                        </div>
                        <div className="mt-1 text-xs text-gray-500">
                          Moved by: {move.moved_by}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-sm text-gray-500 italic">
                    No room moves recorded for this booking
                  </div>
                )}
              </div>

              <div className="flex space-x-2 pt-4 border-t">
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

      {/* Room Move Reason Dialog */}
      <Dialog open={showMoveReasonDialog} onOpenChange={setShowMoveReasonDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Room Move - Reason Required</DialogTitle>
          </DialogHeader>
          {moveData && (
            <div className="space-y-4">
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="text-sm text-blue-900">
                  <div className="font-semibold mb-2">Moving Booking:</div>
                  <div>Guest: <strong>{moveData.booking.guest_name}</strong></div>
                  <div>From: <strong>Room {moveData.oldRoom}</strong> → <strong>Room {moveData.newRoom}</strong></div>
                  <div>Dates: <strong>{moveData.newCheckIn}</strong> to <strong>{moveData.newCheckOut}</strong></div>
                </div>
              </div>

              <div>
                <Label>Reason for Move *</Label>
                <select
                  className="w-full border rounded-md p-2 mb-2"
                  value={moveReason}
                  onChange={(e) => setMoveReason(e.target.value)}
                >
                  <option value="">Select reason...</option>
                  <option value="Guest Request">Guest Request</option>
                  <option value="Room Maintenance">Room Maintenance</option>
                  <option value="Upgrade">Room Upgrade</option>
                  <option value="Downgrade">Room Downgrade</option>
                  <option value="Overbooking">Overbooking Resolution</option>
                  <option value="VIP Guest">VIP Guest Priority</option>
                  <option value="Room Issue">Room Issue / Complaint</option>
                  <option value="Operational">Operational Reasons</option>
                  <option value="Other">Other</option>
                </select>
                {moveReason === 'Other' && (
                  <Input
                    placeholder="Please specify..."
                    onChange={(e) => setMoveReason(e.target.value)}
                  />
                )}
              </div>

              <div className="text-xs text-gray-600 bg-gray-50 p-3 rounded">
                <strong>Note:</strong> This move will be recorded in the room move history with timestamp and your user details for audit purposes.
              </div>

              <div className="flex space-x-2">
                <Button onClick={handleConfirmMove} className="flex-1">
                  Confirm Move
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setShowMoveReasonDialog(false);
                    setMoveReason('');
                    setMoveData(null);
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Find Room Dialog */}
      <Dialog open={showFindRoomDialog} onOpenChange={setShowFindRoomDialog}>
        <DialogContent className="max-w-3xl">
          <DialogHeader>
            <DialogTitle>Find Available Room</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="grid grid-cols-4 gap-4">
              <div>
                <Label>Check-in</Label>
                <Input
                  type="date"
                  value={findRoomCriteria.check_in}
                  onChange={(e) => setFindRoomCriteria({...findRoomCriteria, check_in: e.target.value})}
                />
              </div>
              <div>
                <Label>Check-out</Label>
                <Input
                  type="date"
                  value={findRoomCriteria.check_out}
                  onChange={(e) => setFindRoomCriteria({...findRoomCriteria, check_out: e.target.value})}
                />
              </div>
              <div>
                <Label>Room Type</Label>
                <select
                  className="w-full border rounded-md p-2"
                  value={findRoomCriteria.room_type}
                  onChange={(e) => setFindRoomCriteria({...findRoomCriteria, room_type: e.target.value})}
                >
                  <option value="all">All Types</option>
                  <option value="standard">Standard</option>
                  <option value="deluxe">Deluxe</option>
                  <option value="suite">Suite</option>
                </select>
              </div>
              <div>
                <Label>Guests</Label>
                <Input
                  type="number"
                  min="1"
                  value={findRoomCriteria.guests_count}
                  onChange={(e) => setFindRoomCriteria({...findRoomCriteria, guests_count: Number(e.target.value)})}
                />
              </div>
            </div>

            <Button onClick={handleFindRoom} className="w-full">
              <Search className="w-4 h-4 mr-2" />
              Search Available Rooms
            </Button>

            {availableRooms.length > 0 && (
              <div className="border rounded-lg p-4 max-h-96 overflow-y-auto">
                <h3 className="font-semibold mb-3 flex items-center">
                  <CheckCircle className="w-5 h-5 text-green-600 mr-2" />
                  {availableRooms.length} Room{availableRooms.length > 1 ? 's' : ''} Available
                </h3>
                <div className="space-y-2">
                  {availableRooms.map(room => (
                    <div key={room.id} className="flex items-center justify-between p-3 bg-green-50 border border-green-200 rounded">
                      <div>
                        <div className="font-semibold">Room {room.room_number}</div>
                        <div className="text-sm text-gray-600 capitalize">
                          {room.room_type} • Floor {room.floor} • Capacity: {room.capacity}
                        </div>
                        <div className="text-sm font-semibold text-green-600">
                          ${room.base_price}/night
                        </div>
                      </div>
                      <Button size="sm" onClick={() => {
                        handleCellClick(room.id, new Date(findRoomCriteria.check_in));
                        setShowFindRoomDialog(false);
                      }}>
                        Book Now
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {findRoomCriteria.check_in && findRoomCriteria.check_out && availableRooms.length === 0 && (
              <div className="text-center py-8 text-red-600">
                <AlertCircle className="w-12 h-12 mx-auto mb-3" />
                <p className="font-semibold">No rooms available for selected dates</p>
                <p className="text-sm">Try different dates or room type</p>
              </div>
            )}
          </div>
        </DialogContent>
      </Dialog>

      {/* Reservation Details Sidebar - Opera Navigator Style */}
      {showSidebar && (
        <>
          {/* Backdrop */}
          <div 
            className="fixed inset-0 bg-black bg-opacity-50 z-40"
            onClick={() => setShowSidebar(false)}
          ></div>
          
          {/* Sidebar */}
          <ReservationSidebar
            booking={selectedBooking}
            folio={selectedBookingFolio}
            room={rooms.find(r => r.id === selectedBooking?.room_id)}
            onClose={() => setShowSidebar(false)}
            getSegmentColor={getSegmentColor}
            getStatusLabel={getStatusLabel}
            getRateTypeInfo={getRateTypeInfo}
          />
        </>
      )}
    </Layout>
  );
};

export default ReservationCalendar;
