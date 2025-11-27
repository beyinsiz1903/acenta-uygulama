import { useState, useEffect, useRef, useCallback, memo, useMemo } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '@/components/Layout';
import ReservationSidebar from '@/components/ReservationSidebar';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogDescription } from '@/components/ui/dialog';
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
  CheckCircle,
  DollarSign,
  CreditCard,
  XCircle,
  Printer,
  Lock,
  History,
  ArrowRightLeft,
  Download,
  Filter,
  CheckSquare,
  Square,
  Trash2,
  Home,
  Users,
  Monitor
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
  const [visibleRoomRange, setVisibleRoomRange] = useState({ start: 0, end: 50 }); // Lazy load rooms (50 at a time for large properties)
  const [totalRoomsToShow, setTotalRoomsToShow] = useState(50); // Initial render limit

  
  // Dialog states
  const [showNewBookingDialog, setShowNewBookingDialog] = useState(false);
  const [showDetailsDialog, setShowDetailsDialog] = useState(false);
  const [showSidebar, setShowSidebar] = useState(false);
  const [showFolioDialog, setShowFolioDialog] = useState(false);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [selectedBookingFolio, setSelectedBookingFolio] = useState(null);
  const [folioCharges, setFolioCharges] = useState([]);
  const [folioPayments, setFolioPayments] = useState([]);
  const [showPaymentForm, setShowPaymentForm] = useState(false);
  const [showChargeForm, setShowChargeForm] = useState(false);
  const [showTransferDialog, setShowTransferDialog] = useState(false);
  const [showActivityLog, setShowActivityLog] = useState(false);
  const [selectedChargesForTransfer, setSelectedChargesForTransfer] = useState([]);
  const [paymentForm, setPaymentForm] = useState({
    amount: '',
    method: 'card',
    reference: '',
    notes: ''
  });
  const [chargeForm, setChargeForm] = useState({
    category: 'room',
    description: '',
    quantity: 1,
    unit_price: '',
    notes: ''
  });
  const [selectedDate, setSelectedDate] = useState(null);
  const [selectedRoom, setSelectedRoom] = useState(null);
  
  // Drag & Drop state
  const [draggingBooking, setDraggingBooking] = useState(null);
  const [dragOverCell, setDragOverCell] = useState(null);
  
  // Resize state for extending/shortening bookings
  const [resizingBooking, setResizingBooking] = useState(null);
  const [resizeDirection, setResizeDirection] = useState(null); // 'start' or 'end'
  const [resizePreview, setResizePreview] = useState(null);
  
  // Filter states
  const [filters, setFilters] = useState({
    roomType: '',
    roomStatus: '',
    bookingStatus: '',
    marketSegment: '',
    showFilters: false
  });
  
  // Bulk operations
  const [selectedBookings, setSelectedBookings] = useState([]);
  const [bulkActionMode, setBulkActionMode] = useState(false);
  
  // View mode - simplified or detailed
  const [viewMode, setViewMode] = useState('simplified'); // 'simplified' or 'detailed'
  
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
  const [groupedConflicts, setGroupedConflicts] = useState(null);
  const [showConflictSolutions, setShowConflictSolutions] = useState(false);

  const [pricingAlerts, setPricingAlerts] = useState([]);
  const [historicalTrends, setHistoricalTrends] = useState(null);
  const [showHistoricalPanel, setShowHistoricalPanel] = useState(false);
  const [moveBookingDialog, setMoveBookingDialog] = useState({ open: false, room: null, bookings: [] });
  const [selectedBookingToMove, setSelectedBookingToMove] = useState(null);
  const [availableRoomsForMove, setAvailableRoomsForMove] = useState([]);



  
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

  const loadCalendarData = useCallback(async () => {
    setLoading(true);
    try {
      // Calculate date range for calendar view
      const startDate = currentDate.toISOString().split('T')[0];
      const endDate = new Date(currentDate);
      endDate.setDate(endDate.getDate() + daysToShow);
      const endDateStr = endDate.toISOString().split('T')[0];
      
      // PERFORMANCE OPTIMIZATION: Load only visible data
      // For 550+ rooms: Load first batch (100 rooms) initially
      // For bookings: Load only date range needed (not all 3 years of data)
      const [roomsRes, bookingsRes, guestsRes, companiesRes, blocksRes] = await Promise.all([
        axios.get(`/pms/rooms?limit=100&offset=${visibleRoomRange.start}`),
        axios.get(`/pms/bookings?start_date=${startDate}&end_date=${endDateStr}&limit=500`),
        axios.get('/pms/guests?limit=200').catch(() => ({ data: [] })),
        axios.get('/companies?limit=100').catch(() => ({ data: [] })),
        axios.get(`/pms/room-blocks?status=active&from_date=${startDate}&to_date=${endDateStr}`).catch(() => ({ data: { blocks: [] } }))
      ]);

      setRooms(roomsRes.data || []);
      setBookings(bookingsRes.data || []);
      setGuests(guestsRes.data || []);
      setCompanies(companiesRes.data || []);
      setRoomBlocks(blocksRes.data.blocks || []);
      
      // Load grouped conflicts for better conflict management (only if needed)
      if (showConflictSolutions) {
        try {
          const conflictsRes = await axios.get('/deluxe/grouped-conflicts');
          setGroupedConflicts(conflictsRes.data);
        } catch (error) {
          console.error('Failed to load grouped conflicts:', error);
        }
      }
      
      // Load Enterprise Mode data (only if panel is open)
      if (showEnterprisePanel) {
        loadEnterpriseData();
      }
    } catch (error) {
      console.error('Failed to load calendar data:', error);
      toast.error('Failed to load calendar data');
    } finally {
      setLoading(false);
    }
  }, [currentDate, daysToShow, visibleRoomRange.start, showConflictSolutions, showEnterprisePanel]);

  useEffect(() => {
    loadCalendarData();
  }, [loadCalendarData]);


  // Resize booking with mouse drag
  useEffect(() => {
    if (!resizingBooking) return;
    
    const handleMouseMove = (e) => {
      // Calculate which cell we're over
      const cells = document.elementsFromPoint(e.clientX, e.clientY);
      const timelineCell = cells.find(el => el.dataset.date && el.dataset.roomId);
      
      if (timelineCell) {
        const newDate = new Date(timelineCell.dataset.date);
        setResizePreview({ date: newDate, direction: resizeDirection });
      }
    };
    
    const handleMouseUp = async () => {
      if (resizePreview && resizingBooking) {
        try {
          const updateData = {
            guest_id: resizingBooking.guest_id,
            room_id: resizingBooking.room_id,
            guests_count: resizingBooking.guests_count || 2,
            adults: resizingBooking.adults || 2,
            children: resizingBooking.children || 0,
            status: resizingBooking.status || 'confirmed'
          };
          
          if (resizeDirection === 'start') {
            // Changing check-in date
            updateData.check_in = resizePreview.date.toISOString().split('T')[0];
            updateData.check_out = resizingBooking.check_out;
          } else {
            // Changing check-out date
            updateData.check_in = resizingBooking.check_in;
            const newCheckOut = new Date(resizePreview.date);
            newCheckOut.setDate(newCheckOut.getDate() + 1); // Add 1 day for checkout
            updateData.check_out = newCheckOut.toISOString().split('T')[0];
          }
          
          // Recalculate total amount based on new dates
          const checkIn = new Date(updateData.check_in);
          const checkOut = new Date(updateData.check_out);
          const nights = Math.ceil((checkOut - checkIn) / (1000 * 60 * 60 * 24));
          const room = rooms.find(r => r.id === resizingBooking.room_id);
          updateData.total_amount = (room?.base_price || 100) * nights;
          
          console.log('🔄 Rezervasyon uzunluğu değiştiriliyor:', {
            bookingId: resizingBooking.id,
            direction: resizeDirection,
            newCheckIn: updateData.check_in,
            newCheckOut: updateData.check_out,
            nights: nights,
            totalAmount: updateData.total_amount
          });
          
          await axios.put(`/pms/bookings/${resizingBooking.id}`, updateData);
          
          if (resizeDirection === 'start') {
            toast.success(`✅ Giriş tarihi değiştirildi: ${updateData.check_in}`);
          } else {
            toast.success(`✅ Çıkış tarihi değiştirildi: ${updateData.check_out} (${nights} gece)`);
          }
          
          loadCalendarData();
        } catch (error) {
          toast.error('Rezervasyon uzunluğu değiştirilemedi');
          console.error('Resize error:', error);
        }
      }
      
      setResizingBooking(null);
      setResizeDirection(null);
      setResizePreview(null);
    };
    
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [resizingBooking, resizeDirection, resizePreview, rooms]);


  // Real-time updates - Poll every 60 seconds for new bookings (optimized for performance)
  useEffect(() => {
    if (!showAIPanel && !showDeluxePanel && !showConflictSolutions) {
      const interval = setInterval(() => {
        // Silent refresh - don't show loading state
        const silentRefresh = async () => {
          try {
            const startDate = currentDate.toISOString().split('T')[0];
            const endDate = new Date(currentDate);
            endDate.setDate(endDate.getDate() + daysToShow);
            const endDateStr = endDate.toISOString().split('T')[0];
            
            // PERFORMANCE: Only fetch bookings for visible date range with limit
            const bookingsRes = await axios.get(`/pms/bookings?start_date=${startDate}&end_date=${endDateStr}&limit=500`);
            const newBookings = bookingsRes.data || [];
            
            // Only update if there are changes
            if (JSON.stringify(newBookings) !== JSON.stringify(bookings)) {
              setBookings(newBookings);
              toast.info('📡 Calendar updated with latest bookings', { duration: 2000 });
            }
          } catch (error) {
            console.error('Silent refresh failed:', error);
          }
        };
        
        silentRefresh();
      }, 60000); // 60 seconds (optimized from 30s for better performance)
      
      return () => clearInterval(interval);
    }
  }, [currentDate, daysToShow, bookings, showAIPanel, showDeluxePanel, showConflictSolutions]);


  const loadHistoricalTrends = async () => {
    try {
      // Get last 90 days for trend analysis
      const endDate = new Date();
      const startDate = new Date();
      startDate.setDate(startDate.getDate() - 90);
      
      const response = await axios.get(`/analytics/occupancy-trend?start_date=${startDate.toISOString().split('T')[0]}&end_date=${endDate.toISOString().split('T')[0]}`);
      setHistoricalTrends(response.data);
    } catch (error) {
      console.error('Failed to load historical trends:', error);
    }
  };


  const loadEnterpriseData = async () => {
    try {
      const startDate = currentDate.toISOString().split('T')[0];
      const endDate = new Date(currentDate.getTime() + daysToShow * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      
      const [leakageRes, heatmapRes, pickupRes, leadTimeRes] = await Promise.all([
        axios.get(`/enterprise/rate-leakage?start_date=${startDate}&end_date=${endDate}`).catch(() => ({ data: { leakages: [] } })),
        axios.get(`/enterprise/availability-heatmap?start_date=${startDate}&end_date=${endDate}`).catch(() => ({ data: { heatmap: [] } })),
        axios.get(`/deluxe/pickup-pace-analytics?start_date=${startDate}&end_date=${endDate}`).catch(() => ({ data: null })),
        axios.get(`/deluxe/lead-time-analysis?start_date=${startDate}&end_date=${endDate}`).catch(() => ({ data: null }))
      ]);
      
      setRateLeakages(leakageRes.data.leakages || []);
      setAvailabilityHeatmap(heatmapRes.data.heatmap || []);
      setPickupPaceData(pickupRes.data);
      setLeadTimeData(leadTimeRes.data);
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
    
    // Calculate booking span for visual representation
    const checkIn = new Date(booking.check_in);
    const checkOut = new Date(booking.check_out);
    const bookingSpan = Math.max(1, Math.ceil((checkOut - checkIn) / (1000 * 60 * 60 * 24)));
    const bookingWidth = bookingSpan * 96; // 96px per day
    
    // Create custom drag image showing full booking length with INLINE STYLES
    const dragPreview = document.createElement('div');
    dragPreview.style.cssText = `
      position: absolute;
      top: -1000px;
      left: 0;
      width: ${bookingWidth}px;
      height: 70px;
      background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
      border-radius: 12px;
      box-shadow: 0 15px 40px rgba(37, 99, 235, 0.5), 0 5px 15px rgba(0,0,0,0.3);
      border: 4px solid #60a5fa;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', system-ui, sans-serif;
    `;
    
    // Create cells for each day with inline styles - More aesthetic layout
    let cellsHTML = '';
    for (let i = 0; i < bookingSpan; i++) {
      const borderStyle = i < bookingSpan - 1 ? 'border-right: 3px solid rgba(255,255,255,0.5);' : '';
      cellsHTML += `
        <div style="
          flex: 1;
          ${borderStyle}
          display: flex;
          align-items: center;
          justify-content: center;
          font-size: 14px;
          color: white;
          padding: 2px;
        ">
          ${i === Math.floor(bookingSpan / 2) ? '📅' : ''}
        </div>
      `;
    }
    
    dragPreview.innerHTML = `
      <div style="
        flex: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 20px;
        font-weight: 900;
        color: white;
        padding: 0 20px;
        text-align: center;
        text-shadow: 0 4px 8px rgba(0,0,0,0.6);
        letter-spacing: 0.5px;
        background: rgba(255,255,255,0.15);
        line-height: 1.2;
      ">
        ${booking.guest_name || 'Misafir'}
      </div>
      <div style="display: flex; height: 20px; background: rgba(0,0,0,0.2);">
        ${cellsHTML}
      </div>
      <div style="
        background: linear-gradient(135deg, #000000 0%, #1e293b 100%);
        color: #fbbf24;
        font-size: 13px;
        padding: 4px 12px;
        font-weight: 900;
        text-align: center;
        height: 20px;
        line-height: 12px;
        letter-spacing: 1.2px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.5);
      ">
        ${bookingSpan} GECE • $${booking.total_amount?.toFixed(0) || '0'}
      </div>
    `;
    
    document.body.appendChild(dragPreview);
    e.dataTransfer.setDragImage(dragPreview, bookingWidth / 2, 30);
    
    setTimeout(() => {
      try {
        document.body.removeChild(dragPreview);
      } catch (err) {
        console.log('Drag preview already removed');
      }
    }, 0);
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
    
    // Check if moving within same room type - ALWAYS ask for reason
    const isSameRoomType = oldRoom?.room_type === newRoom?.room_type;
    
    setMoveData({
      booking: draggingBooking,
      oldRoom: oldRoom?.room_number,
      newRoom: newRoom?.room_number,
      oldRoomType: oldRoom?.room_type,
      newRoomType: newRoom?.room_type,
      isSameRoomType: isSameRoomType,
      oldCheckIn: draggingBooking.check_in,
      newCheckIn: newCheckIn.toISOString().split('T')[0],
      newCheckOut: newCheckOut.toISOString().split('T')[0],
      newRoomId: newRoomId
    });
    
    // ALWAYS show reason dialog for all room moves
    setShowMoveReasonDialog(true);
    setDraggingBooking(null);
  };

  const handleConfirmMove = async () => {
    if (!moveReason.trim()) {
      toast.error('Lütfen oda taşıma nedeni belirtin');
      return;
    }
    
    // Extra validation for same room type moves
    if (moveData.isSameRoomType && moveReason === '') {
      toast.error('Aynı oda tipi içinde taşıma yapıyorsunuz. Neden zorunludur.');
      return;
    }
    
    console.log('🔄 Oda taşıma işlemi:', {
      bookingId: moveData.booking.id,
      from: `${moveData.oldRoom} (${moveData.oldRoomType}) - ${moveData.oldCheckIn}`,
      to: `${moveData.newRoom} (${moveData.newRoomType}) - ${moveData.newCheckIn}`,
      isSameRoomType: moveData.isSameRoomType,
      reason: moveReason,
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
      
      console.log('✅ Rezervasyon güncellendi:', updateResponse.data);
      
      // Log room move history with enhanced details
      await axios.post('/pms/room-move-history', {
        booking_id: moveData.booking.id,
        old_room: moveData.oldRoom,
        new_room: moveData.newRoom,
        old_room_type: moveData.oldRoomType,
        new_room_type: moveData.newRoomType,
        is_same_room_type: moveData.isSameRoomType,
        old_check_in: moveData.oldCheckIn,
        new_check_in: moveData.newCheckIn,
        reason: moveReason,
        moved_by: user.name,
        timestamp: new Date().toISOString()
      }).catch(err => console.log('Geçmiş kaydı başarısız:', err));
      
      // Always navigate to the new booking date to ensure it's visible
      const newCheckIn = new Date(moveData.newCheckIn);
      console.log('📅 Takvim yeni tarihe yönlendiriliyor:', newCheckIn.toISOString().split('T')[0]);
      
      setShowMoveReasonDialog(false);
      setMoveReason('');
      setMoveData(null);
      
      // Set the new date FIRST, then reload data
      setCurrentDate(newCheckIn);
      
      const moveTypeInfo = moveData.isSameRoomType 
        ? `(Aynı tip: ${moveData.newRoomType})` 
        : `(${moveData.oldRoomType} → ${moveData.newRoomType})`;
      
      toast.success(`✅ Rezervasyon Oda ${moveData.newRoom}'a taşındı ${moveTypeInfo}`);
      
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
  // Get bookings for a specific cell (room + date) - Memoized for performance
  const getBookingsForCell = useCallback((roomId, date) => {
    return bookings.filter(booking => {
      const checkIn = new Date(booking.check_in);
      const checkOut = new Date(booking.check_out);
      const cellDate = new Date(date);
      
      checkIn.setHours(0, 0, 0, 0);
      checkOut.setHours(0, 0, 0, 0);
      cellDate.setHours(0, 0, 0, 0);
      
      return booking.room_id === roomId && 
             cellDate >= checkIn && 
             cellDate < checkOut;
    });
  }, [bookings]);

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
      corporate: 'bg-blue-500',          // Corporate → Soft Blue
      'ota': 'bg-purple-500',            // OTA → Soft Purple
      'walk_in': 'bg-orange-400',        // Walk-in → Soft Orange
      'walk-in': 'bg-orange-400',        // Walk-in → Soft Orange
      group: 'bg-emerald-500',           // Group → Emerald
      leisure: 'bg-pink-400',            // Leisure → Soft Pink
      government: 'bg-indigo-500',       // Government → Soft Indigo
      promotional: 'bg-gradient-to-r from-amber-400 to-orange-400',  // Promo → Soft Gradient
      promo: 'bg-gradient-to-r from-amber-400 to-orange-400',
      'non_refundable': 'bg-rose-500',   // Non-refundable → Rose
      'advance_purchase': 'bg-teal-500', // Advance Purchase → Teal
      guaranteed: 'bg-sky-500',          // Guaranteed → Sky Blue
      default: 'bg-slate-500'            // Default → Slate
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
      'group': { label: 'GROUP', color: 'text-green-300' },
      'promotional': { label: '🎉 PROMO', color: 'text-yellow-300 font-bold' },
      'promo': { label: '🎉 PROMO', color: 'text-yellow-300 font-bold' },
      'non_refundable': { label: 'NON-REF', color: 'text-red-300' },
      'advance_purchase': { label: 'ADVANCE', color: 'text-teal-300' }
    };
    
    return rateTypes[booking.rate_type] || { label: booking.rate_type?.toUpperCase() || 'STD', color: 'text-gray-300' };
  };


  // RMS Dynamic Pricing - Generate alerts based on occupancy and conflicts
  const generatePricingAlerts = () => {
    const alerts = [];
    const dateRange = Array.from({ length: daysToShow }, (_, i) => {
      const date = new Date(currentDate);
      date.setDate(date.getDate() + i);
      return date;
    });

    dateRange.forEach(date => {
      const occ = getOccupancyForDate(date);
      const dateStr = date.toISOString().split('T')[0];
      
      // High demand alert
      if (occ >= 90) {
        alerts.push({
          date: dateStr,
          type: 'increase',
          severity: 'high',
          message: `Increase rates by 15-25% (${occ}% occupancy)`,
          suggested_action: 'INCREASE',
          percentage: '15-25%'
        });
      } else if (occ >= 80) {
        alerts.push({
          date: dateStr,
          type: 'increase',
          severity: 'medium',
          message: `Consider rate increase of 10-15% (${occ}% occupancy)`,
          suggested_action: 'INCREASE',
          percentage: '10-15%'
        });
      }
      // Low demand alert
      else if (occ < 40) {
        alerts.push({
          date: dateStr,
          type: 'decrease',
          severity: 'medium',
          message: `Consider promotional rates or packages (${occ}% occupancy)`,
          suggested_action: 'PROMOTE',
          percentage: '10-20% discount'
        });
      }
    });

    return alerts.slice(0, 10); // Top 10 alerts
  };

  // Calculate pricing alerts when data changes
  useEffect(() => {
    if (bookings.length > 0 && rooms.length > 0) {
      const alerts = generatePricingAlerts();
      setPricingAlerts(alerts);
    }
  }, [bookings, rooms, currentDate, daysToShow]);


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

  // Filtered rooms and bookings based on active filters
  const filteredRooms = useMemo(() => {
    let filtered = [...rooms];
    
    if (filters.roomType) {
      filtered = filtered.filter(r => r.room_type === filters.roomType);
    }
    
    if (filters.roomStatus) {
      filtered = filtered.filter(r => r.status === filters.roomStatus);
    }
    
    return filtered;
  }, [rooms, filters.roomType, filters.roomStatus]);

  const filteredBookings = useMemo(() => {
    let filtered = [...bookings];
    
    if (filters.bookingStatus) {
      filtered = filtered.filter(b => b.status === filters.bookingStatus);
    }
    
    if (filters.marketSegment) {
      filtered = filtered.filter(b => b.market_segment === filters.marketSegment);
    }
    
    return filtered;
  }, [bookings, filters.bookingStatus, filters.marketSegment]);

  // Quick stats
  const quickStats = useMemo(() => {
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    const todayBookings = bookings.filter(b => {
      const checkIn = new Date(b.check_in);
      const checkOut = new Date(b.check_out);
      checkIn.setHours(0, 0, 0, 0);
      checkOut.setHours(0, 0, 0, 0);
      return checkIn <= today && checkOut > today && b.status !== 'cancelled';
    });
    
    const arrivals = bookings.filter(b => {
      const checkIn = new Date(b.check_in);
      checkIn.setHours(0, 0, 0, 0);
      return checkIn.getTime() === today.getTime();
    });
    
    const departures = bookings.filter(b => {
      const checkOut = new Date(b.check_out);
      checkOut.setHours(0, 0, 0, 0);
      return checkOut.getTime() === today.getTime();
    });
    
    const occupiedRooms = todayBookings.length;
    const totalRooms = rooms.length;
    const occupancyRate = totalRooms > 0 ? (occupiedRooms / totalRooms * 100).toFixed(1) : 0;
    
    const todayRevenue = todayBookings.reduce((sum, b) => {
      const nights = Math.ceil((new Date(b.check_out) - new Date(b.check_in)) / (1000 * 60 * 60 * 24));
      return sum + (b.total_amount || 0) / (nights || 1);
    }, 0);
    
    return {
      occupiedRooms,
      totalRooms,
      occupancyRate,
      availableRooms: totalRooms - occupiedRooms,
      arrivals: arrivals.length,
      departures: departures.length,
      todayRevenue: todayRevenue.toFixed(2)
    };
  }, [bookings, rooms]);


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
            <Button 
              variant={bulkActionMode ? "default" : "outline"}
              onClick={() => {
                setBulkActionMode(!bulkActionMode);
                setSelectedBookings([]);
              }}
            >
              <CheckSquare className="w-4 h-4 mr-2" />
              Bulk Actions
            </Button>
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

        {/* Quick Stats Panel */}
        <div className="grid grid-cols-6 gap-4 mb-4">
          <Card>
            <CardContent className="p-4">
              <div className="text-xs text-gray-600">Occupancy</div>
              <div className="text-2xl font-bold text-blue-600">{quickStats.occupancyRate}%</div>
              <div className="text-xs text-gray-500">{quickStats.occupiedRooms}/{quickStats.totalRooms} rooms</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-xs text-gray-600">Available</div>
              <div className="text-2xl font-bold text-green-600">{quickStats.availableRooms}</div>
              <div className="text-xs text-gray-500">rooms ready</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-xs text-gray-600">Arrivals</div>
              <div className="text-2xl font-bold text-orange-600">{quickStats.arrivals}</div>
              <div className="text-xs text-gray-500">today</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-xs text-gray-600">Departures</div>
              <div className="text-2xl font-bold text-purple-600">{quickStats.departures}</div>
              <div className="text-xs text-gray-500">today</div>
            </CardContent>
          </Card>
          <Card>
            <CardContent className="p-4">
              <div className="text-xs text-gray-600">Today Revenue</div>
              <div className="text-2xl font-bold text-green-600">${quickStats.todayRevenue}</div>
              <div className="text-xs text-gray-500">estimated</div>
            </CardContent>
          </Card>
          <Card className="cursor-pointer hover:bg-gray-50" onClick={() => setFilters({...filters, showFilters: !filters.showFilters})}>
            <CardContent className="p-4 flex flex-col items-center justify-center">
              <Filter className={`w-6 h-6 mb-1 ${filters.showFilters ? 'text-blue-600' : 'text-gray-600'}`} />
              <div className="text-xs font-semibold">{filters.showFilters ? 'Hide Filters' : 'Show Filters'}</div>
            </CardContent>
          </Card>
          <Card className="cursor-pointer hover:bg-gray-50" onClick={() => setViewMode(viewMode === 'simplified' ? 'detailed' : 'simplified')}>
            <CardContent className="p-4 flex flex-col items-center justify-center">
              <Monitor className={`w-6 h-6 mb-1 ${viewMode === 'simplified' ? 'text-green-600' : 'text-blue-600'}`} />
              <div className="text-xs font-semibold">{viewMode === 'simplified' ? '✨ Minimal' : '📊 Detailed'}</div>
            </CardContent>
          </Card>
        </div>

        {/* Advanced Filters Panel */}
        {filters.showFilters && (
          <Card className="mb-4 border-blue-200 bg-blue-50">
            <CardContent className="p-4">
              <div className="grid grid-cols-4 gap-4">
                <div>
                  <Label className="text-xs">Room Type</Label>
                  <select
                    className="w-full border rounded-md p-2 text-sm"
                    value={filters.roomType}
                    onChange={(e) => setFilters({...filters, roomType: e.target.value})}
                  >
                    <option value="">All Types</option>
                    <option value="suite">Suite</option>
                    <option value="deluxe">Deluxe</option>
                    <option value="superior">Superior</option>
                    <option value="standard">Standard</option>
                    <option value="economy">Economy</option>
                  </select>
                </div>
                <div>
                  <Label className="text-xs">Room Status</Label>
                  <select
                    className="w-full border rounded-md p-2 text-sm"
                    value={filters.roomStatus}
                    onChange={(e) => setFilters({...filters, roomStatus: e.target.value})}
                  >
                    <option value="">All Status</option>
                    <option value="available">Available</option>
                    <option value="occupied">Occupied</option>
                    <option value="dirty">Dirty</option>
                    <option value="cleaning">Cleaning</option>
                    <option value="inspected">Inspected</option>
                    <option value="out_of_order">Out of Order</option>
                  </select>
                </div>
                <div>
                  <Label className="text-xs">Booking Status</Label>
                  <select
                    className="w-full border rounded-md p-2 text-sm"
                    value={filters.bookingStatus}
                    onChange={(e) => setFilters({...filters, bookingStatus: e.target.value})}
                  >
                    <option value="">All Status</option>
                    <option value="confirmed">Confirmed</option>
                    <option value="guaranteed">Guaranteed</option>
                    <option value="checked_in">Checked In</option>
                    <option value="checked_out">Checked Out</option>
                  </select>
                </div>
                <div>
                  <Label className="text-xs">Market Segment</Label>
                  <select
                    className="w-full border rounded-md p-2 text-sm"
                    value={filters.marketSegment}
                    onChange={(e) => setFilters({...filters, marketSegment: e.target.value})}
                  >
                    <option value="">All Segments</option>
                    <option value="leisure">Leisure</option>
                    <option value="corporate">Corporate</option>
                    <option value="group">Group</option>
                    <option value="government">Government</option>
                  </select>
                </div>
              </div>
              <div className="mt-3 flex justify-end">
                <Button
                  size="sm"
                  variant="outline"
                  onClick={() => setFilters({
                    roomType: '',
                    roomStatus: '',
                    bookingStatus: '',
                    marketSegment: '',
                    showFilters: true
                  })}
                >
                  Clear All Filters
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* Bulk Actions Toolbar */}
        {bulkActionMode && (
          <Card className="mb-4 border-purple-200 bg-purple-50">
            <CardContent className="p-4">
              <div className="flex justify-between items-center">
                <div className="flex items-center gap-4">
                  <div className="font-semibold">
                    {selectedBookings.length} booking(s) selected
                  </div>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      setSelectedBookings([]);
                      setBulkActionMode(false);
                    }}
                  >
                    Cancel Selection
                  </Button>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    disabled={selectedBookings.length === 0}
                    onClick={async () => {
                      if (window.confirm(`Check-in ${selectedBookings.length} bookings?`)) {
                        try {
                          let success = 0;
                          for (const bookingId of selectedBookings) {
                            try {
                              await axios.post(`/frontdesk/checkin/${bookingId}`);
                              success++;
                            } catch (error) {
                              console.error(`Failed to check-in ${bookingId}:`, error);
                            }
                          }
                          toast.success(`${success}/${selectedBookings.length} bookings checked in`);
                          setSelectedBookings([]);
                          setBulkActionMode(false);
                          loadCalendarData();
                        } catch (error) {
                          toast.error('Bulk check-in failed');
                        }
                      }
                    }}
                  >
                    <CheckCircle className="w-4 h-4 mr-2" />
                    Bulk Check-In
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={selectedBookings.length === 0}
                    onClick={async () => {
                      if (window.confirm(`Check-out ${selectedBookings.length} bookings?`)) {
                        try {
                          let success = 0;
                          for (const bookingId of selectedBookings) {
                            try {
                              await axios.post(`/frontdesk/checkout/${bookingId}`);
                              success++;
                            } catch (error) {
                              console.error(`Failed to check-out ${bookingId}:`, error);
                            }
                          }
                          toast.success(`${success}/${selectedBookings.length} bookings checked out`);
                          setSelectedBookings([]);
                          setBulkActionMode(false);
                          loadCalendarData();
                        } catch (error) {
                          toast.error('Bulk check-out failed');
                        }
                      }
                    }}
                  >
                    <XCircle className="w-4 h-4 mr-2" />
                    Bulk Check-Out
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        )}

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
                  {groupedConflicts && groupedConflicts.total_conflict_count > 0 && (
                    <Button
                      size="sm"
                      variant={showConflictSolutions ? "default" : "outline"}
                      onClick={() => setShowConflictSolutions(!showConflictSolutions)}
                      className="flex items-center gap-2 bg-gradient-to-r from-red-500 to-pink-600 text-white hover:from-red-600 hover:to-pink-700"
                    >
                      ⚠️ Conflicts ({groupedConflicts.total_conflict_count})
                    </Button>
                  )}
                  <Button
                    size="sm"
                    variant={showHistoricalPanel ? "default" : "outline"}
                    onClick={() => {
                      setShowHistoricalPanel(!showHistoricalPanel);
                      if (!historicalTrends) loadHistoricalTrends();
                    }}
                    className="flex items-center gap-2"
                  >
                    📊 Historical Trends
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

              {/* Pickup Pace Analytics */}
              {pickupPaceData && (
                <div className="bg-white p-3 rounded-lg border-2 border-amber-300">
                  <div className="text-sm font-semibold text-amber-700 mb-3 flex items-center justify-between">
                    <span>📊 Pickup Pace Analysis</span>
                    <Badge variant="outline" className="bg-amber-100 text-amber-700">
                      {pickupPaceData.period || '30 days'}
                    </Badge>
                  </div>
                  <div className="grid grid-cols-3 gap-3 mb-3">
                    <div className="text-center bg-amber-50 p-2 rounded">
                      <div className="text-xl font-bold text-amber-700">
                        {pickupPaceData.total_bookings || 0}
                      </div>
                      <div className="text-xs text-gray-600">Total Bookings</div>
                    </div>
                    <div className="text-center bg-green-50 p-2 rounded">
                      <div className="text-xl font-bold text-green-700">
                        {pickupPaceData.pace_percentage || 0}%
                      </div>
                      <div className="text-xs text-gray-600">vs Last Year</div>
                    </div>
                    <div className="text-center bg-blue-50 p-2 rounded">
                      <div className="text-xl font-bold text-blue-700">
                        {pickupPaceData.avg_daily_pickup || 0}
                      </div>
                      <div className="text-xs text-gray-600">Avg Daily</div>
                    </div>
                  </div>
                  {pickupPaceData.trend && (
                    <div className="text-xs">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-gray-600">Trend:</span>
                        <Badge className={`${
                          pickupPaceData.trend === 'up' ? 'bg-green-500' :
                          pickupPaceData.trend === 'down' ? 'bg-red-500' :
                          'bg-gray-500'
                        } text-white text-[9px]`}>
                          {pickupPaceData.trend === 'up' ? '↗ Increasing' :
                           pickupPaceData.trend === 'down' ? '↘ Decreasing' :
                           '→ Stable'}
                        </Badge>
                      </div>
                      <div className="bg-gray-100 rounded-full h-2 mt-2">
                        <div 
                          className={`h-2 rounded-full ${
                            pickupPaceData.pace_percentage >= 100 ? 'bg-green-500' :
                            pickupPaceData.pace_percentage >= 80 ? 'bg-yellow-500' :
                            'bg-red-500'
                          }`}
                          style={{ width: `${Math.min(pickupPaceData.pace_percentage || 0, 100)}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Lead Time Analysis */}
              {leadTimeData && (
                <div className="bg-white p-3 rounded-lg border-2 border-amber-300">
                  <div className="text-sm font-semibold text-amber-700 mb-3">
                    ⏱️ Lead Time Analysis
                  </div>
                  <div className="grid grid-cols-2 gap-3">
                    <div className="text-center bg-purple-50 p-2 rounded">
                      <div className="text-xl font-bold text-purple-700">
                        {leadTimeData.avg_lead_time || 0}
                      </div>
                      <div className="text-xs text-gray-600">Avg Lead Days</div>
                    </div>
                    <div className="text-center bg-indigo-50 p-2 rounded">
                      <div className="text-xl font-bold text-indigo-700">
                        {leadTimeData.median_lead_time || 0}
                      </div>
                      <div className="text-xs text-gray-600">Median Days</div>
                    </div>
                  </div>
                  {leadTimeData.distribution && (
                    <div className="mt-3 space-y-1">
                      <div className="text-xs text-gray-600 font-medium">Booking Window:</div>
                      {Object.entries(leadTimeData.distribution).slice(0, 4).map(([range, count]) => (
                        <div key={range} className="flex items-center justify-between text-xs">
                          <span className="text-gray-600">{range}</span>
                          <div className="flex items-center gap-2">
                            <div className="w-24 bg-gray-200 rounded-full h-1.5">
                              <div 
                                className="bg-amber-500 h-1.5 rounded-full"
                                style={{ width: `${(count / Math.max(...Object.values(leadTimeData.distribution))) * 100}%` }}
                              />
                            </div>
                            <span className="font-medium w-8 text-right">{count}</span>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}

              {/* Empty State */}
              {groupBookings.length === 0 && oversellProtection.length === 0 && !channelMixData && !pickupPaceData && !leadTimeData && (
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


              {/* RMS Dynamic Pricing Alerts */}
              {pricingAlerts.length > 0 && (
                <div className="bg-white p-3 rounded-lg border-2 border-blue-300">
                  <div className="text-sm font-semibold text-blue-700 mb-3 flex items-center justify-between">
                    <span>📈 RMS Pricing Alerts</span>
                    <Badge variant="outline" className="bg-blue-100 text-blue-700">
                      {pricingAlerts.length} alerts
                    </Badge>
                  </div>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {pricingAlerts.map((alert, idx) => (
                      <div 
                        key={idx} 
                        className={`p-3 rounded-lg border-l-4 ${
                          alert.type === 'increase' && alert.severity === 'high' ? 'bg-green-50 border-l-green-600' :
                          alert.type === 'increase' ? 'bg-blue-50 border-l-blue-500' :
                          'bg-orange-50 border-l-orange-500'
                        }`}
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex-1">
                            <div className="font-semibold text-sm flex items-center gap-2">
                              {alert.type === 'increase' ? '📈' : '📉'}
                              {new Date(alert.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}
                            </div>
                            <div className="text-xs text-gray-600 mt-1">
                              {alert.message}
                            </div>
                          </div>
                          <Badge className={`${
                            alert.type === 'increase' && alert.severity === 'high' ? 'bg-green-600' :
                            alert.type === 'increase' ? 'bg-blue-500' :
                            'bg-orange-500'
                          } text-white text-xs`}>
                            {alert.suggested_action}
                          </Badge>
                        </div>
                        <div className="flex items-center justify-between pt-2 border-t border-gray-200">
                          <span className="text-xs text-gray-500">Suggested Change:</span>
                          <span className={`text-xs font-bold ${
                            alert.type === 'increase' ? 'text-green-600' : 'text-orange-600'
                          }`}>
                            {alert.type === 'increase' ? '+' : ''}{alert.percentage}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                  <div className="mt-3 pt-3 border-t text-xs text-gray-600">
                    <div className="flex items-center gap-2">
                      <span className="font-medium">💡 Tip:</span>
                      <span>Pricing alerts are calculated based on occupancy trends and market demand</span>
                    </div>
                  </div>
                </div>
              )}

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


        {/* Conflict Solutions Panel */}
        {showConflictSolutions && groupedConflicts && (
          <Card className="border-red-300 bg-red-50">
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg flex items-center gap-2 text-red-800">
                  ⚠️ Booking Conflicts & Solutions
                </CardTitle>
                <Badge variant="destructive">
                  {groupedConflicts.total_conflict_count} conflicts in {groupedConflicts.affected_rooms} rooms
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Summary Cards */}
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-white p-3 rounded-lg border border-red-200 text-center">
                  <div className="text-2xl font-bold text-red-600">{groupedConflicts.summary.critical}</div>
                  <div className="text-xs text-gray-600">Critical (&gt;5 overlaps)</div>
                </div>
                <div className="bg-white p-3 rounded-lg border border-orange-200 text-center">
                  <div className="text-2xl font-bold text-orange-600">{groupedConflicts.summary.high}</div>
                  <div className="text-xs text-gray-600">High (3-5 overlaps)</div>
                </div>
                <div className="bg-white p-3 rounded-lg border border-yellow-200 text-center">
                  <div className="text-2xl font-bold text-yellow-600">{groupedConflicts.summary.medium}</div>
                  <div className="text-xs text-gray-600">Medium (2 overlaps)</div>
                </div>
              </div>

              {/* Top Critical Rooms */}
              <div>
                <div className="text-sm font-semibold text-gray-700 mb-3 flex items-center justify-between">
                  <span>🔥 Top Critical Rooms (Immediate Action Required)</span>
                  <Button 
                    size="sm" 
                    variant="outline"
                    className="text-xs h-7"
                    onClick={async () => {
                      if (!confirm('This will automatically move bookings to resolve all conflicts. Continue?')) return;
                      
                      try {
                        toast.info('🤖 AI analyzing conflicts and finding solutions...');
                        const response = await axios.post('/ai/solve-overbooking', {
                          start_date: currentDate.toISOString().split('T')[0],
                          end_date: new Date(currentDate.getTime() + (daysToShow * 24 * 60 * 60 * 1000)).toISOString().split('T')[0]
                        });
                        
                        if (response.data.solutions) {
                          toast.success(`✅ Resolved ${response.data.solutions.length} conflicts!`);
                          loadCalendarData(); // Refresh
                          setShowConflictSolutions(false);
                        } else {
                          toast.warning('No automatic solution available. Please resolve manually.');
                        }
                      } catch (error) {
                        toast.error(error.response?.data?.detail || 'Failed to auto-resolve conflicts');
                      }
                    }}
                  >
                    🤖 Auto-Resolve All
                  </Button>
                </div>
                <div className="space-y-2 max-h-80 overflow-y-auto">
                  {groupedConflicts.top_critical_rooms.map((room, index) => (
                    <div 
                      key={room.room_id} 
                      className={`bg-white p-4 rounded-lg border-l-4 ${
                        room.severity === 'critical' ? 'border-l-red-600' :
                        room.severity === 'high' ? 'border-l-orange-500' :
                        'border-l-yellow-500'
                      } shadow-sm`}
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center gap-3">
                          <div className={`
                            w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold
                            ${room.severity === 'critical' ? 'bg-red-600 text-white' :
                              room.severity === 'high' ? 'bg-orange-500 text-white' :
                              'bg-yellow-500 text-white'}
                          `}>
                            {index + 1}
                          </div>
                          <div>
                            <div className="font-bold text-lg">Room {room.room_number}</div>
                            <div className="text-xs text-gray-600 capitalize">{room.room_type}</div>
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-red-600">{room.total_overlaps}</div>
                          <div className="text-xs text-gray-600">overlaps</div>
                        </div>
                      </div>

                      {/* Conflict Dates */}
                      <div className="space-y-2 mt-3 pt-3 border-t">
                        <div className="text-xs font-semibold text-gray-700">Conflict Dates:</div>
                        {room.conflict_dates.slice(0, 3).map((conflict, idx) => (
                          <div key={idx} className="bg-gray-50 p-2 rounded text-xs">
                            <div className="flex items-center justify-between mb-1">
                              <span className="font-medium">{conflict.date}</span>
                              <Badge variant="destructive" className="text-xs">
                                {conflict.overlap_count} bookings
                              </Badge>
                            </div>
                            <div className="text-gray-600">
                              {conflict.bookings.slice(0, 2).map((booking, bidx) => (
                                <div key={bidx} className="truncate">
                                  • {booking.check_in.split('T')[0]} → {booking.check_out.split('T')[0]} (${Math.round(booking.total_amount || 0)})
                                </div>
                              ))}
                            </div>
                          </div>
                        ))}
                        {room.conflict_count > 3 && (
                          <div className="text-xs text-gray-500 italic">
                            +{room.conflict_count - 3} more conflict dates
                          </div>
                        )}
                      </div>

                      {/* Solutions */}
                      <div className="mt-3 pt-3 border-t bg-blue-50 -mx-4 -mb-4 p-3 rounded-b-lg">
                        <div className="text-xs font-semibold text-blue-900 mb-2">💡 Suggested Solutions:</div>
                        <div className="space-y-1 text-xs">
                          {room.severity === 'critical' && (
                            <>
                              <div className="flex items-start gap-2">
                                <span className="text-blue-600">1.</span>
                                <span>Move {room.total_overlaps - 1} guests to similar available rooms ({room.room_type})</span>
                              </div>
                              <div className="flex items-start gap-2">
                                <span className="text-blue-600">2.</span>
                                <span>Upgrade {room.total_overlaps - 1} bookings to higher category at no extra cost</span>
                              </div>
                              <div className="flex items-start gap-2">
                                <span className="text-blue-600">3.</span>
                                <span>Contact guests for voluntary relocation with compensation (voucher/discount)</span>
                              </div>
                            </>
                          )}
                          {room.severity === 'high' && (
                            <>
                              <div className="flex items-start gap-2">
                                <span className="text-blue-600">1.</span>
                                <span>Find {room.total_overlaps - 1} similar rooms and reassign</span>
                              </div>
                              <div className="flex items-start gap-2">
                                <span className="text-blue-600">2.</span>
                                <span>Check if any booking can be moved to adjacent dates</span>
                              </div>
                            </>
                          )}
                          {room.severity === 'medium' && (
                            <>
                              <div className="flex items-start gap-2">
                                <span className="text-blue-600">1.</span>
                                <span>Reassign 1 booking to an available room of same type</span>
                              </div>
                              <div className="flex items-start gap-2">
                                <span className="text-blue-600">2.</span>
                                <span>Contact the later-arriving guest for alternative arrangement</span>
                              </div>
                            </>
                          )}
                        </div>
                        <div className="mt-2 flex gap-2">
                          <Button 
                            size="sm" 
                            className="flex-1 text-xs h-7 bg-blue-600 hover:bg-blue-700"
                            onClick={() => {
                              // Get all bookings for this room on conflict dates
                              const roomBookings = room.conflict_dates.flatMap(conflict => 
                                conflict.bookings
                              );
                              setMoveBookingDialog({
                                open: true,
                                room: { room_number: room.room_number, room_type: room.room_type, id: room.room_id },
                                bookings: roomBookings
                              });
                            }}
                          >
                            🔄 Move Bookings
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline"
                            className="flex-1 text-xs h-7"
                            onClick={() => {
                              // Find first conflict date
                              const firstConflict = room.conflict_dates[0];
                              if (firstConflict && firstConflict.bookings.length > 0) {
                                const booking = firstConflict.bookings[0];
                                // Open find room with this booking's dates
                                window.open(`#find-room?check_in=${booking.check_in.split('T')[0]}&check_out=${booking.check_out.split('T')[0]}&room_type=${room.room_type}`, '_self');
                              }
                            }}
                          >
                            🔍 Find Rooms
                          </Button>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Action Tips */}
              <div className="bg-white p-3 rounded-lg border border-blue-200">
                <div className="text-xs font-semibold text-blue-900 mb-2">📝 Best Practices:</div>
                <ul className="text-xs text-gray-700 space-y-1 list-disc list-inside">
                  <li>Resolve conflicts starting from earliest check-in dates</li>
                  <li>Prioritize VIP guests and high-value bookings when relocating</li>
                  <li>Always offer upgrade or compensation for inconvenience</li>
                  <li>Document all changes and notify affected guests immediately</li>
                  <li>Keep alternative accommodations list ready for extreme cases</li>
                </ul>
              </div>
            </CardContent>
          </Card>
        )}


        {/* Historical Trends Panel */}
        {showHistoricalPanel && (
          <Card className="border-blue-300 bg-blue-50">
            <CardHeader className="pb-3">
              <CardTitle className="text-lg flex items-center gap-2 text-blue-800">
                📊 Historical Performance Analysis
              </CardTitle>
              <CardDescription>
                90-day occupancy and revenue trends
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              {historicalTrends ? (
                <>
                  {/* Summary Stats */}
                  <div className="grid grid-cols-4 gap-3">
                    <div className="bg-white p-3 rounded-lg border border-blue-200 text-center">
                      <div className="text-2xl font-bold text-blue-700">
                        {historicalTrends.avg_occupancy || 0}%
                      </div>
                      <div className="text-xs text-gray-600">Avg Occupancy</div>
                    </div>
                    <div className="bg-white p-3 rounded-lg border border-green-200 text-center">
                      <div className="text-2xl font-bold text-green-700">
                        ${historicalTrends.avg_adr || 0}
                      </div>
                      <div className="text-xs text-gray-600">Avg ADR</div>
                    </div>
                    <div className="bg-white p-3 rounded-lg border border-purple-200 text-center">
                      <div className="text-2xl font-bold text-purple-700">
                        ${historicalTrends.total_revenue || 0}
                      </div>
                      <div className="text-xs text-gray-600">Total Revenue</div>
                    </div>
                    <div className="bg-white p-3 rounded-lg border border-amber-200 text-center">
                      <div className="text-2xl font-bold text-amber-700">
                        {historicalTrends.total_bookings || 0}
                      </div>
                      <div className="text-xs text-gray-600">Total Bookings</div>
                    </div>
                  </div>

                  {/* Trend Indicators */}
                  <div className="grid grid-cols-3 gap-3">
                    <div className="bg-white p-3 rounded-lg border">
                      <div className="text-xs font-semibold text-gray-700 mb-2">Occupancy Trend</div>
                      <div className={`text-lg font-bold ${
                        historicalTrends.occupancy_trend === 'up' ? 'text-green-600' :
                        historicalTrends.occupancy_trend === 'down' ? 'text-red-600' :
                        'text-gray-600'
                      }`}>
                        {historicalTrends.occupancy_trend === 'up' ? '↗ Increasing' :
                         historicalTrends.occupancy_trend === 'down' ? '↘ Decreasing' :
                         '→ Stable'}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {historicalTrends.occupancy_change || 0}% vs previous period
                      </div>
                    </div>
                    <div className="bg-white p-3 rounded-lg border">
                      <div className="text-xs font-semibold text-gray-700 mb-2">Revenue Trend</div>
                      <div className={`text-lg font-bold ${
                        historicalTrends.revenue_trend === 'up' ? 'text-green-600' :
                        historicalTrends.revenue_trend === 'down' ? 'text-red-600' :
                        'text-gray-600'
                      }`}>
                        {historicalTrends.revenue_trend === 'up' ? '↗ Increasing' :
                         historicalTrends.revenue_trend === 'down' ? '↘ Decreasing' :
                         '→ Stable'}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        {historicalTrends.revenue_change || 0}% vs previous period
                      </div>
                    </div>
                    <div className="bg-white p-3 rounded-lg border">
                      <div className="text-xs font-semibold text-gray-700 mb-2">ADR Trend</div>
                      <div className={`text-lg font-bold ${
                        historicalTrends.adr_trend === 'up' ? 'text-green-600' :
                        historicalTrends.adr_trend === 'down' ? 'text-red-600' :
                        'text-gray-600'
                      }`}>
                        {historicalTrends.adr_trend === 'up' ? '↗ Increasing' :
                         historicalTrends.adr_trend === 'down' ? '↘ Decreasing' :
                         '→ Stable'}
                      </div>
                      <div className="text-xs text-gray-500 mt-1">
                        ${historicalTrends.adr_change || 0} vs previous period
                      </div>
                    </div>
                  </div>

                  {/* Best & Worst Days */}
                  <div className="grid grid-cols-2 gap-3">
                    <div className="bg-green-50 p-3 rounded-lg border border-green-200">
                      <div className="text-xs font-semibold text-green-900 mb-2">🌟 Best Performance Days</div>
                      {historicalTrends.best_days && historicalTrends.best_days.slice(0, 3).map((day, idx) => (
                        <div key={idx} className="text-xs text-gray-700 flex items-center justify-between mb-1">
                          <span>{new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                          <Badge className="bg-green-600 text-white text-[9px]">
                            {day.occupancy}% occ
                          </Badge>
                        </div>
                      ))}
                    </div>
                    <div className="bg-red-50 p-3 rounded-lg border border-red-200">
                      <div className="text-xs font-semibold text-red-900 mb-2">📉 Worst Performance Days</div>
                      {historicalTrends.worst_days && historicalTrends.worst_days.slice(0, 3).map((day, idx) => (
                        <div key={idx} className="text-xs text-gray-700 flex items-center justify-between mb-1">
                          <span>{new Date(day.date).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })}</span>
                          <Badge className="bg-red-600 text-white text-[9px]">
                            {day.occupancy}% occ
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Insights */}
                  <div className="bg-white p-3 rounded-lg border border-blue-200">
                    <div className="text-xs font-semibold text-blue-900 mb-2">💡 Key Insights:</div>
                    <ul className="text-xs text-gray-700 space-y-1 list-disc list-inside">
                      <li>Average occupancy is {historicalTrends.avg_occupancy > 70 ? 'healthy' : 'below target'} at {historicalTrends.avg_occupancy}%</li>
                      <li>ADR trend is {historicalTrends.adr_trend === 'up' ? 'positive' : historicalTrends.adr_trend === 'down' ? 'declining' : 'stable'}</li>
                      <li>Revenue performance is {historicalTrends.revenue_trend === 'up' ? 'improving' : historicalTrends.revenue_trend === 'down' ? 'declining' : 'stable'}</li>
                      <li>Consider reviewing pricing strategy for low-performing days</li>
                    </ul>
                  </div>
                </>
              ) : (
                <div className="text-center py-8">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto mb-2"></div>
                  <div className="text-sm text-gray-600">Loading historical data...</div>
                </div>
              )}
            </CardContent>
          </Card>
        )}




        {/* Move Booking Dialog */}
        <Dialog open={moveBookingDialog.open} onOpenChange={(open) => !open && setMoveBookingDialog({ open: false, room: null, bookings: [] })}>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                🔄 Move Booking to Resolve Conflict
              </DialogTitle>
            </DialogHeader>
            
            {moveBookingDialog.room && (
              <div className="space-y-4">
                {/* Current Room Info */}
                <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                  <div className="font-semibold text-red-900 mb-2">
                    Conflicted Room: {moveBookingDialog.room.room_number}
                  </div>
                  <div className="text-sm text-gray-700">
                    {moveBookingDialog.bookings.length} overlapping bookings need to be resolved
                  </div>
                </div>

                {/* Select Booking to Move */}
                <div>
                  <Label className="text-sm font-semibold mb-2 block">Select booking to move:</Label>
                  <div className="space-y-2">
                    {moveBookingDialog.bookings.map((booking) => {
                      const guest = guests.find(g => g.id === booking.guest_id);
                      return (
                        <div 
                          key={booking.id}
                          onClick={() => {
                            setSelectedBookingToMove(booking);
                            // Find available rooms for this booking's dates
                            const findAvailableRooms = async () => {
                              try {
                                const params = new URLSearchParams({
                                  check_in: booking.check_in.split('T')[0],
                                  check_out: booking.check_out.split('T')[0],
                                  room_type: moveBookingDialog.room.room_type
                                });
                                const response = await axios.get(`/frontdesk/available-rooms?${params.toString()}`);
                                setAvailableRoomsForMove(response.data.available_rooms || []);
                              } catch (error) {
                                toast.error('Failed to find available rooms');
                              }
                            };
                            findAvailableRooms();
                          }}
                          className={`p-3 rounded-lg border-2 cursor-pointer transition-all ${
                            selectedBookingToMove?.id === booking.id 
                              ? 'border-blue-500 bg-blue-50' 
                              : 'border-gray-200 hover:border-blue-300'
                          }`}
                        >
                          <div className="flex items-center justify-between">
                            <div>
                              <div className="font-medium">{guest?.name || 'Guest'}</div>
                              <div className="text-xs text-gray-600">
                                {new Date(booking.check_in).toLocaleDateString()} → {new Date(booking.check_out).toLocaleDateString()}
                              </div>
                            </div>
                            <div className="text-right">
                              <Badge>{booking.status}</Badge>
                              <div className="text-xs text-gray-600 mt-1">${Math.round(booking.total_amount || 0)}</div>
                            </div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Available Rooms for Selected Booking */}
                {selectedBookingToMove && availableRoomsForMove.length > 0 && (
                  <div>
                    <Label className="text-sm font-semibold mb-2 block">
                      Available rooms for {new Date(selectedBookingToMove.check_in).toLocaleDateString()} → {new Date(selectedBookingToMove.check_out).toLocaleDateString()}:
                    </Label>
                    <div className="grid grid-cols-2 gap-3 max-h-64 overflow-y-auto">
                      {availableRoomsForMove.map((room) => (
                        <Card key={room.id} className="border-l-4 border-l-green-500">
                          <CardContent className="p-3">
                            <div className="space-y-2">
                              <div className="flex items-center justify-between">
                                <span className="font-semibold">Room {room.room_number}</span>
                                <Badge variant="secondary">{room.room_type}</Badge>
                              </div>
                              <div className="text-xs text-gray-600">
                                Floor {room.floor} • ${room.base_price}/night
                              </div>
                              <Button 
                                size="sm" 
                                className="w-full"
                                onClick={async () => {
                                  try {
                                    await axios.put(`/bookings/${selectedBookingToMove.id}`, {
                                      ...selectedBookingToMove,
                                      room_id: room.id
                                    });
                                    toast.success(`Booking moved to Room ${room.room_number}!`);
                                    setMoveBookingDialog({ open: false, room: null, bookings: [] });
                                    setSelectedBookingToMove(null);
                                    setAvailableRoomsForMove([]);
                                    loadCalendarData(); // Refresh calendar
                                  } catch (error) {
                                    toast.error('Failed to move booking');
                                  }
                                }}
                              >
                                Move Here
                              </Button>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                  </div>
                )}

                {selectedBookingToMove && availableRoomsForMove.length === 0 && (
                  <div className="text-center py-8 bg-gray-50 rounded-lg">
                    <div className="text-gray-600 mb-2">No available rooms found</div>
                    <div className="text-xs text-gray-500">Try selecting a different booking or adjusting dates</div>
                  </div>
                )}
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Legend - Market Segments & Quick Tips */}
        <Card>
          <CardContent className="py-3">
            <div className="space-y-3">
              {/* Market Segment Colors - Enhanced & Customizable */}
              <div>
                <div className="flex items-center justify-between mb-2">
                  <div className="text-xs font-semibold text-gray-700">Market Segments & Rate Types:</div>
                  <Button 
                    size="sm" 
                    variant="ghost"
                    className="h-6 text-xs"
                    onClick={() => toast.info('Legend customization coming soon!')}
                  >
                    ⚙️ Customize
                  </Button>
                </div>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2 text-xs">
                  {/* Standard Segments */}
                  <div className="flex items-center gap-2 p-1.5 bg-gray-50 rounded">
                    <div className="w-4 h-4 bg-blue-600 rounded flex-shrink-0"></div>
                    <span className="truncate">Corporate</span>
                  </div>
                  <div className="flex items-center gap-2 p-1.5 bg-gray-50 rounded">
                    <div className="w-4 h-4 bg-purple-600 rounded flex-shrink-0"></div>
                    <span className="truncate">OTA</span>
                  </div>
                  <div className="flex items-center gap-2 p-1.5 bg-gray-50 rounded">
                    <div className="w-4 h-4 bg-orange-500 rounded flex-shrink-0"></div>
                    <span className="truncate">Walk-in</span>
                  </div>
                  <div className="flex items-center gap-2 p-1.5 bg-gray-50 rounded">
                    <div className="w-4 h-4 bg-green-600 rounded flex-shrink-0"></div>
                    <span className="truncate">Group</span>
                  </div>
                  <div className="flex items-center gap-2 p-1.5 bg-gray-50 rounded">
                    <div className="w-4 h-4 bg-pink-500 rounded flex-shrink-0"></div>
                    <span className="truncate">Leisure</span>
                  </div>
                  <div className="flex items-center gap-2 p-1.5 bg-gray-50 rounded">
                    <div className="w-4 h-4 bg-indigo-600 rounded flex-shrink-0"></div>
                    <span className="truncate">Government</span>
                  </div>
                  {/* Special Rate Types */}
                  <div className="flex items-center gap-2 p-1.5 bg-gradient-to-r from-yellow-100 to-orange-100 rounded">
                    <div className="w-4 h-4 bg-gradient-to-r from-yellow-500 to-orange-500 rounded flex-shrink-0"></div>
                    <span className="truncate font-medium">🎉 Promo</span>
                  </div>
                  <div className="flex items-center gap-2 p-1.5 bg-gray-50 rounded">
                    <div className="w-4 h-4 bg-red-600 rounded flex-shrink-0"></div>
                    <span className="truncate">Non-Refund</span>
                  </div>
                  <div className="flex items-center gap-2 p-1.5 bg-gray-50 rounded">
                    <div className="w-4 h-4 bg-teal-600 rounded flex-shrink-0"></div>
                    <span className="truncate">Advance</span>
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



        {/* Occupancy Graph - Above Calendar */}
        <Card className="bg-white shadow-sm">
          <CardContent className="p-4">
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-semibold text-gray-700">Doluluk %</div>
              <div className="text-xs text-gray-500">Son {daysToShow} Gün</div>
            </div>
            <div className="h-16 flex items-end gap-0.5">
              {dateRange.map((date, idx) => {
                const dayBookings = bookings.filter(b => {
                  const checkIn = new Date(b.check_in);
                  const checkOut = new Date(b.check_out);
                  checkIn.setHours(0, 0, 0, 0);
                  checkOut.setHours(0, 0, 0, 0);
                  date.setHours(0, 0, 0, 0);
                  return date >= checkIn && date < checkOut && b.status !== 'cancelled';
                }).length;
                
                const occupancyRate = rooms.length > 0 ? (dayBookings / rooms.length) * 100 : 0;
                const height = Math.max((occupancyRate / 100) * 64, 4); // Min 4px height
                
                return (
                  <div key={idx} className="flex-1 flex flex-col items-center gap-1">
                    <div 
                      className={`w-full rounded-t transition-all cursor-pointer ${
                        occupancyRate >= 90 ? 'bg-red-500 hover:bg-red-600' :
                        occupancyRate >= 80 ? 'bg-orange-400 hover:bg-orange-500' :
                        occupancyRate >= 70 ? 'bg-yellow-400 hover:bg-yellow-500' :
                        occupancyRate >= 50 ? 'bg-green-400 hover:bg-green-500' :
                        'bg-blue-300 hover:bg-blue-400'
                      }`}
                      style={{ height: `${height}px` }}
                      title={`${new Date(date).toLocaleDateString()}: ${occupancyRate.toFixed(1)}% (${dayBookings}/${rooms.length})`}
                    ></div>
                    <div className="text-[9px] text-gray-500 font-semibold">
                      {occupancyRate.toFixed(0)}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>

        {/* Calendar Grid */}
        <Card>
          <CardContent className="p-0">
            {/* STRUCTURE: Header outside, Grid inside scroll container */}
            
            {/* Date Header Row - OUTSIDE scroll, so it scrolls with page */}
            <div className="overflow-x-auto border-b">
              <div className="min-w-max">
                <div 
                  className="flex bg-white shadow-sm" 
                  data-testid="calendar-date-header"
                >
                <div className="w-32 flex-shrink-0 p-3 border-r font-bold text-gray-700 text-xs uppercase tracking-wider">
                  Odalar
                </div>
                {dateRange.map((date, idx) => {
                  const intensity = getHeatmapIntensity(date);
                  
                  // Calculate daily rate (ADR) for this date
                  const dayBookings = bookings.filter(b => {
                    const checkIn = new Date(b.check_in);
                    const checkOut = new Date(b.check_out);
                    checkIn.setHours(0, 0, 0, 0);
                    checkOut.setHours(0, 0, 0, 0);
                    const currentDate = new Date(date);
                    currentDate.setHours(0, 0, 0, 0);
                    return currentDate >= checkIn && currentDate < checkOut && b.status !== 'cancelled';
                  });
                  
                  const totalRevenue = dayBookings.reduce((sum, b) => {
                    const nights = Math.ceil((new Date(b.check_out) - new Date(b.check_in)) / (1000 * 60 * 60 * 24));
                    return sum + ((b.total_amount || 0) / nights);
                  }, 0);
                  
                  const adr = dayBookings.length > 0 ? (totalRevenue / dayBookings.length) : 0;
                  
                  return (
                  <div
                    key={idx}
                    className={`w-24 flex-shrink-0 p-2.5 border-r text-center ${
                      isToday(date) ? 'bg-blue-600 text-white' : 'bg-white text-gray-700'
                    }`}
                    title={`Occupancy intensity: ${intensity} | ADR: $${adr.toFixed(0)}`}
                  >
                    <div className="text-[11px] font-bold uppercase tracking-wide">{formatDateWithDay(date)}</div>
                    <div className={`text-[10px] mt-1 font-semibold ${isToday(date) ? 'text-blue-100' : 'text-gray-500'}`}>
                      ${adr > 0 ? adr.toFixed(0) : '-'}
                    </div>
                  </div>
                  );
                })}
              </div>
            </div>
            
            {/* Room Rows - INSIDE separate scroll container */}
            <div className="overflow-x-auto">
              <div className="min-w-max">
              {rooms.length === 0 ? (
                <div className="p-12 text-center text-gray-500">
                  <CalendarIcon className="w-12 h-12 mx-auto mb-4 opacity-50" />
                  <p>No rooms available</p>
                </div>
              ) : (
                (() => {
                  // Apply filters first
                  const roomsToShow = filteredRooms;
                  
                  // Group filtered rooms by type
                  const groupedRooms = roomsToShow.reduce((acc, room) => {
                    const type = room.room_type || 'standard';
                    if (!acc[type]) acc[type] = [];
                    acc[type].push(room);
                    return acc;
                  }, {});

                  // Sort room types
                  const roomTypeOrder = ['suite', 'deluxe', 'superior', 'standard', 'economy'];
                  const sortedTypes = Object.keys(groupedRooms).sort((a, b) => {
                    const aIndex = roomTypeOrder.indexOf(a.toLowerCase());
                    const bIndex = roomTypeOrder.indexOf(b.toLowerCase());
                    if (aIndex === -1 && bIndex === -1) return a.localeCompare(b);
                    if (aIndex === -1) return 1;
                    if (bIndex === -1) return -1;
                    return aIndex - bIndex;
                  });

                  return sortedTypes.map((roomType) => (
                    <div key={roomType}>
                      {/* Room Type Header - Minimal Style */}
                      <div className="sticky left-0 z-10 bg-gradient-to-r from-slate-100 to-gray-100 border-b-2 border-slate-300">
                        <div className="flex items-center px-4 py-2">
                          <Building2 className="w-4 h-4 mr-2 text-slate-600" />
                          <span className="font-bold text-sm text-slate-700 tracking-wide uppercase">
                            {roomType}
                          </span>
                          <span className="ml-2 text-xs text-slate-500 font-normal">
                            {groupedRooms[roomType].length} odalar
                          </span>
                        </div>
                      </div>

                      {/* Rooms of this type */}
                      {groupedRooms[roomType].map((room) => (
                        <div key={room.id} className="flex border-b border-gray-100 hover:bg-blue-50/30 transition-colors">
                          {/* Room Cell - Modern Design */}
                          <div className="w-32 flex-shrink-0 p-3 border-r border-gray-200 bg-white">
                            <div className="flex items-center gap-2">
                              <div className="w-2.5 h-2.5 bg-emerald-500 rounded-full shadow-sm"></div>
                              <div className="font-bold text-sm text-gray-800">{room.room_number}</div>
                            </div>
                            <div className="text-[10px] text-gray-500 ml-4 mt-1 font-medium">
                              {room.room_type} • Kat {room.floor}
                            </div>
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
                            data-date={date.toISOString()}
                            data-room-id={room.id}
                            className={`w-24 flex-shrink-0 border-r border-gray-100 relative cursor-pointer hover:bg-blue-50/20 transition-all ${
                              isToday(date) ? 'bg-blue-50/40' : 'bg-white'
                            } ${isDragOver ? 'bg-emerald-50 ring-2 ring-emerald-400' : ''}
                            ${roomBlock ? 'bg-gray-50' : ''}`}
                            style={{ height: viewMode === 'simplified' ? '56px' : '76px' }}
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

                            {/* Empty cell indicator - Modern */}
                            {!booking && !roomBlock && (
                              <div className="absolute inset-0 flex items-center justify-center opacity-0 hover:opacity-100 transition-opacity">
                                <Plus className="w-5 h-5 text-blue-400" />
                              </div>
                            )}
                            
                            {/* Booking bar - Modern Aesthetic Design */}
                            {isStart && booking && (
                              <div
                                draggable
                                onDragStart={(e) => handleDragStart(e, booking)}
                                onDragEnd={handleDragEnd}
                                onDoubleClick={() => handleBookingDoubleClick(booking)}
                                className={`absolute top-1.5 left-1 rounded-xl ${getSegmentColor(
                                  booking.market_segment || booking.rate_type
                                )} text-white text-xs overflow-hidden shadow-lg hover:shadow-2xl transition-all cursor-move z-20 group border-2 border-white/20 ${
                                  draggingBooking?.id === booking.id ? 'opacity-30 scale-95 ring-2 ring-blue-500 animate-pulse' : ''
                                } ${hasConflict(room.id, date) ? 'ring-2 ring-red-400 animate-pulse' : ''}
                                ${showDeluxePanel && isGroupBooking(booking.id) ? 'ring-2 ring-amber-400' : ''}`}
                                style={{
                                  width: `${calculateBookingSpan(booking, currentDate) * 96 - 8}px`,
                                  height: viewMode === 'simplified' ? '50px' : '68px',
                                  background: draggingBooking?.id === booking.id 
                                    ? 'linear-gradient(135deg, rgba(59, 130, 246, 0.8) 0%, rgba(37, 99, 235, 0.8) 100%)'
                                    : undefined
                                }}
                                title={`Detaylar için çift tıkla | Taşımak için sürükle\n${booking.guest_name || 'Misafir'} - ${booking.market_segment || 'Standard'}${showDeluxePanel && isGroupBooking(booking.id) ? `\n👥 GRUP: ${getGroupInfo(booking.id)?.company_name}` : ''}`}
                              >
                                {/* Bulk Selection Checkbox */}
                                {bulkActionMode && (
                                  <input
                                    type="checkbox"
                                    className="absolute top-1 left-1 w-4 h-4 cursor-pointer z-10"
                                    checked={selectedBookings.includes(booking.id)}
                                    onChange={(e) => {
                                      e.stopPropagation();
                                      if (e.target.checked) {
                                        setSelectedBookings([...selectedBookings, booking.id]);
                                      } else {
                                        setSelectedBookings(selectedBookings.filter(id => id !== booking.id));
                                      }
                                    }}
                                    onClick={(e) => e.stopPropagation()}
                                  />
                                )}
                                
                                {/* Main booking info - Modern Clean Design */}
                                {viewMode === 'simplified' ? (
                                  /* Simplified View - Ultra Clean & Modern */
                                  <div className={`p-2.5 h-full flex flex-col justify-center ${bulkActionMode ? 'pl-6' : ''}`}>
                                    <div className="font-bold text-[13px] truncate leading-tight text-white drop-shadow-sm">
                                      {booking.guest_name || 'Misafir'}
                                    </div>
                                    <div className="text-[11px] font-bold text-white/90 mt-1 flex items-center gap-1">
                                      <DollarSign className="w-3 h-3" />
                                      {booking.total_amount?.toFixed(0) || '0'}
                                    </div>
                                  </div>
                                ) : (
                                  /* Detailed View - Full Info with Better Typography */
                                  <div className="p-2.5 relative">
                                    <div className={`font-bold text-sm truncate pr-8 flex items-center gap-1 text-white drop-shadow-sm ${bulkActionMode ? 'pl-6' : ''}`}>
                                      {(booking.rate_type === 'promotional' || booking.rate_type === 'promo') && (
                                        <span className="text-yellow-300 animate-pulse">✨</span>
                                      )}
                                      {booking.guest_name || 'Misafir'}
                                    </div>
                                    <div className="text-[11px] text-white/90 flex items-center mt-1.5">
                                      <Clock className="w-3 h-3 mr-1" />
                                      {calculateBookingSpan(booking, currentDate)}n
                                    </div>
                                    {booking.company_name && (
                                      <div className="text-[11px] text-white/90 flex items-center truncate mt-0.5">
                                        <Building2 className="w-3 h-3 mr-1" />
                                        {booking.company_name}
                                      </div>
                                    )}
                                  </div>
                                )}
                                
                                {/* Status indicators - top right - Only in detailed mode */}
                                {viewMode === 'detailed' && (
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
                                )}
                                
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

                                
                                {/* Resize Handles - Left (check-in) and Right (check-out) */}
                                <div 
                                  className="absolute left-0 top-0 bottom-0 w-3 bg-white/30 hover:bg-yellow-300/80 cursor-ew-resize group/resize border-r-2 border-white/40 hover:border-yellow-400 transition-all z-30"
                                  onMouseDown={(e) => {
                                    e.stopPropagation();
                                    setResizingBooking(booking);
                                    setResizeDirection('start');
                                  }}
                                  title="Giriş tarihini değiştirmek için sürükle"
                                >
                                  <div className="absolute inset-0 flex items-center justify-center opacity-60 group-hover/resize:opacity-100">
                                    <div className="w-1 h-10 bg-white rounded shadow-lg"></div>
                                  </div>
                                </div>
                                <div 
                                  className="absolute right-0 top-0 bottom-0 w-3 bg-white/30 hover:bg-yellow-300/80 cursor-ew-resize group/resize border-l-2 border-white/40 hover:border-yellow-400 transition-all z-30"
                                  onMouseDown={(e) => {
                                    e.stopPropagation();
                                    setResizingBooking(booking);
                                    setResizeDirection('end');
                                  }}
                                  title="Çıkış tarihini değiştirmek için sürükle"
                                >
                                  <div className="absolute inset-0 flex items-center justify-center opacity-60 group-hover/resize:opacity-100">
                                    <div className="w-1 h-10 bg-white rounded shadow-lg"></div>
                                  </div>
                                </div>

                              </div>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
                ));
                })()
              )}
              </div>
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
            <DialogDescription>
              Create a new reservation for the selected room and date
            </DialogDescription>
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
            <DialogDescription>
              Complete information about the selected reservation
            </DialogDescription>
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
            <DialogTitle>Oda Değişikliği - Neden Gerekli</DialogTitle>
          </DialogHeader>
          {moveData && (
            <div className="space-y-4">
              {/* Same Room Type Warning */}
              {moveData.isSameRoomType && (
                <div className="bg-amber-50 border border-amber-300 rounded-lg p-4 flex items-start space-x-3">
                  <AlertCircle className="w-5 h-5 text-amber-600 mt-0.5 flex-shrink-0" />
                  <div className="text-sm text-amber-900">
                    <div className="font-semibold mb-1">Aynı Oda Tipi İçinde Taşıma</div>
                    <div>Bu rezervasyon <strong>{moveData.oldRoomType}</strong> tipinden yine <strong>{moveData.newRoomType}</strong> tipine taşınıyor. Lütfen bu değişikliğin nedenini belirtin.</div>
                  </div>
                </div>
              )}

              <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <div className="text-sm text-blue-900">
                  <div className="font-semibold mb-2">Rezervasyon Taşınıyor:</div>
                  <div>Misafir: <strong>{moveData.booking.guest_name}</strong></div>
                  <div>
                    Oda: <strong>Oda {moveData.oldRoom}</strong> ({moveData.oldRoomType}) 
                    → <strong>Oda {moveData.newRoom}</strong> ({moveData.newRoomType})
                  </div>
                  <div>Tarihler: <strong>{moveData.newCheckIn}</strong> - <strong>{moveData.newCheckOut}</strong></div>
                </div>
              </div>

              <div>
                <Label>Taşıma Nedeni *</Label>
                <select
                  className="w-full border rounded-md p-2 mb-2"
                  value={moveReason}
                  onChange={(e) => setMoveReason(e.target.value)}
                >
                  <option value="">Neden seçin...</option>
                  <option value="Misafir Talebi">Misafir Talebi</option>
                  <option value="Oda Bakımı">Oda Bakımı</option>
                  <option value="Upgrade">Oda Yükseltme (Upgrade)</option>
                  <option value="Downgrade">Oda Düşürme (Downgrade)</option>
                  <option value="Overbooking">Aşırı Rezervasyon Çözümü</option>
                  <option value="VIP Misafir">VIP Misafir Önceliği</option>
                  <option value="Oda Sorunu">Oda Sorunu / Şikayet</option>
                  <option value="Operasyonel">Operasyonel Nedenler</option>
                  <option value="Oda Görünümü">Oda Görünümü / Manzara</option>
                  <option value="Gürültü">Gürültü Şikayeti</option>
                  <option value="Temizlik">Temizlik Sorunu</option>
                  <option value="Diğer">Diğer</option>
                </select>
                {moveReason === 'Diğer' && (
                  <Input
                    placeholder="Lütfen belirtin..."
                    className="mt-2"
                    onChange={(e) => setMoveReason(`Diğer: ${e.target.value}`)}
                  />
                )}
              </div>

              <div className="text-xs text-gray-600 bg-gray-50 p-3 rounded">
                <strong>Not:</strong> Bu taşıma işlemi oda değişiklik geçmişine kaydedilecek ve denetim amacıyla tarih, saat ve kullanıcı bilgileriniz ile birlikte saklanacaktır.
              </div>

              <div className="flex space-x-2">
                <Button onClick={handleConfirmMove} className="flex-1">
                  Taşımayı Onayla
                </Button>
                <Button 
                  variant="outline" 
                  onClick={() => {
                    setShowMoveReasonDialog(false);
                    setMoveReason('');
                    setMoveData(null);
                  }}
                >
                  İptal
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

      {/* Folio View Dialog */}
      {showFolioDialog && selectedBookingFolio && (
        <Dialog open={showFolioDialog} onOpenChange={setShowFolioDialog}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <div className="flex justify-between items-start">
                <div>
                  <DialogTitle>Guest Folio - Booking #{selectedBooking?.id?.slice(0, 8)}</DialogTitle>
                  <DialogDescription>
                    View all charges, payments, and balance details for this reservation
                  </DialogDescription>
                </div>
                <div className="flex gap-2">
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowActivityLog(!showActivityLog)}
                  >
                    <History className="w-4 h-4 mr-2" />
                    Activity Log
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={async () => {
                      try {
                        const response = await axios.get(`/folio/${selectedBookingFolio.id}/excel`, {
                          responseType: 'blob'
                        });
                        const url = window.URL.createObjectURL(new Blob([response.data]));
                        const link = document.createElement('a');
                        link.href = url;
                        link.setAttribute('download', `folio-${selectedBookingFolio.folio_number}.xlsx`);
                        document.body.appendChild(link);
                        link.click();
                        link.remove();
                        toast.success('Folio downloaded');
                      } catch (error) {
                        toast.error('Failed to download folio');
                        console.error(error);
                      }
                    }}
                  >
                    <Download className="w-4 h-4 mr-2" />
                    Export
                  </Button>
                  {selectedBookingFolio?.status === 'open' && (selectedBookingFolio?.balance || 0) === 0 && (
                    <Button
                      size="sm"
                      variant="default"
                      onClick={async () => {
                        if (window.confirm('Are you sure you want to close this folio? This action cannot be undone.')) {
                          try {
                            await axios.post(`/folio/${selectedBookingFolio.id}/close`);
                            toast.success('Folio closed successfully');
                            setSelectedBookingFolio({...selectedBookingFolio, status: 'closed'});
                          } catch (error) {
                            toast.error('Failed to close folio');
                            console.error(error);
                          }
                        }
                      }}
                    >
                      <Lock className="w-4 h-4 mr-2" />
                      Close Folio
                    </Button>
                  )}
                </div>
              </div>
            </DialogHeader>
            
            <div className="space-y-4">
              {/* Folio Summary */}
              <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-6 rounded-lg">
                <div className="flex justify-between items-start mb-4">
                  <div>
                    <div className="text-lg font-semibold">Folio #{selectedBookingFolio?.folio_number}</div>
                    <div className="text-sm text-gray-600">Created: {new Date(selectedBookingFolio?.created_at).toLocaleDateString()}</div>
                  </div>
                  <Badge variant={selectedBookingFolio?.status === 'closed' ? 'secondary' : 'default'}>
                    {selectedBookingFolio?.status === 'closed' ? '🔒 Closed' : '✓ Open'}
                  </Badge>
                </div>
                <div className="grid grid-cols-3 gap-4">
                  <div>
                    <div className="text-sm text-gray-600">Guest</div>
                    <div className="font-bold">{selectedBooking?.guest_name || 'N/A'}</div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">Room</div>
                    <div className="font-bold">
                      {rooms.find(r => r.id === selectedBooking?.room_id)?.room_number || 'N/A'}
                    </div>
                  </div>
                  <div>
                    <div className="text-sm text-gray-600">Balance</div>
                    <div className="text-2xl font-bold text-blue-600">
                      ${selectedBookingFolio?.balance?.toFixed(2) || '0.00'}
                    </div>
                  </div>
                </div>
              </div>
              
              {/* Charges List */}
              <div>
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-lg font-semibold">Charges</h3>
                  <div className="flex gap-2">
                    {selectedChargesForTransfer.length > 0 && (
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => setShowTransferDialog(true)}
                      >
                        <ArrowRightLeft className="w-4 h-4 mr-2" />
                        Transfer ({selectedChargesForTransfer.length})
                      </Button>
                    )}
                    {selectedBookingFolio?.status !== 'closed' && (
                      <Button 
                        size="sm" 
                        variant="outline"
                        onClick={() => {
                          setChargeForm({
                            category: 'room',
                            description: '',
                            quantity: 1,
                            unit_price: '',
                            notes: ''
                          });
                          setShowChargeForm(!showChargeForm);
                        }}
                      >
                        <Plus className="w-4 h-4 mr-2" />
                        Add Charge
                      </Button>
                    )}
                  </div>
                </div>
                
                {/* Charge Form */}
                {showChargeForm && (
                  <Card className="mb-4 border-orange-200 bg-orange-50">
                    <CardContent className="p-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label>Category *</Label>
                          <select
                            className="w-full border rounded-md p-2"
                            value={chargeForm.category}
                            onChange={(e) => setChargeForm({...chargeForm, category: e.target.value})}
                          >
                            <option value="room">Room Charge</option>
                            <option value="fnb">Food & Beverage</option>
                            <option value="minibar">Minibar</option>
                            <option value="laundry">Laundry</option>
                            <option value="spa">Spa & Wellness</option>
                            <option value="telephone">Telephone</option>
                            <option value="parking">Parking</option>
                            <option value="other">Other</option>
                          </select>
                        </div>
                        <div>
                          <Label>Description *</Label>
                          <Input
                            value={chargeForm.description}
                            onChange={(e) => setChargeForm({...chargeForm, description: e.target.value})}
                            placeholder="Charge description..."
                            autoFocus
                          />
                        </div>
                        <div>
                          <Label>Quantity *</Label>
                          <Input
                            type="number"
                            min="1"
                            value={chargeForm.quantity}
                            onChange={(e) => setChargeForm({...chargeForm, quantity: parseInt(e.target.value) || 1})}
                          />
                        </div>
                        <div>
                          <Label>Unit Price *</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={chargeForm.unit_price}
                            onChange={(e) => setChargeForm({...chargeForm, unit_price: e.target.value})}
                            placeholder="0.00"
                          />
                        </div>
                        <div className="col-span-2">
                          <Label>Notes</Label>
                          <Input
                            value={chargeForm.notes}
                            onChange={(e) => setChargeForm({...chargeForm, notes: e.target.value})}
                            placeholder="Additional notes..."
                          />
                        </div>
                      </div>
                      <div className="flex gap-2 mt-4">
                        <Button 
                          size="sm"
                          onClick={async () => {
                            try {
                              if (!chargeForm.description || !chargeForm.unit_price) {
                                toast.error('Please fill in all required fields');
                                return;
                              }
                              
                              const amount = parseFloat(chargeForm.unit_price) * chargeForm.quantity;
                              const tax_rate = 0.18; // %18 KDV
                              const tax_amount = amount * tax_rate;
                              const total = amount + tax_amount;
                              
                              await axios.post(`/folio/${selectedBookingFolio.id}/charge`, {
                                charge_category: chargeForm.category,
                                description: chargeForm.description,
                                quantity: chargeForm.quantity,
                                unit_price: parseFloat(chargeForm.unit_price),
                                amount: amount,
                                tax_rate: tax_rate,
                                tax_amount: tax_amount,
                                total: total,
                                notes: chargeForm.notes || undefined
                              });
                              
                              toast.success('Charge added successfully');
                              
                              // Reload folio details
                              const detailsRes = await axios.get(`/folio/${selectedBookingFolio.id}`);
                              setFolioCharges(detailsRes.data.charges || []);
                              setFolioPayments(detailsRes.data.payments || []);
                              setSelectedBookingFolio({...selectedBookingFolio, balance: detailsRes.data.balance});
                              
                              setShowChargeForm(false);
                              setChargeForm({ category: 'room', description: '', quantity: 1, unit_price: '', notes: '' });
                            } catch (error) {
                              toast.error('Failed to add charge');
                              console.error(error);
                            }
                          }}
                        >
                          Save Charge
                        </Button>
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => {
                            setShowChargeForm(false);
                            setChargeForm({ category: 'room', description: '', quantity: 1, unit_price: '', notes: '' });
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}
                
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {folioCharges.length === 0 ? (
                    <div className="text-center text-gray-400 py-8">No charges posted</div>
                  ) : (
                    folioCharges.map((charge) => (
                      <Card key={charge.id} className={charge.voided ? 'opacity-50' : ''}>
                        <CardContent className="p-4">
                          <div className="flex gap-3 items-start">
                            {/* Checkbox for transfer */}
                            {!charge.voided && selectedBookingFolio?.status !== 'closed' && (
                              <input
                                type="checkbox"
                                className="mt-1 w-4 h-4 cursor-pointer"
                                checked={selectedChargesForTransfer.includes(charge.id)}
                                onChange={(e) => {
                                  if (e.target.checked) {
                                    setSelectedChargesForTransfer([...selectedChargesForTransfer, charge.id]);
                                  } else {
                                    setSelectedChargesForTransfer(selectedChargesForTransfer.filter(id => id !== charge.id));
                                  }
                                }}
                              />
                            )}
                            <div className="flex-1">
                              <div className="font-semibold">{charge.description}</div>
                              <div className="text-sm text-gray-600">
                                {charge.charge_category?.toUpperCase()} • Qty: {charge.quantity || 1} × ${charge.unit_price?.toFixed(2) || '0.00'}
                              </div>
                              <div className="text-xs text-gray-500">
                                {new Date(charge.date || charge.posted_at).toLocaleDateString()}
                              </div>
                            </div>
                            <div className="text-right flex items-start gap-2">
                              <div>
                                <div className="font-bold">${charge.total?.toFixed(2) || charge.amount?.toFixed(2) || '0.00'}</div>
                                {charge.voided && (
                                  <div className="text-xs text-red-600">VOIDED</div>
                                )}
                              </div>
                              {!charge.voided && selectedBookingFolio?.status !== 'closed' && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-6 w-6 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                                  onClick={async () => {
                                    if (window.confirm('Are you sure you want to void this charge?')) {
                                      try {
                                        await axios.post(`/folio/${selectedBookingFolio.id}/void-charge/${charge.id}`);
                                        toast.success('Charge voided successfully');
                                        
                                        // Reload folio details
                                        const detailsRes = await axios.get(`/folio/${selectedBookingFolio.id}`);
                                        setFolioCharges(detailsRes.data.charges || []);
                                        setFolioPayments(detailsRes.data.payments || []);
                                        setSelectedBookingFolio({...selectedBookingFolio, balance: detailsRes.data.balance});
                                      } catch (error) {
                                        toast.error('Failed to void charge');
                                        console.error(error);
                                      }
                                    }
                                  }}
                                >
                                  <XCircle className="w-4 h-4" />
                                </Button>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))
                  )}
                </div>
              </div>
              
              {/* Payments List */}
              <div>
                <div className="flex justify-between items-center mb-3">
                  <h3 className="text-lg font-semibold">Payments</h3>
                  <Button 
                    size="sm" 
                    onClick={() => {
                      setPaymentForm({
                        amount: selectedBookingFolio?.balance?.toFixed(2) || '',
                        method: 'card',
                        reference: '',
                        notes: ''
                      });
                      setShowPaymentForm(!showPaymentForm);
                    }}
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    Record Payment
                  </Button>
                </div>
                
                {/* Payment Form */}
                {showPaymentForm && (
                  <Card className="mb-4 border-blue-200 bg-blue-50">
                    <CardContent className="p-4">
                      <div className="grid grid-cols-2 gap-4">
                        <div>
                          <Label>Amount *</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={paymentForm.amount}
                            onChange={(e) => setPaymentForm({...paymentForm, amount: e.target.value})}
                            placeholder="0.00"
                            autoFocus
                          />
                        </div>
                        <div>
                          <Label>Payment Method *</Label>
                          <select
                            className="w-full border rounded-md p-2"
                            value={paymentForm.method}
                            onChange={(e) => setPaymentForm({...paymentForm, method: e.target.value})}
                          >
                            <option value="card">Credit Card</option>
                            <option value="cash">Cash</option>
                            <option value="bank_transfer">Bank Transfer</option>
                            <option value="check">Check</option>
                          </select>
                        </div>
                        <div>
                          <Label>Reference Number</Label>
                          <Input
                            value={paymentForm.reference}
                            onChange={(e) => setPaymentForm({...paymentForm, reference: e.target.value})}
                            placeholder="Transaction ref..."
                          />
                        </div>
                        <div>
                          <Label>Notes</Label>
                          <Input
                            value={paymentForm.notes}
                            onChange={(e) => setPaymentForm({...paymentForm, notes: e.target.value})}
                            placeholder="Additional notes..."
                          />
                        </div>
                      </div>
                      <div className="flex gap-2 mt-4">
                        <Button 
                          size="sm"
                          onClick={async () => {
                            try {
                              if (!paymentForm.amount || parseFloat(paymentForm.amount) <= 0) {
                                toast.error('Please enter a valid amount');
                                return;
                              }
                              
                              await axios.post(`/folio/${selectedBookingFolio.id}/payment`, {
                                amount: parseFloat(paymentForm.amount),
                                method: paymentForm.method,
                                payment_type: 'interim',
                                reference: paymentForm.reference || undefined,
                                notes: paymentForm.notes || undefined
                              });
                              
                              toast.success('Payment recorded successfully');
                              
                              // Reload folio details
                              const detailsRes = await axios.get(`/folio/${selectedBookingFolio.id}`);
                              setFolioCharges(detailsRes.data.charges || []);
                              setFolioPayments(detailsRes.data.payments || []);
                              setSelectedBookingFolio({...selectedBookingFolio, balance: detailsRes.data.balance});
                              
                              setShowPaymentForm(false);
                              setPaymentForm({ amount: '', method: 'card', reference: '', notes: '' });
                            } catch (error) {
                              toast.error('Failed to record payment');
                              console.error(error);
                            }
                          }}
                        >
                          Save Payment
                        </Button>
                        <Button 
                          size="sm" 
                          variant="outline"
                          onClick={() => {
                            setShowPaymentForm(false);
                            setPaymentForm({ amount: '', method: 'card', reference: '', notes: '' });
                          }}
                        >
                          Cancel
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                )}
                
                <div className="space-y-2 max-h-96 overflow-y-auto">
                  {folioPayments.length === 0 ? (
                    <div className="text-center text-gray-400 py-8">No payments recorded</div>
                  ) : (
                    folioPayments.map((payment) => (
                      <Card key={payment.id} className={`${payment.voided ? 'opacity-50 border-gray-300 bg-gray-100' : 'border-green-200 bg-green-50'}`}>
                        <CardContent className="p-4">
                          <div className="flex justify-between items-start">
                            <div className="flex-1">
                              <div className="flex items-center gap-2 mb-1">
                                <div className={`font-semibold ${payment.voided ? 'text-gray-600' : 'text-green-700'}`}>
                                  {payment.method === 'card' ? '💳 Credit Card' : 
                                   payment.method === 'cash' ? '💵 Cash' :
                                   payment.method === 'bank_transfer' ? '🏦 Bank Transfer' :
                                   payment.method === 'check' ? '📝 Check' : payment.method?.toUpperCase()}
                                </div>
                                <Badge variant="outline" className="text-xs">
                                  {payment.payment_type}
                                </Badge>
                                {payment.voided && (
                                  <Badge variant="destructive" className="text-xs">
                                    VOIDED
                                  </Badge>
                                )}
                              </div>
                              <div className="text-sm text-gray-600 mb-1">
                                📅 {new Date(payment.processed_at).toLocaleString('tr-TR', {
                                  year: 'numeric',
                                  month: 'long',
                                  day: 'numeric',
                                  hour: '2-digit',
                                  minute: '2-digit'
                                })}
                              </div>
                              {payment.reference && (
                                <div className="text-xs text-gray-500">
                                  Ref: {payment.reference}
                                </div>
                              )}
                              {(payment.processed_by_name || payment.processed_by) && !payment.voided && (
                                <div className="text-xs text-gray-500">
                                  👤 Processed by: {payment.processed_by_name || payment.processed_by}
                                </div>
                              )}
                              {payment.voided && payment.voided_by && (
                                <div className="text-xs text-red-600">
                                  ❌ Voided by: {payment.voided_by}
                                </div>
                              )}
                              {payment.voided && payment.void_reason && (
                                <div className="text-xs text-red-600 italic">
                                  Reason: {payment.void_reason}
                                </div>
                              )}
                              {payment.notes && (
                                <div className="text-xs text-gray-500 mt-1 italic">
                                  📝 {payment.notes}
                                </div>
                              )}
                            </div>
                            <div className="text-right flex items-start gap-2">
                              <div>
                                <div className={`text-xl font-bold ${payment.voided ? 'text-gray-500 line-through' : 'text-green-600'}`}>
                                  -${payment.amount?.toFixed(2) || '0.00'}
                                </div>
                                <div className="text-xs text-gray-500">
                                  {payment.status || 'PAID'}
                                </div>
                              </div>
                              {!payment.voided && selectedBookingFolio?.status !== 'closed' && (
                                <Button
                                  size="sm"
                                  variant="ghost"
                                  className="h-6 w-6 p-0 text-red-500 hover:text-red-700 hover:bg-red-50"
                                  onClick={async () => {
                                    const reason = window.prompt('Void reason:', 'Voided by staff');
                                    if (reason !== null) {
                                      try {
                                        await axios.post(`/payment/${payment.id}/void`, null, {
                                          params: { void_reason: reason }
                                        });
                                        toast.success('Payment voided successfully');
                                        
                                        // Reload folio details
                                        const detailsRes = await axios.get(`/folio/${selectedBookingFolio.id}`);
                                        setFolioCharges(detailsRes.data.charges || []);
                                        setFolioPayments(detailsRes.data.payments || []);
                                        setSelectedBookingFolio({...selectedBookingFolio, balance: detailsRes.data.balance});
                                      } catch (error) {
                                        toast.error('Failed to void payment');
                                        console.error(error);
                                      }
                                    }
                                  }}
                                >
                                  <XCircle className="w-4 h-4" />
                                </Button>
                              )}
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))
                  )}
                </div>
              </div>
              
              {/* Activity Log - Collapsible */}
              {showActivityLog && (
                <div className="border-t pt-4">
                  <h3 className="text-lg font-semibold mb-3 flex items-center gap-2">
                    <History className="w-5 h-5" />
                    Activity Log
                  </h3>
                  <div className="bg-gray-50 p-4 rounded-lg max-h-96 overflow-y-auto">
                    <div className="space-y-2">
                      {(() => {
                        const activities = [];
                        
                        // Add charges to timeline
                        folioCharges.forEach(charge => {
                          activities.push({
                            type: 'charge',
                            timestamp: charge.posted_at,
                            icon: '💰',
                            color: charge.voided ? 'text-gray-500' : 'text-orange-600',
                            title: charge.voided ? 'Charge Voided' : 'Charge Added',
                            description: charge.description,
                            amount: charge.total || charge.amount,
                            user: charge.posted_by
                          });
                        });
                        
                        // Add payments to timeline
                        folioPayments.forEach(payment => {
                          activities.push({
                            type: 'payment',
                            timestamp: payment.processed_at,
                            icon: payment.voided ? '🚫' : '💳',
                            color: payment.voided ? 'text-gray-500' : 'text-green-600',
                            title: payment.voided ? 'Payment Voided' : 'Payment Processed',
                            description: `${payment.method} - ${payment.reference || 'No ref'}`,
                            amount: -payment.amount,
                            user: payment.voided ? payment.voided_by : payment.processed_by_name || payment.processed_by,
                            extra: payment.void_reason
                          });
                        });
                        
                        // Sort by timestamp (newest first)
                        activities.sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));
                        
                        return activities.length === 0 ? (
                          <div className="text-center text-gray-400 py-8">No activity recorded</div>
                        ) : (
                          activities.map((activity, index) => (
                            <div key={index} className="flex gap-3 pb-3 border-b last:border-0">
                              <div className="text-2xl">{activity.icon}</div>
                              <div className="flex-1">
                                <div className={`font-semibold ${activity.color}`}>{activity.title}</div>
                                <div className="text-sm text-gray-600">{activity.description}</div>
                                <div className="text-xs text-gray-500">
                                  {new Date(activity.timestamp).toLocaleString('tr-TR', {
                                    year: 'numeric',
                                    month: 'short',
                                    day: 'numeric',
                                    hour: '2-digit',
                                    minute: '2-digit'
                                  })}
                                  {activity.user && ` • by ${activity.user}`}
                                </div>
                                {activity.extra && (
                                  <div className="text-xs text-gray-500 italic mt-1">
                                    {activity.extra}
                                  </div>
                                )}
                              </div>
                              <div className={`font-bold ${activity.color}`}>
                                {activity.amount > 0 ? '+' : ''}${activity.amount?.toFixed(2)}
                              </div>
                            </div>
                          ))
                        );
                      })()}
                    </div>
                  </div>
                </div>
              )}
              
              {/* Totals Summary */}
              <div className="border-t pt-4 bg-gray-50 p-4 rounded-lg">
                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Total Charges:</span>
                    <span className="font-semibold">
                      ${folioCharges.filter(c => !c.voided).reduce((sum, c) => sum + (c.total || c.amount || 0), 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-gray-600">Total Payments:</span>
                    <span className="font-semibold text-green-600">
                      -${folioPayments.filter(p => !p.voided).reduce((sum, p) => sum + (p.amount || 0), 0).toFixed(2)}
                    </span>
                  </div>
                  <div className="border-t-2 border-gray-300 pt-3 mt-2 flex justify-between items-center">
                    <span className="text-xl font-bold">Outstanding Balance:</span>
                    <span className={`text-3xl font-bold ${
                      (selectedBookingFolio?.balance || 0) > 0 ? 'text-red-600' : 'text-green-600'
                    }`}>
                      ${selectedBookingFolio?.balance?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                  {(selectedBookingFolio?.balance || 0) === 0 && folioCharges.length > 0 && (
                    <div className="text-center text-green-600 text-sm font-semibold pt-2 bg-green-100 py-2 rounded">
                      ✓ Fully Paid
                    </div>
                  )}
                  {(selectedBookingFolio?.balance || 0) > 0 && (
                    <div className="text-center text-orange-600 text-sm font-semibold pt-2 bg-orange-100 py-2 rounded">
                      ⚠ Payment Required
                    </div>
                  )}
                </div>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}

      {/* Transfer Charges Dialog */}
      {showTransferDialog && (
        <Dialog open={showTransferDialog} onOpenChange={setShowTransferDialog}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Transfer Charges to Another Folio</DialogTitle>
              <DialogDescription>
                Select destination folio to transfer {selectedChargesForTransfer.length} selected charge(s)
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-4">
              {/* Selected Charges Summary */}
              <div className="bg-blue-50 p-4 rounded-lg">
                <div className="text-sm font-semibold mb-2">Selected Charges:</div>
                {folioCharges.filter(c => selectedChargesForTransfer.includes(c.id)).map(charge => (
                  <div key={charge.id} className="text-sm flex justify-between py-1">
                    <span>{charge.description}</span>
                    <span className="font-semibold">${charge.total?.toFixed(2)}</span>
                  </div>
                ))}
                <div className="border-t mt-2 pt-2 flex justify-between font-bold">
                  <span>Total to Transfer:</span>
                  <span>
                    ${folioCharges
                      .filter(c => selectedChargesForTransfer.includes(c.id))
                      .reduce((sum, c) => sum + (c.total || c.amount || 0), 0)
                      .toFixed(2)}
                  </span>
                </div>
              </div>

              {/* Destination Selection */}
              <div>
                <Label>Transfer to Guest/Booking *</Label>
                <select
                  className="w-full border rounded-md p-2"
                  onChange={async (e) => {
                    if (e.target.value) {
                      try {
                        // Get folio for selected booking
                        const folioRes = await axios.get(`/folio/booking/${e.target.value}`);
                        
                        if (folioRes.data && folioRes.data.length > 0) {
                          const targetFolio = folioRes.data[0];
                          
                          if (window.confirm(`Transfer ${selectedChargesForTransfer.length} charges to ${targetFolio.folio_number}?`)) {
                            await axios.post('/folio/transfer', {
                              operation_type: 'transfer',
                              from_folio_id: selectedBookingFolio.id,
                              to_folio_id: targetFolio.id,
                              charge_ids: selectedChargesForTransfer
                            });
                            
                            toast.success('Charges transferred successfully');
                            
                            // Reload folio details
                            const detailsRes = await axios.get(`/folio/${selectedBookingFolio.id}`);
                            setFolioCharges(detailsRes.data.charges || []);
                            setFolioPayments(detailsRes.data.payments || []);
                            setSelectedBookingFolio({...selectedBookingFolio, balance: detailsRes.data.balance});
                            
                            setSelectedChargesForTransfer([]);
                            setShowTransferDialog(false);
                          }
                        } else {
                          toast.error('No folio found for selected booking');
                        }
                      } catch (error) {
                        toast.error('Failed to transfer charges');
                        console.error(error);
                      }
                    }
                  }}
                >
                  <option value="">-- Select booking --</option>
                  {bookings
                    .filter(b => b.id !== selectedBooking?.id && b.status !== 'cancelled')
                    .map(booking => (
                      <option key={booking.id} value={booking.id}>
                        {booking.guest_name} - Room {rooms.find(r => r.id === booking.room_id)?.room_number || '?'} ({booking.status})
                      </option>
                    ))}
                </select>
              </div>

              <div className="flex justify-end gap-2">
                <Button 
                  variant="outline"
                  onClick={() => {
                    setShowTransferDialog(false);
                    setSelectedChargesForTransfer([]);
                  }}
                >
                  Cancel
                </Button>
              </div>
            </div>
          </DialogContent>
        </Dialog>
      )}


      {/* Reservation Details Sidebar - Opera Navigator Style */}
      {showSidebar && (
        <>
          {/* Backdrop - soft blur effect */}
          <div 
            className="fixed top-16 right-0 bottom-0 left-0 bg-black/40 backdrop-blur-sm z-40 animate-fade-in"
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
            onViewFolio={async (bookingId) => {
              try {
                console.log('🔍 Fetching folio for booking:', bookingId);
                
                // Fetch folio data
                const folioRes = await axios.get(`/folio/booking/${bookingId}`);
                
                console.log('✅ Folio response:', folioRes.data);
                
                if (folioRes.data && folioRes.data.length > 0) {
                  const folio = folioRes.data[0];
                  setSelectedBookingFolio(folio);
                  
                  console.log('📄 Loading full folio details for:', folio.id);
                  
                  // Fetch full folio details (includes charges and payments)
                  const detailsRes = await axios.get(`/folio/${folio.id}`);
                  
                  console.log('✅ Folio details response:', detailsRes.data);
                  console.log('💰 Charges found:', detailsRes.data.charges?.length || 0);
                  console.log('💳 Payments found:', detailsRes.data.payments?.length || 0);
                  
                  setFolioCharges(detailsRes.data.charges || []);
                  setFolioPayments(detailsRes.data.payments || []);
                  
                  // Close sidebar and open folio dialog
                  setShowSidebar(false);
                  setShowFolioDialog(true);
                  
                  toast.success('Folio loaded successfully');
                } else {
                  console.warn('⚠️ No folio found in response');
                  toast.info('No folio found for this booking');
                }
              } catch (error) {
                console.error('❌ Error loading folio:', error);
                console.error('❌ Error details:', {
                  message: error.message,
                  response: error.response?.data,
                  status: error.response?.status,
                  url: error.config?.url
                });
                toast.error(`Failed to load folio: ${error.response?.data?.detail || error.message}`);
              }
            }}
            onEditReservation={(booking) => {
              console.log('Editing reservation:', booking.id);
              setShowSidebar(false);
              // Open edit booking dialog
              toast.info('Edit reservation feature - Opening edit form...');
            }}
            onSendConfirmation={(booking) => {
              console.log('Sending confirmation for:', booking.id);
              toast.success('Confirmation email sent to guest!');
            }}
          />
        </>
      )}
    </Layout>
  );
};

export default ReservationCalendar;
