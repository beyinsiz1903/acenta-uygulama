import { useState, useEffect, useMemo, Suspense, lazy } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import Layout from '@/components/Layout';
import GlobalSearch from '@/components/GlobalSearch';
import PickupPaceChart from '@/components/PickupPaceChart';
import LeadTimeCurve from '@/components/LeadTimeCurve';
import ForecastGraph from '@/components/ForecastGraph';
import RevenueDashboard from '@/components/RevenueDashboard';
import AIActivityLog from '@/components/AIActivityLog';
import StaffTaskManager from '@/components/StaffTaskManager';
import FeedbackSystem from '@/components/FeedbackSystem';
import AllotmentGrid from '@/components/AllotmentGrid';
import GroupRevenueByCompany from '@/components/GroupRevenueByCompany';
import PickupPaceReport from '@/components/PickupPaceReport';
import VirtualizedBookingList from '@/components/VirtualizedBookingList';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { 
  BedDouble, Users, Calendar, Plus, CheckCircle, DollarSign, 
  ClipboardList, BarChart3, TrendingUp, UserCheck, LogIn, LogOut, Home, FileText, 
  Star, Send, MessageSquare, UserPlus, ArrowRight, RefreshCw, User, Search, CheckSquare, Download, Clock
} from 'lucide-react';
import FloatingActionButton from '@/components/FloatingActionButton';

const PMSModule = ({ user, tenant, onLogout }) => {
  const { t } = useTranslation();
  const [rooms, setRooms] = useState([]);
  const [guests, setGuests] = useState([]);
  const [groupedBookings, setGroupedBookings] = useState([]);

  const [bookings, setBookings] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [arrivals, setArrivals] = useState([]);
  const [departures, setDepartures] = useState([]);
  const [inhouse, setInhouse] = useState([]);
  const [housekeepingTasks, setHousekeepingTasks] = useState([]);
  const [roomStatusBoard, setRoomStatusBoard] = useState(null);
  const [dueOutRooms, setDueOutRooms] = useState([]);
  const [stayoverRooms, setStayoverRooms] = useState([]);
  const [arrivalRooms, setArrivalRooms] = useState([]);
  const [auditLogs, setAuditLogs] = useState([]);
  const [userPermissions, setUserPermissions] = useState({});
  const [otaReservations, setOtaReservations] = useState([]);
  const [rmsSuggestions, setRmsSuggestions] = useState([]);
  const [exceptions, setExceptions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [aiPrediction, setAiPrediction] = useState(null);
  const [aiPatterns, setAiPatterns] = useState(null);
  const [openDialog, setOpenDialog] = useState(null);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [selectedGuest, setSelectedGuest] = useState(null);

  const [folio, setFolio] = useState(null);
  const [folios, setFolios] = useState([]);
  const [selectedFolio, setSelectedFolio] = useState(null);
  const [folioCharges, setFolioCharges] = useState([]);
  const [folioPayments, setFolioPayments] = useState([]);
  const [roomBlocks, setRoomBlocks] = useState([]);
  const [selectedRoom, setSelectedRoom] = useState(null);
  const [newRoomBlock, setNewRoomBlock] = useState({
    type: 'out_of_order',
    reason: '',
    details: '',
    start_date: '',
    end_date: '',
    allow_sell: false
  });
  

  // Search and filter states
  const [globalSearchQuery, setGlobalSearchQuery] = useState('');
  const [quickFilters, setQuickFilters] = useState({
    roomType: '',
    bookingStatus: '',
    paymentStatus: ''
  });
  
  // Bulk selection states
  const [selectedRooms, setSelectedRooms] = useState([]);
  const [bulkRoomMode, setBulkRoomMode] = useState(false);

  // Phase H - CRM & Upsell states
  const [selectedGuest360, setSelectedGuest360] = useState(null);
  const [guest360Data, setGuest360Data] = useState(null);
  const [loadingGuest360, setLoadingGuest360] = useState(false);
  const [selectedBookingDetail, setSelectedBookingDetail] = useState(null);
  const [expandedChargeItems, setExpandedChargeItems] = useState({});
  const [guestTag, setGuestTag] = useState('');
  const [guestNote, setGuestNote] = useState('');
  const [upsellOffers, setUpsellOffers] = useState([]);
  const [messageTemplates, setMessageTemplates] = useState([]);
  const [newMessage, setNewMessage] = useState({
    channel: 'email',
    recipient: '',
    subject: '',
    body: '',
    template_id: null
  });
  const [sentMessages, setSentMessages] = useState([]);
  const [findRoomCriteria, setFindRoomCriteria] = useState({
    check_in: '',
    check_out: '',
    room_type: '',
    guests: 1
  });
  const [availableRooms, setAvailableRooms] = useState([]);
  const [loadingAvailableRooms, setLoadingAvailableRooms] = useState(false);

  const [maintenanceDialogOpen, setMaintenanceDialogOpen] = useState(false);
  const [maintenanceForm, setMaintenanceForm] = useState({
    room_id: null,
    room_number: '',
    issue_type: 'housekeeping_damage',
    priority: 'normal',
    description: ''
  });

  const [reports, setReports] = useState({
    occupancy: null,
    revenue: null,
    daily: null,
    forecast: [],
    dailyFlash: null,
    marketSegment: null,
    companyAging: null,
    hkEfficiency: null
  });
  
  // Active tab state - check URL hash on mount
  const [activeTab, setActiveTab] = useState(() => {
    const hash = window.location.hash.replace('#', '');
    return hash || 'frontdesk';
  });

  const [newRoom, setNewRoom] = useState({
    room_number: '', room_type: 'standard', floor: 1, capacity: 2, base_price: 100, amenities: []
  });

  const [newGuest, setNewGuest] = useState({
    name: '', email: '', phone: '', id_number: '', address: ''
  });

  const [newBooking, setNewBooking] = useState({
    guest_id: '',
    room_id: '',
    check_in: '',
    check_out: '',
    adults: 1,
    children: 0,
    children_ages: [],
    guests_count: 1,
    total_amount: 0,
    base_rate: 0,
    channel: 'direct',
    company_id: '',
    contracted_rate: '',
    rate_type: '',
    market_segment: '',
    cancellation_policy: '',
    billing_address: '',
    billing_tax_number: '',
    billing_contact_person: '',
    override_reason: ''
  });

  // Multi-room booking state: each item is one room in the booking
  const [multiRoomBooking, setMultiRoomBooking] = useState([
    {
      room_id: '',
      adults: 1,
      children: 0,
      children_ages: [],
      total_amount: 0,
      base_rate: 0,
      rate_plan: '',
      package_code: null
    }
  ]);

  const [newCompany, setNewCompany] = useState({
    name: '',
    corporate_code: '',
    tax_number: '',
    billing_address: '',
    contact_person: '',
    contact_email: '',
    contact_phone: '',
    contracted_rate: '',
    default_rate_type: '',
    default_market_segment: '',
    default_cancellation_policy: '',
    payment_terms: '',
    status: 'pending'
  });

  // Lightweight stats for UI (kept outside heavy JSX where possible)
  const bookingStats = useMemo(() => {
    const total = bookings.length;
    const confirmed = bookings.filter(b => b.status === 'confirmed').length;
    const checkedIn = bookings.filter(b => b.status === 'checked_in').length;
    const totalRevenue = bookings.reduce((sum, b) => sum + (b.total_amount || 0), 0);
    const avgAdr = total > 0 ? totalRevenue / total : 0;
    return { total, confirmed, checkedIn, totalRevenue, avgAdr };
  }, [bookings]);

  const [newCharge, setNewCharge] = useState({
    charge_type: 'food', description: '', amount: 0, quantity: 1
  });

  const [newFolioCharge, setNewFolioCharge] = useState({
    charge_category: 'room',
    description: '',
    amount: 0,
    quantity: 1,
    auto_calculate_tax: false
  });

  const [newPayment, setNewPayment] = useState({
    amount: 0, method: 'card', reference: '', notes: ''
  });

  const [newFolioPayment, setNewFolioPayment] = useState({
    amount: 0,
    method: 'card',
    payment_type: 'interim',
    reference: '',
    notes: ''
  });

  const [paymentForm, setPaymentForm] = useState({
    amount: 0,
    method: 'card',
    payment_type: 'interim',
    reference: '',
    notes: ''
  });

  const addRoomToMultiBooking = () => {
    setMultiRoomBooking(prev => [
      ...prev,
      {
        room_id: '',
        adults: 1,
        children: 0,
        children_ages: [],
        total_amount: 0,
        base_rate: 0,
        rate_plan: '',
        package_code: null
      }
    ]);
  };

  const removeRoomFromMultiBooking = (index) => {
    setMultiRoomBooking(prev => {
      if (prev.length === 1) return prev; // En az 1 oda kalsın
      return prev.filter((_, i) => i !== index);
    });
  };

  const updateMultiRoomField = (index, field, value) => {
    setMultiRoomBooking(prev => prev.map((room, i) => {
      if (i !== index) return room;
      if (field === 'adults' || field === 'children' || field === 'base_rate' || field === 'total_amount') {
        const numeric = field === 'base_rate' || field === 'total_amount'
          ? parseFloat(value) || 0
          : parseInt(value) || 0;
        return { ...room, [field]: numeric };
      }
      return { ...room, [field]: value };
    }));
  };

  const updateMultiRoomChildrenAges = (index, childrenCount) => {
    setMultiRoomBooking(prev => prev.map((room, i) => {
      if (i !== index) return room;
      const count = parseInt(childrenCount) || 0;
      let ages = room.children_ages || [];
      if (count > ages.length) {
        ages = [...ages, ...Array(count - ages.length).fill(0)];
      } else {
        ages = ages.slice(0, count);
      }
      return { ...room, children: count, children_ages: ages };
    }));
  };

  const updateMultiRoomChildAge = (roomIndex, ageIndex, age) => {
    setMultiRoomBooking(prev => prev.map((room, i) => {
      if (i !== roomIndex) return room;
      const ages = [...(room.children_ages || [])];
      ages[ageIndex] = parseInt(age) || 0;
      return { ...room, children_ages: ages };
    }));
  };

  const [newHKTask, setNewHKTask] = useState({
    room_id: '', task_type: 'cleaning', priority: 'normal', notes: ''
  });

  useEffect(() => {
    // Only load essential data on initial mount
    loadData();
    // Load audit logs and channel manager data lazily (after 1 second)
    setTimeout(() => {
      loadAuditLogs();
      loadChannelManagerData();
    }, 1000);
  }, []);
  
  // Flags to track if tab-specific data has been loaded at least once
  const [hasLoadedFrontdesk, setHasLoadedFrontdesk] = useState(false);
  const [hasLoadedHousekeeping, setHasLoadedHousekeeping] = useState(false);
  const [hasLoadedReports, setHasLoadedReports] = useState(false);

  // Load data when tab changes (lazy-load per tab, but only once)
  useEffect(() => {
    if (activeTab === 'reports' && !hasLoadedReports) {
      console.log('🔄 Reports tab activated, loading reports (first time)...');
      loadReports();
      setHasLoadedReports(true);
    } else if (activeTab === 'frontdesk' && !hasLoadedFrontdesk) {
      console.log('🔄 Frontdesk tab activated, loading data (first time)...');
      loadFrontDeskData();
      setHasLoadedFrontdesk(true);
    } else if (activeTab === 'housekeeping' && !hasLoadedHousekeeping) {
      console.log('🔄 Housekeeping tab activated, loading data (first time)...');
      loadHousekeepingData();
      setHasLoadedHousekeeping(true);
    }
  }, [activeTab, hasLoadedFrontdesk, hasLoadedHousekeeping, hasLoadedReports]);

  const loadData = async () => {
    try {
      // PERFORMANCE OPTIMIZED: Load only essential data with limits for 550+ room properties
      const today = new Date().toISOString().split('T')[0];
      const nextWeek = new Date();
      nextWeek.setDate(nextWeek.getDate() + 7);
      const nextWeekStr = nextWeek.toISOString().split('T')[0];
      
      const [roomsRes, guestsRes, bookingsRes, companiesRes] = await Promise.all([
        axios.get('/pms/rooms?limit=100', { timeout: 15000 }), // Limit rooms for initial load
        axios.get('/pms/guests?limit=100', { timeout: 15000 }), // Limit guests to 100
        axios.get(`/pms/bookings?start_date=${today}&end_date=${nextWeekStr}&limit=200`, { timeout: 15000 }), // Only next 7 days
        axios.get('/companies?limit=50', { timeout: 15000 }) // Limit companies to 50
      ]);

      const rawBookings = bookingsRes.data || [];
      const grouped = [];
      const seenGroupIds = new Set();

      // First, handle grouped bookings (with group_booking_id)
      rawBookings
        .filter(b => b.group_booking_id)
        .forEach(b => {
          if (seenGroupIds.has(b.group_booking_id)) return;
          const sameGroup = rawBookings.filter(x => x.group_booking_id === b.group_booking_id);
          seenGroupIds.add(b.group_booking_id);
          grouped.push({
            type: 'group',
            group_booking_id: b.group_booking_id,
            master_booking: b,
            bookings: sameGroup
          });
        });

      // Then add single bookings (no group id)
      rawBookings
        .filter(b => !b.group_booking_id)
        .forEach(b => {
          grouped.push({
            type: 'single',
            booking: b
          });
        });

      setGroupedBookings(grouped);

      setRooms(roomsRes.data);
      setGuests(guestsRes.data);
      setBookings(bookingsRes.data);
      setCompanies(companiesRes.data);
    } catch (error) {
      toast.error('Failed to load data');
      console.error('PMS data load error:', error);
    } finally {
      setLoading(false);
    }
  };

  const loadFrontDeskData = async () => {
    try {
      const [arrivalsRes, departuresRes, inhouseRes] = await Promise.all([
        axios.get('/frontdesk/arrivals'),
        axios.get('/frontdesk/departures'),
        axios.get('/frontdesk/inhouse')
      ]);
      setArrivals(arrivalsRes.data);
      setDepartures(departuresRes.data);
      setInhouse(inhouseRes.data);
      
      // Load AI insights
      loadAIInsights();
    } catch (error) {
      toast.error('Failed to load front desk data');
    }
  };

  const loadAIInsights = async () => {
    try {
      const [predictionRes, patternsRes] = await Promise.all([
        axios.get('/ai/pms/occupancy-prediction').catch(() => null),
        axios.get('/ai/pms/guest-patterns').catch(() => null)
      ]);
      if (predictionRes) setAiPrediction(predictionRes.data);
      if (patternsRes) setAiPatterns(patternsRes.data);
    } catch (error) {
      // Fail silently - AI features are optional
      console.error('AI insights not available');
    }
  };

  const loadHousekeepingData = async () => {
    try {
      // Load essential data first
      const [tasksRes, boardRes] = await Promise.all([
        axios.get('/housekeeping/tasks'),
        axios.get('/housekeeping/room-status')
      ]);
      setHousekeepingTasks(tasksRes.data);
      setRoomStatusBoard(boardRes.data);
      
      // Load additional data in background
      setTimeout(async () => {
        try {
          const [dueOutRes, stayoverRes, arrivalsRes, blocksRes] = await Promise.all([
            axios.get('/housekeeping/due-out'),
            axios.get('/housekeeping/stayovers'),
            axios.get('/housekeeping/arrivals'),
            axios.get('/pms/room-blocks?status=active')
          ]);
          setDueOutRooms(dueOutRes.data.due_out_rooms || []);
          setStayoverRooms(stayoverRes.data.stayover_rooms || []);
          setArrivalRooms(arrivalsRes.data.arrival_rooms || []);
          setRoomBlocks(blocksRes.data.blocks || []);
        } catch (error) {
          console.error('Failed to load additional housekeeping data:', error);
        }
      }, 500);
    } catch (error) {
      toast.error('Failed to load housekeeping data');
    }
  };

  // Cached rate plans and packages to avoid refetching on every change
  const [ratePlans, setRatePlans] = useState([]);
  const [packages, setPackages] = useState([]);

  const loadRateData = async (channel, companyId, stayDate) => {
    try {
      const params = {};
      if (channel) params.channel = channel;
      if (companyId) params.company_id = companyId;
      if (stayDate) params.stay_date = stayDate;
      const [rpRes, pkgRes] = await Promise.all([
        axios.get('/rates/rate-plans', { params }),
        axios.get('/rates/packages')
      ]);
      setRatePlans(rpRes.data || []);
      setPackages(pkgRes.data || []);
    } catch (error) {
      console.error('Failed to load rate plans/packages', error);
      toast.error('Failed to load rate plans');
    }
  };

  const loadAuditLogs = async () => {
    try {
      // Reduce limit for faster load
      const response = await axios.get('/audit-logs?limit=20');
      setAuditLogs(response.data.logs || []);
    } catch (error) {
      // Permission denied is okay
      if (error.response?.status !== 403) {
        console.error('Failed to load audit logs:', error);
      }
    }
  };

  const loadChannelManagerData = async () => {
    try {
      const [otaRes, suggestionsRes, exceptionsRes] = await Promise.all([
        axios.get('/channel-manager/ota-reservations?status=pending'),
        axios.get('/rms/suggestions?status=pending'),
        axios.get('/channel-manager/exceptions?status=pending')
      ]);
      setOtaReservations(otaRes.data.reservations || []);
      setRmsSuggestions(suggestionsRes.data.suggestions || []);
      setExceptions(exceptionsRes.data.exceptions || []);
    } catch (error) {
      console.error('Failed to load channel manager data:', error);
    }
  };

  const handleImportOTA = async (otaId) => {
    try {
      const response = await axios.post(`/channel-manager/import-reservation/${otaId}`);
      toast.success(`✅ ${response.data.message} - Room ${response.data.room_number}`);
      loadChannelManagerData();
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import reservation');
    }
  };

  const handleApplyRMSSuggestion = async (suggestionId) => {
    try {
      const response = await axios.post(`/rms/apply-suggestion/${suggestionId}`);
      toast.success(`✅ ${response.data.message}`);
      loadChannelManagerData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to apply suggestion');
    }
  };

  const handleGenerateRMSSuggestions = async () => {
    try {
      const today = new Date().toISOString().split('T')[0];
      const nextWeek = new Date(Date.now() + 7 * 24 * 60 * 60 * 1000).toISOString().split('T')[0];
      const response = await axios.post(`/rms/generate-suggestions?start_date=${today}&end_date=${nextWeek}`);
      toast.success(`✅ ${response.data.message}`);
      loadChannelManagerData();
    } catch (error) {
      toast.error('Failed to generate suggestions');
    }
  };

  const checkPermission = async (permission) => {
    try {
      const response = await axios.post('/permissions/check', null, {
        params: { permission }
      });
      return response.data.has_permission;
    } catch (error) {
      return false;
    }
  };

  const loadReports = async () => {
    try {
      console.log('📊 Loading reports...');
      const today = new Date().toISOString().split('T')[0];
      const monthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0];
      const monthEnd = new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString().split('T')[0];
      
      // Use .catch() on each request so one failure doesn't break all reports
      const [occupancyRes, revenueRes, dailyRes, forecastRes, forecast30Res, dailyFlashRes, marketSegmentRes, companyAgingRes, hkEfficiencyRes] = await Promise.all([
        axios.get(`/reports/occupancy?start_date=${monthStart}&end_date=${monthEnd}`).catch(e => { console.error('Occupancy report failed:', e); return { data: null }; }),
        axios.get(`/reports/revenue?start_date=${monthStart}&end_date=${monthEnd}`).catch(e => { console.error('Revenue report failed:', e); return { data: null }; }),
        axios.get('/reports/daily-summary').catch(e => { console.error('Daily summary failed:', e); return { data: null }; }),
        axios.get('/reports/forecast?days=7').catch(e => { console.error('Forecast failed:', e); return { data: null }; }),
        axios.get('/reports/forecast?days=30').catch(e => { console.error('30-day forecast failed:', e); return { data: null }; }),
        axios.get('/reports/daily-flash').catch(e => { console.error('Daily flash failed:', e); return { data: null }; }),
        axios.get(`/reports/market-segment?start_date=${monthStart}&end_date=${monthEnd}`).catch(e => { console.error('Market segment failed:', e); return { data: null }; }),
        axios.get('/reports/company-aging').catch(e => { console.error('Company aging failed:', e); return { data: null }; }),
        axios.get(`/reports/housekeeping-efficiency?start_date=${monthStart}&end_date=${monthEnd}`).catch(e => { console.error('HK efficiency failed:', e); return { data: null }; })
      ]);
      
      console.log('✅ Reports loaded:', { 
        occupancy: !!occupancyRes.data, 
        revenue: !!revenueRes.data, 
        daily: !!dailyRes.data 
      });
      
      setReports({
        occupancy: occupancyRes.data,
        revenue: revenueRes.data,
        daily: dailyRes.data,
        forecast: forecastRes.data,
        forecast30: forecast30Res.data,
        dailyFlash: dailyFlashRes.data,
        marketSegment: marketSegmentRes.data,
        companyAging: companyAgingRes.data,
        hkEfficiency: hkEfficiencyRes.data
      });
    } catch (error) {
      console.error('❌ Reports loading error:', error);
      toast.error('Failed to load some reports');
    }
  };

  const handleCheckIn = async (bookingId) => {
    try {
      const response = await axios.post(`/frontdesk/checkin/${bookingId}?create_folio=true`);
      toast.success(`✅ ${response.data.message} - Room ${response.data.room_number}`);
      loadData();
      loadFrontDeskData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Check-in failed');
    }
  };

  const handleCheckOut = async (bookingId) => {
    try {
      const response = await axios.post(`/frontdesk/checkout/${bookingId}?auto_close_folios=true`);
      if (response.data.total_balance > 0.01) {
        toast.warning(`⚠️ Check-out with outstanding balance: $${response.data.total_balance.toFixed(2)}`);
      } else {
        toast.success(`✅ ${response.data.message} - ${response.data.folios_closed} folios closed`);
      }
      loadData();
      loadFrontDeskData();
      loadHousekeepingData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Check-out failed');
    }
  };

  const loadFolio = async (bookingId) => {
    try {
      const response = await axios.get(`/frontdesk/folio/${bookingId}`);
      setFolio(response.data);
      setSelectedBooking(bookingId);
      setOpenDialog('folio');
    } catch (error) {
      toast.error('Failed to load folio');
    }
  };

  const handleAddCharge = async (e) => {
    e.preventDefault();
    try {
      await axios.post(
        `/frontdesk/folio/${selectedBooking}/charge`,
        null,
        { params: newCharge }
      );
      toast.success('Charge added');
      loadFolio(selectedBooking);
      setNewCharge({ charge_type: 'food', description: '', amount: 0, quantity: 1 });
    } catch (error) {
      toast.error('Failed to add charge');
    }
  };

  const handleProcessPayment = async (e) => {
    e.preventDefault();
    try {
      await axios.post(
        `/frontdesk/payment/${selectedBooking}`,
        null,
        { params: newPayment }
      );
      toast.success('Payment processed');
      loadFolio(selectedBooking);
      setNewPayment({ amount: 0, method: 'card', reference: '', notes: '' });
    } catch (error) {
      toast.error('Failed to process payment');
    }
  };

  const handleCreateHKTask = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/housekeeping/tasks', null, { params: newHKTask });
      toast.success('Task created');
      setOpenDialog(null);
      loadHousekeepingData();
      setNewHKTask({ room_id: '', task_type: 'cleaning', priority: 'normal', notes: '' });
    } catch (error) {
      toast.error('Failed to create task');
    }
  };

  const handleUpdateHKTask = async (taskId, status) => {
    try {
      await axios.put(`/housekeeping/tasks/${taskId}`, null, { params: { status } });
      toast.success('Task updated');
      loadHousekeepingData();
      loadData();
    } catch (error) {
      toast.error('Failed to update task');
    }
  };

  const handleCreateRoom = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/pms/rooms', newRoom);
      toast.success('Room created');
      setOpenDialog(null);
      loadData();
      setNewRoom({ room_number: '', room_type: 'standard', floor: 1, capacity: 2, base_price: 100, amenities: [] });
    } catch (error) {
      toast.error('Failed to create room');
    }
  };

  const handleCreateGuest = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/pms/guests', newGuest);
      toast.success('Guest created');
      setOpenDialog(null);
      loadData();
      setNewGuest({ name: '', email: '', phone: '', id_number: '', address: '' });
    } catch (error) {
      toast.error('Failed to create guest');
    }
  };

  const handleCreateCompany = async (e) => {
    e.preventDefault();
    try {
      const response = await axios.post('/companies', newCompany);
      toast.success('Company created successfully');
      setOpenDialog(null);
      loadData();
      // Auto-select the newly created company
      const company = response.data;
      handleCompanySelect(company.id);
      setNewCompany({
        name: '',
        corporate_code: '',
        tax_number: '',
        billing_address: '',
        contact_person: '',
        contact_email: '',
        contact_phone: '',
        contracted_rate: '',
        default_rate_type: '',
        default_market_segment: '',
        default_cancellation_policy: '',
        payment_terms: '',
        status: 'pending'
      });
    } catch (error) {
      toast.error('Failed to create company');
    }
  };

  const handleCompanySelect = (companyId) => {
    if (companyId === "none") {
      setSelectedCompany(null);
      setNewBooking({
        ...newBooking,
        company_id: null,
        contracted_rate: '',
        rate_type: '',
        market_segment: '',
        cancellation_policy: '',
        billing_address: '',
        billing_tax_number: '',
        billing_contact_person: ''
      });
      return;
    }
    
    const company = companies.find(c => c.id === companyId);
    if (company) {
      setSelectedCompany(company);
      setNewBooking({
        ...newBooking,
        company_id: companyId,
        contracted_rate: company.contracted_rate || '',
        rate_type: company.default_rate_type || '',
        market_segment: company.default_market_segment || '',
        cancellation_policy: company.default_cancellation_policy || '',
        billing_address: company.billing_address || '',
        billing_tax_number: company.tax_number || '',
        billing_contact_person: company.contact_person || ''
      });
    }
  };

  const handleContractedRateSelect = (contractedRate) => {
    // Auto-fill rate type and market segment based on contracted rate
    const rateMapping = {
      'corp_std': { rate_type: 'corporate', market_segment: 'corporate', cancellation_policy: 'h48' },
      'corp_pref': { rate_type: 'corporate', market_segment: 'corporate', cancellation_policy: 'flexible' },
      'gov': { rate_type: 'government', market_segment: 'government', cancellation_policy: 'h24' },
      'ta': { rate_type: 'wholesale', market_segment: 'wholesale', cancellation_policy: 'd7' },
      'crew': { rate_type: 'corporate', market_segment: 'crew', cancellation_policy: 'same_day' },
      'mice': { rate_type: 'package', market_segment: 'mice', cancellation_policy: 'd14' },
      'lts': { rate_type: 'long_stay', market_segment: 'long_stay', cancellation_policy: 'flexible' },
      'tou': { rate_type: 'wholesale', market_segment: 'wholesale', cancellation_policy: 'd14' }
    };

    const mapping = rateMapping[contractedRate];
    if (mapping) {
      setNewBooking({
        ...newBooking,
        contracted_rate: contractedRate,
        rate_type: mapping.rate_type,
        market_segment: mapping.market_segment,
        cancellation_policy: mapping.cancellation_policy
      });
    }
  };

  const handleChildrenChange = (count) => {
    const childrenCount = parseInt(count) || 0;
    const currentAges = newBooking.children_ages;
    
    // Adjust children_ages array based on new count
    let newAges = [...currentAges];
    if (childrenCount > currentAges.length) {
      // Add default ages for new children
      newAges = [...currentAges, ...Array(childrenCount - currentAges.length).fill(0)];
    } else {
      // Remove excess ages
      newAges = currentAges.slice(0, childrenCount);
    }
    
    setNewBooking({
      ...newBooking,
      children: childrenCount,
      children_ages: newAges,
      guests_count: newBooking.adults + childrenCount
    });
  };

  const handleChildAgeChange = (index, age) => {
    const newAges = [...newBooking.children_ages];
    newAges[index] = parseInt(age) || 0;
    setNewBooking({
      ...newBooking,
      children_ages: newAges
    });
  };

  const handleCreateBooking = async (e) => {
    e.preventDefault();

    // Rate override kontrolü (ana form)
    if (newBooking.base_rate > 0 && newBooking.base_rate !== newBooking.total_amount) {
      if (!newBooking.override_reason) {
        toast.error('Please provide a reason for rate override');
        return;
      }
    }

    if (!newBooking.guest_id) {
      toast.error('Please select guest');
      return;
    }

    if (!newBooking.check_in || !newBooking.check_out) {
      toast.error('Please select check-in and check-out dates');
      return;
    }

    // Load rate data for this booking window
    await loadRateData(newBooking.channel, newBooking.company_id, newBooking.check_in);

    // Multi-room validasyonu
    if (!multiRoomBooking || multiRoomBooking.length === 0) {
      toast.error('Please add at least one room');
      return;
    }

    const invalidRoom = multiRoomBooking.find(r => !r.room_id);
    if (invalidRoom) {
      toast.error('Please select room for each line');
      return;
    }

    try {
      const roomsPayload = multiRoomBooking.map(room => ({
        room_id: room.room_id,
        adults: room.adults,
        children: room.children,
        children_ages: room.children_ages || [],
        total_amount: room.total_amount,
        base_rate: room.base_rate,
        rate_plan: room.rate_plan || newBooking.rate_type || 'Standard',
        package_code: room.package_code || null
      }));

      const payload = {
        guest_id: newBooking.guest_id,
        arrival_date: newBooking.check_in,
        departure_date: newBooking.check_out,
        rooms: roomsPayload,
        company_id: newBooking.company_id || null,
        channel: newBooking.channel || 'direct',
        special_requests: undefined
      };

      await axios.post('/pms/bookings/multi-room', payload);
      toast.success('Booking created successfully');
      setOpenDialog(null);
      loadData();
      setSelectedCompany(null);
      setNewBooking({
        guest_id: '',
        room_id: '',
        check_in: '',
        check_out: '',
        adults: 1,
        children: 0,
        children_ages: [],
        guests_count: 1,
        total_amount: 0,
        base_rate: 0,
        channel: 'direct',
        company_id: '',
        contracted_rate: '',
        rate_type: '',
        market_segment: '',
        cancellation_policy: '',
        billing_address: '',
        billing_tax_number: '',
        billing_contact_person: '',
        override_reason: ''
      });
      setMultiRoomBooking([
        {
          room_id: '',
          adults: 1,
          children: 0,
          children_ages: [],
          total_amount: 0,
          base_rate: 0,
          rate_plan: '',
          package_code: null
        }
      ]);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create booking');
    }
  };

  // Folio Management Functions
  const loadBookingFolios = async (bookingId) => {
    try {
      const response = await axios.get(`/folio/booking/${bookingId}`);
      setFolios(response.data);
      setSelectedBooking(bookingId);
      setOpenDialog('folio-view');
      
      // Auto-select guest folio if exists
      const guestFolio = response.data.find(f => f.folio_type === 'guest');
      if (guestFolio) {
        loadFolioDetails(guestFolio.id);
      }
    } catch (error) {
      toast.error('Failed to load folios');
    }
  };

  const loadFolioDetails = async (folioId) => {
    try {
      const response = await axios.get(`/folio/${folioId}`);
      setSelectedFolio(response.data.folio);
      setFolioCharges(response.data.charges || []);
      setFolioPayments(response.data.payments || []);
    } catch (error) {
      toast.error('Failed to load folio details');
    }
  };

  const handlePostCharge = async (e) => {
    e.preventDefault();
    if (!selectedFolio) return;
    
    try {
      await axios.post(`/folio/${selectedFolio.id}/charge`, newFolioCharge);
      toast.success('Charge posted successfully');
      loadFolioDetails(selectedFolio.id);
      setNewFolioCharge({
        charge_category: 'room',
        description: '',
        amount: 0,
        quantity: 1,
        auto_calculate_tax: false
      });
      setOpenDialog('folio-view');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to post charge');
    }
  };

  const handlePostPayment = async (e) => {
    e.preventDefault();
    if (!selectedFolio) return;
    
    try {
      await axios.post(`/folio/${selectedFolio.id}/payment`, newFolioPayment);
      toast.success('Payment posted successfully');
      loadFolioDetails(selectedFolio.id);
      setNewFolioPayment({
        amount: 0,
        method: 'card',
        payment_type: 'interim',
        reference: '',
        notes: ''
      });
      setOpenDialog('folio-view');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to post payment');
    }
  };

  const updateRoomStatus = async (roomId, newStatus) => {
    try {
      await axios.put(`/pms/rooms/${roomId}`, { status: newStatus });
      toast.success('Room status updated');
      loadData();
      loadHousekeepingData();
    } catch (error) {
      toast.error('Failed to update status');
    }
  };

  const quickUpdateRoomStatus = async (roomId, newStatus) => {
    try {
      const response = await axios.put(`/housekeeping/room/${roomId}/status?new_status=${newStatus}`);
      toast.success(response.data.message);
      loadHousekeepingData();
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to update status');
    }
  };

  const createRoomBlock = async () => {
    if (!selectedRoom) {
      toast.error('Please select a room');
      return;
    }
    if (!newRoomBlock.reason || !newRoomBlock.start_date) {
      toast.error('Please fill in all required fields');
      return;
    }
    
    try {
      const response = await axios.post('/pms/room-blocks', {
        room_id: selectedRoom.id,
        ...newRoomBlock
      });
      
      if (response.data.warnings && response.data.warnings.length > 0) {
        response.data.warnings.forEach(warning => {
          toast.warning(warning.message);
        });
      }
      
      toast.success(response.data.message);
      setOpenDialog(null);
      setSelectedRoom(null);
      setNewRoomBlock({
        type: 'out_of_order',
        reason: '',
        details: '',
        start_date: '',
        end_date: '',
        allow_sell: false
      });
      loadHousekeepingData();
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create room block');
    }
  };

  const cancelRoomBlock = async (blockId) => {
    try {
      await axios.post(`/pms/room-blocks/${blockId}/cancel`);
      toast.success('Room block cancelled');
      loadHousekeepingData();
      loadData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to cancel block');
    }
  };

  // Phase H - Load Guest 360° Profile
  const loadGuest360 = async (guestId) => {
    setLoadingGuest360(true);
    try {
      const response = await axios.get(`/crm/guest/${guestId}`, { timeout: 15000 });
      setGuest360Data(response.data);
      setOpenDialog('guest360');
    } catch (error) {
      console.error('Guest 360 error:', error);
      if (error.code === 'ECONNABORTED') {
        toast.error('Request timeout - Guest profile has too much data. Please try again.');
      } else {
        toast.error(error.response?.data?.detail || 'Failed to load guest profile. Please try again later.');
      }
    } finally {
      setLoadingGuest360(false);
    }
  };

  const addGuestTag = async () => {
    if (!guestTag || !selectedGuest360) return;
    try {
      await axios.post(`/crm/guest/add-tag?guest_id=${selectedGuest360}&tag=${guestTag}`);
      toast.success('Tag added');
      setGuestTag('');
      loadGuest360(selectedGuest360);
    } catch (error) {
      toast.error('Failed to add tag');
    }
  };

  const addGuestNote = async () => {
    if (!guestNote || !selectedGuest360) return;
    try {
      await axios.post(`/crm/guest/note?guest_id=${selectedGuest360}&note=${guestNote}`);
      toast.success('Note added');
      setGuestNote('');
      loadGuest360(selectedGuest360);
    } catch (error) {
      toast.error('Failed to add note');
    }
  };

  const generateUpsellOffers = async (bookingId) => {
    try {
      const response = await axios.post(`/ai/upsell/generate?booking_id=${bookingId}`, {}, { timeout: 10000 });
      toast.success(`Generated ${response.data.total_offers} upsell offers`);
      setUpsellOffers(response.data.offers);
    } catch (error) {
      console.error('Upsell generation error:', error);
      if (error.response?.status === 503) {
        toast.error('AI service is temporarily unavailable. Using default offers.');
      } else if (error.response?.status === 404) {
        toast.error('Booking not found or no available upsell options.');
      } else {
        toast.error(error.response?.data?.detail || 'Failed to generate upsell offers. Please try again.');
      }
    }
  };

  const loadMessageTemplates = async () => {
    try {
      const response = await axios.get('/messages/templates');
      setMessageTemplates(response.data.templates || []);
    } catch (error) {
      console.error('Failed to load templates');
    }
  };

  const sendMessage = async () => {
    if (!newMessage.recipient || !newMessage.body) {
      toast.error('Please fill in all fields');
      return;
    }

    try {
      let response;
      if (newMessage.channel === 'email') {
        response = await axios.post('/messages/send-email', {
          recipient: newMessage.recipient,
          subject: newMessage.subject,
          body: newMessage.body
        });
      } else if (newMessage.channel === 'sms') {
        response = await axios.post('/messages/send-sms', {
          recipient: newMessage.recipient,
          body: newMessage.body
        });
      } else if (newMessage.channel === 'whatsapp') {
        response = await axios.post('/messages/send-whatsapp', {
          recipient: newMessage.recipient,
          body: newMessage.body
        });
      }

      toast.success('Message sent successfully!');
      setSentMessages([response.data, ...sentMessages]);
      setNewMessage({
        channel: 'email',
        recipient: '',
        subject: '',
        body: '',
        template_id: null
      });
    } catch (error) {
      console.error('Message send error:', error);
      if (error.response?.status === 503) {
        toast.error(`${newMessage.channel.toUpperCase()} service is not configured. Please configure API credentials in Settings.`);
      } else if (error.response?.status === 401) {
        toast.error('Authentication failed. Please check your API credentials.');
      } else {
        toast.error(error.response?.data?.detail || `Failed to send ${newMessage.channel} message. Please check your configuration.`);
      }
    }
  };

  if (loading) {
    return (
      <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="pms">
        <div className="flex items-center justify-center h-screen">
          <div className="text-center">
            <RefreshCw className="w-12 h-12 animate-spin text-blue-600 mx-auto mb-4" />
            <p className="text-lg font-medium text-gray-700">Loading PMS Data...</p>
            <p className="text-sm text-gray-500 mt-2">Please wait while we load your data</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="pms">
      <div className="p-6 space-y-6">
        <div className="mb-6 flex justify-between items-start gap-4">
          <div>
            <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>{t('pms.title')}</h1>
            <p className="text-gray-600">{t('pms.subtitle')}</p>
          </div>
          <div className="w-96">
            <GlobalSearch onSelectResult={(result) => {
              console.log('Search result selected:', result);
              toast.success(`Selected ${result.type}: ${result.data.name || result.data.room_number || result.data.id}`);
            }} />
          </div>
        </div>


        {/* Quick Actions Toolbar */}
        <Card className="border-blue-200 bg-gradient-to-r from-blue-50 to-purple-50">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="text-sm font-semibold text-gray-700">Quick Actions:</div>
              </div>
              <div className="flex gap-2">
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => {
                    setOpenDialog('newbooking');
                    toast.info('Opening new booking form...');
                  }}
                >
                  <Plus className="w-4 h-4 mr-2" />
                  New Booking
                </Button>
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => {
                    setOpenDialog('newguest');
                  }}
                >
                  <UserPlus className="w-4 h-4 mr-2" />
                  New Guest
                </Button>
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={async () => {
                    try {
                      const response = await axios.get('/reports/flash-report');
                      toast.success('Flash report generated!');
                      console.log('Flash report:', response.data);
                    } catch (error) {
                      toast.error('Failed to generate report');
                    }
                  }}
                >
                  <FileText className="w-4 h-4 mr-2" />
                  Flash Report
                </Button>
                <Button 
                  size="sm" 
                  variant="outline"
                  onClick={() => loadData()}
                >
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Refresh
                </Button>
              </div>
            </div>
          </CardContent>
        </Card>


        <Tabs
          value={activeTab}
          className="w-full"
          onValueChange={(v) => {
            // Sekme değeri hemen değişsin (UI anında tepki versin)
            setActiveTab(v);
            // Ağır veri yükleri sadece ilk girişte, arkada tetikleniyor (useEffect)
          }}
        >
          <TabsList className="grid w-full grid-cols-12 gap-1">
            <TabsTrigger value="frontdesk" data-testid="tab-frontdesk">
              <UserCheck className="w-4 h-4 mr-2" />
              {t('pms.frontDesk')}
            </TabsTrigger>
            <TabsTrigger value="housekeeping" data-testid="tab-housekeeping">
              <ClipboardList className="w-4 h-4 mr-2" />
              {t('pms.housekeeping')}
            </TabsTrigger>
            <TabsTrigger value="rooms" data-testid="tab-rooms">
              <BedDouble className="w-4 h-4 mr-2" />
              {t('pms.rooms')}
            </TabsTrigger>
            <TabsTrigger value="guests" data-testid="tab-guests">
              <Users className="w-4 h-4 mr-2" />
              {t('pms.guests')}
            </TabsTrigger>
            <TabsTrigger value="bookings" data-testid="tab-bookings">
              <Calendar className="w-4 h-4 mr-2" />
              {t('pms.bookings')}
            </TabsTrigger>
            <TabsTrigger value="upsell" data-testid="tab-upsell">
              <TrendingUp className="w-4 h-4 mr-2" />
              🤖 Upsell
            </TabsTrigger>
            <TabsTrigger value="messaging" data-testid="tab-messaging">
              💬 Messages
            </TabsTrigger>
            <TabsTrigger value="reports" data-testid="tab-reports">
              <FileText className="w-4 h-4 mr-2" />
              {t('pms.reports')}
            </TabsTrigger>
            <TabsTrigger value="tasks" data-testid="tab-tasks">
              🔧 Tasks
            </TabsTrigger>
            <TabsTrigger value="feedback" data-testid="tab-feedback">
              ⭐ Feedback
            </TabsTrigger>
            <TabsTrigger value="allotment" data-testid="tab-allotment">
              🏢 Allotment
            </TabsTrigger>
            <TabsTrigger value="pos" data-testid="tab-pos">
              🍽️ POS
            </TabsTrigger>
          </TabsList>

          {/* FRONT DESK TAB */}
          <TabsContent value="frontdesk" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="cursor-pointer hover:shadow-lg transition" onClick={loadFrontDeskData}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">{t('pms.todayArrivals')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{arrivals.length}</div>
                  <p className="text-xs text-gray-500">{t('pms.expectedCheckins')}</p>
                </CardContent>
              </Card>
              
              <Card className="cursor-pointer hover:shadow-lg transition" onClick={loadFrontDeskData}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">{t('pms.todayDepartures')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{departures.length}</div>
                  <p className="text-xs text-gray-500">{t('pms.expectedCheckouts')}</p>
                </CardContent>
              </Card>
              
              <Card className="cursor-pointer hover:shadow-lg transition" onClick={loadFrontDeskData}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">{t('pms.inHouseGuests')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{inhouse.length}</div>
                  <p className="text-xs text-gray-500">{t('pms.currentlyStaying')}</p>
                </CardContent>
              </Card>
            </div>

            {/* AI Insights */}
            {(aiPrediction || aiPatterns) && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {aiPrediction && (
                  <Card className="bg-gradient-to-br from-green-50 to-blue-50 border-green-200">
                    <CardHeader>
                      <CardTitle className="flex items-center text-green-700">
                        <TrendingUp className="w-5 h-5 mr-2" />
                        {t('ai.occupancyPrediction')}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2 text-sm">
                        <div className="flex justify-between">
                          <span className="text-gray-600">Current Occupancy:</span>
                          <span className="font-semibold">{aiPrediction.current_occupancy?.toFixed(1)}%</span>
                        </div>
                        <div className="flex justify-between">
                          <span className="text-gray-600">Upcoming Bookings:</span>
                          <span className="font-semibold">{aiPrediction.upcoming_bookings}</span>
                        </div>
                        {aiPrediction.prediction && (
                          <div className="mt-3 p-3 bg-white rounded border border-green-100">
                            <p className="text-xs text-gray-700">{JSON.stringify(aiPrediction.prediction).substring(0, 200)}</p>
                          </div>
                        )}
                      </div>
                      <div className="text-xs text-gray-500 mt-2">{t('ai.poweredBy')}</div>
                    </CardContent>
                  </Card>
                )}
                
                {aiPatterns && (
                  <Card className="bg-gradient-to-br from-purple-50 to-pink-50 border-purple-200">
                    <CardHeader>
                      <CardTitle className="flex items-center text-purple-700">
                        <Users className="w-5 h-5 mr-2" />
                        {t('ai.guestPatterns')}
                      </CardTitle>
                    </CardHeader>
                    <CardContent>
                      {aiPatterns.insights && Array.isArray(aiPatterns.insights) ? (
                        <div className="space-y-1">
                          {aiPatterns.insights.map((insight, idx) => (
                            <p key={idx} className="text-sm text-gray-700">{insight}</p>
                          ))}
                        </div>
                      ) : (
                        <p className="text-sm text-gray-700">Guest pattern analysis available</p>
                      )}
                      <div className="text-xs text-gray-500 mt-2">{t('ai.poweredBy')}</div>
                    </CardContent>
                  </Card>
                )}
              </div>
            )}

            <Tabs defaultValue="arrivals">
              <TabsList>
                <TabsTrigger value="arrivals">{t('pms.arrivals')}</TabsTrigger>
                <TabsTrigger value="departures">{t('pms.departures')}</TabsTrigger>
                <TabsTrigger value="inhouse">{t('pms.inHouse')}</TabsTrigger>
              </TabsList>

              <TabsContent value="arrivals" className="space-y-4">
                {arrivals.map((booking) => (
                  <Card key={booking.id}>
                    <CardContent className="pt-6">
                      <div className="flex justify-between items-center">
                        <div>
                          <div className="font-bold text-lg">{booking.guest?.name}</div>
                          <div className="text-sm text-gray-600">Room {booking.room?.room_number} - {booking.room?.room_type}</div>
                          <div className="text-sm text-gray-500">Check-in: {new Date(booking.check_in).toLocaleDateString()}</div>
                        </div>
                        <div className="space-x-2">
                          {booking.status === 'confirmed' && (
                            <Button onClick={() => handleCheckIn(booking.id)} data-testid={`checkin-${booking.id}`}>
                              <LogIn className="w-4 h-4 mr-2" />
                              Check In
                            </Button>
                          )}
                          <Button variant="outline" onClick={() => loadFolio(booking.id)}>
                            View Folio
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </TabsContent>

              <TabsContent value="departures" className="space-y-4">
                {departures.map((booking) => (
                  <Card key={booking.id}>
                    <CardContent className="pt-6">
                      <div className="flex justify-between items-center">
                        <div>
                          <div className="font-bold text-lg">{booking.guest?.name}</div>
                          <div className="text-sm text-gray-600">Room {booking.room?.room_number}</div>
                          <div className="text-sm text-gray-500">Check-out: {new Date(booking.check_out).toLocaleDateString()}</div>
                          <div className="text-sm font-medium mt-1">
                            Balance: <span className={booking.balance > 0 ? 'text-red-600' : 'text-green-600'}>
                              ${booking.balance?.toFixed(2) || '0.00'}
                            </span>
                          </div>
                        </div>
                        <div className="space-x-2">
                          <Button variant="outline" onClick={() => loadFolio(booking.id)}>
                            View Folio
                          </Button>
                          <Button 
                            onClick={() => handleCheckOut(booking.id)} 
                            disabled={booking.balance > 0}
                            data-testid={`checkout-${booking.id}`}
                          >
                            <LogOut className="w-4 h-4 mr-2" />
                            Check Out
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </TabsContent>

              <TabsContent value="inhouse" className="space-y-4">
                {inhouse.map((booking) => (
                  <Card key={booking.id}>
                    <CardContent className="pt-6">
                      <div className="flex justify-between items-center">
                        <div>
                          <div className="font-bold text-lg">{booking.guest?.name}</div>
                          <div className="text-sm text-gray-600">Room {booking.room?.room_number} - {booking.room?.room_type}</div>
                          <div className="text-sm text-gray-500">
                            Check-in: {new Date(booking.check_in).toLocaleDateString()} | 
                            Check-out: {new Date(booking.check_out).toLocaleDateString()}
                          </div>
                        </div>
                        <Button variant="outline" onClick={() => loadFolio(booking.id)}>
                          Manage Folio
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </TabsContent>
            </Tabs>
          </TabsContent>

          {/* HOUSEKEEPING TAB */}
          <TabsContent value="housekeeping" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold">Housekeeping Management</h2>
              <div className="space-x-2">
                <Button onClick={() => setOpenDialog('hktask')}>
                  <Plus className="w-4 h-4 mr-2" />
                  Create Task
                </Button>
                <Button onClick={() => setOpenDialog('roomblock')} variant="outline">
                  <Plus className="w-4 h-4 mr-2" />
                  Block Room
                </Button>
              </div>
            </div>

            {/* Block Counters */}
            {roomBlocks.length > 0 && (
              <div className="flex gap-4 p-4 bg-gray-50 rounded-lg border">
                <div className="flex items-center gap-2">
                  <span className="font-semibold">Room Blocks:</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-red-600 rounded"></div>
                  <span className="text-sm">Out of Order: {roomBlocks.filter(b => b.type === 'out_of_order' && b.status === 'active').length}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-orange-500 rounded"></div>
                  <span className="text-sm">Out of Service: {roomBlocks.filter(b => b.type === 'out_of_service' && b.status === 'active').length}</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 bg-yellow-500 rounded"></div>
                  <span className="text-sm">Maintenance: {roomBlocks.filter(b => b.type === 'maintenance' && b.status === 'active').length}</span>
                </div>
              </div>
            )}

            {/* Status Overview */}
            {roomStatusBoard && (
              <div className="grid grid-cols-3 md:grid-cols-7 gap-4">
                {Object.entries(roomStatusBoard.status_counts).map(([status, count]) => (
                  <Card key={status} className={`border-2 ${
                    status === 'dirty' ? 'border-red-200 bg-red-50' :
                    status === 'cleaning' ? 'border-yellow-200 bg-yellow-50' :
                    status === 'inspected' ? 'border-green-200 bg-green-50' :
                    status === 'available' ? 'border-blue-200 bg-blue-50' :
                    'border-gray-200'
                  }`}>
                    <CardContent className="pt-4">
                      <div className="text-3xl font-bold">{count}</div>
                      <div className="text-xs capitalize font-semibold">{status.replace('_', ' ')}</div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            )}

            {/* Due Out / Stayover / Arrivals Lists */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {/* Due Out Today */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center">
                    <LogOut className="w-5 h-5 mr-2 text-red-600" />
                    Due Out ({dueOutRooms.length})
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 max-h-96 overflow-y-auto">
                  {dueOutRooms.length === 0 ? (
                    <div className="text-center text-gray-400 py-4">No departures</div>
                  ) : (
                    dueOutRooms.map((room, idx) => (
                      <div key={idx} className={`p-3 rounded border ${room.is_today ? 'bg-red-50 border-red-200' : 'bg-orange-50 border-orange-200'}`}>
                        <div className="font-bold">Room {room.room_number}</div>
                        <div className="text-sm text-gray-600">{room.guest_name}</div>
                        <div className="text-xs text-gray-500">
                          {new Date(room.checkout_date).toLocaleDateString()}
                          {room.is_today && <span className="ml-2 text-red-600 font-semibold">TODAY</span>}
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              {/* Stayovers */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center">
                    <Home className="w-5 h-5 mr-2 text-blue-600" />
                    Stayovers ({stayoverRooms.length})
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 max-h-96 overflow-y-auto">
                  {stayoverRooms.length === 0 ? (
                    <div className="text-center text-gray-400 py-4">No stayovers</div>
                  ) : (
                    stayoverRooms.map((room, idx) => (
                      <div key={idx} className="p-3 rounded border bg-blue-50 border-blue-200">
                        <div className="font-bold">Room {room.room_number}</div>
                        <div className="text-sm text-gray-600">{room.guest_name}</div>
                        <div className="text-xs text-gray-500">
                          {room.nights_remaining} night(s) remaining
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>

              {/* Arrivals */}
              <Card>
                <CardHeader>
                  <CardTitle className="text-lg flex items-center">
                    <LogIn className="w-5 h-5 mr-2 text-green-600" />
                    Arrivals ({arrivalRooms.length})
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-2 max-h-96 overflow-y-auto">
                  {arrivalRooms.length === 0 ? (
                    <div className="text-center text-gray-400 py-4">No arrivals</div>
                  ) : (
                    arrivalRooms.map((room, idx) => (
                      <div key={idx} className={`p-3 rounded border ${
                        room.ready ? 'bg-green-50 border-green-200' : 'bg-yellow-50 border-yellow-200'
                      }`}>
                        <div className="font-bold">Room {room.room_number}</div>
                        <div className="text-sm text-gray-600">{room.guest_name}</div>
                        <div className="text-xs flex items-center justify-between">
                          <span className={room.ready ? 'text-green-600 font-semibold' : 'text-yellow-600'}>
                            {room.ready ? '✓ Ready' : `⚠ ${room.room_status}`}
                          </span>
                        </div>
                      </div>
                    ))
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Room Status Board */}
            {roomStatusBoard && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>Room Status Board</span>
                    <div className="flex gap-3 text-xs">
                      {/* Priority Indicators */}
                      <div className="flex gap-2 items-center border-r pr-3">
                        <span className="text-gray-600 font-semibold">Priority:</span>
                        <span className="flex items-center gap-1">
                          <span className="w-3 h-3 rounded-full bg-red-500"></span> Urgent
                        </span>
                        <span className="flex items-center gap-1">
                          <span className="w-3 h-3 rounded-full bg-orange-500"></span> High
                        </span>
                      </div>
                      {/* Status Colors (Global System) */}
                      <div className="flex gap-2 items-center">
                        <span className="text-gray-600 font-semibold">Status:</span>
                        <span className="flex items-center gap-1">
                          <span className="w-3 h-3 rounded-full bg-green-500"></span> Available
                        </span>
                        <span className="flex items-center gap-1">
                          <span className="w-3 h-3 rounded-full bg-red-500"></span> Dirty
                        </span>
                        <span className="flex items-center gap-1">
                          <span className="w-3 h-3 rounded-full bg-yellow-500"></span> Cleaning
                        </span>
                        <span className="flex items-center gap-1">
                          <span className="w-3 h-3 rounded-full bg-purple-500"></span> Occupied
                        </span>
                      </div>
                    </div>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                    {roomStatusBoard.rooms.map((room) => {
                      const roomBlock = roomBlocks.find(b => b.room_id === room.id && b.status === 'active');
                      
                      // Priority calculation
                      const isDueOutToday = dueOutRooms.some(r => r.room_number === room.room_number && r.is_today);
                      const isArrivalToday = arrivalRooms.some(r => r.room_number === room.room_number && r.ready === false);
                      const needsCleaning = room.status === 'dirty' && (isDueOutToday || isArrivalToday);
                      
                      // Priority badge color
                      let priorityColor = '';
                      let priorityIcon = null;
                      let priorityTitle = '';
                      
                      if (needsCleaning && isDueOutToday) {
                        priorityColor = 'bg-red-600';
                        priorityIcon = '🔥';
                        priorityTitle = 'URGENT: Due Out Today - Needs Cleaning';
                      } else if (needsCleaning && isArrivalToday) {
                        priorityColor = 'bg-orange-600';
                        priorityIcon = '⚡';
                        priorityTitle = 'HIGH: Arrival Today - Needs Cleaning';
                      } else if (isDueOutToday) {
                        priorityColor = 'bg-orange-500';
                        priorityIcon = '📤';
                        priorityTitle = 'Due Out Today';
                      } else if (isArrivalToday) {
                        priorityColor = 'bg-blue-600';
                        priorityIcon = '📥';
                        priorityTitle = 'Arrival Today';
                      }
                      
                      // Global color system: green=available, red=dirty/risk, yellow=pending, purple=occupied
                      const statusColors = {
                        'dirty': 'bg-red-100 border-red-300', // RISK
                        'cleaning': 'bg-yellow-100 border-yellow-300', // PENDING
                        'inspected': 'bg-green-100 border-green-300', // AVAILABLE (ready for occupancy)
                        'available': 'bg-green-100 border-green-300', // AVAILABLE
                        'occupied': 'bg-purple-100 border-purple-300' // OCCUPIED
                      };
                      
                      return (
                      <Card key={room.id} className={`cursor-pointer hover:shadow-lg transition-shadow relative ${
                        statusColors[room.status] || 'bg-gray-100 border-gray-300'
                      } ${priorityColor ? 'ring-2 ring-offset-1 ' + (priorityColor === 'bg-red-600' ? 'ring-red-500' : priorityColor === 'bg-orange-600' ? 'ring-orange-500' : 'ring-blue-500') : ''}`}>
                        <div className="absolute top-1 right-1 flex gap-1">
                          {/* New Booking Button */}
                          <button
                            onClick={(e) => {
                              e.stopPropagation();
                              setOpenDialog('booking');
                              setNewBooking(prev => ({...prev, room_id: room.id, room_number: room.room_number}));
                            }}
                            className="w-6 h-6 bg-blue-600 hover:bg-blue-700 text-white rounded-full flex items-center justify-center transition-all hover:scale-110 shadow-md"
                            title="Yeni Rezervasyon Oluştur"
                          >
                            <span className="text-sm font-bold">+</span>
                          </button>
                          
                          {priorityIcon && (
                            <span className={`px-1.5 py-0.5 text-[10px] font-bold ${priorityColor} text-white rounded flex items-center`} title={priorityTitle}>
                              {priorityIcon}
                            </span>
                          )}
                          {roomBlock && (
                            <>
                              {roomBlock.type === 'out_of_order' && (
                                <span className="px-1.5 py-0.5 text-[10px] font-bold bg-red-600 text-white rounded" title={roomBlock.reason}>OOO</span>
                              )}
                              {roomBlock.type === 'out_of_service' && (
                                <span className="px-1.5 py-0.5 text-[10px] font-bold bg-orange-500 text-white rounded" title={roomBlock.reason}>OOS</span>
                              )}
                              {roomBlock.type === 'maintenance' && (
                                <span className="px-1.5 py-0.5 text-[10px] font-bold bg-yellow-600 text-white rounded" title={roomBlock.reason}>MNT</span>
                              )}
                            </>
                          )}
                        </div>
                        <CardContent className="p-3">
                          <div className="font-bold text-lg">{room.room_number}</div>
                          <div className="text-xs capitalize">{room.room_type}</div>
                          <div className="text-xs font-semibold mt-1 capitalize">{room.status.replace('_', ' ')}</div>
                          {priorityTitle && (
                            <div className="text-[10px] font-semibold mt-1 truncate" style={{color: priorityColor.replace('bg-', '').replace('-600', '-700').replace('-500', '-600')}}>
                              {priorityTitle.replace('URGENT: ', '').replace('HIGH: ', '')}
                            </div>
                          )}
                          {roomBlock && (
                            <div className="text-[10px] text-gray-600 mt-1 truncate" title={roomBlock.reason}>
                              {roomBlock.reason}
                            </div>
                          )}
                          <div className="flex gap-1 mt-2">
                            {room.status === 'dirty' && (
                              <Button size="sm" variant="outline" className={`h-6 text-xs ${needsCleaning ? 'bg-red-50 border-red-400 text-red-700 hover:bg-red-100' : ''}`} onClick={() => quickUpdateRoomStatus(room.id, 'cleaning')}>
                                Clean {needsCleaning && '⚡'}
                              </Button>
                            )}
                            {room.status === 'cleaning' && (
                              <Button size="sm" variant="outline" className="h-6 text-xs" onClick={() => quickUpdateRoomStatus(room.id, 'inspected')}>
                                Done
                              </Button>
                            )}
                            {room.status === 'inspected' && (
                              <Button size="sm" variant="outline" className="h-6 text-xs" onClick={() => quickUpdateRoomStatus(room.id, 'available')}>
                                Ready
                              </Button>
                            )}
                            {/* Maintenance issue from HK */}
                            <Button
                              size="sm"
                              variant="outline"
                              className="h-6 text-[10px] ml-auto"
                              onClick={(e) => {
                                e.stopPropagation();
                                setMaintenanceForm({
                                  room_id: room.id,
                                  room_number: room.room_number,
                                  issue_type: 'housekeeping_damage',
                                  priority: 'normal',
                                  description: ''
                                });
                                setMaintenanceDialogOpen(true);
                              }}
                            >
                              MNT
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    )})}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Task Priority Filter & Stats */}
            <div className="grid grid-cols-4 gap-4">
              <Card className="cursor-pointer hover:shadow-lg transition" onClick={() => toast.info('Showing all tasks')}>
                <CardContent className="p-4 text-center">
                  <div className="text-2xl font-bold text-gray-700">{housekeepingTasks.length}</div>
                  <div className="text-xs text-gray-600">Total Tasks</div>
                </CardContent>
              </Card>
              <Card className="cursor-pointer hover:shadow-lg transition border-red-200">
                <CardContent className="p-4 text-center">
                  <div className="text-2xl font-bold text-red-600">
                    {housekeepingTasks.filter(t => t.priority === 'high').length}
                  </div>
                  <div className="text-xs text-gray-600">High Priority</div>
                </CardContent>
              </Card>
              <Card className="cursor-pointer hover:shadow-lg transition border-yellow-200">
                <CardContent className="p-4 text-center">
                  <div className="text-2xl font-bold text-yellow-600">
                    {housekeepingTasks.filter(t => t.status === 'in_progress').length}
                  </div>
                  <div className="text-xs text-gray-600">In Progress</div>
                </CardContent>
              </Card>
              <Card className="cursor-pointer hover:shadow-lg transition border-green-200">
                <CardContent className="p-4 text-center">
                  <div className="text-2xl font-bold text-green-600">
                    {housekeepingTasks.filter(t => t.status === 'completed').length}
                  </div>
                  <div className="text-xs text-gray-600">Completed Today</div>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-4">
              {housekeepingTasks.length === 0 ? (
                <div className="text-center py-12 text-gray-400">
                  <ClipboardList className="w-16 h-16 mx-auto mb-4 opacity-50" />
                  <p>No housekeeping tasks</p>
                </div>
              ) : (
                housekeepingTasks
                  .sort((a, b) => {
                    // Sort by priority first
                    const priorityOrder = { high: 0, medium: 1, low: 2 };
                    const priorityDiff = (priorityOrder[a.priority] || 1) - (priorityOrder[b.priority] || 1);
                    if (priorityDiff !== 0) return priorityDiff;
                    
                    // Then by status
                    const statusOrder = { pending: 0, in_progress: 1, completed: 2 };
                    return (statusOrder[a.status] || 0) - (statusOrder[b.status] || 0);
                  })
                  .map((task) => (
                    <Card key={task.id} className={`${
                      task.priority === 'high' ? 'border-l-4 border-l-red-500' :
                      task.priority === 'medium' ? 'border-l-4 border-l-yellow-500' :
                      'border-l-4 border-l-green-500'
                    }`}>
                      <CardContent className="pt-6">
                        <div className="flex justify-between items-start">
                          <div className="flex-1">
                            <div className="flex items-center gap-2 mb-2">
                              <div className="font-bold text-lg">Room {task.room?.room_number}</div>
                              <Badge variant={
                                task.priority === 'high' ? 'destructive' :
                                task.priority === 'medium' ? 'default' :
                                'outline'
                              }>
                                {task.priority?.toUpperCase()} PRIORITY
                              </Badge>
                              <Badge variant="outline" className="text-xs">
                                {task.task_type}
                              </Badge>
                            </div>
                            <div className="text-sm text-gray-600 capitalize mb-1">
                              Assigned to: {task.assigned_to || 'Unassigned'}
                            </div>
                            {task.notes && (
                              <div className="text-sm text-gray-500 bg-gray-50 p-2 rounded mt-2">
                                💬 {task.notes}
                              </div>
                            )}
                            {task.estimated_duration && (
                              <div className="text-xs text-gray-500 mt-2">
                                ⏱️ Estimated: {task.estimated_duration} minutes
                              </div>
                            )}
                          </div>
                          <div className="space-x-2 flex items-center gap-2">
                            {task.status === 'pending' && (
                              <Button size="sm" onClick={() => handleUpdateHKTask(task.id, 'in_progress')}>
                                <Clock className="w-4 h-4 mr-2" />
                                Start
                              </Button>
                            )}
                            {task.status === 'in_progress' && (
                              <Button size="sm" variant="default" className="bg-green-600" onClick={() => handleUpdateHKTask(task.id, 'completed')}>
                                <CheckCircle className="w-4 h-4 mr-2" />
                                Complete
                              </Button>
                            )}
                            <span className={`px-3 py-2 rounded-lg text-sm font-semibold ${
                              task.status === 'completed' ? 'bg-green-100 text-green-700' : 
                              task.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                              'bg-gray-100 text-gray-700'
                            }`}>
                              {task.status === 'completed' ? '✅ Done' : 
                               task.status === 'in_progress' ? '🔄 Working' :
                               '⏸️ Pending'}
                            </span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))
              )}
            </div>
          </TabsContent>

          {/* ROOMS TAB */}
          <TabsContent value="rooms" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold">Rooms ({rooms.length})</h2>
              <div className="flex gap-2">
                <Button 
                  variant={bulkRoomMode ? "default" : "outline"}
                  size="sm"
                  onClick={() => {
                    setBulkRoomMode(!bulkRoomMode);
                    setSelectedRooms([]);
                  }}
                >
                  <CheckSquare className="w-4 h-4 mr-2" />
                  Bulk Mode
                </Button>
                <Button onClick={() => setOpenDialog('room')}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Room
                </Button>
              </div>
            </div>
            
            {/* Bulk Actions Toolbar */}
            {bulkRoomMode && selectedRooms.length > 0 && (
              <Card className="border-purple-200 bg-purple-50">
                <CardContent className="p-4">
                  <div className="flex justify-between items-center">
                    <div className="font-semibold">{selectedRooms.length} room(s) selected</div>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        onClick={async () => {
                          const newStatus = window.prompt('New status:', 'clean');
                          if (newStatus) {
                            try {
                              let success = 0;
                              for (const roomId of selectedRooms) {
                                try {
                                  await axios.patch(`/pms/rooms/${roomId}`, { status: newStatus });
                                  success++;
                                } catch (error) {
                                  console.error(`Failed to update room ${roomId}:`, error);
                                }
                              }
                              toast.success(`${success}/${selectedRooms.length} rooms updated`);
                              setSelectedRooms([]);
                              setBulkRoomMode(false);
                              loadData();
                            } catch (error) {
                              toast.error('Bulk update failed');
                            }
                          }
                        }}
                      >
                        Update Status
                      </Button>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setSelectedRooms([]);
                          setBulkRoomMode(false);
                        }}
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {rooms.map((room) => {
                const roomBlock = roomBlocks.find(b => b.room_id === room.id && b.status === 'active');
                // Find current booking for this room
                const currentBooking = bookings.find(b => b.room_id === room.id && b.status === 'checked_in');
                const currentGuest = currentBooking ? guests.find(g => g.id === currentBooking.guest_id) : null;
                
                return (
                <Card key={room.id} className={`${roomBlock ? 'border-2 border-red-400' : ''} ${currentBooking ? 'border-l-4 border-l-blue-500' : ''} ${selectedRooms.includes(room.id) ? 'ring-2 ring-purple-500' : ''}`}>
                  <CardHeader className="relative pb-2">
                    {/* Bulk Selection Checkbox */}
                    {bulkRoomMode && (
                      <input
                        type="checkbox"
                        className="absolute top-2 right-2 w-5 h-5 cursor-pointer z-20"
                        checked={selectedRooms.includes(room.id)}
                        onChange={(e) => {
                          if (e.target.checked) {
                            setSelectedRooms([...selectedRooms, room.id]);
                          } else {
                            setSelectedRooms(selectedRooms.filter(id => id !== room.id));
                          }
                        }}
                      />
                    )}
                    
                    {/* New Booking + Button */}
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenDialog('booking');
                        setNewBooking(prev => ({...prev, room_id: room.id, room_number: room.room_number}));
                      }}
                      className="absolute top-2 left-2 w-7 h-7 bg-blue-600 hover:bg-blue-700 text-white rounded-full flex items-center justify-center transition-all hover:scale-110 shadow-lg z-10"
                      title="Yeni Rezervasyon Oluştur"
                    >
                      <Plus className="w-4 h-4" />
                    </button>
                    
                    {roomBlock && (
                      <div className="absolute top-2 right-2 flex gap-1">
                        {roomBlock.type === 'out_of_order' && (
                          <span className="px-2 py-1 text-xs font-bold bg-red-600 text-white rounded">OUT OF ORDER</span>
                        )}
                        {roomBlock.type === 'out_of_service' && (
                          <span className="px-2 py-1 text-xs font-bold bg-orange-500 text-white rounded">OUT OF SERVICE</span>
                        )}
                        {roomBlock.type === 'maintenance' && (
                          <span className="px-2 py-1 text-xs font-bold bg-yellow-600 text-white rounded">MAINTENANCE</span>
                        )}
                      </div>
                    )}
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">Room {room.room_number}</CardTitle>
                      <Badge variant={room.status === 'occupied' ? 'default' : room.status === 'available' ? 'secondary' : 'outline'}>
                        {room.status}
                      </Badge>
                    </div>
                    <CardDescription className="capitalize text-xs">{room.room_type} • Floor {room.floor} • ${room.base_price}/night</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    
                    {/* Current Guest Information */}
                    {currentBooking && currentGuest && (
                      <div className="bg-blue-50 rounded-lg p-3 space-y-2 border border-blue-200">
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-semibold text-blue-900 flex items-center gap-1">
                            <User className="w-3 h-3" />
                            Current Guest
                          </span>
                          <Button 
                            size="sm" 
                            variant="ghost" 
                            className="h-6 px-2 text-xs"
                            onClick={() => {
                              setSelectedGuest(currentGuest);
                              setOpenDialog('guestinfo');
                            }}
                          >
                            View Profile
                          </Button>
                        </div>
                        <div className="space-y-1">
                          <div className="font-medium text-sm text-gray-900">{currentGuest.name || currentGuest.email}</div>
                          <div className="flex items-center gap-2 text-xs text-gray-600">
                            <LogIn className="w-3 h-3" />
                            Check-in: {new Date(currentBooking.check_in).toLocaleDateString()}
                          </div>
                          <div className="flex items-center gap-2 text-xs text-gray-600">
                            <LogOut className="w-3 h-3" />
                            Check-out: {new Date(currentBooking.check_out).toLocaleDateString()}
                          </div>
                        </div>
                        
                        {/* Quick Actions */}
                        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-blue-200">
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="h-8 text-xs"
                            onClick={async () => {
                              try {
                                const folioRes = await axios.get(`/folio/booking/${currentBooking.id}`);
                                if (folioRes.data && folioRes.data.length > 0) {
                                  setSelectedFolio(folioRes.data[0]);
                                  setOpenDialog('folio-view');
                                  toast.success('Folio açıldı');
                                } else {
                                  toast.error('Folio bulunamadı');
                                }
                              } catch (error) {
                                toast.error('Folio yüklenemedi');
                              }
                            }}
                          >
                            <FileText className="w-3 h-3 mr-1" />
                            Folio
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="h-8 text-xs"
                            onClick={() => {
                              setSelectedBooking(currentBooking);
                              setOpenDialog('payment');
                            }}
                          >
                            <DollarSign className="w-3 h-3 mr-1" />
                            Payment
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="h-8 text-xs"
                            onClick={async () => {
                              if (confirm('Check-out yapmak istediğinize emin misiniz?')) {
                                try {
                                  await axios.post(`/frontdesk/checkout/${currentBooking.id}`);
                                  toast.success('Check-out başarılı');
                                  loadData();
                                } catch (error) {
                                  toast.error(error.response?.data?.detail || 'Check-out başarısız');
                                }
                              }
                            }}
                          >
                            <LogOut className="w-3 h-3 mr-1" />
                            Check-out
                          </Button>
                          <Button 
                            size="sm" 
                            variant="outline" 
                            className="h-8 text-xs"
                            onClick={() => {
                              setSelectedGuest(currentGuest);
                              setOpenDialog('guestinfo');
                            }}
                          >
                            <User className="w-3 h-3 mr-1" />
                            Guest Info
                          </Button>
                        </div>
                      </div>
                    )}

                    {/* Room Status Controls */}
                    <div className="flex justify-between items-center pt-2">
                      <span className="text-xs text-gray-600">Room Status:</span>
                      <Select value={room.status} onValueChange={(v) => updateRoomStatus(room.id, v)}>
                        <SelectTrigger className="w-32 h-8 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="available">Available</SelectItem>
                          <SelectItem value="occupied">Occupied</SelectItem>
                          <SelectItem value="dirty">Dirty</SelectItem>
                          <SelectItem value="cleaning">Cleaning</SelectItem>
                          <SelectItem value="inspected">Inspected</SelectItem>
                          <SelectItem value="maintenance">Maintenance</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Room Block Info */}
                    {roomBlock && (
                      <div className="pt-2 border-t">
                        <div className="text-xs font-semibold text-red-600 mb-1">Blocked</div>
                        <div className="text-xs text-gray-600 mb-1">
                          Reason: {roomBlock.reason}
                        </div>
                        <div className="text-xs text-gray-500 mb-2">
                          {new Date(roomBlock.start_date).toLocaleDateString()} - {roomBlock.end_date ? new Date(roomBlock.end_date).toLocaleDateString() : 'Open-ended'}
                        </div>
                        <div className="flex gap-2">
                          <Button size="sm" variant="outline" className="h-7 text-xs" onClick={() => {
                            setSelectedRoom(room);
                            setOpenDialog('viewblocks');
                          }}>
                            View Blocks
                          </Button>
                          <Button size="sm" variant="destructive" className="h-7 text-xs" onClick={() => cancelRoomBlock(roomBlock.id)}>
                            End Block
                          </Button>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>
              )})}
            </div>
          </TabsContent>

          {/* GUESTS TAB */}
          <TabsContent value="guests" className="space-y-4">
            <div className="flex justify-between items-center gap-4">
              <h2 className="text-2xl font-semibold">Guests ({guests.length})</h2>
              <div className="flex gap-2 flex-1 max-w-md">
                <div className="relative flex-1">
                  <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <Input
                    placeholder="Search guests by name, email, phone..."
                    value={globalSearchQuery}
                    onChange={(e) => setGlobalSearchQuery(e.target.value)}
                    className="pl-10"
                  />
                </div>
                <Button onClick={() => setOpenDialog('guest')}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Guest
                </Button>
              </div>
            </div>
            
            {/* Guest Stats */}
            <div className="grid grid-cols-4 gap-4">
              <Card>
                <CardContent className="p-4">
                  <div className="text-xs text-gray-600">Total Guests</div>
                  <div className="text-2xl font-bold">{guests.length}</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-xs text-gray-600">VIP Guests</div>
                  <div className="text-2xl font-bold text-purple-600">
                    {guests.filter(g => g.loyalty_tier === 'vip').length}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-xs text-gray-600">Gold Members</div>
                  <div className="text-2xl font-bold text-yellow-600">
                    {guests.filter(g => g.loyalty_tier === 'gold').length}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-xs text-gray-600">Repeat Guests</div>
                  <div className="text-2xl font-bold text-green-600">
                    {guests.filter(g => (g.total_stays || 0) > 1).length}
                  </div>
                </CardContent>
              </Card>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {guests
                .filter(guest => {
                  if (!globalSearchQuery) return true;
                  const query = globalSearchQuery.toLowerCase();
                  return (
                    guest.name?.toLowerCase().includes(query) ||
                    guest.email?.toLowerCase().includes(query) ||
                    guest.phone?.toLowerCase().includes(query) ||
                    guest.id_number?.toLowerCase().includes(query)
                  );
                })
                .map((guest) => (
                <Card key={guest.id}>
                  <CardHeader>
                    <CardTitle className="flex justify-between items-center">
                      <span>{guest.name}</span>
                      {guest.loyalty_tier && guest.loyalty_tier !== 'standard' && (
                        <span className={`px-2 py-1 text-xs rounded ${
                          guest.loyalty_tier === 'vip' ? 'bg-purple-600 text-white' :
                          guest.loyalty_tier === 'gold' ? 'bg-yellow-500 text-white' :
                          guest.loyalty_tier === 'silver' ? 'bg-gray-400 text-white' :
                          'bg-blue-500 text-white'
                        }`}>
                          {guest.loyalty_tier?.toUpperCase()}
                        </span>
                      )}
                    </CardTitle>
                    <CardDescription>{guest.email}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Phone:</span>
                      <span className="font-medium">{guest.phone}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>ID:</span>
                      <span className="font-medium">{guest.id_number}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Loyalty Points:</span>
                      <span className="font-medium">{guest.loyalty_points}</span>
                    </div>
                    <Button 
                      className="w-full mt-3" 
                      variant="outline"
                      onClick={() => {
                        setSelectedGuest360(guest.id);
                        loadGuest360(guest.id);
                      }}
                    >
                      🌟 View 360° Profile
                    </Button>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* BOOKINGS TAB */}
          <TabsContent value="bookings" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold">Bookings ({bookingStats.total})</h2>
              <div className="flex gap-2">
                <Button variant="outline" onClick={() => setOpenDialog('findroom')}>
                  <Home className="w-4 h-4 mr-2" />
                  Find Available Rooms
                </Button>
                <Button onClick={() => setOpenDialog('booking')}>
                  <Plus className="w-4 h-4 mr-2" />
                  New Booking
                </Button>
              </div>
            </div>

            {/* Booking Stats */}
            <div className="grid grid-cols-5 gap-4">
              <Card>
                <CardContent className="p-4">
                  <div className="text-xs text-gray-600">Total Bookings</div>
                  <div className="text-2xl font-bold">{bookingStats.total}</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-xs text-gray-600">Confirmed</div>
                  <div className="text-2xl font-bold text-blue-600">
                    {bookingStats.confirmed}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-xs text-gray-600">Checked In</div>
                  <div className="text-2xl font-bold text-green-600">
                    {bookingStats.checkedIn}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-xs text-gray-600">Total Revenue</div>
                  <div className="text-2xl font-bold text-green-600">
                    ${bookingStats.totalRevenue.toFixed(0)}
                  </div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="p-4">
                  <div className="text-xs text-gray-600">Avg ADR</div>
                  <div className="text-2xl font-bold text-purple-600">
                    ${bookingStats.avgAdr.toFixed(0)}
                  </div>
                </CardContent>
              </Card>
            </div>

            <div className="space-y-4">
              <VirtualizedBookingList
                bookings={bookings}
                onSelectBooking={(booking) => {
                  setSelectedBookingDetail(booking);
                  setOpenDialog('bookingDetail');
                  toast.info('Opening booking details...');
                }}
                height={600}
              />
            </div>
          </TabsContent>

          {/* UPSELL CENTER TAB */}
          <TabsContent value="upsell" className="space-y-6">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-bold">🤖 AI Upsell Center</h2>
              <Button onClick={() => {
                const activeBooking = bookings.find(b => b.status === 'confirmed');
                if (activeBooking) {
                  generateUpsellOffers(activeBooking.id);
                } else {
                  toast.error('No active bookings to generate offers');
                }
              }}>
                Generate AI Offers
              </Button>
            </div>

            {/* Performance Dashboard */}
            <div className="grid grid-cols-4 gap-4">
              <Card>
                <CardContent className="pt-4 text-center">
                  <div className="text-3xl font-bold text-purple-600">{upsellOffers.length}</div>
                  <div className="text-sm text-gray-600">Active Offers</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4 text-center">
                  <div className="text-3xl font-bold text-green-600">
                    ${Math.round(upsellOffers.reduce((sum, o) => sum + o.price, 0))}
                  </div>
                  <div className="text-sm text-gray-600">Potential Revenue</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4 text-center">
                  <div className="text-3xl font-bold text-blue-600">
                    {upsellOffers.length > 0 ? Math.round((upsellOffers.reduce((sum, o) => sum + o.confidence, 0) / upsellOffers.length) * 100) : 0}%
                  </div>
                  <div className="text-sm text-gray-600">Avg Confidence</div>
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-4 text-center">
                  <div className="text-3xl font-bold text-orange-600">
                    ${Math.round(upsellOffers.reduce((sum, o) => sum + (o.price * o.confidence), 0))}
                  </div>
                  <div className="text-sm text-gray-600">Expected Revenue</div>
                </CardContent>
              </Card>
            </div>

            {/* AI Offers */}
            <div className="space-y-4">
              {upsellOffers.length === 0 ? (
                <Card>
                  <CardContent className="text-center py-12">
                    <div className="text-6xl mb-4">🤖</div>
                    <h3 className="text-xl font-semibold mb-2">No Active Upsell Offers</h3>
                    <p className="text-gray-600 mb-4">Generate AI-powered upsell recommendations for your guests</p>
                    <Button onClick={() => {
                      const activeBooking = bookings.find(b => b.status === 'confirmed');
                      if (activeBooking) {
                        generateUpsellOffers(activeBooking.id);
                      } else {
                        toast.error('No active bookings');
                      }
                    }}>
                      Generate Offers
                    </Button>
                  </CardContent>
                </Card>
              ) : (
                upsellOffers.map((offer) => (
                  <Card key={offer.id} className="border-2 border-purple-200">
                    <CardHeader>
                      <div className="flex justify-between items-start">
                        <div>
                          <CardTitle className="flex items-center gap-2">
                            {offer.type === 'room_upgrade' && '⬆️'}
                            {offer.type === 'early_checkin' && '⏰'}
                            {offer.type === 'late_checkout' && '🌅'}
                            {offer.type === 'airport_transfer' && '✈️'}
                            {offer.type.replace('_', ' ').split(' ').map(w => w.charAt(0).toUpperCase() + w.slice(1)).join(' ')}
                          </CardTitle>
                          <CardDescription className="mt-1">
                            {offer.current_item && (
                              <span>From: <span className="font-semibold">{offer.current_item}</span> → </span>
                            )}
                            <span className="font-semibold text-green-600">{offer.target_item}</span>
                          </CardDescription>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold text-purple-600">${offer.price}</div>
                          <div className="text-xs text-gray-500">per booking</div>
                        </div>
                      </div>
                    </CardHeader>
                    <CardContent className="space-y-3">
                      {/* Confidence Bar */}
                      <div>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="text-gray-600">AI Confidence</span>
                          <span className={`font-bold ${
                            offer.confidence >= 0.8 ? 'text-green-600' :
                            offer.confidence >= 0.6 ? 'text-yellow-600' :
                            'text-orange-600'
                          }`}>
                            {Math.round(offer.confidence * 100)}%
                          </span>
                        </div>
                        <div className="w-full h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div 
                            className={`h-full ${
                              offer.confidence >= 0.8 ? 'bg-green-500' :
                              offer.confidence >= 0.6 ? 'bg-yellow-500' :
                              'bg-orange-500'
                            }`}
                            style={{ width: `${offer.confidence * 100}%` }}
                          ></div>
                        </div>
                      </div>

                      {/* Reason */}
                      <div className="bg-blue-50 p-3 rounded text-sm">
                        <span className="font-semibold text-blue-700">💡 AI Insight:</span> {offer.reason}
                      </div>

                      {/* Actions */}
                      <div className="flex gap-2">
                        <Button className="flex-1 bg-green-600 hover:bg-green-700" onClick={() => {
                          toast.success('Upsell offer accepted! Sending to guest...');
                        }}>
                          ✅ Accept & Send
                        </Button>
                        <Button variant="outline" className="flex-1" onClick={() => {
                          setUpsellOffers(upsellOffers.filter(o => o.id !== offer.id));
                          toast.info('Offer declined');
                        }}>
                          ❌ Decline
                        </Button>
                      </div>

                      {/* Valid Until */}
                      <div className="text-xs text-gray-500 text-center">
                        Valid until: {new Date(offer.valid_until).toLocaleString()}
                      </div>
                    </CardContent>
                  </Card>
                ))
              )}
            </div>
          </TabsContent>

          {/* REPORTS TAB */}
          <TabsContent value="reports" className="space-y-6">
            <h2 className="text-2xl font-bold">Hotel Analytics & Reports</h2>
            
            {/* Visualization Charts */}
            <div className="grid grid-cols-2 gap-6">
              <Card>
                <CardContent className="pt-6">
                  <PickupPaceChart data={reports.pickupPace} />
                </CardContent>
              </Card>
              <Card>
                <CardContent className="pt-6">
                  <LeadTimeCurve data={reports.leadTime} />
                </CardContent>
              </Card>
            </div>

            {/* 30-Day Forecast */}
            {reports.forecast30 && (
              <Card>
                <CardContent className="pt-6">
                  <ForecastGraph data={reports.forecast30} />
                </CardContent>
              </Card>
            )}

            {/* Revenue Dashboard */}
            <div>
              <h3 className="text-xl font-bold mb-4">Revenue Analytics</h3>
              <RevenueDashboard />
            </div>

            {/* Group Reports */}
            <Card>
              <CardHeader>
                <CardTitle>Group Revenue by Company</CardTitle>
              </CardHeader>
              <CardContent>
                <GroupRevenueByCompany />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Pickup Pace Report</CardTitle>
              </CardHeader>
              <CardContent>
                <PickupPaceReport />
              </CardContent>
            </Card>


            {/* AI Activity Log */}
            <div>
              <h3 className="text-xl font-bold mb-4">AI Intelligence Activity</h3>
              <AIActivityLog />
            </div>
            
            {/* Show message if no reports loaded yet */}
            {!reports.daily && !reports.revenue && !reports.occupancy && (
              <Card>
                <CardContent className="py-12 text-center">
                  <FileText className="w-16 h-16 mx-auto text-gray-400 mb-4" />
                  <p className="text-gray-600 mb-2">Loading reports...</p>
                  <p className="text-sm text-gray-500">If reports don't load, please check console for errors</p>
                </CardContent>
              </Card>
            )}
            
            {/* Quick Stats */}
            {reports.daily && (
              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Occupancy Rate</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">{reports.daily.occupancy_rate}%</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">In-House</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">{reports.daily.inhouse}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Today's Arrivals</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">{reports.daily.arrivals}</div>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm">Daily Revenue</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="text-3xl font-bold">${reports.daily.daily_revenue}</div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Revenue Metrics */}
            {reports.revenue && (
              <Card>
                <CardHeader>
                  <CardTitle>Revenue Analysis (This Month)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                    <div>
                      <div className="text-sm text-gray-600">Total Revenue</div>
                      <div className="text-3xl font-bold text-blue-600">${reports.revenue.total_revenue}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">ADR (Average Daily Rate)</div>
                      <div className="text-3xl font-bold text-green-600">${reports.revenue.adr}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">RevPAR (Revenue Per Available Room)</div>
                      <div className="text-3xl font-bold text-purple-600">${reports.revenue.rev_par}</div>
                    </div>
                  </div>
                  
                  {reports.revenue.revenue_by_type && (
                    <div className="mt-6">
                      <div className="text-sm font-medium mb-2">Revenue Breakdown</div>
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                        {Object.entries(reports.revenue.revenue_by_type).map(([type, amount]) => (
                          <div key={type} className="text-sm">
                            <span className="capitalize text-gray-600">{type}:</span>
                            <span className="font-medium ml-2">${amount.toFixed(2)}</span>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Occupancy Report */}
            {reports.occupancy && (
              <Card>
                <CardHeader>
                  <CardTitle>Occupancy Report (This Month)</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div>
                      <div className="text-sm text-gray-600">Total Rooms</div>
                      <div className="text-2xl font-bold">{reports.occupancy.total_rooms}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Room Nights Available</div>
                      <div className="text-2xl font-bold">{reports.occupancy.total_room_nights}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Room Nights Sold</div>
                      <div className="text-2xl font-bold">{reports.occupancy.occupied_room_nights}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Occupancy Rate</div>
                      <div className="text-2xl font-bold text-blue-600">{reports.occupancy.occupancy_rate}%</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* 7-Day Forecast */}
            {reports.forecast.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>7-Day Forecast</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="space-y-2">
                    {reports.forecast.map((day) => (
                      <div key={day.date} className="flex justify-between items-center py-2 border-b">
                        <div>
                          <span className="font-medium">{new Date(day.date).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</span>
                          <span className="text-sm text-gray-600 ml-4">{day.bookings} bookings</span>
                        </div>
                        <div className="text-right">
                          <div className="text-lg font-bold">{day.occupancy_rate}%</div>
                          <div className="text-xs text-gray-500">occupancy</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {/* MANAGEMENT DASHBOARD */}
            <div className="border-t pt-6 mt-6">
              <h3 className="text-xl font-bold mb-4">📊 Management Dashboard</h3>
              
              {/* Daily Flash Report */}
              {reports.dailyFlash && (
                <Card className="mb-6 bg-gradient-to-r from-blue-50 to-purple-50">
                  <CardHeader>
                    <CardTitle className="flex items-center">
                      <span className="text-2xl mr-2">⚡</span>
                      Daily Flash Report - {new Date(reports.dailyFlash.date).toLocaleDateString()}
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                      {/* Occupancy */}
                      <div className="bg-white p-4 rounded-lg shadow">
                        <h4 className="font-semibold text-gray-700 mb-3">Occupancy</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-sm">Occupied:</span>
                            <span className="font-bold">{reports.dailyFlash.occupancy.occupied_rooms} / {reports.dailyFlash.occupancy.total_rooms}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm">Rate:</span>
                            <span className="font-bold text-blue-600">{reports.dailyFlash.occupancy.occupancy_rate}%</span>
                          </div>
                        </div>
                      </div>

                      {/* Movements */}
                      <div className="bg-white p-4 rounded-lg shadow">
                        <h4 className="font-semibold text-gray-700 mb-3">Movements</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-sm">Arrivals:</span>
                            <span className="font-bold text-green-600">{reports.dailyFlash.movements.arrivals}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm">Departures:</span>
                            <span className="font-bold text-red-600">{reports.dailyFlash.movements.departures}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm">Stayovers:</span>
                            <span className="font-bold">{reports.dailyFlash.movements.stayovers}</span>
                          </div>
                        </div>
                      </div>

                      {/* Revenue */}
                      <div className="bg-white p-4 rounded-lg shadow">
                        <h4 className="font-semibold text-gray-700 mb-3">Revenue</h4>
                        <div className="space-y-2">
                          <div className="flex justify-between">
                            <span className="text-sm">Room:</span>
                            <span className="font-bold">${reports.dailyFlash.revenue.room_revenue.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm">F&B:</span>
                            <span className="font-bold">${reports.dailyFlash.revenue.fb_revenue.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-sm">Other:</span>
                            <span className="font-bold">${reports.dailyFlash.revenue.other_revenue.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between border-t pt-2 mt-2">
                            <span className="text-sm font-semibold">Total:</span>
                            <span className="font-bold text-lg text-purple-600">${reports.dailyFlash.revenue.total_revenue.toFixed(2)}</span>
                          </div>
                          <div className="flex justify-between text-xs text-gray-600">
                            <span>ADR: ${reports.dailyFlash.revenue.adr.toFixed(2)}</span>
                            <span>RevPAR: ${reports.dailyFlash.revenue.rev_par.toFixed(2)}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Market Segment & Rate Type */}
              {reports.marketSegment && (
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6">
                  <Card>
                    <CardHeader>
                      <CardTitle>📈 Market Segment Performance</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {Object.entries(reports.marketSegment.market_segments || {}).map(([segment, data]) => (
                          <div key={segment} className="border-b pb-2">
                            <div className="flex justify-between items-center">
                              <span className="font-medium capitalize">{segment.replace('_', ' ')}</span>
                              <span className="text-sm text-gray-600">{data.bookings} bookings</span>
                            </div>
                            <div className="flex justify-between text-sm mt-1">
                              <span className="text-gray-600">{data.nights} nights</span>
                              <span className="font-semibold">${data.revenue.toFixed(2)} (ADR: ${data.adr.toFixed(2)})</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader>
                      <CardTitle>💰 Rate Type Performance</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-3">
                        {Object.entries(reports.marketSegment.rate_types || {}).map(([rateType, data]) => (
                          <div key={rateType} className="border-b pb-2">
                            <div className="flex justify-between items-center">
                              <span className="font-medium capitalize">{rateType.replace('_', ' ')}</span>
                              <span className="text-sm text-gray-600">{data.bookings} bookings</span>
                            </div>
                            <div className="flex justify-between text-sm mt-1">
                              <span className="text-gray-600">{data.nights} nights</span>
                              <span className="font-semibold">${data.revenue.toFixed(2)} (ADR: ${data.adr.toFixed(2)})</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Company Aging Report */}
              {reports.companyAging && (
                <Card className="mb-6">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>🏢 Company AR Aging Report</span>
                      <span className="text-lg font-bold text-red-600">Total AR: ${reports.companyAging.total_ar.toFixed(2)}</span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="overflow-x-auto">
                      <table className="w-full">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-4 py-2 text-left text-sm font-semibold">Company</th>
                            <th className="px-4 py-2 text-left text-sm font-semibold">Code</th>
                            <th className="px-4 py-2 text-right text-sm font-semibold">0-7 Days</th>
                            <th className="px-4 py-2 text-right text-sm font-semibold">8-14 Days</th>
                            <th className="px-4 py-2 text-right text-sm font-semibold">15-30 Days</th>
                            <th className="px-4 py-2 text-right text-sm font-semibold">30+ Days</th>
                            <th className="px-4 py-2 text-right text-sm font-semibold">Total</th>
                          </tr>
                        </thead>
                        <tbody>
                          {reports.companyAging.companies.slice(0, 10).map((company, idx) => (
                            <tr key={idx} className="border-b hover:bg-gray-50">
                              <td className="px-4 py-2 text-sm">{company.company_name}</td>
                              <td className="px-4 py-2 text-sm text-gray-600">{company.corporate_code}</td>
                              <td className="px-4 py-2 text-sm text-right">${company.aging['0-7 days'].toFixed(2)}</td>
                              <td className="px-4 py-2 text-sm text-right">${company.aging['8-14 days'].toFixed(2)}</td>
                              <td className="px-4 py-2 text-sm text-right text-yellow-600">${company.aging['15-30 days'].toFixed(2)}</td>
                              <td className="px-4 py-2 text-sm text-right text-red-600">${company.aging['30+ days'].toFixed(2)}</td>
                              <td className="px-4 py-2 text-sm text-right font-bold">${company.total_balance.toFixed(2)}</td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {reports.companyAging.companies.length > 10 && (
                        <div className="text-center text-sm text-gray-500 mt-3">
                          Showing top 10 of {reports.companyAging.company_count} companies
                        </div>
                      )}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Housekeeping Efficiency */}
              {reports.hkEfficiency && (
                <Card>
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>🧹 Housekeeping Efficiency</span>
                      <span className="text-sm text-gray-600">
                        {reports.hkEfficiency.total_tasks_completed} tasks in {reports.hkEfficiency.date_range_days} days
                      </span>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="mb-4 p-3 bg-blue-50 rounded">
                      <div className="text-center">
                        <div className="text-sm text-gray-600">Average Tasks Per Day (All Staff)</div>
                        <div className="text-2xl font-bold text-blue-600">{reports.hkEfficiency.daily_average_all_staff}</div>
                      </div>
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {Object.entries(reports.hkEfficiency.staff_performance || {}).map(([staff, data]) => (
                        <div key={staff} className="border rounded p-3">
                          <div className="font-semibold">{staff}</div>
                          <div className="text-sm text-gray-600 mt-1">Tasks: {data.tasks_completed}</div>
                          <div className="text-sm text-gray-600">Daily Avg: {data.daily_average}</div>
                          <div className="text-xs text-gray-500 mt-2">
                            {Object.entries(data.by_type).map(([type, count]) => (
                              <span key={type} className="mr-2">{type}: {count}</span>
                            ))}
                          </div>
                        </div>
                      ))}
                    </div>
                  </CardContent>
                </Card>
              )}

              {/* Audit Logs */}
              <Card className="mt-6">
                <CardHeader>
                  <CardTitle className="flex items-center justify-between">
                    <span>📋 Audit Trail</span>
                    <Button variant="outline" size="sm" onClick={loadAuditLogs}>
                      Refresh
                    </Button>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  {auditLogs.length === 0 ? (
                    <div className="text-center text-gray-400 py-8">
                      No audit logs available or insufficient permissions
                    </div>
                  ) : (
                    <div className="overflow-x-auto">
                      <table className="w-full text-sm">
                        <thead className="bg-gray-50">
                          <tr>
                            <th className="px-3 py-2 text-left font-semibold">Timestamp</th>
                            <th className="px-3 py-2 text-left font-semibold">User</th>
                            <th className="px-3 py-2 text-left font-semibold">Role</th>
                            <th className="px-3 py-2 text-left font-semibold">Action</th>
                            <th className="px-3 py-2 text-left font-semibold">Entity</th>
                            <th className="px-3 py-2 text-left font-semibold">Changes</th>
                          </tr>
                        </thead>
                        <tbody>
                          {auditLogs.slice(0, 20).map((log, idx) => (
                            <tr key={idx} className="border-b hover:bg-gray-50">
                              <td className="px-3 py-2 text-xs text-gray-600">
                                {new Date(log.timestamp).toLocaleString()}
                              </td>
                              <td className="px-3 py-2">{log.user_name}</td>
                              <td className="px-3 py-2">
                                <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                                  {log.user_role}
                                </span>
                              </td>
                              <td className="px-3 py-2 font-semibold">{log.action}</td>
                              <td className="px-3 py-2 text-gray-600">{log.entity_type}</td>
                              <td className="px-3 py-2 text-xs text-gray-500">
                                {log.changes ? JSON.stringify(log.changes).substring(0, 50) + '...' : '-'}
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                      {auditLogs.length > 20 && (
                        <div className="text-center text-sm text-gray-500 mt-3">
                          Showing 20 of {auditLogs.length} logs
                        </div>
                      )}
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* CHANNEL MANAGER & RMS */}
              <div className="border-t pt-6 mt-6">
                <h3 className="text-xl font-bold mb-4">🌐 Channel Manager & Revenue Management</h3>
                
                {/* OTA Reservations */}
                <Card className="mb-6">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>📥 OTA Reservations (Pending Import)</span>
                      <Button variant="outline" size="sm" onClick={loadChannelManagerData}>
                        Refresh
                      </Button>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {otaReservations.length === 0 ? (
                      <div className="text-center text-gray-400 py-8">
                        No pending OTA reservations
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {otaReservations.slice(0, 10).map((ota) => (
                          <Card key={ota.id} className="bg-blue-50 border-blue-200">
                            <CardContent className="p-4">
                              <div className="flex justify-between items-start">
                                <div className="flex-1">
                                  <div className="flex items-center gap-2">
                                    <span className="font-bold">{ota.guest_name}</span>
                                    <span className="px-2 py-0.5 bg-blue-600 text-white rounded text-xs">
                                      {ota.channel_type.replace('_', '.')}
                                    </span>
                                  </div>
                                  <div className="text-sm text-gray-600 mt-1">
                                    {ota.room_type} • {ota.adults} adults {ota.children > 0 && `+ ${ota.children} children`}
                                  </div>
                                  <div className="text-sm text-gray-500">
                                    {new Date(ota.check_in).toLocaleDateString()} - {new Date(ota.check_out).toLocaleDateString()}
                                  </div>
                                  <div className="text-sm font-semibold text-green-600 mt-1">
                                    ${ota.total_amount.toFixed(2)}
                                    {ota.commission_amount && <span className="text-gray-500 ml-2">(Commission: ${ota.commission_amount.toFixed(2)})</span>}
                                  </div>
                                  <div className="text-xs text-gray-400 mt-1">
                                    Booking ID: {ota.channel_booking_id}
                                  </div>
                                </div>
                                <Button 
                                  size="sm" 
                                  onClick={() => handleImportOTA(ota.id)}
                                  className="ml-4"
                                >
                                  Import to PMS
                                </Button>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                        {otaReservations.length > 10 && (
                          <div className="text-center text-sm text-gray-500">
                            Showing 10 of {otaReservations.length} reservations
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* RMS Suggestions */}
                <Card className="mb-6">
                  <CardHeader>
                    <CardTitle className="flex items-center justify-between">
                      <span>💡 Revenue Management Suggestions</span>
                      <Button variant="outline" size="sm" onClick={handleGenerateRMSSuggestions}>
                        Generate Suggestions
                      </Button>
                    </CardTitle>
                  </CardHeader>
                  <CardContent>
                    {rmsSuggestions.length === 0 ? (
                      <div className="text-center text-gray-400 py-8">
                        No pending rate suggestions
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {rmsSuggestions.slice(0, 15).map((suggestion) => (
                          <Card key={suggestion.id} className={`${
                            suggestion.suggested_rate > suggestion.current_rate 
                              ? 'bg-green-50 border-green-200' 
                              : 'bg-orange-50 border-orange-200'
                          }`}>
                            <CardContent className="p-4">
                              <div className="flex justify-between items-start">
                                <div className="flex-1">
                                  <div className="flex items-center gap-3">
                                    <span className="font-bold">{suggestion.room_type}</span>
                                    <span className="text-sm text-gray-600">
                                      {new Date(suggestion.date).toLocaleDateString()}
                                    </span>
                                  </div>
                                  <div className="mt-2 flex items-center gap-4">
                                    <div>
                                      <div className="text-xs text-gray-500">Current Rate</div>
                                      <div className="font-semibold">${suggestion.current_rate.toFixed(2)}</div>
                                    </div>
                                    <div className="text-2xl">→</div>
                                    <div>
                                      <div className="text-xs text-gray-500">Suggested Rate</div>
                                      <div className={`font-bold text-lg ${
                                        suggestion.suggested_rate > suggestion.current_rate 
                                          ? 'text-green-600' 
                                          : 'text-orange-600'
                                      }`}>
                                        ${suggestion.suggested_rate.toFixed(2)}
                                        <span className="text-sm ml-2">
                                          ({suggestion.suggested_rate > suggestion.current_rate ? '+' : ''}
                                          {((suggestion.suggested_rate - suggestion.current_rate) / suggestion.current_rate * 100).toFixed(0)}%)
                                        </span>
                                      </div>
                                    </div>
                                  </div>
                                  <div className="text-sm text-gray-600 mt-2">
                                    {suggestion.reason}
                                  </div>
                                  <div className="text-xs text-gray-500 mt-1">
                                    Confidence: {suggestion.confidence_score}% • 
                                    Occupancy: {suggestion.based_on?.occupancy_rate}%
                                  </div>
                                </div>
                                <Button 
                                  size="sm" 
                                  onClick={() => handleApplyRMSSuggestion(suggestion.id)}
                                  className="ml-4"
                                  variant={suggestion.suggested_rate > suggestion.current_rate ? "default" : "outline"}
                                >
                                  Apply
                                </Button>
                              </div>
                            </CardContent>
                          </Card>
                        ))}
                        {rmsSuggestions.length > 15 && (
                          <div className="text-center text-sm text-gray-500">
                            Showing 15 of {rmsSuggestions.length} suggestions
                          </div>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Exception Queue */}
                {exceptions.length > 0 && (
                  <Card>
                    <CardHeader>
                      <CardTitle>⚠️ Exception Queue ({exceptions.length})</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="space-y-2">
                        {exceptions.slice(0, 5).map((exc) => (
                          <div key={exc.id} className="border-l-4 border-red-400 bg-red-50 p-3 rounded">
                            <div className="flex justify-between items-start">
                              <div>
                                <div className="font-semibold text-red-700">{exc.exception_type.replace('_', ' ').toUpperCase()}</div>
                                <div className="text-sm text-gray-700 mt-1">{exc.error_message}</div>
                                <div className="text-xs text-gray-500 mt-1">
                                  {exc.channel_type} • {new Date(exc.created_at).toLocaleString()}
                                </div>
                              </div>
                            </div>
                          </div>
                        ))}
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            </div>
          </TabsContent>

          {/* MESSAGING CENTER TAB */}
          <TabsContent value="messaging" className="space-y-6">
            <h2 className="text-2xl font-bold">💬 Messaging Center</h2>
            
            <div className="grid grid-cols-3 gap-6">
              {/* Message Composer */}
              <div className="col-span-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Compose Message</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {/* Channel Selector */}
                    <div>
                      <Label>Channel</Label>
                      <Select value={newMessage.channel} onValueChange={(v) => setNewMessage({...newMessage, channel: v})}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="email">📧 Email</SelectItem>
                          <SelectItem value="sms">📱 SMS</SelectItem>
                          <SelectItem value="whatsapp">💬 WhatsApp</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>

                    {/* Recipient */}
                    <div>
                      <Label>Recipient {newMessage.channel === 'email' ? '(Email)' : '(Phone)'}</Label>
                      <Input 
                        value={newMessage.recipient}
                        onChange={(e) => setNewMessage({...newMessage, recipient: e.target.value})}
                        placeholder={newMessage.channel === 'email' ? 'guest@example.com' : '+1234567890'}
                      />
                    </div>

                    {/* Subject (Email only) */}
                    {newMessage.channel === 'email' && (
                      <div>
                        <Label>Subject</Label>
                        <Input 
                          value={newMessage.subject}
                          onChange={(e) => setNewMessage({...newMessage, subject: e.target.value})}
                          placeholder="Welcome to our hotel!"
                        />
                      </div>
                    )}

                    {/* Message Body */}
                    <div>
                      <Label>Message</Label>
                      <Textarea 
                        value={newMessage.body}
                        onChange={(e) => setNewMessage({...newMessage, body: e.target.value})}
                        rows={8}
                        placeholder="Dear guest, we're excited to welcome you..."
                      />
                    </div>

                    {/* Send Button */}
                    <Button className="w-full" onClick={sendMessage}>
                      Send Message
                    </Button>
                  </CardContent>
                </Card>
              </div>

              {/* Templates & History */}
              <div className="space-y-4">
                {/* Quick Templates */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Quick Templates</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <Button 
                        variant="outline" 
                        className="w-full justify-start"
                        onClick={() => setNewMessage({
                          ...newMessage,
                          subject: 'Welcome to Our Hotel',
                          body: 'Dear Guest,\n\nWe are thrilled to welcome you! Your room will be ready for check-in at 3:00 PM.\n\nBest regards,\nHotel Team'
                        })}
                      >
                        📧 Welcome Email
                      </Button>
                      <Button 
                        variant="outline" 
                        className="w-full justify-start"
                        onClick={() => setNewMessage({
                          ...newMessage,
                          subject: 'Special Upgrade Offer',
                          body: 'Hello! We have a special room upgrade offer for you at just $45. Would you like to upgrade to a Deluxe room?'
                        })}
                      >
                        ⬆️ Upgrade Offer
                      </Button>
                      <Button 
                        variant="outline" 
                        className="w-full justify-start"
                        onClick={() => setNewMessage({
                          ...newMessage,
                          subject: 'Thank You',
                          body: 'Thank you for choosing our hotel! We hope you enjoyed your stay. We would love to hear your feedback.'
                        })}
                      >
                        🙏 Thank You
                      </Button>
                    </div>
                  </CardContent>
                </Card>

                {/* Sent Messages */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Recent Messages ({sentMessages.length})</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2 max-h-64 overflow-y-auto">
                      {sentMessages.length === 0 ? (
                        <div className="text-center text-gray-400 py-4 text-sm">
                          No messages sent yet
                        </div>
                      ) : (
                        sentMessages.map((msg, idx) => (
                          <div key={idx} className="p-2 bg-gray-50 rounded text-xs">
                            <div className="font-semibold flex justify-between">
                              <span>{msg.recipient}</span>
                              <span className="text-green-600">✓ Sent</span>
                            </div>
                            <div className="text-gray-600 mt-1 truncate">{msg.body || msg.subject}</div>
                          </div>
                        ))
                      )}
                    </div>
                  </CardContent>
                </Card>
              </div>
            </div>
          </TabsContent>

          {/* STAFF TASK MANAGER TAB */}
          <TabsContent value="tasks" className="space-y-6">
            <StaffTaskManager />
          </TabsContent>

          {/* FEEDBACK SYSTEM TAB */}
          <TabsContent value="feedback" className="space-y-6">
            <FeedbackSystem />
          </TabsContent>

          {/* ALLOTMENT GRID TAB */}
          <TabsContent value="allotment" className="space-y-6">
            <AllotmentGrid />
          </TabsContent>

          {/* POS INTEGRATION TAB */}
          <TabsContent value="pos" className="space-y-6">
            <div>
              <h3 className="text-2xl font-bold mb-4">POS Integration</h3>
              <div className="grid grid-cols-2 gap-6">
                <Card>
                  <CardHeader>
                    <CardTitle>Restaurant Charges</CardTitle>
                    <CardDescription>Post restaurant bills to guest folios</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-4">
                      <div className="flex justify-between items-center p-4 bg-gray-50 rounded">
                        <div>
                          <div className="font-semibold">Table 5 - Room 201</div>
                          <div className="text-sm text-gray-600">2 guests, $85.50</div>
                        </div>
                        <Button size="sm" onClick={() => toast.success('Charged to room folio')}>
                          Post to Folio
                        </Button>
                      </div>
                      <div className="flex justify-between items-center p-4 bg-gray-50 rounded">
                        <div>
                          <div className="font-semibold">Bar Tab - Room 305</div>
                          <div className="text-sm text-gray-600">$42.00</div>
                        </div>
                        <Button size="sm" onClick={() => toast.success('Charged to room folio')}>
                          Post to Folio
                        </Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>POS Settings</CardTitle>
                    <CardDescription>Configure POS integration</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3 text-sm">
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">POS System:</span>
                        <span className="font-semibold">Micros</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Auto-post:</span>
                        <span className="font-semibold text-green-600">Enabled</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Service Charge:</span>
                        <span className="font-semibold">10%</span>
                      </div>
                      <div className="flex justify-between items-center">
                        <span className="text-gray-600">Tax:</span>
                        <span className="font-semibold">8%</span>
                      </div>
                      <Button variant="outline" className="w-full mt-4">
                        Configure Settings
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              </div>

              <Card className="mt-6">
                <CardHeader>
                  <CardTitle>Today's F&B Revenue</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-4 gap-4">
                    <div className="text-center">
                      <div className="text-3xl font-bold text-green-600">$2,450</div>
                      <div className="text-sm text-gray-600">Restaurant</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-blue-600">$1,280</div>
                      <div className="text-sm text-gray-600">Bar</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-purple-600">$580</div>
                      <div className="text-sm text-gray-600">Room Service</div>
                    </div>
                    <div className="text-center">
                      <div className="text-3xl font-bold text-orange-600">$4,310</div>
                      <div className="text-sm text-gray-600">Total F&B</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* Folio Dialog */}
        <Dialog open={openDialog === 'folio'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent className="max-w-4xl max-h-[80vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Guest Folio</DialogTitle>
            </DialogHeader>
            {folio && (
              <div className="space-y-6">
                {/* Charges */}
                <div>
                  <h3 className="font-semibold mb-2">Charges</h3>
                  <div className="space-y-2">
                    {folio.charges.map((charge, idx) => (
                      <div key={idx} className="flex justify-between text-sm border-b pb-2">
                        <div>
                          <div className="font-medium">{charge.description}</div>
                          <div className="text-xs text-gray-500 capitalize">{charge.charge_type}</div>
                        </div>
                        <div className="text-right">
                          <div>${charge.total.toFixed(2)}</div>
                          <div className="text-xs text-gray-500">{charge.quantity} × ${charge.amount}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                  
                  {/* Add Charge Form */}
                  <form onSubmit={handleAddCharge} className="mt-4 p-4 bg-gray-50 rounded">
                    <div className="grid grid-cols-2 gap-4">
                      <Select value={newCharge.charge_type} onValueChange={(v) => setNewCharge({...newCharge, charge_type: v})}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="food">Food & Beverage</SelectItem>
                          <SelectItem value="laundry">Laundry</SelectItem>
                          <SelectItem value="minibar">Minibar</SelectItem>
                          <SelectItem value="spa">Spa</SelectItem>
                          <SelectItem value="phone">Phone</SelectItem>
                          <SelectItem value="other">Other</SelectItem>
                        </SelectContent>
                      </Select>
                      <Input
                        placeholder="Description"
                        value={newCharge.description}
                        onChange={(e) => setNewCharge({...newCharge, description: e.target.value})}
                        required
                      />
                      <Input
                        type="number"
                        step="0.01"
                        placeholder="Amount"
                        value={newCharge.amount}
                        onChange={(e) => setNewCharge({...newCharge, amount: parseFloat(e.target.value)})}
                        required
                      />
                      <Button type="submit">Add Charge</Button>
                    </div>
                  </form>
                </div>

                {/* Payments */}
                <div>
                  <h3 className="font-semibold mb-2">Payments</h3>
                  <div className="space-y-2">
                    {folio.payments.map((payment, idx) => (
                      <div key={idx} className="flex justify-between text-sm border-b pb-2">
                        <div>
                          <div className="font-medium capitalize">{payment.method}</div>
                          {payment.reference && <div className="text-xs text-gray-500">Ref: {payment.reference}</div>}
                        </div>
                        <div className="text-green-600 font-medium">${payment.amount.toFixed(2)}</div>
                      </div>
                    ))}
                  </div>
                  
                  {/* Add Payment Form */}
                  <form onSubmit={handleProcessPayment} className="mt-4 p-4 bg-gray-50 rounded">
                    <div className="grid grid-cols-2 gap-4">
                      <Input
                        type="number"
                        step="0.01"
                        placeholder="Amount"
                        value={newPayment.amount}
                        onChange={(e) => setNewPayment({...newPayment, amount: parseFloat(e.target.value)})}
                        required
                      />
                      <Select value={newPayment.method} onValueChange={(v) => setNewPayment({...newPayment, method: v})}>
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="cash">Cash</SelectItem>
                          <SelectItem value="card">Card</SelectItem>
                          <SelectItem value="bank_transfer">Bank Transfer</SelectItem>
                          <SelectItem value="online">Online</SelectItem>
                        </SelectContent>
                      </Select>
                      <Input
                        placeholder="Reference (optional)"
                        value={newPayment.reference}
                        onChange={(e) => setNewPayment({...newPayment, reference: e.target.value})}
                      />
                      <Button type="submit">Process Payment</Button>
                    </div>
                  </form>
                </div>

                {/* Summary */}
                <div className="border-t pt-4">
                  <div className="flex justify-between text-lg font-bold">
                    <span>Total Charges:</span>
                    <span>${folio.total_charges.toFixed(2)}</span>
                  </div>
                  <div className="flex justify-between text-lg font-bold text-green-600">
                    <span>Total Paid:</span>
                    <span>${folio.total_paid.toFixed(2)}</span>
                  </div>
                  <div className={`flex justify-between text-2xl font-bold ${folio.balance > 0 ? 'text-red-600' : 'text-gray-600'}`}>
                    <span>Balance:</span>
                    <span>${folio.balance.toFixed(2)}</span>
                  </div>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Room Dialog */}
        <Dialog open={openDialog === 'room'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Room</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateRoom} className="space-y-4">
              <div>
                <Label>Room Number</Label>
                <Input value={newRoom.room_number} onChange={(e) => setNewRoom({...newRoom, room_number: e.target.value})} required />
              </div>
              <div>
                <Label>Room Type</Label>
                <Select value={newRoom.room_type} onValueChange={(v) => setNewRoom({...newRoom, room_type: v})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="standard">Standard</SelectItem>
                    <SelectItem value="deluxe">Deluxe</SelectItem>
                    <SelectItem value="suite">Suite</SelectItem>
                    <SelectItem value="presidential">Presidential</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Floor</Label>
                  <Input type="number" value={newRoom.floor} onChange={(e) => setNewRoom({...newRoom, floor: parseInt(e.target.value)})} required />
                </div>
                <div>
                  <Label>Capacity</Label>
                  <Input type="number" value={newRoom.capacity} onChange={(e) => setNewRoom({...newRoom, capacity: parseInt(e.target.value)})} required />
                </div>
              </div>
              <div>
                <Label>Base Price</Label>
                <Input type="number" step="0.01" value={newRoom.base_price} onChange={(e) => setNewRoom({...newRoom, base_price: parseFloat(e.target.value)})} required />
              </div>
              <Button type="submit" className="w-full">Create Room</Button>
            </form>
          </DialogContent>
        </Dialog>

        {/* Guest Dialog */}
        <Dialog open={openDialog === 'guest'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Register New Guest</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateGuest} className="space-y-4">
              <div>
                <Label>Name</Label>
                <Input value={newGuest.name} onChange={(e) => setNewGuest({...newGuest, name: e.target.value})} required />
              </div>
              <div>
                <Label>Email</Label>
                <Input type="email" value={newGuest.email} onChange={(e) => setNewGuest({...newGuest, email: e.target.value})} required />
              </div>
              <div>
                <Label>Phone</Label>
                <Input value={newGuest.phone} onChange={(e) => setNewGuest({...newGuest, phone: e.target.value})} required />
              </div>
              <div>
                <Label>ID Number</Label>
                <Input value={newGuest.id_number} onChange={(e) => setNewGuest({...newGuest, id_number: e.target.value})} required />
              </div>
              <div>
                <Label>Address</Label>
                <Input value={newGuest.address} onChange={(e) => setNewGuest({...newGuest, address: e.target.value})} />
              </div>
              <Button type="submit" className="w-full">Register Guest</Button>
            </form>
          </DialogContent>
        </Dialog>

        {/* Booking Dialog */}
        <Dialog open={openDialog === 'booking'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Create New Booking</DialogTitle>
              <DialogDescription>Fill in the booking details below</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateBooking} className="space-y-6">
              {/* Guest selection */}
              <div className="grid grid-cols-2 gap-4 items-end">
                <div>
                  <Label>Guest *</Label>
                  <Select value={newBooking.guest_id} onValueChange={(v) => setNewBooking({...newBooking, guest_id: v})}>
                    <SelectTrigger><SelectValue placeholder="Select guest" /></SelectTrigger>
                    <SelectContent>
                      {guests.map(g => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex justify-end">
                  <Button
                    type="button"
                    variant="outline"
                    size="sm"
                    onClick={() => setOpenDialog('guest')}
                  >
                    Register New Guest
                  </Button>
                </div>
              </div>

              {/* Multi-room rooms list */}
              <div className="mt-4 border rounded-lg p-4 space-y-4 bg-slate-50">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="font-semibold text-sm">Rooms in this Booking</h3>
                    <p className="text-xs text-slate-500">You can add multiple rooms under one reservation (family, small group, etc.).</p>
                  </div>
                  <Button type="button" variant="outline" size="sm" onClick={addRoomToMultiBooking}>
                    <Plus className="w-4 h-4 mr-1" /> Add Room
                  </Button>
                </div>

                <div className="space-y-3">
                  {multiRoomBooking.map((room, index) => (
                    <div key={index} className="border rounded-md bg-white p-3 space-y-3">
                      <div className="flex items-center justify-between">
                        <div className="font-medium text-sm">Room #{index + 1}</div>
                        {multiRoomBooking.length > 1 && (
                          <Button
                            type="button"
                            variant="ghost"
                            size="sm"
                            className="text-red-500 hover:text-red-700 hover:bg-red-50"
                            onClick={() => removeRoomFromMultiBooking(index)}
                          >
                            Remove
                          </Button>
                        )}
                      </div>

                      <div className="grid grid-cols-3 gap-3">
                        <div>
                          <Label className="text-xs">Room *</Label>
                          <Select
                            value={room.room_id}
                            onValueChange={(v) => updateMultiRoomField(index, 'room_id', v)}
                          >
                            <SelectTrigger><SelectValue placeholder="Select room" /></SelectTrigger>
                            <SelectContent>
                              {rooms.filter(r => r.status === 'available').map(r => (
                                <SelectItem key={r.id} value={r.id}>
                                  Room {r.room_number} - {r.room_type}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-xs">Adults</Label>
                          <Input
                            type="number"
                            min="1"
                            value={room.adults}
                            onChange={(e) => updateMultiRoomField(index, 'adults', e.target.value)}
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Children</Label>
                          <Input
                            type="number"
                            min="0"
                            value={room.children}
                            onChange={(e) => updateMultiRoomChildrenAges(index, e.target.value)}
                          />
                        </div>
                      </div>

                      {room.children > 0 && (
                        <div>
                          <Label className="text-xs">Children Ages</Label>
                          <div className="grid grid-cols-4 gap-2 mt-1">
                            {Array.from({ length: room.children }).map((_, ageIndex) => (
                              <Input
                                key={ageIndex}
                                type="number"
                                min="0"
                                max="17"
                                placeholder={`Child ${ageIndex + 1}`}
                                value={room.children_ages?.[ageIndex] ?? ''}
                                onChange={(e) => updateMultiRoomChildAge(index, ageIndex, e.target.value)}
                              />
                            ))}
                          </div>
                        </div>
                      )}

                      <div className="grid grid-cols-2 gap-3 pt-2 border-t mt-2">
                        <div>
                          <Label className="text-xs">Rate Plan</Label>
                          <Select
                            value={room.rate_plan || ''}
                            onValueChange={(v) => {
                              // Set rate plan and suggest base rate from selected plan
                              const selected = ratePlans.find(rp => rp.code === v || rp.id === v);
                              updateMultiRoomField(index, 'rate_plan', v);
                              if (selected && selected.base_price) {
                                updateMultiRoomField(index, 'base_rate', selected.base_price);
                                if (!room.total_amount || room.total_amount === 0) {
                                  updateMultiRoomField(index, 'total_amount', selected.base_price);
                                }
                              }
                            }}
                          >
                            <SelectTrigger><SelectValue placeholder="Select rate plan" /></SelectTrigger>
                            <SelectContent>
                              {ratePlans.map(rp => (
                                <SelectItem key={rp.id} value={rp.code || rp.id}>
                                  {rp.name} ({rp.code}) - {rp.currency} {rp.base_price}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                        <div>
                          <Label className="text-xs">Package</Label>
                          <Select
                            value={room.package_code || ''}
                            onValueChange={(v) => updateMultiRoomField(index, 'package_code', v)}
                          >
                            <SelectTrigger><SelectValue placeholder="No package" /></SelectTrigger>
                            <SelectContent>
                              {packages.map(pkg => (
                                <SelectItem key={pkg.id} value={pkg.code}>
                                  {pkg.name} ({pkg.code})
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>
                      </div>

                      <div className="grid grid-cols-2 gap-3 pt-2">
                        <div>
                          <Label className="text-xs">Base Rate</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={room.base_rate === 0 ? '' : room.base_rate}
                            onChange={(e) => updateMultiRoomField(index, 'base_rate', e.target.value)}
                          />
                        </div>
                        <div>
                          <Label className="text-xs">Total Amount *</Label>
                          <Input
                            type="number"
                            step="0.01"
                            value={room.total_amount === 0 ? '' : room.total_amount}
                            onChange={(e) => updateMultiRoomField(index, 'total_amount', e.target.value)}
                          />
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Check-in and Check-out */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Check-in *</Label>
                  <Input type="date" value={newBooking.check_in} onChange={(e) => setNewBooking({...newBooking, check_in: e.target.value})} required />
                </div>
                <div>
                  <Label>Check-out *</Label>
                  <Input type="date" value={newBooking.check_out} onChange={(e) => setNewBooking({...newBooking, check_out: e.target.value})} required />
                </div>
              </div>

              {/* Adults and Children for summary (kept for compatibility but hidden) */}
              <div className="hidden">
                <Input 
                  type="number" 
                  min="1" 
                  value={newBooking.adults} 
                  onChange={(e) => {
                    const adults = parseInt(e.target.value) || 1;
                    setNewBooking({...newBooking, adults, guests_count: adults + newBooking.children});
                  }} 
                />
                <Input 
                  type="number" 
                  min="0" 
                  value={newBooking.children} 
                  onChange={(e) => handleChildrenChange(e.target.value)} 
                />
              </div>

              {/* Children Ages - Show only if children > 0 */}
              {newBooking.children > 0 && (
                <div>
                  <Label>Children Ages</Label>
                  <div className="grid grid-cols-4 gap-2 mt-2">
                    {Array.from({ length: newBooking.children }).map((_, index) => (
                      <Input
                        key={index}
                        type="number"
                        min="0"
                        max="17"
                        placeholder={`Child ${index + 1} age`}
                        value={newBooking.children_ages[index] || ''}
                        onChange={(e) => handleChildAgeChange(index, e.target.value)}
                      />
                    ))}
                  </div>
                </div>
              )}

              {/* Company Selection */}
              <div>
                <div className="flex justify-between items-center mb-2">
                  <Label>Company (Optional)</Label>
                  <Button 
                    type="button" 
                    variant="outline" 
                    size="sm" 
                    onClick={() => setOpenDialog('company')}
                  >
                    <Plus className="w-4 h-4 mr-1" />
                    New Company
                  </Button>
                </div>
                <Select value={newBooking.company_id || "none"} onValueChange={handleCompanySelect}>
                  <SelectTrigger><SelectValue placeholder="Select company (optional)" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">None</SelectItem>
                    {companies.filter(c => c.status === 'active').map(c => (
                      <SelectItem key={c.id} value={c.id}>{c.name} - {c.corporate_code}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>

              {/* Contracted Rate */}
              {newBooking.company_id && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Contracted Rate</Label>
                    <Select value={newBooking.contracted_rate} onValueChange={handleContractedRateSelect}>
                      <SelectTrigger><SelectValue placeholder="Select rate" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="corp_std">Standard Corporate</SelectItem>
                        <SelectItem value="corp_pref">Preferred Corporate</SelectItem>
                        <SelectItem value="gov">Government Rate</SelectItem>
                        <SelectItem value="ta">Travel Agent Rate</SelectItem>
                        <SelectItem value="crew">Airline Crew Rate</SelectItem>
                        <SelectItem value="mice">Event/Conference Rate</SelectItem>
                        <SelectItem value="lts">Long Stay/Project Rate</SelectItem>
                        <SelectItem value="tou">Tour Operator Rate</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Rate Type</Label>
                    <Select value={newBooking.rate_type} onValueChange={(v) => setNewBooking({...newBooking, rate_type: v})}>
                      <SelectTrigger><SelectValue placeholder="Select type" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="bar">BAR / Rack Rate</SelectItem>
                        <SelectItem value="corporate">Corporate Rate</SelectItem>
                        <SelectItem value="government">Government Rate</SelectItem>
                        <SelectItem value="wholesale">Wholesale Rate</SelectItem>
                        <SelectItem value="package">Package Rate</SelectItem>
                        <SelectItem value="promotional">Promotional Rate</SelectItem>
                        <SelectItem value="non_refundable">Non-Refundable</SelectItem>
                        <SelectItem value="long_stay">Long Stay Rate</SelectItem>
                        <SelectItem value="day_use">Day Use Rate</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}

              {/* Market Segment and Cancellation Policy */}
              {newBooking.company_id && (
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Market Segment</Label>
                    <Select value={newBooking.market_segment} onValueChange={(v) => setNewBooking({...newBooking, market_segment: v})}>
                      <SelectTrigger><SelectValue placeholder="Select segment" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="corporate">Corporate</SelectItem>
                        <SelectItem value="leisure">Leisure</SelectItem>
                        <SelectItem value="group">Group</SelectItem>
                        <SelectItem value="mice">MICE/Event</SelectItem>
                        <SelectItem value="government">Government</SelectItem>
                        <SelectItem value="crew">Airline Crew</SelectItem>
                        <SelectItem value="wholesale">Wholesale</SelectItem>
                        <SelectItem value="long_stay">Long Stay</SelectItem>
                        <SelectItem value="complimentary">Complimentary</SelectItem>
                        <SelectItem value="other">Other</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  <div>
                    <Label>Cancellation Policy</Label>
                    <Select value={newBooking.cancellation_policy} onValueChange={(v) => setNewBooking({...newBooking, cancellation_policy: v})}>
                      <SelectTrigger><SelectValue placeholder="Select policy" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="same_day">Same Day (18:00)</SelectItem>
                        <SelectItem value="h24">24 Hours</SelectItem>
                        <SelectItem value="h48">48 Hours</SelectItem>
                        <SelectItem value="h72">72 Hours</SelectItem>
                        <SelectItem value="d7">7 Days</SelectItem>
                        <SelectItem value="d14">14 Days</SelectItem>
                        <SelectItem value="non_refundable">Non-Refundable</SelectItem>
                        <SelectItem value="flexible">Flexible</SelectItem>
                        <SelectItem value="special_event">Special Event</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                </div>
              )}

              {/* Billing Information */}
              {newBooking.company_id && (
                <div className="space-y-4 border-t pt-4">
                  <h3 className="font-semibold">Billing Information</h3>
                  <div>
                    <Label>Billing Address</Label>
                    <Textarea 
                      value={newBooking.billing_address} 
                      onChange={(e) => setNewBooking({...newBooking, billing_address: e.target.value})}
                      rows={2}
                    />
                  </div>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Tax Number</Label>
                      <Input 
                        value={newBooking.billing_tax_number} 
                        onChange={(e) => setNewBooking({...newBooking, billing_tax_number: e.target.value})}
                      />

              {/* Multi-room section placeholder: future enhancement */}

                    </div>
                    <div>
                      <Label>Contact Person</Label>
                      <Input 
                        value={newBooking.billing_contact_person} 
                        onChange={(e) => setNewBooking({...newBooking, billing_contact_person: e.target.value})}
                      />
                    </div>
                  </div>
                </div>
              )}

              {/* Channel selection (rate details managed per-room above) */}
              <div className="grid grid-cols-3 gap-4 border-t pt-4">
                <div className="col-span-2 text-xs text-gray-500 flex items-center">
                  Per-room base rate and total amount are managed in the multi-room section above.
                </div>
                <div>
                  <Label>Channel</Label>
                  <Select value={newBooking.channel} onValueChange={(v) => setNewBooking({...newBooking, channel: v})}>
                    <SelectTrigger><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="direct">Direct</SelectItem>
                      <SelectItem value="booking_com">Booking.com</SelectItem>
                      <SelectItem value="expedia">Expedia</SelectItem>
                      <SelectItem value="airbnb">Airbnb</SelectItem>
                      <SelectItem value="agoda">Agoda</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>

              {/* Override Reason - Show if rate is different from base */}
              {false && newBooking.base_rate > 0 && newBooking.base_rate !== newBooking.total_amount && (
                <div className="bg-yellow-50 border border-yellow-200 p-4 rounded">
                  <Label className="text-yellow-800">Override Reason * (Required for rate change)</Label>
                  <Textarea 
                    value={newBooking.override_reason} 
                    onChange={(e) => setNewBooking({...newBooking, override_reason: e.target.value})}
                    placeholder="Explain why the rate is different from the base rate..."
                    className="mt-2"
                    required
                  />
                </div>
              )}

              <Button type="submit" className="w-full">Create Booking</Button>
            </form>
          </DialogContent>
        </Dialog>

        {/* Quick Company Create Dialog */}
        <Dialog open={openDialog === 'company'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Quick Company Creation</DialogTitle>
              <DialogDescription>Create a new company profile (status: pending)</DialogDescription>
            </DialogHeader>
            <form onSubmit={handleCreateCompany} className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Company Name *</Label>
                  <Input 
                    value={newCompany.name} 
                    onChange={(e) => setNewCompany({...newCompany, name: e.target.value})}
                    required
                  />
                </div>
                <div>
                  <Label>Corporate Code</Label>
                  <Input 
                    value={newCompany.corporate_code} 
                    onChange={(e) => setNewCompany({...newCompany, corporate_code: e.target.value})}
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Tax Number</Label>
                  <Input 
                    value={newCompany.tax_number} 
                    onChange={(e) => setNewCompany({...newCompany, tax_number: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Contact Person</Label>
                  <Input 
                    value={newCompany.contact_person} 
                    onChange={(e) => setNewCompany({...newCompany, contact_person: e.target.value})}
                  />
                </div>
              </div>

              <div>
                <Label>Billing Address</Label>
                <Textarea 
                  value={newCompany.billing_address} 
                  onChange={(e) => setNewCompany({...newCompany, billing_address: e.target.value})}
                  rows={2}
                />
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Contact Email</Label>
                  <Input 
                    type="email"
                    value={newCompany.contact_email} 
                    onChange={(e) => setNewCompany({...newCompany, contact_email: e.target.value})}
                  />
                </div>
                <div>
                  <Label>Contact Phone</Label>
                  <Input 
                    value={newCompany.contact_phone} 
                    onChange={(e) => setNewCompany({...newCompany, contact_phone: e.target.value})}
                  />
                </div>
              </div>

              <div className="text-sm text-gray-500 bg-blue-50 p-3 rounded">
                ℹ️ This company will be created with "Pending" status. Sales team can complete the profile later with contracted rates and payment terms.
              </div>

              <Button type="submit" className="w-full">Create Company</Button>
            </form>
          </DialogContent>
        </Dialog>

        {/* Folio View Dialog */}
        <Dialog open={openDialog === 'folio-view'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent className="max-w-5xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle>Folio Management</DialogTitle>
              <DialogDescription>
                {selectedFolio && `Folio ${selectedFolio.folio_number} - ${selectedFolio.folio_type.toUpperCase()}`}
              </DialogDescription>
            </DialogHeader>

            {selectedFolio && (
              <div className="space-y-6">
                {/* Header Summary */}
                <div className="bg-gradient-to-r from-blue-50 to-purple-50 p-6 rounded-lg border">
                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <div className="text-sm text-gray-600">Guest</div>
                      <div className="font-semibold">
                        {guests.find(g => g.id === selectedFolio.guest_id)?.name || 'N/A'}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Booking</div>
                      <div className="font-semibold">
                        {(() => {
                          const booking = bookings.find(b => b.id === selectedFolio.booking_id);
                          if (!booking) return 'N/A';
                          return `${new Date(booking.check_in).toLocaleDateString()} - ${new Date(booking.check_out).toLocaleDateString()}`;
                        })()}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Current Balance</div>
                      <div className={`text-2xl font-bold ${selectedFolio.balance > 0 ? 'text-red-600' : selectedFolio.balance < 0 ? 'text-green-600' : 'text-gray-600'}`}>
                        ${selectedFolio.balance?.toFixed(2) || '0.00'}
                      </div>
                      <div className="text-xs text-gray-500">
                        {selectedFolio.balance > 0 ? 'Guest owes hotel' : selectedFolio.balance < 0 ? 'Hotel owes guest' : 'Balanced'}
                      </div>
                    </div>
                  </div>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <Button onClick={() => setOpenDialog('post-charge')} variant="default">
                    <Plus className="w-4 h-4 mr-2" />
                    Post Charge
                  </Button>
                  <Button onClick={() => setOpenDialog('post-payment')} variant="default">
                    <Plus className="w-4 h-4 mr-2" />
                    Post Payment
                  </Button>
                </div>

                {/* Charges and Payments Lists */}
                <div className="grid grid-cols-2 gap-6">
                  {/* Charges List */}
                  <div>
                    <h3 className="text-lg font-semibold mb-3 flex items-center">
                      <ClipboardList className="w-5 h-5 mr-2" />
                      Charges
                    </h3>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {folioCharges.length === 0 ? (
                        <div className="text-center text-gray-400 py-8">No charges posted</div>
                      ) : 
                        folioCharges.map((charge) => {
                          // Check if this is a POS charge with line items
                          const isPOSCharge = charge.charge_category === 'restaurant' || charge.charge_category === 'bar' || charge.charge_category === 'room_service';
                          const hasLineItems = charge.line_items && charge.line_items.length > 0;
                          const isExpanded = expandedChargeItems[charge.id];
                          
                          return (
                          <Card key={charge.id} className={charge.voided ? 'opacity-50 bg-gray-50' : ''}>
                            <CardContent className="p-4">
                              <div 
                                className={`flex justify-between items-start ${isPOSCharge && hasLineItems ? 'cursor-pointer hover:bg-gray-50' : ''}`}
                                onClick={() => {
                                  if (isPOSCharge && hasLineItems) {
                                    setExpandedChargeItems(prev => ({
                                      ...prev,
                                      [charge.id]: !prev[charge.id]
                                    }));
                                  }
                                }}
                              >
                                <div className="flex-1">
                                  <div className="flex items-center gap-2">
                                    <div className="font-semibold">{charge.description}</div>
                                    {isPOSCharge && hasLineItems && (
                                      <button className="text-blue-600 text-xs">
                                        {isExpanded ? '▼ Hide Items' : '▶ Show Items'}
                                      </button>
                                    )}
                                  </div>
                                  <div className="text-sm text-gray-600">
                                    {charge.charge_category.replace('_', ' ').toUpperCase()}
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    {new Date(charge.date).toLocaleDateString()} • Qty: {charge.quantity}
                                  </div>
                                  {charge.voided && (
                                    <div className="text-xs text-red-600 mt-1">
                                      VOIDED: {charge.void_reason}
                                    </div>
                                  )}
                                </div>
                                <div className="text-right">
                                  <div className="font-bold">${charge.total.toFixed(2)}</div>
                                  {charge.tax_amount > 0 && (
                                    <div className="text-xs text-gray-500">
                                      +${charge.tax_amount.toFixed(2)} tax
                                    </div>
                                  )}
                                </div>
                              </div>

                              {/* POS Line Items Breakdown - NEW */}
                              {isPOSCharge && hasLineItems && isExpanded && (
                                <div className="mt-3 pt-3 border-t bg-blue-50/50 rounded p-3">
                                  <div className="text-xs font-semibold text-gray-700 mb-2">POS Fiş Detayı:</div>
                                  <div className="space-y-1.5">
                                    {charge.line_items.map((item, idx) => (
                                      <div key={idx} className="flex justify-between items-center text-sm">
                                        <div className="flex-1">
                                          <span className="font-medium text-gray-700">
                                            {item.quantity} x {item.item_name}
                                          </span>
                                          {item.modifiers && item.modifiers.length > 0 && (
                                            <div className="text-xs text-gray-500 ml-4">
                                              ({item.modifiers.join(', ')})
                                            </div>
                                          )}
                                        </div>
                                        <span className="font-semibold text-gray-800">
                                          ${(item.unit_price * item.quantity).toFixed(2)}
                                        </span>
                                      </div>
                                    ))}
                                  </div>
                                  <div className="mt-2 pt-2 border-t flex justify-between text-sm">
                                    <span className="font-semibold">Subtotal:</span>
                                    <span className="font-bold">${charge.total.toFixed(2)}</span>
                                  </div>
                                </div>
                              )}
                            </CardContent>
                          </Card>
                        );
                        })
                      }
                    </div>
                    <div className="mt-4 pt-4 border-t">
                      <div className="flex justify-between font-semibold">
                        <span>Total Charges:</span>
                        <span>${folioCharges.filter(c => !c.voided).reduce((sum, c) => sum + c.total, 0).toFixed(2)}</span>
                      </div>
                    </div>
                  </div>

                  {/* Payments List */}
                  <div>
                    <h3 className="text-lg font-semibold mb-3 flex items-center">
                      <DollarSign className="w-5 h-5 mr-2" />
                      Payments
                    </h3>
                    <div className="space-y-2 max-h-96 overflow-y-auto">
                      {folioPayments.length === 0 ? (
                        <div className="text-center text-gray-400 py-8">No payments posted</div>
                      ) : (
                        folioPayments.map((payment) => (
                          <Card key={payment.id} className="bg-green-50">
                            <CardContent className="p-4">
                              <div className="flex justify-between items-start">
                                <div className="flex-1">
                                  <div className="font-semibold">{payment.method.toUpperCase()}</div>
                                  <div className="text-sm text-gray-600">
                                    {payment.payment_type.replace('_', ' ').toUpperCase()}
                                  </div>
                                  <div className="text-xs text-gray-500">
                                    {new Date(payment.processed_at).toLocaleDateString()}
                                  </div>
                                  {payment.reference && (
                                    <div className="text-xs text-gray-500">
                                      Ref: {payment.reference}
                                    </div>
                                  )}
                                </div>
                                <div className="text-right">
                                  <div className="font-bold text-green-600">${payment.amount.toFixed(2)}</div>
                                </div>
                              </div>
                            </CardContent>
                          </Card>
                        ))
                      )}
                    </div>
                    <div className="mt-4 pt-4 border-t">
                      <div className="flex justify-between font-semibold">
                        <span>Total Payments:</span>
                        <span className="text-green-600">${folioPayments.reduce((sum, p) => sum + p.amount, 0).toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Net Balance */}
                <div className="bg-gray-50 p-6 rounded-lg border-2 border-gray-300">
                  <div className="flex justify-between items-center">
                    <span className="text-xl font-semibold">Net Balance:</span>
                    <span className={`text-3xl font-bold ${selectedFolio.balance > 0 ? 'text-red-600' : selectedFolio.balance < 0 ? 'text-green-600' : 'text-gray-600'}`}>
                      ${selectedFolio.balance?.toFixed(2) || '0.00'}
                    </span>
                  </div>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Post Charge Dialog */}
        <Dialog open={openDialog === 'post-charge'} onOpenChange={(open) => !open && setOpenDialog('folio-view')}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Post Charge</DialogTitle>
            </DialogHeader>
            <form onSubmit={handlePostCharge} className="space-y-4">
              <div>
                <Label>Charge Category *</Label>
                <Select value={newFolioCharge.charge_category} onValueChange={(v) => setNewFolioCharge({...newFolioCharge, charge_category: v})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="room">Room</SelectItem>
                    <SelectItem value="food">Food & Beverage</SelectItem>
                    <SelectItem value="minibar">Minibar</SelectItem>
                    <SelectItem value="spa">Spa</SelectItem>
                    <SelectItem value="laundry">Laundry</SelectItem>
                    <SelectItem value="phone">Phone</SelectItem>
                    <SelectItem value="internet">Internet</SelectItem>
                    <SelectItem value="parking">Parking</SelectItem>
                    <SelectItem value="city_tax">City Tax</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Description *</Label>
                <Input 
                  value={newFolioCharge.description} 
                  onChange={(e) => setNewFolioCharge({...newFolioCharge, description: e.target.value})}
                  placeholder="e.g., Room 101 - Night Charge"
                  required
                />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Amount *</Label>
                  <Input 
                    type="number" 
                    step="0.01"
                    value={newFolioCharge.amount} 
                    onChange={(e) => setNewFolioCharge({...newFolioCharge, amount: parseFloat(e.target.value) || 0})}
                    required
                  />
                </div>
                <div>
                  <Label>Quantity *</Label>
                  <Input 
                    type="number" 
                    min="1"
                    value={newFolioCharge.quantity} 
                    onChange={(e) => setNewFolioCharge({...newFolioCharge, quantity: parseFloat(e.target.value) || 1})}
                    required
                  />
                </div>
              </div>
              <div className="flex items-center space-x-2">
                <input 
                  type="checkbox" 
                  id="auto-tax"
                  checked={newFolioCharge.auto_calculate_tax}
                  onChange={(e) => setNewFolioCharge({...newFolioCharge, auto_calculate_tax: e.target.checked})}
                  className="rounded"
                />
                <Label htmlFor="auto-tax" className="cursor-pointer">
                  Auto-calculate city tax
                </Label>
              </div>
              <Button type="submit" className="w-full">Post Charge</Button>
            </form>
          </DialogContent>
        </Dialog>

        {/* Post Payment Dialog */}
        <Dialog open={openDialog === 'post-payment'} onOpenChange={(open) => !open && setOpenDialog('folio-view')}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Post Payment</DialogTitle>
            </DialogHeader>
            <form onSubmit={handlePostPayment} className="space-y-4">
              <div>
                <Label>Payment Method *</Label>
                <Select value={newFolioPayment.method} onValueChange={(v) => setNewFolioPayment({...newFolioPayment, method: v})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cash">Cash</SelectItem>
                    <SelectItem value="card">Credit/Debit Card</SelectItem>
                    <SelectItem value="bank_transfer">Bank Transfer</SelectItem>
                    <SelectItem value="online">Online Payment</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Payment Type *</Label>
                <Select value={newFolioPayment.payment_type} onValueChange={(v) => setNewFolioPayment({...newFolioPayment, payment_type: v})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="prepayment">Prepayment</SelectItem>
                    <SelectItem value="deposit">Deposit</SelectItem>
                    <SelectItem value="interim">Interim Payment</SelectItem>
                    <SelectItem value="final">Final Payment</SelectItem>
                    <SelectItem value="refund">Refund</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Amount *</Label>
                <Input 
                  type="number" 
                  step="0.01"
                  value={newFolioPayment.amount} 
                  onChange={(e) => setNewFolioPayment({...newFolioPayment, amount: parseFloat(e.target.value) || 0})}
                  required
                />
              </div>
              <div>
                <Label>Reference / Auth Code</Label>
                <Input 
                  value={newFolioPayment.reference} 
                  onChange={(e) => setNewFolioPayment({...newFolioPayment, reference: e.target.value})}
                  placeholder="e.g., AUTH123456"
                />
              </div>
              <div>
                <Label>Notes</Label>
                <Textarea 
                  value={newFolioPayment.notes} 
                  onChange={(e) => setNewFolioPayment({...newFolioPayment, notes: e.target.value})}
                  rows={2}
                />
              </div>
              <Button type="submit" className="w-full">Post Payment</Button>
            </form>
          </DialogContent>
        </Dialog>

        {/* HK Task Dialog */}
        <Dialog open={openDialog === 'hktask'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create Housekeeping Task</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateHKTask} className="space-y-4">
              <div>
                <Label>Room</Label>
                <Select value={newHKTask.room_id} onValueChange={(v) => setNewHKTask({...newHKTask, room_id: v})}>
                  <SelectTrigger><SelectValue placeholder="Select room" /></SelectTrigger>
                  <SelectContent>
                    {rooms.map(r => <SelectItem key={r.id} value={r.id}>Room {r.room_number}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Task Type</Label>
                <Select value={newHKTask.task_type} onValueChange={(v) => setNewHKTask({...newHKTask, task_type: v})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="cleaning">Cleaning</SelectItem>
                    <SelectItem value="inspection">Inspection</SelectItem>
                    <SelectItem value="maintenance">Maintenance</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Priority</Label>
                <Select value={newHKTask.priority} onValueChange={(v) => setNewHKTask({...newHKTask, priority: v})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="urgent">Urgent</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Notes</Label>
                <Textarea value={newHKTask.notes} onChange={(e) => setNewHKTask({...newHKTask, notes: e.target.value})} />
              </div>
              <Button type="submit" className="w-full">Create Task</Button>
            </form>
          </DialogContent>
        </Dialog>

        {/* Room Block Dialog */}
        <Dialog open={openDialog === 'roomblock'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Block Room</DialogTitle>
              <DialogDescription>
                Create an Out of Order, Out of Service, or Maintenance block for a room
              </DialogDescription>
            </DialogHeader>
            <form onSubmit={(e) => { e.preventDefault(); createRoomBlock(); }} className="space-y-4">
              <div>
                <Label>Room *</Label>
                <Select value={selectedRoom?.id || ''} onValueChange={(v) => setSelectedRoom(rooms.find(r => r.id === v))}>
                  <SelectTrigger><SelectValue placeholder="Select room" /></SelectTrigger>
                  <SelectContent>
                    {rooms.map(r => <SelectItem key={r.id} value={r.id}>Room {r.room_number} ({r.room_type})</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Block Type *</Label>
                <Select value={newRoomBlock.type} onValueChange={(v) => setNewRoomBlock({...newRoomBlock, type: v})}>
                  <SelectTrigger><SelectValue /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="out_of_order">Out of Order (Cannot be sold)</SelectItem>
                    <SelectItem value="out_of_service">Out of Service</SelectItem>
                    <SelectItem value="maintenance">Maintenance</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Reason *</Label>
                <Input 
                  value={newRoomBlock.reason} 
                  onChange={(e) => setNewRoomBlock({...newRoomBlock, reason: e.target.value})}
                  placeholder="e.g., Plumbing issue, Renovation"
                  maxLength={200}
                />
              </div>
              <div>
                <Label>Details (optional)</Label>
                <Textarea 
                  value={newRoomBlock.details} 
                  onChange={(e) => setNewRoomBlock({...newRoomBlock, details: e.target.value})}
                  placeholder="Additional details about the block"
                  rows={3}
                />
              </div>
              <div>
                <Label>Start Date *</Label>
                <Input 
                  type="date"
                  value={newRoomBlock.start_date} 
                  onChange={(e) => setNewRoomBlock({...newRoomBlock, start_date: e.target.value})}
                />
              </div>
              <div>
                <Label>End Date (optional - leave empty for open-ended)</Label>
                <Input 
                  type="date"
                  value={newRoomBlock.end_date} 
                  onChange={(e) => setNewRoomBlock({...newRoomBlock, end_date: e.target.value})}
                />
              </div>
              <div className="flex items-center space-x-2">
                <input 
                  type="checkbox"
                  id="allow_sell"
                  checked={newRoomBlock.allow_sell}
                  onChange={(e) => setNewRoomBlock({...newRoomBlock, allow_sell: e.target.checked})}
                  className="h-4 w-4"
                />
                <Label htmlFor="allow_sell" className="cursor-pointer">
                  Allow room to be sold during block period
                </Label>
              </div>
              <Button type="submit" className="w-full">Create Room Block</Button>
            </form>
          </DialogContent>
        </Dialog>

        {/* View Room Blocks Dialog */}
        <Dialog open={openDialog === 'viewblocks'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>Room Blocks - Room {selectedRoom?.room_number}</DialogTitle>
              <DialogDescription>All blocks for this room</DialogDescription>
            </DialogHeader>
            <div className="space-y-3 max-h-96 overflow-y-auto">
              {selectedRoom && roomBlocks.filter(b => b.room_id === selectedRoom.id).length === 0 && (
                <div className="text-center text-gray-400 py-8">No blocks for this room</div>
              )}
              {selectedRoom && roomBlocks.filter(b => b.room_id === selectedRoom.id).map((block) => (
                <Card key={block.id} className={`${
                  block.status === 'cancelled' ? 'bg-gray-50' : 
                  block.type === 'out_of_order' ? 'border-red-400' :
                  block.type === 'out_of_service' ? 'border-orange-400' :
                  'border-yellow-400'
                }`}>
                  <CardContent className="pt-4">
                    <div className="flex justify-between items-start">
                      <div className="flex-1">
                        <div className="flex items-center gap-2 mb-2">
                          <span className={`px-2 py-1 text-xs font-bold rounded ${
                            block.type === 'out_of_order' ? 'bg-red-600 text-white' :
                            block.type === 'out_of_service' ? 'bg-orange-500 text-white' :
                            'bg-yellow-600 text-white'
                          }`}>
                            {block.type === 'out_of_order' ? 'OUT OF ORDER' :
                             block.type === 'out_of_service' ? 'OUT OF SERVICE' :
                             'MAINTENANCE'}
                          </span>
                          <span className={`px-2 py-1 text-xs font-semibold rounded ${
                            block.status === 'active' ? 'bg-green-100 text-green-700' :
                            block.status === 'cancelled' ? 'bg-gray-200 text-gray-600' :
                            'bg-yellow-100 text-yellow-700'
                          }`}>
                            {block.status}
                          </span>
                        </div>
                        <div className="text-sm font-medium text-gray-900 mb-1">
                          {block.reason}
                        </div>
                        {block.details && (
                          <div className="text-xs text-gray-600 mb-2">
                            {block.details}
                          </div>
                        )}
                        <div className="text-xs text-gray-500">
                          {new Date(block.start_date).toLocaleDateString()} - {
                            block.end_date ? new Date(block.end_date).toLocaleDateString() : 'Open-ended'
                          }
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {block.allow_sell ? '✓ Can be sold' : '✗ Cannot be sold'}
                        </div>
                      </div>
                      {block.status === 'active' && (
                        <Button 
                          size="sm" 
                          variant="destructive" 
                          onClick={() => {
                            cancelRoomBlock(block.id);
                            setOpenDialog(null);
                          }}
                        >
                          Cancel
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </DialogContent>
        </Dialog>

        {/* Guest 360° Profile Dialog */}
        <Dialog open={openDialog === 'guest360'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="text-2xl">🌟 Guest 360° Profile</DialogTitle>
              <DialogDescription>Complete guest intelligence and relationship data</DialogDescription>
            </DialogHeader>
            
            {loadingGuest360 ? (
              <div className="text-center py-12">
                <div className="text-4xl mb-4">⏳</div>
                <div>Loading guest profile...</div>
              </div>
            ) : guest360Data ? (
              <div className="space-y-4">
                {/* Quick Action Buttons - NEW */}
                <div className="flex gap-2 p-4 bg-gradient-to-r from-blue-50 to-purple-50 rounded-lg border border-blue-200">
                  <Button 
                    onClick={() => {
                      toast.success('Opening offer creation for ' + guest360Data.guest?.name);
                      // TODO: Navigate to offer creation or open offer dialog
                    }}
                    className="flex-1 bg-green-600 hover:bg-green-700"
                  >
                    <Send className="w-4 h-4 mr-2" />
                    Send Offer
                  </Button>
                  <Button 
                    onClick={() => {
                      // Scroll to notes section or auto-focus note input
                      const noteInput = document.querySelector('textarea[placeholder*="note"]');
                      if (noteInput) noteInput.focus();
                      toast.info('Note section ready - add your note below');
                    }}
                    variant="outline"
                    className="flex-1 border-blue-400 hover:bg-blue-50"
                  >
                    <FileText className="w-4 h-4 mr-2" />
                    Add Note
                  </Button>
                  <Button 
                    onClick={async () => {
                      try {
                        const preference = prompt('Enter room preference (e.g., High Floor, Sea View, Quiet Room):');
                        if (preference) {
                          await axios.post(`/crm/guest/add-tag?guest_id=${selectedGuest360}&tag=PREF: ${preference}`);
                          toast.success('Room preference saved!');
                          loadGuest360(selectedGuest360);
                        }
                      } catch (error) {
                        toast.error('Failed to save preference');
                      }
                    }}
                    variant="outline"
                    className="flex-1 border-purple-400 hover:bg-purple-50"
                  >
                    <Star className="w-4 h-4 mr-2" />
                    Block Room Preference
                  </Button>
                  <Button 
                    onClick={() => {
                      // Navigate to messaging center with pre-filled guest
                      window.location.href = `/ota-messaging-hub?guest=${guest360Data.guest?.id}&name=${guest360Data.guest?.name}`;
                    }}
                    variant="outline"
                    className="flex-1 border-orange-400 hover:bg-orange-50"
                  >
                    <MessageSquare className="w-4 h-4 mr-2" />
                    Message Guest
                  </Button>
                </div>

                {/* Identity Card */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Identity & Contact</CardTitle>
                  </CardHeader>
                  <CardContent className="grid grid-cols-2 gap-4">
                    <div>
                      <div className="text-sm text-gray-600">Name</div>
                      <div className="font-semibold">{guest360Data.guest?.name}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Email</div>
                      <div className="font-semibold">{guest360Data.guest?.email}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Phone</div>
                      <div className="font-semibold">{guest360Data.guest?.phone}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Country</div>
                      <div className="font-semibold">{guest360Data.guest?.country || 'N/A'}</div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Loyalty Status</div>
                      <div className={`inline-block px-2 py-1 rounded text-sm font-bold ${
                        guest360Data.profile?.loyalty_status === 'vip' ? 'bg-purple-600 text-white' :
                        guest360Data.profile?.loyalty_status === 'gold' ? 'bg-yellow-500 text-white' :
                        guest360Data.profile?.loyalty_status === 'silver' ? 'bg-gray-400 text-white' :
                        'bg-blue-500 text-white'
                      }`}>
                        {guest360Data.profile?.loyalty_status?.toUpperCase() || 'STANDARD'}
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600">Last Seen</div>
                      <div className="font-semibold">
                        {guest360Data.profile?.last_seen_date ? new Date(guest360Data.profile.last_seen_date).toLocaleDateString() : 'N/A'}
                      </div>
                    </div>
                  </CardContent>
                </Card>


                {/* Loyalty Progress Card */}
                <Card className="bg-gradient-to-r from-purple-50 to-pink-50 border-purple-200">
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Crown className="w-5 h-5 text-purple-600" />
                      Loyalty Program Status
                    </CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="text-2xl font-bold">
                          {guest360Data.profile?.loyalty_points || guest360Data.guest?.loyalty_points || 0} pts
                        </div>
                        <div className="text-sm text-gray-600">Current Balance</div>
                      </div>
                      <div className={`px-4 py-2 rounded-lg font-bold text-lg ${
                        guest360Data.profile?.loyalty_status === 'vip' ? 'bg-purple-600 text-white' :
                        guest360Data.profile?.loyalty_status === 'gold' ? 'bg-yellow-500 text-white' :
                        guest360Data.profile?.loyalty_status === 'silver' ? 'bg-gray-400 text-white' :
                        'bg-blue-500 text-white'
                      }`}>
                        {(guest360Data.profile?.loyalty_status || guest360Data.guest?.loyalty_tier || 'standard').toUpperCase()}
                      </div>
                    </div>
                    
                    {/* Progress to Next Tier */}
                    <div>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="text-gray-600">Progress to Next Tier</span>
                        <span className="font-semibold">
                          {(() => {
                            const currentPoints = guest360Data.profile?.loyalty_points || guest360Data.guest?.loyalty_points || 0;
                            const currentStatus = guest360Data.profile?.loyalty_status || guest360Data.guest?.loyalty_tier || 'standard';
                            const thresholds = { standard: 1000, silver: 2500, gold: 5000, vip: 10000 };
                            const nextTier = 
                              currentStatus === 'standard' ? 'silver' :
                              currentStatus === 'silver' ? 'gold' :
                              currentStatus === 'gold' ? 'vip' :
                              null;
                            
                            if (!nextTier) return 'MAX TIER';
                            const needed = thresholds[nextTier] - currentPoints;
                            return needed > 0 ? `${needed} pts to ${nextTier.toUpperCase()}` : 'Eligible for upgrade!';
                          })()}
                        </span>
                      </div>
                      <div className="w-full bg-gray-200 rounded-full h-3">
                        <div 
                          className="bg-gradient-to-r from-purple-600 to-pink-600 h-3 rounded-full transition-all"
                          style={{ 
                            width: `${(() => {
                              const currentPoints = guest360Data.profile?.loyalty_points || guest360Data.guest?.loyalty_points || 0;
                              const currentStatus = guest360Data.profile?.loyalty_status || guest360Data.guest?.loyalty_tier || 'standard';
                              const thresholds = { standard: 1000, silver: 2500, gold: 5000, vip: 10000 };
                              const current = thresholds[currentStatus] || 0;
                              const nextTier = 
                                currentStatus === 'standard' ? 'silver' :
                                currentStatus === 'silver' ? 'gold' :
                                currentStatus === 'gold' ? 'vip' :
                                null;
                              
                              if (!nextTier) return 100;
                              const next = thresholds[nextTier];
                              const progress = ((currentPoints - current) / (next - current)) * 100;
                              return Math.min(Math.max(progress, 0), 100);
                            })()}%` 
                          }}
                        ></div>
                      </div>
                    </div>
                    
                    {/* Tier Benefits */}
                    <div className="text-xs space-y-1">
                      <div className="font-semibold mb-2">Current Benefits:</div>
                      {guest360Data.profile?.loyalty_status === 'vip' || guest360Data.guest?.loyalty_tier === 'vip' ? (
                        <>
                          <div className="flex items-center gap-2">✨ Suite Upgrades</div>
                          <div className="flex items-center gap-2">🎁 Welcome Gifts</div>
                          <div className="flex items-center gap-2">🍾 Complimentary Services</div>
                          <div className="flex items-center gap-2">⚡ Priority Check-in/out</div>
                        </>
                      ) : guest360Data.profile?.loyalty_status === 'gold' || guest360Data.guest?.loyalty_tier === 'gold' ? (
                        <>
                          <div className="flex items-center gap-2">🔄 Free Room Upgrade</div>
                          <div className="flex items-center gap-2">☕ Complimentary Breakfast</div>
                          <div className="flex items-center gap-2">📅 Late Check-out</div>
                        </>
                      ) : guest360Data.profile?.loyalty_status === 'silver' || guest360Data.guest?.loyalty_tier === 'silver' ? (
                        <>
                          <div className="flex items-center gap-2">💰 10% Discount</div>
                          <div className="flex items-center gap-2">🎯 Points on Stays</div>
                        </>
                      ) : (
                        <>
                          <div className="flex items-center gap-2">⭐ Earn Points</div>
                          <div className="flex items-center gap-2">📧 Exclusive Offers</div>
                        </>
                      )}
                    </div>
                  </CardContent>
                </Card>


                {/* Stats Dashboard */}
                <div className="grid grid-cols-4 gap-4">
                  <Card>
                    <CardContent className="pt-4 text-center">
                      <div className="text-3xl font-bold text-blue-600">{guest360Data.stats?.total_stays || 0}</div>
                      <div className="text-sm text-gray-600">Total Stays</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4 text-center">
                      <div className="text-3xl font-bold text-green-600">{guest360Data.stats?.total_nights || 0}</div>
                      <div className="text-sm text-gray-600">Total Nights</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4 text-center">
                      <div className="text-3xl font-bold text-purple-600">${guest360Data.stats?.lifetime_value || 0}</div>
                      <div className="text-sm text-gray-600">Lifetime Value</div>
                    </CardContent>
                  </Card>
                  <Card>
                    <CardContent className="pt-4 text-center">
                      <div className="text-3xl font-bold text-orange-600">${guest360Data.stats?.average_adr || 0}</div>
                      <div className="text-sm text-gray-600">Avg ADR</div>
                    </CardContent>
                  </Card>
                </div>

                {/* Tags & Notes */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg">Tags & Notes</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <div className="text-sm text-gray-600 mb-2">Tags:</div>
                      <div className="flex flex-wrap gap-2">
                        {guest360Data.guest?.tags?.map((tag, idx) => (
                          <span key={idx} className="px-2 py-1 bg-blue-100 text-blue-700 rounded text-xs">
                            {tag}
                          </span>
                        ))}
                        <div className="flex gap-2">
                          <Input 
                            placeholder="Add tag..."
                            value={guestTag}
                            onChange={(e) => setGuestTag(e.target.value)}
                            className="h-8 w-32"
                          />
                          <Button size="sm" onClick={addGuestTag}>Add</Button>
                        </div>
                      </div>
                    </div>
                    <div>
                      <div className="text-sm text-gray-600 mb-2">Notes:</div>
                      <div className="space-y-2 max-h-32 overflow-y-auto mb-2">
                        {guest360Data.guest?.notes?.map((note, idx) => (
                          <div key={idx} className="text-xs bg-gray-50 p-2 rounded">
                            <div className="font-semibold">{note.created_by} - {new Date(note.created_at).toLocaleString()}</div>
                            <div>{note.text}</div>
                          </div>
                        ))}
                      </div>
                      <div className="flex gap-2">
                        <Textarea 
                          placeholder="Add note..."
                          value={guestNote}
                          onChange={(e) => setGuestNote(e.target.value)}
                          className="h-16"
                        />
                        <Button size="sm" onClick={addGuestNote}>Add Note</Button>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Booking History - Enhanced Timeline */}
                <Card>
                  <CardHeader>
                    <CardTitle className="text-lg flex items-center gap-2">
                      <Calendar className="w-5 h-5" />
                      Stay History Timeline
                    </CardTitle>
                    <CardDescription>
                      {guest360Data.profile?.total_stays || 0} total stays • 
                      ${(guest360Data.profile?.total_spending || 0).toFixed(0)} lifetime value
                    </CardDescription>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-3 max-h-96 overflow-y-auto">
                      {guest360Data.recent_bookings && guest360Data.recent_bookings.length > 0 ? (
                        guest360Data.recent_bookings.map((booking, idx) => {
                          const nights = Math.ceil((new Date(booking.check_out) - new Date(booking.check_in)) / (1000 * 60 * 60 * 24));
                          const adr = nights > 0 ? (booking.total_amount / nights).toFixed(0) : 0;
                          
                          return (
                            <div key={idx} className="relative pl-8 pb-4 border-l-2 border-blue-300 last:border-0">
                              {/* Timeline Dot */}
                              <div className={`absolute left-[-9px] top-0 w-4 h-4 rounded-full ${
                                booking.status === 'checked_out' ? 'bg-green-500' :
                                booking.status === 'checked_in' ? 'bg-blue-500' :
                                booking.status === 'confirmed' ? 'bg-yellow-500' :
                                'bg-gray-400'
                              } border-2 border-white`}></div>
                              
                              <div className="bg-gray-50 p-3 rounded-lg hover:bg-gray-100 transition">
                                <div className="flex justify-between items-start mb-2">
                                  <div>
                                    <div className="font-semibold text-base">
                                      {new Date(booking.check_in).toLocaleDateString('tr-TR', {
                                        day: 'numeric',
                                        month: 'long',
                                        year: 'numeric'
                                      })}
                                    </div>
                                    <div className="text-xs text-gray-600">
                                      {nights} nights • Room {booking.room_number || '?'}
                                    </div>
                                  </div>
                                  <Badge variant={
                                    booking.status === 'checked_out' ? 'secondary' :
                                    booking.status === 'checked_in' ? 'default' :
                                    'outline'
                                  }>
                                    {booking.status}
                                  </Badge>
                                </div>
                                
                                <div className="grid grid-cols-3 gap-2 text-xs">
                                  <div>
                                    <div className="text-gray-600">Total</div>
                                    <div className="font-bold text-green-600">${booking.total_amount?.toFixed(2)}</div>
                                  </div>
                                  <div>
                                    <div className="text-gray-600">ADR</div>
                                    <div className="font-bold">${adr}</div>
                                  </div>
                                  <div>
                                    <div className="text-gray-600">Channel</div>
                                    <div className="font-bold capitalize">{booking.ota_channel || booking.channel || 'Direct'}</div>
                                  </div>
                                </div>
                                
                                {booking.special_requests && (
                                  <div className="mt-2 text-xs text-gray-600 italic">
                                    💬 "{booking.special_requests}"
                                  </div>
                                )}
                              </div>
                            </div>
                          );
                        })
                      ) : (
                        <div className="text-center text-gray-400 py-8">No booking history available</div>
                      )}
                    </div>
                  </CardContent>
                </Card>

                {/* Channel Distribution - Enhanced with Pie Chart */}
                {guest360Data.stats?.channel_distribution && (
                  <Card>
                    <CardHeader>
                      <CardTitle className="text-lg">Channel Distribution</CardTitle>
                      <CardDescription>Booking sources breakdown</CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="grid grid-cols-2 gap-4">
                        {/* Pie Chart */}
                        <div>
                          <ResponsiveContainer width="100%" height={200}>
                            <PieChart>
                              <Pie
                                data={Object.entries(guest360Data.stats.channel_distribution).map(([channel, count]) => ({
                                  name: channel.charAt(0).toUpperCase() + channel.slice(1),
                                  value: count
                                }))}
                                cx="50%"
                                cy="50%"
                                labelLine={false}
                                label={({name, percent}) => `${name} ${(percent * 100).toFixed(0)}%`}
                                outerRadius={80}
                                fill="#8884d8"
                                dataKey="value"
                              >
                                {Object.keys(guest360Data.stats.channel_distribution).map((entry, index) => {
                                  const colors = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899'];
                                  return <Cell key={`cell-${index}`} fill={colors[index % colors.length]} />;
                                })}
                              </Pie>
                              <Tooltip />
                            </PieChart>
                          </ResponsiveContainer>
                        </div>
                        
                        {/* Stats */}
                        <div className="flex flex-col justify-center gap-3">
                          {Object.entries(guest360Data.stats.channel_distribution).map(([channel, count], index) => {
                            const colors = ['bg-blue-500', 'bg-green-500', 'bg-orange-500', 'bg-purple-500', 'bg-pink-500'];
                            return (
                              <div key={channel} className="flex items-center justify-between">
                                <div className="flex items-center gap-2">
                                  <div className={`w-3 h-3 ${colors[index % colors.length]} rounded`}></div>
                                  <span className="text-sm capitalize">{channel}</span>
                                </div>
                                <span className="font-bold">{count}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}
              </div>
            ) : (
              <div className="text-center py-12 text-gray-500">
                Select a guest to view their 360° profile
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Booking Detail Dialog - Double-Click to Open */}
        <Dialog open={openDialog === 'bookingDetail'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent className="max-w-2xl">
            <DialogHeader>
              <DialogTitle>📋 Booking Details</DialogTitle>
              <DialogDescription>Full reservation information and actions</DialogDescription>
            </DialogHeader>
            
            {selectedBookingDetail && (
              <div className="space-y-4">
                {/* Guest & Room Info */}
                <div className="grid grid-cols-2 gap-4">
                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">Guest Information</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Name:</span>
                        <span className="font-semibold">
                          {guests.find(g => g.id === selectedBookingDetail.guest_id)?.name || 'N/A'}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Email:</span>
                        <span className="text-xs">
                          {guests.find(g => g.id === selectedBookingDetail.guest_id)?.email || 'N/A'}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Phone:</span>
                        <span className="text-xs">
                          {guests.find(g => g.id === selectedBookingDetail.guest_id)?.phone || 'N/A'}
                        </span>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-3">
                      <CardTitle className="text-sm">Room & Dates</CardTitle>
                    </CardHeader>
                    <CardContent className="space-y-2">
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Room:</span>
                        <span className="font-semibold">
                          {rooms.find(r => r.id === selectedBookingDetail.room_id)?.room_number || 'N/A'}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Check-in:</span>
                        <span className="font-semibold">
                          {new Date(selectedBookingDetail.check_in).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="flex justify-between text-sm">
                        <span className="text-gray-600">Check-out:</span>
                        <span className="font-semibold">
                          {new Date(selectedBookingDetail.check_out).toLocaleDateString()}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Financial & Corporate Info */}
                <Card className="bg-gradient-to-r from-green-50 to-emerald-50">
                  <CardContent className="pt-4 space-y-3">
                    <div className="grid grid-cols-3 gap-4 text-center">
                      <div>
                        <div className="text-2xl font-bold text-green-700">
                          ${selectedBookingDetail.total_amount || 0}
                        </div>
                        <div className="text-xs text-gray-600">Total Amount</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-blue-700">
                          {selectedBookingDetail.adults || 1}
                        </div>
                        <div className="text-xs text-gray-600">Adults</div>
                      </div>
                      <div>
                        <div className="text-2xl font-bold text-purple-700">
                          {selectedBookingDetail.status?.toUpperCase() || 'N/A'}
                        </div>
                        <div className="text-xs text-gray-600">Status</div>
                      </div>
                    </div>

                    {selectedBookingDetail.company_id && (
                      <div className="grid grid-cols-2 gap-4 text-xs text-left bg-white/60 p-3 rounded border border-emerald-100">
                        <div className="space-y-1">
                          <div className="text-[11px] font-semibold text-gray-700">Corporate</div>
                          <div className="text-gray-800 font-medium">
                            {(() => {
                              const company = companies.find(c => c.id === selectedBookingDetail.company_id);
                              return company ? company.name : 'Corporate Booking';
                            })()}
                          </div>
                          <div className="text-[11px] text-gray-500">
                            Code: {
                              (() => {
                                const company = companies.find(c => c.id === selectedBookingDetail.company_id);
                                return company?.corporate_code || 'N/A';
                              })()
                            }
                          </div>
                        </div>
                        <div className="space-y-1">
                          <div className="text-[11px] font-semibold text-gray-700">Rate Details</div>
                          <div className="text-[11px] text-gray-600">
                            Contracted: <span className="font-medium">{selectedBookingDetail.contracted_rate || 'N/A'}</span>
                          </div>
                          <div className="text-[11px] text-gray-600">
                            Segment: <span className="font-medium">{selectedBookingDetail.market_segment || 'corporate'}</span>
                          </div>
                          <div className="text-[11px] text-gray-600">
                            Policy: <span className="font-medium">{selectedBookingDetail.cancellation_policy || 'standard'}</span>
                          </div>
                        </div>
                      </div>
                    )}
                  </CardContent>
                </Card>

                {/* Quick Actions */}
                <div className="grid grid-cols-3 gap-2">
                  <Button 
                    size="sm"
                    onClick={() => {
                      loadBookingFolios(selectedBookingDetail.id);
                      setOpenDialog(null);
                    }}
                    className="bg-green-600 hover:bg-green-700"
                  >
                    <DollarSign className="w-4 h-4 mr-1" />
                    View Folio
                  </Button>
                  <Button 
                    size="sm"
                    variant="outline"
                    onClick={() => {
                      toast.info('Editing booking...');
                      // TODO: Open edit form
                    }}
                  >
                    <FileText className="w-4 h-4 mr-1" />
                    Edit Details
                  </Button>
                  <Button 
                    size="sm"
                    variant="outline"
                    className="border-red-400 text-red-700 hover:bg-red-50"
                    onClick={() => {
                      if (confirm('Cancel this booking?')) {
                        toast.success('Booking cancelled');
                        setOpenDialog(null);
                      }
                    }}
                  >
                    Cancel Booking
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Floating Action Button - Quick Actions */}
        {/* Maintenance Work Order Dialog */}
        <Dialog open={maintenanceDialogOpen} onOpenChange={setMaintenanceDialogOpen}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Yeni Maintenance Work Order</DialogTitle>
              <DialogDescription>
                Oda {maintenanceForm.room_number} için mühendislik / bakım talebi oluşturun.
              </DialogDescription>
            </DialogHeader>
            <div className="space-y-4 mt-2">
              <div>
                <Label className="text-xs text-gray-600">Issue Type</Label>
                <Select
                  value={maintenanceForm.issue_type}
                  onValueChange={(v) => setMaintenanceForm((prev) => ({ ...prev, issue_type: v }))}
                >
                  <SelectTrigger className="h-9 mt-1 text-sm">
                    <SelectValue placeholder="Select issue type" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="housekeeping_damage">Housekeeping Damage</SelectItem>
                    <SelectItem value="plumbing">Plumbing</SelectItem>
                    <SelectItem value="hvac">HVAC</SelectItem>
                    <SelectItem value="electrical">Electrical</SelectItem>
                    <SelectItem value="furniture">Furniture</SelectItem>
                    <SelectItem value="other">Other</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs text-gray-600">Priority</Label>
                <Select
                  value={maintenanceForm.priority}
                  onValueChange={(v) => setMaintenanceForm((prev) => ({ ...prev, priority: v }))}
                >
                  <SelectTrigger className="h-9 mt-1 text-sm">
                    <SelectValue placeholder="Priority" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="normal">Normal</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="urgent">Urgent</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-xs text-gray-600">Description</Label>
                <Textarea
                  className="mt-1 text-sm min-h-[80px]"
                  value={maintenanceForm.description}
                  onChange={(e) => setMaintenanceForm((prev) => ({ ...prev, description: e.target.value }))}
                  placeholder="Short description of the issue (e.g., shower leaking, AC not cooling)…"
                />
              </div>
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setMaintenanceDialogOpen(false)}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                onClick={async () => {
                  try {
                    const payload = {
                      room_id: maintenanceForm.room_id,
                      room_number: maintenanceForm.room_number,
                      issue_type: maintenanceForm.issue_type,
                      priority: maintenanceForm.priority,
                      source: 'housekeeping',
                      description: maintenanceForm.description || undefined
                    };
                    const res = await axios.post('/maintenance/work-orders', payload, {
                      headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
                    });
                    toast.success(`Maintenance work order created for room ${res.data.room_number || maintenanceForm.room_number}`);
                    setMaintenanceDialogOpen(false);
                  } catch (error) {
                    console.error('Failed to create maintenance work order', error);
                    toast.error('Maintenance work order could not be created');
                  }
                }}
              >
                Create Work Order
              </Button>
            </div>
          </DialogContent>
        </Dialog>

        {/* FloatingActionButton - Quick Actions (mirrors top toolbar) */}
        <FloatingActionButton
          actions={[
            {
              label: 'New Booking',
              icon: <Plus className="w-5 h-5" />,
              onClick: () => {
                setOpenDialog('newbooking');
                toast.info('Opening new booking form...');
              }
            },
            {
              label: 'New Guest',
              icon: <UserPlus className="w-5 h-5" />,
              onClick: () => setOpenDialog('newguest')
            },
            {
              label: 'Flash Report',
              icon: <FileText className="w-5 h-5" />,
              onClick: async () => {
                try {
                  const response = await axios.get('/reports/flash-report');
                  toast.success('Flash report generated!');
                  console.log('Flash report:', response.data);
                } catch (error) {
                  toast.error('Failed to generate report');
                }
              }
            },
            {
              label: 'Refresh Dashboard',
              icon: <RefreshCw className="w-5 h-5" />,
              onClick: () => loadData()
            }
          ]}
        />

        {/* Maintenance Work Order Dialog */}
        <Dialog open={maintenanceDialogOpen} onOpenChange={setMaintenanceDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Yeni Maintenance Work Order</DialogTitle>
            <DialogDescription>
              Oda {maintenanceForm.room_number} için mühendislik / bakım talebi oluşturun.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 mt-2">
            <div>
              <Label className="text-xs text-gray-600">Issue Type</Label>
              <Select
                value={maintenanceForm.issue_type}
                onValueChange={(v) => setMaintenanceForm((prev) => ({ ...prev, issue_type: v }))}
              >
                <SelectTrigger className="h-9 mt-1 text-sm">
                  <SelectValue placeholder="Select issue type" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="housekeeping_damage">Housekeeping Damage</SelectItem>
                  <SelectItem value="plumbing">Plumbing</SelectItem>
                  <SelectItem value="hvac">HVAC</SelectItem>
                  <SelectItem value="electrical">Electrical</SelectItem>
                  <SelectItem value="furniture">Furniture</SelectItem>
                  <SelectItem value="other">Other</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-gray-600">Priority</Label>
              <Select
                value={maintenanceForm.priority}
                onValueChange={(v) => setMaintenanceForm((prev) => ({ ...prev, priority: v }))}
              >
                <SelectTrigger className="h-9 mt-1 text-sm">
                  <SelectValue placeholder="Priority" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="low">Low</SelectItem>
                  <SelectItem value="normal">Normal</SelectItem>
                  <SelectItem value="high">High</SelectItem>
                  <SelectItem value="urgent">Urgent</SelectItem>
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label className="text-xs text-gray-600">Description</Label>
              <Textarea
                className="mt-1 text-sm min-h-[80px]"
                value={maintenanceForm.description}
                onChange={(e) => setMaintenanceForm((prev) => ({ ...prev, description: e.target.value }))}
                placeholder="Short description of the issue (e.g., shower leaking, AC not cooling)…"
              />
            </div>
          </div>
          <div className="mt-4 flex justify-end gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setMaintenanceDialogOpen(false)}
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={async () => {
                try {
                  const payload = {
                    room_id: maintenanceForm.room_id,
                    room_number: maintenanceForm.room_number,
                    issue_type: maintenanceForm.issue_type,
                    priority: maintenanceForm.priority,
                    source: 'housekeeping',
                    description: maintenanceForm.description || undefined
                  };
                  const res = await axios.post(`${process.env.REACT_APP_BACKEND_URL}/maintenance/work-orders`, payload, {
                    headers: { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
                  });
                  toast.success(`Maintenance work order created for room ${res.data.room_number || maintenanceForm.room_number}`);
                  setMaintenanceDialogOpen(false);
                } catch (error) {
                  console.error('Failed to create maintenance work order', error);
                  toast.error('Maintenance work order could not be created');
                }
              }}
            >
              Create Work Order
            </Button>
          </div>
        </DialogContent>
      </Dialog>
      </div>

        {/* Guest Info Dialog - Kimlik Bilgileri */}
        <Dialog open={openDialog === 'guestinfo'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <User className="w-5 h-5" />
                Guest Information
              </DialogTitle>
              <DialogDescription>
                View and update guest personal and identification details
              </DialogDescription>
            </DialogHeader>
            
            {selectedGuest && (
              <div className="space-y-6">
                {/* Personal Information */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold border-b pb-2">Personal Information</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>Full Name</Label>
                      <Input 
                        value={selectedGuest.name || ''} 
                        onChange={(e) => setSelectedGuest({...selectedGuest, name: e.target.value})}
                        placeholder="Full Name"
                      />
                    </div>
                    <div>
                      <Label>Email</Label>
                      <Input 
                        type="email"
                        value={selectedGuest.email || ''} 
                        onChange={(e) => setSelectedGuest({...selectedGuest, email: e.target.value})}
                        placeholder="email@example.com"
                      />
                    </div>
                    <div>
                      <Label>Phone</Label>
                      <Input 
                        value={selectedGuest.phone || ''} 
                        onChange={(e) => setSelectedGuest({...selectedGuest, phone: e.target.value})}
                        placeholder="+90 555 123 4567"
                      />
                    </div>
                    <div>
                      <Label>Date of Birth</Label>
                      <Input 
                        type="date"
                        value={selectedGuest.date_of_birth?.split('T')[0] || ''} 
                        onChange={(e) => setSelectedGuest({...selectedGuest, date_of_birth: e.target.value})}
                      />
                    </div>
                    <div>
                      <Label>Nationality</Label>
                      <Input 
                        value={selectedGuest.nationality || ''} 
                        onChange={(e) => setSelectedGuest({...selectedGuest, nationality: e.target.value})}
                        placeholder="TR"
                      />
                    </div>
                    <div>
                      <Label>Gender</Label>
                      <Select 
                        value={selectedGuest.gender || ''} 
                        onValueChange={(v) => setSelectedGuest({...selectedGuest, gender: v})}
                      >
                        <SelectTrigger>
                          <SelectValue placeholder="Select gender" />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="male">Male</SelectItem>
                          <SelectItem value="female">Female</SelectItem>
                          <SelectItem value="other">Other</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>

                {/* Identification Information */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold border-b pb-2">Identification Details</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div>
                      <Label>ID Type</Label>
                      <Select 
                        value={selectedGuest.id_type || 'passport'} 
                        onValueChange={(v) => setSelectedGuest({...selectedGuest, id_type: v})}
                      >
                        <SelectTrigger>
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          <SelectItem value="passport">Passport</SelectItem>
                          <SelectItem value="national_id">National ID</SelectItem>
                          <SelectItem value="drivers_license">Driver's License</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                    <div>
                      <Label>ID Number</Label>
                      <Input 
                        value={selectedGuest.id_number || ''} 
                        onChange={(e) => setSelectedGuest({...selectedGuest, id_number: e.target.value})}
                        placeholder="ID/Passport Number"
                      />
                    </div>
                    <div>
                      <Label>Issue Date</Label>
                      <Input 
                        type="date"
                        value={selectedGuest.id_issue_date?.split('T')[0] || ''} 
                        onChange={(e) => setSelectedGuest({...selectedGuest, id_issue_date: e.target.value})}
                      />
                    </div>
                    <div>
                      <Label>Expiry Date</Label>
                      <Input 
                        type="date"
                        value={selectedGuest.id_expiry_date?.split('T')[0] || ''} 
                        onChange={(e) => setSelectedGuest({...selectedGuest, id_expiry_date: e.target.value})}
                      />
                    </div>
                    <div className="col-span-2">
                      <Label>Issuing Authority</Label>
                      <Input 
                        value={selectedGuest.id_issuing_authority || ''} 
                        onChange={(e) => setSelectedGuest({...selectedGuest, id_issuing_authority: e.target.value})}
                        placeholder="e.g., Ministry of Interior"
                      />
                    </div>
                  </div>
                </div>

                {/* Address Information */}
                <div className="space-y-4">
                  <h3 className="text-lg font-semibold border-b pb-2">Address</h3>
                  <div className="grid grid-cols-2 gap-4">
                    <div className="col-span-2">
                      <Label>Street Address</Label>
                      <Input 
                        value={selectedGuest.address || ''} 
                        onChange={(e) => setSelectedGuest({...selectedGuest, address: e.target.value})}
                        placeholder="Street address"
                      />
                    </div>
                    <div>
                      <Label>City</Label>
                      <Input 
                        value={selectedGuest.city || ''} 
                        onChange={(e) => setSelectedGuest({...selectedGuest, city: e.target.value})}
                        placeholder="City"
                      />
                    </div>
                    <div>
                      <Label>Postal Code</Label>
                      <Input 
                        value={selectedGuest.postal_code || ''} 
                        onChange={(e) => setSelectedGuest({...selectedGuest, postal_code: e.target.value})}
                        placeholder="Postal code"
                      />
                    </div>
                    <div>
                      <Label>Country</Label>
                      <Input 
                        value={selectedGuest.country || ''} 
                        onChange={(e) => setSelectedGuest({...selectedGuest, country: e.target.value})}
                        placeholder="Country"
                      />
                    </div>
                  </div>
                </div>

                {/* Additional Notes */}
                <div className="space-y-2">
                  <Label>Notes</Label>
                  <Textarea 
                    value={selectedGuest.notes || ''} 
                    onChange={(e) => setSelectedGuest({...selectedGuest, notes: e.target.value})}
                    placeholder="Additional notes about the guest..."
                    rows={3}
                  />
                </div>

                {/* Action Buttons */}
                <div className="flex justify-end gap-2 pt-4 border-t">
                  <Button variant="outline" onClick={() => setOpenDialog(null)}>
                    Cancel
                  </Button>
                  <Button onClick={async () => {
                    try {
                      await axios.put(`/pms/guests/${selectedGuest.id}`, selectedGuest);
                      toast.success('Guest information updated successfully');
                      setOpenDialog(null);
                      loadData();
                    } catch (error) {
                      toast.error('Failed to update guest information');
                      console.error(error);
                    }
                  }}>
                    <User className="w-4 h-4 mr-2" />
                    Save Changes
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>
        </Dialog>

        {/* Payment Dialog */}
        <Dialog open={openDialog === 'payment'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent className="max-w-md">
            <DialogHeader>
              <DialogTitle>Process Payment</DialogTitle>
              <DialogDescription>
                Record payment for this booking
              </DialogDescription>
            </DialogHeader>
            
            {selectedBooking && (
              <div className="space-y-4">
                <div>
                  <Label>Amount</Label>
                  <Input 
                    type="number"
                    value={paymentForm.amount}
                    onChange={(e) => setPaymentForm({...paymentForm, amount: parseFloat(e.target.value)})}
                    placeholder="0.00"
                  />
                </div>
                <div>
                  <Label>Payment Method</Label>
                  <Select 
                    value={paymentForm.method} 
                    onValueChange={(v) => setPaymentForm({...paymentForm, method: v})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="cash">Cash</SelectItem>
                      <SelectItem value="card">Card</SelectItem>
                      <SelectItem value="bank_transfer">Bank Transfer</SelectItem>
                      <SelectItem value="cheque">Cheque</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Payment Type</Label>
                  <Select 
                    value={paymentForm.payment_type} 
                    onValueChange={(v) => setPaymentForm({...paymentForm, payment_type: v})}
                  >
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="prepayment">Prepayment</SelectItem>
                      <SelectItem value="deposit">Deposit</SelectItem>
                      <SelectItem value="interim">Interim Payment</SelectItem>
                      <SelectItem value="final">Final Payment</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Reference</Label>
                  <Input 
                    value={paymentForm.reference}
                    onChange={(e) => setPaymentForm({...paymentForm, reference: e.target.value})}
                    placeholder="Transaction reference"
                  />
                </div>
                <div>
                  <Label>Notes</Label>
                  <Textarea 
                    value={paymentForm.notes}
                    onChange={(e) => setPaymentForm({...paymentForm, notes: e.target.value})}
                    placeholder="Payment notes..."
                    rows={2}
                  />
                </div>
                
                <div className="flex justify-end gap-2 pt-4 border-t">
                  <Button variant="outline" onClick={() => setOpenDialog(null)}>
                    Cancel
                  </Button>
                  <Button onClick={async () => {
                    try {
                      // Get folio for this booking
                      const folioRes = await axios.get(`/folio/booking/${selectedBooking.id}`);
                      if (folioRes.data && folioRes.data.length > 0) {
                        const folio = folioRes.data[0];
                        await axios.post(`/folio/${folio.id}/payment`, paymentForm);
                        toast.success('Payment recorded successfully');
                        setOpenDialog(null);
                        setPaymentForm({ amount: 0, method: 'card', payment_type: 'interim', reference: '', notes: '' });
                        loadData();
                      } else {
                        toast.error('No folio found for this booking');
                      }
                    } catch (error) {
                      toast.error('Failed to record payment');
                      console.error(error);
                    }
                  }}>
                    <DollarSign className="w-4 h-4 mr-2" />
                    Record Payment
                  </Button>
                </div>
              </div>
            )}
          </DialogContent>


        {/* Find Available Rooms Dialog */}
        <Dialog open={openDialog === 'findroom'} onOpenChange={(open) => !open && setOpenDialog(null)}>
          <DialogContent className="max-w-4xl max-h-[90vh] overflow-y-auto">
            <DialogHeader>
              <DialogTitle className="flex items-center gap-2">
                <Home className="w-5 h-5" />
                Find Available Rooms
              </DialogTitle>
              <DialogDescription>
                Search for available rooms based on dates and preferences
              </DialogDescription>
            </DialogHeader>
            
            <div className="space-y-6">
              {/* Search Criteria */}
              <div className="grid grid-cols-2 gap-4 p-4 bg-gray-50 rounded-lg">
                <div>
                  <Label>Check-in Date *</Label>
                  <Input 
                    type="date"
                    value={findRoomCriteria.check_in}
                    onChange={(e) => setFindRoomCriteria({...findRoomCriteria, check_in: e.target.value})}
                    min={new Date().toISOString().split('T')[0]}
                  />
                </div>
                <div>
                  <Label>Check-out Date *</Label>
                  <Input 
                    type="date"
                    value={findRoomCriteria.check_out}
                    onChange={(e) => setFindRoomCriteria({...findRoomCriteria, check_out: e.target.value})}
                    min={findRoomCriteria.check_in || new Date().toISOString().split('T')[0]}
                  />
                </div>
                <div>
                  <Label>Room Type</Label>
                  <Select 
                    value={findRoomCriteria.room_type} 
                    onValueChange={(v) => setFindRoomCriteria({...findRoomCriteria, room_type: v})}
                  >
                    <SelectTrigger>
                      <SelectValue placeholder="Any type" />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="any">Any type</SelectItem>
                      <SelectItem value="standard">Standard</SelectItem>
                      <SelectItem value="deluxe">Deluxe</SelectItem>
                      <SelectItem value="suite">Suite</SelectItem>
                      <SelectItem value="presidential">Presidential</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Number of Guests</Label>
                  <Input 
                    type="number"
                    min="1"
                    max="6"
                    value={findRoomCriteria.guests}
                    onChange={(e) => setFindRoomCriteria({...findRoomCriteria, guests: parseInt(e.target.value)})}
                  />
                </div>
              </div>

              <Button 
                onClick={async () => {
                  if (!findRoomCriteria.check_in || !findRoomCriteria.check_out) {
                    toast.error('Please select check-in and check-out dates');
                    return;
                  }
                  
                  setLoadingAvailableRooms(true);
                  try {
                    const params = new URLSearchParams({
                      check_in: findRoomCriteria.check_in,
                      check_out: findRoomCriteria.check_out
                    });
                    
                    if (findRoomCriteria.room_type) {
                      params.append('room_type', findRoomCriteria.room_type);
                    }
                    
                    const response = await axios.get(`/frontdesk/available-rooms?${params.toString()}`);
                    setAvailableRooms(response.data.available_rooms || []);
                    
                    if (response.data.available_rooms.length === 0) {
                      toast.info('No available rooms found for selected dates');
                    } else {
                      toast.success(`Found ${response.data.available_rooms.length} available rooms`);
                    }
                  } catch (error) {
                    toast.error('Failed to search for rooms');
                    console.error(error);
                  } finally {
                    setLoadingAvailableRooms(false);
                  }
                }}
                disabled={loadingAvailableRooms}
                className="w-full"
              >
                {loadingAvailableRooms ? (
                  <>
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                    Searching...
                  </>
                ) : (
                  <>
                    <Home className="w-4 h-4 mr-2" />
                    Search Available Rooms
                  </>
                )}
              </Button>

              {/* Results */}
              {availableRooms.length > 0 && (
                <div className="space-y-3">
                  <div className="flex items-center justify-between border-b pb-2">
                    <h3 className="font-semibold text-lg">
                      Available Rooms ({availableRooms.length})
                    </h3>
                    <Badge variant="secondary">
                      {findRoomCriteria.check_in} to {findRoomCriteria.check_out}
                    </Badge>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-3 max-h-96 overflow-y-auto">
                    {availableRooms.map((room) => (
                      <Card key={room.id} className="border-l-4 border-l-green-500">
                        <CardContent className="p-4">
                          <div className="space-y-2">
                            <div className="flex items-center justify-between">
                              <span className="text-lg font-semibold">Room {room.room_number}</span>
                              <Badge>{room.room_type}</Badge>
                            </div>
                            <div className="text-sm text-gray-600 space-y-1">
                              <div className="flex justify-between">
                                <span>Floor:</span>
                                <span className="font-medium">{room.floor}</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Base Price:</span>
                                <span className="font-medium text-blue-600">${room.base_price}/night</span>
                              </div>
                              <div className="flex justify-between">
                                <span>Capacity:</span>
                                <span className="font-medium">{room.capacity || room.max_occupancy || 2} guests</span>
                              </div>
                              {room.amenities && room.amenities.length > 0 && (
                                <div className="pt-2 border-t">
                                  <span className="text-xs text-gray-500">
                                    Amenities: {room.amenities.slice(0, 3).join(', ')}
                                  </span>
                                </div>
                              )}
                            </div>
                            <Button 
                              size="sm" 
                              className="w-full mt-2"
                              onClick={() => {
                                setNewBooking({
                                  ...newBooking,
                                  room_id: room.id,
                                  check_in: findRoomCriteria.check_in,
                                  check_out: findRoomCriteria.check_out,
                                  adults: findRoomCriteria.guests
                                });
                                setOpenDialog('booking');
                                toast.success(`Room ${room.room_number} selected`);
                              }}
                            >
                              Select This Room
                            </Button>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </DialogContent>
        </Dialog>

        </Dialog>

    </Layout>
  );
};

export default PMSModule;
