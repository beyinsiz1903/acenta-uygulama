import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import Layout from '@/components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import { 
  BedDouble, Users, Calendar, Plus, CheckCircle, DollarSign, 
  ClipboardList, BarChart3, TrendingUp, UserCheck, LogIn, LogOut as LogOutIcon
} from 'lucide-react';

const PMSModule = ({ user, tenant, onLogout }) => {
  const { t } = useTranslation();
  const [rooms, setRooms] = useState([]);
  const [guests, setGuests] = useState([]);
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
  const [loading, setLoading] = useState(true);
  const [aiPrediction, setAiPrediction] = useState(null);
  const [aiPatterns, setAiPatterns] = useState(null);
  const [openDialog, setOpenDialog] = useState(null);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [selectedCompany, setSelectedCompany] = useState(null);
  const [folio, setFolio] = useState(null);
  const [folios, setFolios] = useState([]);
  const [selectedFolio, setSelectedFolio] = useState(null);
  const [folioCharges, setFolioCharges] = useState([]);
  const [folioPayments, setFolioPayments] = useState([]);
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

  const [newHKTask, setNewHKTask] = useState({
    room_id: '', task_type: 'cleaning', priority: 'normal', notes: ''
  });

  useEffect(() => {
    loadData();
    loadAuditLogs();
  }, []);

  const loadData = async () => {
    try {
      const [roomsRes, guestsRes, bookingsRes, companiesRes] = await Promise.all([
        axios.get('/pms/rooms'),
        axios.get('/pms/guests'),
        axios.get('/pms/bookings'),
        axios.get('/companies')
      ]);
      setRooms(roomsRes.data);
      setGuests(guestsRes.data);
      setBookings(bookingsRes.data);
      setCompanies(companiesRes.data);
    } catch (error) {
      toast.error('Failed to load data');
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
      const [tasksRes, boardRes, dueOutRes, stayoverRes, arrivalsRes] = await Promise.all([
        axios.get('/housekeeping/tasks'),
        axios.get('/housekeeping/room-status'),
        axios.get('/housekeeping/due-out'),
        axios.get('/housekeeping/stayovers'),
        axios.get('/housekeeping/arrivals')
      ]);
      setHousekeepingTasks(tasksRes.data);
      setRoomStatusBoard(boardRes.data);
      setDueOutRooms(dueOutRes.data.due_out_rooms || []);
      setStayoverRooms(stayoverRes.data.stayover_rooms || []);
      setArrivalRooms(arrivalsRes.data.arrival_rooms || []);
    } catch (error) {
      toast.error('Failed to load housekeeping data');
    }
  };

  const loadAuditLogs = async () => {
    try {
      const response = await axios.get('/audit-logs?limit=50');
      setAuditLogs(response.data.logs || []);
    } catch (error) {
      // Permission denied is okay
      if (error.response?.status !== 403) {
        console.error('Failed to load audit logs:', error);
      }
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
      const today = new Date().toISOString().split('T')[0];
      const monthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0];
      const monthEnd = new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString().split('T')[0];
      
      const [occupancyRes, revenueRes, dailyRes, forecastRes, dailyFlashRes, marketSegmentRes, companyAgingRes, hkEfficiencyRes] = await Promise.all([
        axios.get(`/reports/occupancy?start_date=${monthStart}&end_date=${monthEnd}`),
        axios.get(`/reports/revenue?start_date=${monthStart}&end_date=${monthEnd}`),
        axios.get('/reports/daily-summary'),
        axios.get('/reports/forecast?days=7'),
        axios.get('/reports/daily-flash'),
        axios.get(`/reports/market-segment?start_date=${monthStart}&end_date=${monthEnd}`),
        axios.get('/reports/company-aging'),
        axios.get(`/reports/housekeeping-efficiency?start_date=${monthStart}&end_date=${monthEnd}`)
      ]);
      
      setReports({
        occupancy: occupancyRes.data,
        revenue: revenueRes.data,
        daily: dailyRes.data,
        forecast: forecastRes.data,
        dailyFlash: dailyFlashRes.data,
        marketSegment: marketSegmentRes.data,
        companyAging: companyAgingRes.data,
        hkEfficiency: hkEfficiencyRes.data
      });
    } catch (error) {
      toast.error('Failed to load reports');
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
    
    // Check for rate override
    if (newBooking.base_rate > 0 && newBooking.base_rate !== newBooking.total_amount) {
      if (!newBooking.override_reason) {
        toast.error('Please provide a reason for rate override');
        return;
      }
    }
    
    try {
      await axios.post('/pms/bookings', newBooking);
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

  if (loading) {
    return (
      <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="pms">
        <div className="p-6 text-center">Loading...</div>
      </Layout>
    );
  }

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="pms">
      <div className="p-6 space-y-6">
        <div>
          <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>{t('pms.title')}</h1>
          <p className="text-gray-600">{t('pms.subtitle')}</p>
        </div>

        <Tabs defaultValue="frontdesk" className="w-full" onValueChange={(v) => {
          if (v === 'frontdesk') loadFrontDeskData();
          if (v === 'housekeeping') loadHousekeepingData();
          if (v === 'reports') loadReports();
        }}>
          <TabsList className="grid w-full grid-cols-6">
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
            <TabsTrigger value="reports" data-testid="tab-reports">
              <BarChart3 className="w-4 h-4 mr-2" />
              {t('pms.reports')}
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
                      <p className="text-sm text-gray-700">{aiPatterns.analysis}</p>
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
                            <LogOutIcon className="w-4 h-4 mr-2" />
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
              <Button onClick={() => setOpenDialog('hktask')}>
                <Plus className="w-4 h-4 mr-2" />
                Create Task
              </Button>
            </div>

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
                  <CardTitle>Room Status Board</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
                    {roomStatusBoard.rooms.map((room) => (
                      <Card key={room.id} className={`cursor-pointer hover:shadow-lg transition-shadow ${
                        room.status === 'dirty' ? 'bg-red-100 border-red-300' :
                        room.status === 'cleaning' ? 'bg-yellow-100 border-yellow-300' :
                        room.status === 'inspected' ? 'bg-green-100 border-green-300' :
                        room.status === 'available' ? 'bg-blue-100 border-blue-300' :
                        room.status === 'occupied' ? 'bg-purple-100 border-purple-300' :
                        'bg-gray-100 border-gray-300'
                      }`}>
                        <CardContent className="p-3">
                          <div className="font-bold text-lg">{room.room_number}</div>
                          <div className="text-xs capitalize">{room.room_type}</div>
                          <div className="text-xs font-semibold mt-1 capitalize">{room.status.replace('_', ' ')}</div>
                          <div className="flex gap-1 mt-2">
                            {room.status === 'dirty' && (
                              <Button size="sm" variant="outline" className="h-6 text-xs" onClick={() => quickUpdateRoomStatus(room.id, 'cleaning')}>
                                Clean
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
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            <div className="space-y-4">
              {housekeepingTasks.map((task) => (
                <Card key={task.id}>
                  <CardContent className="pt-6">
                    <div className="flex justify-between items-center">
                      <div>
                        <div className="font-bold">Room {task.room?.room_number}</div>
                        <div className="text-sm text-gray-600 capitalize">{task.task_type} - {task.priority} priority</div>
                        {task.notes && <div className="text-sm text-gray-500">{task.notes}</div>}
                      </div>
                      <div className="space-x-2">
                        {task.status === 'pending' && (
                          <Button size="sm" onClick={() => handleUpdateHKTask(task.id, 'in_progress')}>
                            Start
                          </Button>
                        )}
                        {task.status === 'in_progress' && (
                          <Button size="sm" onClick={() => handleUpdateHKTask(task.id, 'completed')}>
                            Complete
                          </Button>
                        )}
                        <span className={`px-3 py-1 rounded text-xs ${task.status === 'completed' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'}`}>
                          {task.status}
                        </span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* ROOMS TAB */}
          <TabsContent value="rooms" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold">Rooms ({rooms.length})</h2>
              <Button onClick={() => setOpenDialog('room')}>
                <Plus className="w-4 h-4 mr-2" />
                Add Room
              </Button>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {rooms.map((room) => (
                <Card key={room.id}>
                  <CardHeader>
                    <CardTitle>Room {room.room_number}</CardTitle>
                    <CardDescription className="capitalize">{room.room_type}</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-2 text-sm">
                    <div className="flex justify-between">
                      <span>Floor:</span>
                      <span className="font-medium">{room.floor}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Capacity:</span>
                      <span className="font-medium">{room.capacity} guests</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Price:</span>
                      <span className="font-medium">${room.base_price}/night</span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span>Status:</span>
                      <Select value={room.status} onValueChange={(v) => updateRoomStatus(room.id, v)}>
                        <SelectTrigger className="w-32 h-8">
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
                  </CardContent>
                </Card>
              ))}
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
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {guests.map((guest) => (
                <Card key={guest.id}>
                  <CardHeader>
                    <CardTitle>{guest.name}</CardTitle>
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
                  </CardContent>
                </Card>
              ))}
            </div>
          </TabsContent>

          {/* BOOKINGS TAB */}
          <TabsContent value="bookings" className="space-y-4">
            <div className="flex justify-between items-center">
              <h2 className="text-2xl font-semibold">Bookings ({bookings.length})</h2>
              <Button onClick={() => setOpenDialog('booking')}>
                <Plus className="w-4 h-4 mr-2" />
                New Booking
              </Button>
            </div>
            <div className="space-y-4">
              {bookings.map((booking) => {
                const guest = guests.find(g => g.id === booking.guest_id);
                const room = rooms.find(r => r.id === booking.room_id);
                return (
                  <Card key={booking.id}>
                    <CardContent className="pt-6">
                      <div className="flex justify-between items-start">
                        <div className="flex-1">
                          <div className="font-semibold text-lg">{guest?.name}</div>
                          <div className="text-sm text-gray-600">Room {room?.room_number} - {room?.room_type}</div>
                          <div className="text-sm text-gray-500">
                            {new Date(booking.check_in).toLocaleDateString()} - {new Date(booking.check_out).toLocaleDateString()}
                          </div>
                        </div>
                        <div className="flex items-center gap-3">
                          <div className="text-right">
                            <div className="text-2xl font-bold">${booking.total_amount}</div>
                            <span className={`px-3 py-1 rounded-full text-xs ${booking.status === 'confirmed' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                              {booking.status.toUpperCase()}
                            </span>
                          </div>
                          <Button 
                            variant="outline" 
                            size="sm"
                            onClick={() => loadBookingFolios(booking.id)}
                            title="View charges & payments"
                          >
                            <DollarSign className="w-4 h-4 mr-1" />
                            View Folio
                          </Button>
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          </TabsContent>

          {/* REPORTS TAB */}
          <TabsContent value="reports" className="space-y-6">
            <h2 className="text-2xl font-bold">Hotel Analytics & Reports</h2>
            
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
              {/* Guest and Room Selection */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Guest *</Label>
                  <Select value={newBooking.guest_id} onValueChange={(v) => setNewBooking({...newBooking, guest_id: v})}>
                    <SelectTrigger><SelectValue placeholder="Select guest" /></SelectTrigger>
                    <SelectContent>
                      {guests.map(g => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Room *</Label>
                  <Select value={newBooking.room_id} onValueChange={(v) => setNewBooking({...newBooking, room_id: v})}>
                    <SelectTrigger><SelectValue placeholder="Select room" /></SelectTrigger>
                    <SelectContent>
                      {rooms.filter(r => r.status === 'available').map(r => (
                        <SelectItem key={r.id} value={r.id}>Room {r.room_number} - {r.room_type}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
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

              {/* Adults and Children */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Adults *</Label>
                  <Input 
                    type="number" 
                    min="1" 
                    value={newBooking.adults} 
                    onChange={(e) => {
                      const adults = parseInt(e.target.value) || 1;
                      setNewBooking({...newBooking, adults, guests_count: adults + newBooking.children});
                    }} 
                    required 
                  />
                </div>
                <div>
                  <Label>Children</Label>
                  <Input 
                    type="number" 
                    min="0" 
                    value={newBooking.children} 
                    onChange={(e) => handleChildrenChange(e.target.value)} 
                  />
                </div>
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
                <Select value={newBooking.company_id} onValueChange={handleCompanySelect}>
                  <SelectTrigger><SelectValue placeholder="Select company (optional)" /></SelectTrigger>
                  <SelectContent>
                    <SelectItem value="">None</SelectItem>
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

              {/* Rate Information */}
              <div className="grid grid-cols-3 gap-4 border-t pt-4">
                <div>
                  <Label>Base Rate</Label>
                  <Input 
                    type="number" 
                    step="0.01" 
                    value={newBooking.base_rate} 
                    onChange={(e) => setNewBooking({...newBooking, base_rate: parseFloat(e.target.value) || 0})}
                  />
                </div>
                <div>
                  <Label>Total Amount *</Label>
                  <Input 
                    type="number" 
                    step="0.01" 
                    value={newBooking.total_amount} 
                    onChange={(e) => setNewBooking({...newBooking, total_amount: parseFloat(e.target.value) || 0})} 
                    required 
                  />
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
              {newBooking.base_rate > 0 && newBooking.base_rate !== newBooking.total_amount && (
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
                      ) : (
                        folioCharges.map((charge) => (
                          <Card key={charge.id} className={charge.voided ? 'opacity-50 bg-gray-50' : ''}>
                            <CardContent className="p-4">
                              <div className="flex justify-between items-start">
                                <div className="flex-1">
                                  <div className="font-semibold">{charge.description}</div>
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
                            </CardContent>
                          </Card>
                        ))
                      )}
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
      </div>
    </Layout>
  );
};

export default PMSModule;
