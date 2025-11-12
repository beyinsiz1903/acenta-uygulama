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
  const [arrivals, setArrivals] = useState([]);
  const [departures, setDepartures] = useState([]);
  const [inhouse, setInhouse] = useState([]);
  const [housekeepingTasks, setHousekeepingTasks] = useState([]);
  const [roomStatusBoard, setRoomStatusBoard] = useState(null);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(null);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [folio, setFolio] = useState(null);
  const [reports, setReports] = useState({
    occupancy: null,
    revenue: null,
    daily: null,
    forecast: []
  });

  const [newRoom, setNewRoom] = useState({
    room_number: '', room_type: 'standard', floor: 1, capacity: 2, base_price: 100, amenities: []
  });

  const [newGuest, setNewGuest] = useState({
    name: '', email: '', phone: '', id_number: '', address: ''
  });

  const [newBooking, setNewBooking] = useState({
    guest_id: '', room_id: '', check_in: '', check_out: '', guests_count: 1, total_amount: 0, channel: 'direct'
  });

  const [newCharge, setNewCharge] = useState({
    charge_type: 'food', description: '', amount: 0, quantity: 1
  });

  const [newPayment, setNewPayment] = useState({
    amount: 0, method: 'card', reference: '', notes: ''
  });

  const [newHKTask, setNewHKTask] = useState({
    room_id: '', task_type: 'cleaning', priority: 'normal', notes: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [roomsRes, guestsRes, bookingsRes] = await Promise.all([
        axios.get('/pms/rooms'),
        axios.get('/pms/guests'),
        axios.get('/pms/bookings')
      ]);
      setRooms(roomsRes.data);
      setGuests(guestsRes.data);
      setBookings(bookingsRes.data);
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
    } catch (error) {
      toast.error('Failed to load front desk data');
    }
  };

  const loadHousekeepingData = async () => {
    try {
      const [tasksRes, boardRes] = await Promise.all([
        axios.get('/housekeeping/tasks'),
        axios.get('/housekeeping/room-status')
      ]);
      setHousekeepingTasks(tasksRes.data);
      setRoomStatusBoard(boardRes.data);
    } catch (error) {
      toast.error('Failed to load housekeeping data');
    }
  };

  const loadReports = async () => {
    try {
      const today = new Date().toISOString().split('T')[0];
      const monthStart = new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0];
      const monthEnd = new Date(new Date().getFullYear(), new Date().getMonth() + 1, 0).toISOString().split('T')[0];
      
      const [occupancyRes, revenueRes, dailyRes, forecastRes] = await Promise.all([
        axios.get(`/reports/occupancy?start_date=${monthStart}&end_date=${monthEnd}`),
        axios.get(`/reports/revenue?start_date=${monthStart}&end_date=${monthEnd}`),
        axios.get('/reports/daily-summary'),
        axios.get('/reports/forecast?days=7')
      ]);
      
      setReports({
        occupancy: occupancyRes.data,
        revenue: revenueRes.data,
        daily: dailyRes.data,
        forecast: forecastRes.data
      });
    } catch (error) {
      toast.error('Failed to load reports');
    }
  };

  const handleCheckIn = async (bookingId) => {
    try {
      await axios.post(`/frontdesk/checkin/${bookingId}`);
      toast.success('Guest checked in successfully');
      loadData();
      loadFrontDeskData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Check-in failed');
    }
  };

  const handleCheckOut = async (bookingId) => {
    try {
      await axios.post(`/frontdesk/checkout/${bookingId}`);
      toast.success('Guest checked out successfully');
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

  const handleCreateBooking = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/pms/bookings', newBooking);
      toast.success('Booking created');
      setOpenDialog(null);
      loadData();
      setNewBooking({ guest_id: '', room_id: '', check_in: '', check_out: '', guests_count: 1, total_amount: 0, channel: 'direct' });
    } catch (error) {
      toast.error('Failed to create booking');
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
          <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>Property Management System</h1>
          <p className="text-gray-600">Complete hotel operations management</p>
        </div>

        <Tabs defaultValue="frontdesk" className="w-full" onValueChange={(v) => {
          if (v === 'frontdesk') loadFrontDeskData();
          if (v === 'housekeeping') loadHousekeepingData();
          if (v === 'reports') loadReports();
        }}>
          <TabsList className="grid w-full grid-cols-6">
            <TabsTrigger value="frontdesk" data-testid="tab-frontdesk">
              <UserCheck className="w-4 h-4 mr-2" />
              Front Desk
            </TabsTrigger>
            <TabsTrigger value="housekeeping" data-testid="tab-housekeeping">
              <ClipboardList className="w-4 h-4 mr-2" />
              Housekeeping
            </TabsTrigger>
            <TabsTrigger value="rooms" data-testid="tab-rooms">
              <BedDouble className="w-4 h-4 mr-2" />
              Rooms
            </TabsTrigger>
            <TabsTrigger value="guests" data-testid="tab-guests">
              <Users className="w-4 h-4 mr-2" />
              Guests
            </TabsTrigger>
            <TabsTrigger value="bookings" data-testid="tab-bookings">
              <Calendar className="w-4 h-4 mr-2" />
              Bookings
            </TabsTrigger>
            <TabsTrigger value="reports" data-testid="tab-reports">
              <BarChart3 className="w-4 h-4 mr-2" />
              Reports
            </TabsTrigger>
          </TabsList>

          {/* FRONT DESK TAB */}
          <TabsContent value="frontdesk" className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <Card className="cursor-pointer hover:shadow-lg transition" onClick={loadFrontDeskData}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Today's Arrivals</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{arrivals.length}</div>
                  <p className="text-xs text-gray-500">Expected check-ins</p>
                </CardContent>
              </Card>
              
              <Card className="cursor-pointer hover:shadow-lg transition" onClick={loadFrontDeskData}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">Today's Departures</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{departures.length}</div>
                  <p className="text-xs text-gray-500">Expected check-outs</p>
                </CardContent>
              </Card>
              
              <Card className="cursor-pointer hover:shadow-lg transition" onClick={loadFrontDeskData}>
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm">In-House Guests</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="text-3xl font-bold">{inhouse.length}</div>
                  <p className="text-xs text-gray-500">Currently staying</p>
                </CardContent>
              </Card>
            </div>

            <Tabs defaultValue="arrivals">
              <TabsList>
                <TabsTrigger value="arrivals">Arrivals</TabsTrigger>
                <TabsTrigger value="departures">Departures</TabsTrigger>
                <TabsTrigger value="inhouse">In-House</TabsTrigger>
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

            {roomStatusBoard && (
              <div className="grid grid-cols-3 md:grid-cols-7 gap-4 mb-6">
                {Object.entries(roomStatusBoard.status_counts).map(([status, count]) => (
                  <Card key={status}>
                    <CardContent className="pt-4">
                      <div className="text-2xl font-bold">{count}</div>
                      <div className="text-xs capitalize">{status.replace('_', ' ')}</div>
                    </CardContent>
                  </Card>
                ))}
              </div>
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
                        <div>
                          <div className="font-semibold text-lg">{guest?.name}</div>
                          <div className="text-sm text-gray-600">Room {room?.room_number} - {room?.room_type}</div>
                          <div className="text-sm text-gray-500">
                            {new Date(booking.check_in).toLocaleDateString()} - {new Date(booking.check_out).toLocaleDateString()}
                          </div>
                        </div>
                        <div className="text-right">
                          <div className="text-2xl font-bold">${booking.total_amount}</div>
                          <span className={`px-3 py-1 rounded-full text-xs ${booking.status === 'confirmed' ? 'bg-green-100 text-green-700' : 'bg-blue-100 text-blue-700'}`}>
                            {booking.status.toUpperCase()}
                          </span>
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
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Create New Booking</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleCreateBooking} className="space-y-4">
              <div>
                <Label>Guest</Label>
                <Select value={newBooking.guest_id} onValueChange={(v) => setNewBooking({...newBooking, guest_id: v})}>
                  <SelectTrigger><SelectValue placeholder="Select guest" /></SelectTrigger>
                  <SelectContent>
                    {guests.map(g => <SelectItem key={g.id} value={g.id}>{g.name}</SelectItem>)}
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Room</Label>
                <Select value={newBooking.room_id} onValueChange={(v) => setNewBooking({...newBooking, room_id: v})}>
                  <SelectTrigger><SelectValue placeholder="Select room" /></SelectTrigger>
                  <SelectContent>
                    {rooms.filter(r => r.status === 'available').map(r => (
                      <SelectItem key={r.id} value={r.id}>Room {r.room_number} - {r.room_type}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Check-in</Label>
                  <Input type="date" value={newBooking.check_in} onChange={(e) => setNewBooking({...newBooking, check_in: e.target.value})} required />
                </div>
                <div>
                  <Label>Check-out</Label>
                  <Input type="date" value={newBooking.check_out} onChange={(e) => setNewBooking({...newBooking, check_out: e.target.value})} required />
                </div>
              </div>
              <div>
                <Label>Number of Guests</Label>
                <Input type="number" min="1" value={newBooking.guests_count} onChange={(e) => setNewBooking({...newBooking, guests_count: parseInt(e.target.value)})} required />
              </div>
              <div>
                <Label>Total Amount</Label>
                <Input type="number" step="0.01" value={newBooking.total_amount} onChange={(e) => setNewBooking({...newBooking, total_amount: parseFloat(e.target.value)})} required />
              </div>
              <Button type="submit" className="w-full">Create Booking</Button>
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
