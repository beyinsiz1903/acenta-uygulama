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
import FrontdeskTab from '@/components/pms/FrontdeskTab';
import HousekeepingTab from '@/components/pms/HousekeepingTab';
import BookingsTab from '@/components/pms/BookingsTab';
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
  Star, Send, MessageSquare, UserPlus, ArrowRight, RefreshCw, User, Search, CheckSquare, Download, Clock, Crown
} from 'lucide-react';
import FloatingActionButton from '@/components/FloatingActionButton';
import { ResponsiveContainer, PieChart, Pie, Cell, Tooltip } from 'recharts';


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
    paymentStatus: '',
    roomView: '',
    amenity: ''
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
  const [posOrders, setPosOrders] = useState([]);
  const [posRevenue, setPosRevenue] = useState({
    restaurant: 0,
    bar: 0,
    room_service: 0,
    total: 0
  });
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
    room_number: '',
    room_type: 'standard',
    floor: 1,
    capacity: 2,
    base_price: 100,
    amenities: [],
    view: '',
    bed_type: ''
  });

  // Bulk room creation UI state
  const [bulkRoomTab, setBulkRoomTab] = useState('range');
  const [bulkRange, setBulkRange] = useState({
    prefix: '',
    start_number: 101,
    end_number: 110,
    floor: 1,
    room_type: 'standard',
    capacity: 2,
    base_price: 100,
    view: 'city',
    bed_type: 'queen',
    amenities: ['wifi']
  });

  const [bulkTemplate, setBulkTemplate] = useState({
    prefix: 'B',
    start_number: 1,
    count: 10,
    floor: 1,
    room_type: 'deluxe',
    capacity: 2,
    base_price: 150,
    view: 'sea',
    bed_type: 'king',
    amenities: ['wifi']
  });

  const [bulkCsvFile, setBulkCsvFile] = useState(null);

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
      if (predictionRes) {
        const raw = predictionRes.data || {};
        // Normalize AI prediction response to a safe, flattened shape
        const normalizedPrediction = {
          current_occupancy: typeof raw.current_occupancy === 'number' ? raw.current_occupancy : 0,
          upcoming_bookings: typeof raw.upcoming_bookings === 'number' ? raw.upcoming_bookings : 0,
          // prediction can be string or object; keep as-is for FrontdeskTab which handles both
          prediction: raw.prediction,
        };
        setAiPrediction(normalizedPrediction);
      }
      if (patternsRes) {
        const rawPatterns = patternsRes.data || {};
        // Normalize guest patterns response to always have a flat insights array of strings
        const insights = Array.isArray(rawPatterns.insights)
          ? rawPatterns.insights.map((item) =>
              typeof item === 'string' ? item : JSON.stringify(item)
            )
          : [];
        setAiPatterns({ insights });
      }
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
      await axios.post('/pms/rooms', {
        ...newRoom,
        view: newRoom.view || null,
        bed_type: newRoom.bed_type || null,
      });
      toast.success('Room created');
      setOpenDialog(null);
      loadData();
      setNewRoom({
        room_number: '',
        room_type: 'standard',
        floor: 1,
        capacity: 2,
        base_price: 100,
        amenities: [],
        view: '',
        bed_type: ''
      });
    } catch (error) {
      toast.error('Failed to create room');
    }
  };

  const handleBulkCreateRange = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post('/pms/rooms/bulk/range', {
        ...bulkRange,
        prefix: bulkRange.prefix || null,
        view: bulkRange.view || null,
        bed_type: bulkRange.bed_type || null,
      });
      toast.success(`Bulk range complete: ${res.data.created} created, ${res.data.skipped} skipped`);
      setOpenDialog(null);
      loadData();
    } catch (error) {
      toast.error(error?.response?.data?.detail || 'Bulk range failed');
    }
  };

  const handleBulkCreateTemplate = async (e) => {
    e.preventDefault();
    try {
      const res = await axios.post('/pms/rooms/bulk/template', {
        ...bulkTemplate,
        prefix: bulkTemplate.prefix || null,
        view: bulkTemplate.view || null,
        bed_type: bulkTemplate.bed_type || null,
      });
      toast.success(`Bulk template complete: ${res.data.created} created, ${res.data.skipped} skipped`);
      setOpenDialog(null);
      loadData();
    } catch (error) {
      toast.error(error?.response?.data?.detail || 'Bulk template failed');
    }
  };

  const downloadRoomsCsvTemplate = () => {
    const header = ['room_number','room_type','floor','capacity','base_price','view','bed_type','amenities'].join(',');
    const example = ['A101','deluxe','1','2','150','sea','king','wifi|balcony'].join(',');
    const csv = `${header}\n${example}\n`;
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'rooms-import-template.csv');
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
  };

  const handleBulkImportCsv = async (e) => {
    e.preventDefault();

    if (!bulkCsvFile) {
      toast.error('Lütfen bir CSV dosyası seçin');
      return;
    }

    try {
      const formData = new FormData();
      formData.append('file', bulkCsvFile);

      const res = await axios.post('/pms/rooms/import-csv', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });

      toast.success(`CSV import: ${res.data.created} created, ${res.data.skipped} skipped, ${res.data.errors} errors`);
      if (res.data.errors > 0) {
        console.warn('CSV import errors:', res.data.error_rows);
      }
      setOpenDialog(null);
      setBulkCsvFile(null);
      loadData();
    } catch (error) {
      toast.error(error?.response?.data?.detail || 'CSV import failed');
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
          <FrontdeskTab
            t={t}
            arrivals={arrivals}
            departures={departures}
            inhouse={inhouse}
            aiPrediction={aiPrediction}
            aiPatterns={aiPatterns}
            handleCheckIn={handleCheckIn}
            handleCheckOut={handleCheckOut}
            loadFolio={loadFolio}
            loadFrontDeskData={loadFrontDeskData}
          />

          {/* HOUSEKEEPING TAB */}
          <HousekeepingTab
            roomBlocks={roomBlocks}
            roomStatusBoard={roomStatusBoard}
            dueOutRooms={dueOutRooms}
            stayoverRooms={stayoverRooms}
            arrivalRooms={arrivalRooms}
            housekeepingTasks={housekeepingTasks}
            quickUpdateRoomStatus={quickUpdateRoomStatus}
            setOpenDialog={setOpenDialog}
            setSelectedRoom={setSelectedRoom}
            setNewBooking={setNewBooking}
            setMaintenanceForm={setMaintenanceForm}
            setMaintenanceDialogOpen={setMaintenanceDialogOpen}
            handleUpdateHKTask={handleUpdateHKTask}
            toast={toast}
          />

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
                <Button variant="outline" onClick={() => setOpenDialog('bulk-rooms')}>
                  <Plus className="w-4 h-4 mr-2" />
                  Hızlı / Çoklu Oda Ekle
                </Button>
                <Button onClick={() => setOpenDialog('room')}>
                  <Plus className="w-4 h-4 mr-2" />
                  Add Room
                </Button>
              </div>
            </div>

            {/* Room Filters */}
            <Card className="border-gray-200">
              <CardContent className="p-4">
                <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
                  <div>
                    <Label>Room Type</Label>
                    <Select
                      value={quickFilters.roomType}
                      onValueChange={(v) => setQuickFilters(prev => ({ ...prev, roomType: v === 'all' ? '' : v }))}
                    >
                      <SelectTrigger><SelectValue placeholder="All" /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="all">All</SelectItem>
                        <SelectItem value="standard">Standard</SelectItem>
                        <SelectItem value="deluxe">Deluxe</SelectItem>
                        <SelectItem value="suite">Suite</SelectItem>
                        <SelectItem value="presidential">Presidential</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div>
                    <Label>Manzara (View)</Label>
                    <Input
                      placeholder="sea/city/garden..."
                      value={quickFilters.roomView}
                      onChange={(e) => setQuickFilters(prev => ({ ...prev, roomView: e.target.value }))}
                    />
                  </div>

                  <div>
                    <Label>Amenity</Label>
                    <Input
                      placeholder="wifi"
                      value={quickFilters.amenity}
                      onChange={(e) => setQuickFilters(prev => ({ ...prev, amenity: e.target.value }))}
                    />
                    <p className="text-[11px] text-gray-500 mt-1">Tek bir amenity ile filtreler (örn: wifi)</p>
                  </div>

                  <div className="flex items-end">
                    <Button
                      type="button"
                      variant="outline"
                      className="w-full"
                      onClick={() => setQuickFilters(prev => ({ ...prev, roomType: '', roomView: '', amenity: '' }))}
                    >
                      Temizle
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>

            
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
              {rooms
                .filter((room) => {
                  return true;
                })
                .map((room) => {
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

                      {/* Room meta badges */}
                      {(room.view || room.bed_type || (room.amenities || []).length > 0) && (
                        <div className="flex flex-wrap gap-1 pt-2">
                          {room.view && <Badge variant="outline" className="text-[10px]">View: {room.view}</Badge>}
                          {room.bed_type && <Badge variant="outline" className="text-[10px]">Bed: {room.bed_type}</Badge>}
                          {(room.amenities || []).slice(0, 3).map((a) => (
                            <Badge key={a} variant="secondary" className="text-[10px]">{a}</Badge>
                          ))}
                          {(room.amenities || []).length > 3 && (
                            <Badge variant="secondary" className="text-[10px]">+{(room.amenities || []).length - 3}</Badge>
                          )}
                        </div>
                      )}
                    </CardHeader>
                    <CardContent className="space-y-3 text-sm">

                      {/* Room photos preview */}
                      {(room.images || []).length > 0 && (
                        <div className="grid grid-cols-3 gap-2">
                          {(room.images || []).slice(0, 3).map((src) => (
                            <button
                              key={src}
                              type="button"
                              className="h-16 rounded-md overflow-hidden border bg-gray-50"
                              onClick={() => {
                                setSelectedRoom(room);
                                setOpenDialog('room-images');
                              }}
                              title="Fotoğrafları Gör"
                            >
                              <img src={src} alt="room" className="w-full h-full object-cover" />
                            </button>
                          ))}
                        </div>
                      )}

                      <div className="flex gap-2">
                        <Button
                          size="sm"
                          variant="outline"
                          className="flex-1"
                          onClick={() => {
                            setSelectedRoom(room);
                            setOpenDialog('room-images');
                          }}
                        >
                          Fotoğraflar
                        </Button>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </TabsContent>

          {/* GUESTS TAB */}
          <TabsContent value="guests" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold">Guests ({guests.length})</h2>
              <Button onClick={() => setOpenDialog('guest')}>
                <Plus className="w-4 h-4 mr-2" />
                Add Guest
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {guests.map((guest) => {
                return (
                <Card key={guest.id}>
                  <CardHeader>
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-lg">{guest.name}</CardTitle>
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setSelectedGuest360(guest.id);
                          loadGuest360(guest.id);
                        }}
                      >
                        <User className="w-4 h-4 mr-2" />
                        Profile
                      </Button>
                    </div>
                    <CardDescription>{guest.email}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-3 text-sm">
                    <div className="space-y-2">
                      <div><strong>Phone:</strong> {guest.phone || 'N/A'}</div>
                      <div><strong>ID Number:</strong> {guest.id_number || 'N/A'}</div>
                      <div><strong>Address:</strong> {guest.address || 'N/A'}</div>
                    </div>
                    <div className="flex gap-2 pt-2">
                      <Button
                        size="sm"
                        variant="outline"
                        onClick={() => {
                          setNewBooking(prev => ({...prev, guest_id: guest.id}));
                          setOpenDialog('newbooking');
                        }}
                      >
                        <Plus className="w-4 h-4 mr-2" />
                        New Booking
                      </Button>
                    </div>
                  </CardContent>
                </Card>
                );
              })}
            </div>
          </TabsContent>

          {/* BOOKINGS TAB */}
          <BookingsTab
            groupedBookings={groupedBookings}
            guests={guests}
            rooms={rooms}
            companies={companies}
            handleCheckIn={handleCheckIn}
            handleCheckOut={handleCheckOut}
            loadBookingFolios={loadBookingFolios}
            generateUpsellOffers={generateUpsellOffers}
            loadGuest360={loadGuest360}
            setSelectedGuest360={setSelectedGuest360}
            setOpenDialog={setOpenDialog}
            setSelectedBooking={setSelectedBooking}
            toast={toast}
          />

          {/* UPSELL TAB */}
          <TabsContent value="upsell" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold">🤖 AI Upsell & Revenue Optimization</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <TrendingUp className="w-5 h-5" />
                    Upsell Opportunities
                  </CardTitle>
                  <CardDescription>AI-generated upsell suggestions for current bookings</CardDescription>
                </CardHeader>
                <CardContent>
                  {upsellOffers.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      <TrendingUp className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>No upsell offers generated yet</p>
                      <p className="text-sm">Select a booking to generate AI-powered upsell suggestions</p>
                    </div>
                  ) : (
                    <div className="space-y-4">
                      {upsellOffers.map((offer, index) => (
                        <div key={index} className="border rounded-lg p-4 space-y-2">
                          <div className="flex justify-between items-start">
                            <div>
                              <h4 className="font-semibold">{offer.title}</h4>
                              <p className="text-sm text-gray-600">{offer.description}</p>
                            </div>
                            <Badge variant="secondary">${offer.additional_revenue}</Badge>
                          </div>
                          <div className="flex justify-between items-center pt-2">
                            <span className="text-xs text-gray-500">Confidence: {offer.confidence}%</span>
                            <Button size="sm" variant="outline">
                              Apply Offer
                            </Button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <BarChart3 className="w-5 h-5" />
                    Revenue Insights
                  </CardTitle>
                  <CardDescription>AI-powered revenue optimization suggestions</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-2 h-2 bg-green-500 rounded-full"></div>
                        <span className="font-semibold text-green-800">Revenue Opportunity</span>
                      </div>
                      <p className="text-sm text-green-700">
                        Increase ADR by 12% through strategic room upgrades and package offerings
                      </p>
                    </div>
                    
                    <div className="bg-blue-50 border border-blue-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-2 h-2 bg-blue-500 rounded-full"></div>
                        <span className="font-semibold text-blue-800">Occupancy Optimization</span>
                      </div>
                      <p className="text-sm text-blue-700">
                        Target corporate segment for weekday bookings to improve occupancy by 8%
                      </p>
                    </div>
                    
                    <div className="bg-purple-50 border border-purple-200 rounded-lg p-4">
                      <div className="flex items-center gap-2 mb-2">
                        <div className="w-2 h-2 bg-purple-500 rounded-full"></div>
                        <span className="font-semibold text-purple-800">Guest Satisfaction</span>
                      </div>
                      <p className="text-sm text-purple-700">
                        Personalized amenity packages can increase guest satisfaction by 15%
                      </p>
                    </div>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>

          {/* MESSAGING TAB */}
          <TabsContent value="messaging" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold">💬 Guest Communication</h2>
              <Button onClick={loadMessageTemplates}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Load Templates
              </Button>
            </div>
            
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Send Message */}
              <Card>
                <CardHeader>
                  <CardTitle>Send Message</CardTitle>
                  <CardDescription>Send email, SMS, or WhatsApp messages to guests</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div>
                    <Label>Channel</Label>
                    <Select
                      value={newMessage.channel}
                      onValueChange={(v) => setNewMessage(prev => ({...prev, channel: v}))}
                    >
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
                  
                  <div>
                    <Label>Recipient</Label>
                    <Input
                      placeholder={newMessage.channel === 'email' ? 'guest@example.com' : '+1234567890'}
                      value={newMessage.recipient}
                      onChange={(e) => setNewMessage(prev => ({...prev, recipient: e.target.value}))}
                    />
                  </div>
                  
                  {newMessage.channel === 'email' && (
                    <div>
                      <Label>Subject</Label>
                      <Input
                        placeholder="Message subject"
                        value={newMessage.subject}
                        onChange={(e) => setNewMessage(prev => ({...prev, subject: e.target.value}))}
                      />
                    </div>
                  )}
                  
                  <div>
                    <Label>Message</Label>
                    <Textarea
                      placeholder="Type your message here..."
                      value={newMessage.body}
                      onChange={(e) => setNewMessage(prev => ({...prev, body: e.target.value}))}
                      rows={4}
                    />
                  </div>
                  
                  <Button onClick={sendMessage} className="w-full">
                    <Send className="w-4 h-4 mr-2" />
                    Send {newMessage.channel.toUpperCase()}
                  </Button>
                </CardContent>
              </Card>

              {/* Message Templates */}
              <Card>
                <CardHeader>
                  <CardTitle>Message Templates</CardTitle>
                  <CardDescription>Pre-defined message templates for common scenarios</CardDescription>
                </CardHeader>
                <CardContent>
                  {messageTemplates.length === 0 ? (
                    <div className="text-center py-8 text-gray-500">
                      <MessageSquare className="w-12 h-12 mx-auto mb-4 opacity-50" />
                      <p>No templates available</p>
                      <p className="text-sm">Click "Load Templates" to fetch available templates</p>
                    </div>
                  ) : (
                    <div className="space-y-2">
                      {messageTemplates.map((template) => (
                        <div key={template.id} className="border rounded-lg p-3">
                          <div className="flex justify-between items-start mb-2">
                            <h4 className="font-semibold text-sm">{template.name}</h4>
                            <Button
                              size="sm"
                              variant="outline"
                              onClick={() => {
                                setNewMessage(prev => ({
                                  ...prev,
                                  subject: template.subject || prev.subject,
                                  body: template.body,
                                  template_id: template.id
                                }));
                              }}
                            >
                              Use
                            </Button>
                          </div>
                          <p className="text-xs text-gray-600">{template.description}</p>
                        </div>
                      ))}
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Sent Messages */}
            {sentMessages.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Recent Messages</CardTitle>
                  <CardDescription>Recently sent messages</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="space-y-3">
                    {sentMessages.slice(0, 5).map((message, index) => (
                      <div key={index} className="border-l-4 border-blue-500 pl-4 py-2">
                        <div className="flex justify-between items-start">
                          <div>
                            <div className="font-semibold text-sm">{message.channel.toUpperCase()} to {message.recipient}</div>
                            <div className="text-xs text-gray-600">{message.subject}</div>
                          </div>
                          <Badge variant="secondary">{message.status}</Badge>
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          {new Date(message.sent_at).toLocaleString()}
                        </div>
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* REPORTS TAB */}
          <TabsContent value="reports" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold">Reports & Analytics</h2>
              <Button onClick={loadReports}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh Reports
              </Button>
            </div>

            {/* Key Metrics Cards */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Occupancy Rate</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {reports.occupancy ? `${reports.occupancy.current_occupancy_rate}%` : 'Loading...'}
                  </div>
                  <p className="text-xs text-gray-600">
                    {reports.occupancy ? `${reports.occupancy.occupied_rooms}/${reports.occupancy.total_rooms} rooms` : ''}
                  </p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">ADR</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {reports.revenue ? `$${reports.revenue.adr}` : 'Loading...'}
                  </div>
                  <p className="text-xs text-gray-600">Average Daily Rate</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">RevPAR</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {reports.revenue ? `$${reports.revenue.revpar}` : 'Loading...'}
                  </div>
                  <p className="text-xs text-gray-600">Revenue Per Available Room</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Total Revenue</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">
                    {reports.revenue ? `$${reports.revenue.total_revenue}` : 'Loading...'}
                  </div>
                  <p className="text-xs text-gray-600">This Month</p>
                </CardContent>
              </Card>
            </div>

            {/* Charts and Detailed Reports */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Occupancy Chart */}
              <Card>
                <CardHeader>
                  <CardTitle>Occupancy Trend</CardTitle>
                  <CardDescription>Daily occupancy for the current month</CardDescription>
                </CardHeader>
                <CardContent>
                  {reports.occupancy && reports.occupancy.daily_data ? (
                    <ResponsiveContainer width="100%" height={300}>
                      <PickupPaceChart data={reports.occupancy.daily_data} />
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-[300px] flex items-center justify-center text-gray-500">
                      <RefreshCw className="w-8 h-8 animate-spin mr-2" />
                      Loading chart data...
                    </div>
                  )}
                </CardContent>
              </Card>

              {/* Revenue Breakdown */}
              <Card>
                <CardHeader>
                  <CardTitle>Revenue Breakdown</CardTitle>
                  <CardDescription>Revenue by source</CardDescription>
                </CardHeader>
                <CardContent>
                  {reports.revenue && reports.revenue.breakdown ? (
                    <ResponsiveContainer width="100%" height={300}>
                      <PieChart>
                        <Pie
                          data={reports.revenue.breakdown}
                          dataKey="amount"
                          nameKey="source"
                          cx="50%"
                          cy="50%"
                          outerRadius={100}
                          fill="#8884d8"
                        >
                          {reports.revenue.breakdown.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={['#0088FE', '#00C49F', '#FFBB28', '#FF8042'][index % 4]} />
                          ))}
                        </Pie>
                        <Tooltip />
                      </PieChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="h-[300px] flex items-center justify-center text-gray-500">
                      <RefreshCw className="w-8 h-8 animate-spin mr-2" />
                      Loading chart data...
                    </div>
                  )}
                </CardContent>
              </Card>
            </div>

            {/* Forecast */}
            {reports.forecast && (
              <Card>
                <CardHeader>
                  <CardTitle>7-Day Forecast</CardTitle>
                  <CardDescription>Predicted occupancy and revenue</CardDescription>
                </CardHeader>
                <CardContent>
                  <ForecastGraph data={reports.forecast} />
                </CardContent>
              </Card>
            )}

            {/* Daily Flash Report */}
            {reports.dailyFlash && (
              <Card>
                <CardHeader>
                  <CardTitle>Daily Flash Report</CardTitle>
                  <CardDescription>Today's key metrics and performance</CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                    <div className="text-center">
                      <div className="text-2xl font-bold text-blue-600">{reports.dailyFlash.arrivals}</div>
                      <div className="text-sm text-gray-600">Arrivals</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-green-600">{reports.dailyFlash.departures}</div>
                      <div className="text-sm text-gray-600">Departures</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-purple-600">{reports.dailyFlash.inhouse}</div>
                      <div className="text-sm text-gray-600">In-House</div>
                    </div>
                    <div className="text-center">
                      <div className="text-2xl font-bold text-orange-600">${reports.dailyFlash.revenue}</div>
                      <div className="text-sm text-gray-600">Revenue</div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* TASKS TAB */}
          <TabsContent value="tasks" className="space-y-4">
            <StaffTaskManager />
          </TabsContent>

          {/* FEEDBACK TAB */}
          <TabsContent value="feedback" className="space-y-4">
            <FeedbackSystem />
          </TabsContent>

          {/* ALLOTMENT TAB */}
          <TabsContent value="allotment" className="space-y-4">
            <AllotmentGrid />
          </TabsContent>

          {/* POS TAB */}
          <TabsContent value="pos" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold">🍽️ Point of Sale Integration</h2>
              <Button onClick={async () => {
                try {
                  const response = await axios.get('/pos/orders/today');
                  setPosOrders(response.data.orders || []);
                  setPosRevenue(response.data.revenue || { restaurant: 0, bar: 0, room_service: 0, total: 0 });
                  toast.success('POS data refreshed');
                } catch (error) {
                  toast.error('Failed to load POS data');
                }
              }}>
                <RefreshCw className="w-4 h-4 mr-2" />
                Refresh POS Data
              </Button>
            </div>

            {/* POS Revenue Summary */}
            <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Restaurant</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">${posRevenue.restaurant}</div>
                  <p className="text-xs text-gray-600">Today's Revenue</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Bar</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">${posRevenue.bar}</div>
                  <p className="text-xs text-gray-600">Today's Revenue</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Room Service</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">${posRevenue.room_service}</div>
                  <p className="text-xs text-gray-600">Today's Revenue</p>
                </CardContent>
              </Card>

              <Card>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm font-medium">Total F&B</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-2xl font-bold">${posRevenue.total}</div>
                  <p className="text-xs text-gray-600">Today's Total</p>
                </CardContent>
              </Card>
            </div>

            {/* Recent POS Orders */}
            <Card>
              <CardHeader>
                <CardTitle>Recent Orders</CardTitle>
                <CardDescription>Latest POS transactions</CardDescription>
              </CardHeader>
              <CardContent>
                {posOrders.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <div className="text-4xl mb-4">🍽️</div>
                    <p>No recent orders</p>
                    <p className="text-sm">POS orders will appear here when available</p>
                  </div>
                ) : (
                  <div className="space-y-3">
                    {posOrders.slice(0, 10).map((order) => (
                      <div key={order.id} className="flex justify-between items-center p-3 border rounded-lg">
                        <div>
                          <div className="font-semibold">Order #{order.id}</div>
                          <div className="text-sm text-gray-600">
                            {order.outlet} • Room {order.room_number || 'N/A'}
                          </div>
                          <div className="text-xs text-gray-500">
                            {new Date(order.created_at).toLocaleString()}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="font-bold">${order.total}</div>
                          <Badge variant={order.status === 'completed' ? 'default' : 'secondary'}>
                            {order.status}
                          </Badge>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>

