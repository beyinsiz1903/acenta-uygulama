import { useState, useEffect } from 'react';
import { Routes, Route, useNavigate, useLocation } from 'react-router-dom';
import axios from 'axios';
import { toast } from 'sonner';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Switch } from '@/components/ui/switch';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Textarea } from '@/components/ui/textarea';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Home,
  Calendar,
  Award,
  Settings,
  LogOut,
  User,
  QrCode,
  Bell,
  Utensils,
  Hotel,
  MapPin,
  Clock,
  Phone,
  Mail,
  Star
} from 'lucide-react';

const GuestPortal = ({ user, onLogout }) => {
  const navigate = useNavigate();
  const location = useLocation();
  const [activeBookings, setActiveBookings] = useState([]);
  const [pastBookings, setPastBookings] = useState([]);
  const [loyaltyPrograms, setLoyaltyPrograms] = useState([]);
  const [totalPoints, setTotalPoints] = useState(0);
  const [notificationPrefs, setNotificationPrefs] = useState(null);
  const [loading, setLoading] = useState(true);
  const [openDialog, setOpenDialog] = useState(null);
  const [selectedBooking, setSelectedBooking] = useState(null);
  const [roomServices, setRoomServices] = useState({});

  const [roomServiceRequest, setRoomServiceRequest] = useState({
    booking_id: '',
    service_type: 'housekeeping',
    description: '',
    notes: ''
  });

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    try {
      const [bookingsRes, loyaltyRes, prefsRes] = await Promise.all([
        axios.get('/guest/bookings'),
        axios.get('/guest/loyalty'),
        axios.get('/guest/notification-preferences')
      ]);

      setActiveBookings(bookingsRes.data.active_bookings);
      setPastBookings(bookingsRes.data.past_bookings);
      setLoyaltyPrograms(loyaltyRes.data.loyalty_programs);
      setTotalPoints(loyaltyRes.data.total_points);
      setNotificationPrefs(prefsRes.data);
    } catch (error) {
      toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const loadRoomServices = async (bookingId) => {
    try {
      const response = await axios.get(`/guest/room-service/${bookingId}`);
      setRoomServices(prev => ({ ...prev, [bookingId]: response.data }));
    } catch (error) {
      console.error('Failed to load room services');
    }
  };

  const handleRoomServiceRequest = async (e) => {
    e.preventDefault();
    try {
      await axios.post('/guest/room-service', roomServiceRequest);
      toast.success('Room service request submitted');
      setOpenDialog(null);
      loadRoomServices(roomServiceRequest.booking_id);
      setRoomServiceRequest({ booking_id: '', service_type: 'housekeeping', description: '', notes: '' });
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to submit request');
    }
  };

  const updateNotificationPref = async (key, value) => {
    try {
      await axios.put('/guest/notification-preferences', { [key]: value });
      setNotificationPrefs(prev => ({ ...prev, [key]: value }));
      toast.success('Preference updated');
    } catch (error) {
      toast.error('Failed to update preference');
    }
  };

  const getTierColor = (tier) => {
    switch(tier) {
      case 'platinum': return 'bg-purple-100 text-purple-700 border-purple-300';
      case 'gold': return 'bg-yellow-100 text-yellow-700 border-yellow-300';
      case 'silver': return 'bg-gray-100 text-gray-700 border-gray-300';
      default: return 'bg-orange-100 text-orange-700 border-orange-300';
    }
  };

  const getTierStars = (tier) => {
    const count = tier === 'platinum' ? 4 : tier === 'gold' ? 3 : tier === 'silver' ? 2 : 1;
    return Array(count).fill(0).map((_, i) => <Star key={i} className="w-3 h-3 fill-current" />);
  };

  const navigation = [
    { name: 'Home', path: '/', icon: Home, id: 'home' },
    { name: 'Bookings', path: '/bookings', icon: Calendar, id: 'bookings' },
    { name: 'Loyalty', path: '/loyalty', icon: Award, id: 'loyalty' },
    { name: 'Settings', path: '/settings', icon: Settings, id: 'settings' },
  ];

  const currentPath = location.pathname === '/' ? 'home' : location.pathname.slice(1);

  if (loading) {
    return <div className="loading-screen">Loading...</div>;
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-blue-50 to-indigo-50">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between max-w-7xl mx-auto">
            <div className="flex items-center space-x-4">
              <h1
                className="text-2xl font-bold cursor-pointer"
                style={{ fontFamily: 'Space Grotesk', color: '#667eea' }}
                onClick={() => navigate('/')}
                data-testid="guest-logo"
              >
                RoomOps Guest
              </h1>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                const isActive = currentPath === item.id;
                return (
                  <Button
                    key={item.path}
                    variant={isActive ? 'default' : 'ghost'}
                    onClick={() => navigate(item.path)}
                    className="flex items-center space-x-2"
                    data-testid={`guest-nav-${item.id}`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.name}</span>
                  </Button>
                );
              })}
            </nav>

            {/* User Menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="outline" size="sm" data-testid="guest-user-menu">
                  <User className="w-4 h-4 mr-2" />
                  {user.name}
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuLabel>My Account</DropdownMenuLabel>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-sm">{user.email}</DropdownMenuItem>
                <DropdownMenuItem className="text-sm">{user.phone}</DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={onLogout} data-testid="guest-logout">
                  <LogOut className="w-4 h-4 mr-2" />
                  Logout
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto p-6">
        <Routes>
          {/* Home / Overview */}
          <Route
            path="/"
            element={
              <div className="space-y-6">
                <div>
                  <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>
                    Welcome, {user.name}
                  </h1>
                  <p className="text-gray-600">Your personalized travel hub</p>
                </div>

                {/* Quick Stats */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-gray-600">Active Bookings</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center">
                        <Calendar className="w-8 h-8 mr-3 text-blue-500" />
                        <div className="text-3xl font-bold">{activeBookings.length}</div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-gray-600">Total Loyalty Points</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center">
                        <Award className="w-8 h-8 mr-3 text-yellow-500" />
                        <div className="text-3xl font-bold">{totalPoints}</div>
                      </div>
                    </CardContent>
                  </Card>

                  <Card>
                    <CardHeader className="pb-2">
                      <CardTitle className="text-sm font-medium text-gray-600">Hotels Visited</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center">
                        <Hotel className="w-8 h-8 mr-3 text-purple-500" />
                        <div className="text-3xl font-bold">{loyaltyPrograms.length}</div>
                      </div>
                    </CardContent>
                  </Card>
                </div>

                {/* Active Bookings */}
                {activeBookings.length > 0 && (
                  <div>
                    <h2 className="text-2xl font-bold mb-4">Your Upcoming Stays</h2>
                    <div className="grid grid-cols-1 gap-4">
                      {activeBookings.slice(0, 3).map((booking) => (
                        <Card key={booking.id} className="card-hover">
                          <CardContent className="pt-6">
                            <div className="flex flex-wrap justify-between items-start gap-4">
                              <div className="flex-1">
                                <h3 className="text-xl font-bold mb-2">{booking.hotel?.property_name}</h3>
                                <div className="space-y-1 text-sm text-gray-600">
                                  <div className="flex items-center">
                                    <MapPin className="w-4 h-4 mr-2" />
                                    {booking.hotel?.address}
                                  </div>
                                  <div className="flex items-center">
                                    <Calendar className="w-4 h-4 mr-2" />
                                    {new Date(booking.check_in).toLocaleDateString()} - {new Date(booking.check_out).toLocaleDateString()}
                                  </div>
                                  <div className="flex items-center">
                                    <Hotel className="w-4 h-4 mr-2" />
                                    Room {booking.room?.room_number} ({booking.room?.room_type})
                                  </div>
                                </div>
                              </div>
                              <div className="flex flex-col items-end space-y-2">
                                <Button
                                  onClick={() => {
                                    setSelectedBooking(booking);
                                    setOpenDialog('qr');
                                  }}
                                  data-testid={`view-qr-${booking.id}`}
                                >
                                  <QrCode className="w-4 h-4 mr-2" />
                                  View QR Code
                                </Button>
                                <Button
                                  variant="outline"
                                  onClick={() => {
                                    setRoomServiceRequest({ ...roomServiceRequest, booking_id: booking.id });
                                    loadRoomServices(booking.id);
                                    setOpenDialog('room-service');
                                  }}
                                >
                                  <Utensils className="w-4 h-4 mr-2" />
                                  Room Service
                                </Button>
                              </div>
                            </div>
                          </CardContent>
                        </Card>
                      ))}
                    </div>
                    {activeBookings.length > 3 && (
                      <Button variant="outline" className="mt-4" onClick={() => navigate('/bookings')}>
                        View All Bookings
                      </Button>
                    )}
                  </div>
                )}
              </div>
            }
          />

          {/* Bookings Page */}
          <Route
            path="/bookings"
            element={
              <div className="space-y-6">
                <h1 className="text-4xl font-bold" style={{ fontFamily: 'Space Grotesk' }}>My Bookings</h1>
                
                <Tabs defaultValue="active">
                  <TabsList>
                    <TabsTrigger value="active">Active ({activeBookings.length})</TabsTrigger>
                    <TabsTrigger value="past">Past ({pastBookings.length})</TabsTrigger>
                  </TabsList>

                  <TabsContent value="active" className="space-y-4 mt-4">
                    {activeBookings.map((booking) => (
                      <Card key={booking.id}>
                        <CardContent className="pt-6">
                          <div className="flex flex-wrap justify-between items-start gap-4">
                            <div className="flex-1">
                              <h3 className="text-xl font-bold mb-2">{booking.hotel?.property_name}</h3>
                              <div className="space-y-1 text-sm text-gray-600">
                                <div className="flex items-center">
                                  <MapPin className="w-4 h-4 mr-2" />
                                  {booking.hotel?.address}
                                </div>
                                <div className="flex items-center">
                                  <Calendar className="w-4 h-4 mr-2" />
                                  Check-in: {new Date(booking.check_in).toLocaleDateString()}
                                </div>
                                <div className="flex items-center">
                                  <Calendar className="w-4 h-4 mr-2" />
                                  Check-out: {new Date(booking.check_out).toLocaleDateString()}
                                </div>
                                <div className="flex items-center">
                                  <Hotel className="w-4 h-4 mr-2" />
                                  Room {booking.room?.room_number} - {booking.room?.room_type}
                                </div>
                                <div className="flex items-center">
                                  <User className="w-4 h-4 mr-2" />
                                  {booking.guests_count} guest(s)
                                </div>
                              </div>
                            </div>
                            <div className="flex flex-col items-end space-y-2">
                              <div className="text-2xl font-bold text-blue-600">${booking.total_amount}</div>
                              <span className={`px-3 py-1 rounded-full text-xs font-medium ${
                                booking.status === 'confirmed' ? 'bg-green-100 text-green-700' :
                                booking.status === 'checked_in' ? 'bg-blue-100 text-blue-700' :
                                'bg-yellow-100 text-yellow-700'
                              }`}>
                                {booking.status.replace('_', ' ').toUpperCase()}
                              </span>
                              <Button
                                size="sm"
                                onClick={() => {
                                  setSelectedBooking(booking);
                                  setOpenDialog('qr');
                                }}
                              >
                                <QrCode className="w-4 h-4 mr-2" />
                                QR Code
                              </Button>
                              <Button
                                size="sm"
                                variant="outline"
                                onClick={() => {
                                  setRoomServiceRequest({ ...roomServiceRequest, booking_id: booking.id });
                                  loadRoomServices(booking.id);
                                  setOpenDialog('room-service');
                                }}
                              >
                                <Utensils className="w-4 h-4 mr-2" />
                                Room Service
                              </Button>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </TabsContent>

                  <TabsContent value="past" className="space-y-4 mt-4">
                    {pastBookings.map((booking) => (
                      <Card key={booking.id}>
                        <CardContent className="pt-6">
                          <div className="flex flex-wrap justify-between items-start gap-4">
                            <div className="flex-1">
                              <h3 className="text-xl font-bold mb-2">{booking.hotel?.property_name}</h3>
                              <div className="space-y-1 text-sm text-gray-600">
                                <div className="flex items-center">
                                  <Calendar className="w-4 h-4 mr-2" />
                                  {new Date(booking.check_in).toLocaleDateString()} - {new Date(booking.check_out).toLocaleDateString()}
                                </div>
                                <div className="flex items-center">
                                  <Hotel className="w-4 h-4 mr-2" />
                                  Room {booking.room?.room_number} - {booking.room?.room_type}
                                </div>
                              </div>
                            </div>
                            <div className="text-right">
                              <div className="text-xl font-bold text-gray-600">${booking.total_amount}</div>
                              <span className="text-xs text-gray-500">{booking.status.toUpperCase()}</span>
                            </div>
                          </div>
                        </CardContent>
                      </Card>
                    ))}
                  </TabsContent>
                </Tabs>
              </div>
            }
          />

          {/* Loyalty Page */}
          <Route
            path="/loyalty"
            element={
              <div className="space-y-6">
                <div>
                  <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>Loyalty Rewards</h1>
                  <p className="text-gray-600">Your points across all hotels</p>
                </div>

                <Card className="bg-gradient-to-r from-blue-500 to-purple-600 text-white">
                  <CardContent className="pt-6 pb-6">
                    <div className="text-center">
                      <div className="text-6xl font-bold mb-2">{totalPoints}</div>
                      <div className="text-xl">Total Points</div>
                    </div>
                  </CardContent>
                </Card>

                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                  {loyaltyPrograms.map((program) => (
                    <Card key={program.id}>
                      <CardHeader>
                        <div className="flex justify-between items-start">
                          <div>
                            <CardTitle>{program.hotel?.property_name}</CardTitle>
                            <CardDescription>{program.hotel?.address}</CardDescription>
                          </div>
                          <Award className="w-6 h-6 text-yellow-500" />
                        </div>
                      </CardHeader>
                      <CardContent className="space-y-4">
                        <div className="flex items-center justify-between">
                          <span className="text-sm text-gray-600">Tier</span>
                          <div className={`px-3 py-1 rounded-full text-xs font-medium flex items-center space-x-1 border ${getTierColor(program.tier)}`}>
                            {getTierStars(program.tier)}
                            <span className="ml-1 capitalize">{program.tier}</span>
                          </div>
                        </div>

                        <div className="text-center py-4 border-t border-b">
                          <div className="text-4xl font-bold text-blue-600">{program.points}</div>
                          <div className="text-sm text-gray-600 mt-1">Available Points</div>
                        </div>

                        <div className="text-sm">
                          <div className="flex justify-between">
                            <span className="text-gray-600">Lifetime Points</span>
                            <span className="font-medium">{program.lifetime_points}</span>
                          </div>
                        </div>
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            }
          />

          {/* Settings Page */}
          <Route
            path="/settings"
            element={
              <div className="space-y-6">
                <h1 className="text-4xl font-bold" style={{ fontFamily: 'Space Grotesk' }}>Settings</h1>

                <Card>
                  <CardHeader>
                    <CardTitle>Notification Preferences</CardTitle>
                    <CardDescription>Manage how you receive updates</CardDescription>
                  </CardHeader>
                  <CardContent className="space-y-4">
                    {notificationPrefs && (
                      <>
                        <div className="flex items-center justify-between">
                          <div className="space-y-0.5">
                            <Label>Email Notifications</Label>
                            <p className="text-sm text-gray-500">Receive updates via email</p>
                          </div>
                          <Switch
                            checked={notificationPrefs.email_notifications}
                            onCheckedChange={(checked) => updateNotificationPref('email_notifications', checked)}
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <div className="space-y-0.5">
                            <Label>WhatsApp Notifications</Label>
                            <p className="text-sm text-gray-500">Get messages on WhatsApp</p>
                          </div>
                          <Switch
                            checked={notificationPrefs.whatsapp_notifications}
                            onCheckedChange={(checked) => updateNotificationPref('whatsapp_notifications', checked)}
                          />
                        </div>

                        <div className="flex items-center justify-between">
                          <div className="space-y-0.5">
                            <Label>In-App Notifications</Label>
                            <p className="text-sm text-gray-500">See updates in the app</p>
                          </div>
                          <Switch
                            checked={notificationPrefs.in_app_notifications}
                            onCheckedChange={(checked) => updateNotificationPref('in_app_notifications', checked)}
                          />
                        </div>

                        <div className="border-t pt-4 mt-4">
                          <h3 className="font-semibold mb-3">Notification Types</h3>
                          
                          <div className="flex items-center justify-between mb-3">
                            <Label>Booking Updates</Label>
                            <Switch
                              checked={notificationPrefs.booking_updates}
                              onCheckedChange={(checked) => updateNotificationPref('booking_updates', checked)}
                            />
                          </div>

                          <div className="flex items-center justify-between mb-3">
                            <Label>Room Service Updates</Label>
                            <Switch
                              checked={notificationPrefs.room_service_updates}
                              onCheckedChange={(checked) => updateNotificationPref('room_service_updates', checked)}
                            />
                          </div>

                          <div className="flex items-center justify-between">
                            <Label>Promotional Offers</Label>
                            <Switch
                              checked={notificationPrefs.promotional}
                              onCheckedChange={(checked) => updateNotificationPref('promotional', checked)}
                            />
                          </div>
                        </div>
                      </>
                    )}
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader>
                    <CardTitle>Account Information</CardTitle>
                  </CardHeader>
                  <CardContent className="space-y-3">
                    <div>
                      <Label>Name</Label>
                      <div className="text-sm text-gray-700 mt-1">{user.name}</div>
                    </div>
                    <div>
                      <Label>Email</Label>
                      <div className="text-sm text-gray-700 mt-1">{user.email}</div>
                    </div>
                    <div>
                      <Label>Phone</Label>
                      <div className="text-sm text-gray-700 mt-1">{user.phone}</div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            }
          />
        </Routes>
      </main>

      {/* QR Code Dialog */}
      <Dialog open={openDialog === 'qr'} onOpenChange={(open) => !open && setOpenDialog(null)}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Your Booking QR Code</DialogTitle>
            <DialogDescription>Show this at the hotel for quick check-in</DialogDescription>
          </DialogHeader>
          {selectedBooking && (
            <div className="space-y-4">
              <div className="text-center">
                <h3 className="font-semibold text-lg mb-2">{selectedBooking.hotel?.property_name}</h3>
                <p className="text-sm text-gray-600 mb-4">
                  Room {selectedBooking.room?.room_number}
                </p>
                {selectedBooking.qr_code && (
                  <img 
                    src={selectedBooking.qr_code} 
                    alt="Booking QR Code" 
                    className="mx-auto border rounded-lg p-4"
                    style={{ maxWidth: '300px' }}
                  />
                )}
                <p className="text-xs text-gray-500 mt-4">
                  This QR code is valid for your entire stay
                </p>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Room Service Dialog */}
      <Dialog open={openDialog === 'room-service'} onOpenChange={(open) => !open && setOpenDialog(null)}>
        <DialogContent className="max-w-2xl">
          <DialogHeader>
            <DialogTitle>Room Service Request</DialogTitle>
            <DialogDescription>Request services for your room</DialogDescription>
          </DialogHeader>
          
          <Tabs defaultValue="request">
            <TabsList className="grid w-full grid-cols-2">
              <TabsTrigger value="request">New Request</TabsTrigger>
              <TabsTrigger value="history">My Requests</TabsTrigger>
            </TabsList>

            <TabsContent value="request">
              <form onSubmit={handleRoomServiceRequest} className="space-y-4">
                <div>
                  <Label htmlFor="service-type">Service Type</Label>
                  <Select 
                    value={roomServiceRequest.service_type} 
                    onValueChange={(v) => setRoomServiceRequest({...roomServiceRequest, service_type: v})}
                  >
                    <SelectTrigger id="service-type">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="housekeeping">Housekeeping</SelectItem>
                      <SelectItem value="food">Food & Beverage</SelectItem>
                      <SelectItem value="maintenance">Maintenance</SelectItem>
                      <SelectItem value="laundry">Laundry</SelectItem>
                      <SelectItem value="concierge">Concierge</SelectItem>
                      <SelectItem value="other">Other</SelectItem>
                    </SelectContent>
                  </Select>
                </div>

                <div>
                  <Label htmlFor="description">Description</Label>
                  <Input
                    id="description"
                    value={roomServiceRequest.description}
                    onChange={(e) => setRoomServiceRequest({...roomServiceRequest, description: e.target.value})}
                    placeholder="Brief description of your request"
                    required
                  />
                </div>

                <div>
                  <Label htmlFor="notes">Additional Notes</Label>
                  <Textarea
                    id="notes"
                    value={roomServiceRequest.notes}
                    onChange={(e) => setRoomServiceRequest({...roomServiceRequest, notes: e.target.value})}
                    placeholder="Any special instructions..."
                    rows={3}
                  />
                </div>

                <Button type="submit" className="w-full">Submit Request</Button>
              </form>
            </TabsContent>

            <TabsContent value="history">
              <div className="space-y-3 max-h-96 overflow-y-auto">
                {roomServices[roomServiceRequest.booking_id]?.map((service) => (
                  <Card key={service.id}>
                    <CardContent className="pt-4">
                      <div className="flex justify-between items-start">
                        <div>
                          <div className="font-semibold capitalize">{service.service_type}</div>
                          <div className="text-sm text-gray-600">{service.description}</div>
                          {service.notes && (
                            <div className="text-xs text-gray-500 mt-1">{service.notes}</div>
                          )}
                          <div className="text-xs text-gray-400 mt-2">
                            {new Date(service.created_at).toLocaleString()}
                          </div>
                        </div>
                        <span className={`px-2 py-1 rounded text-xs font-medium ${
                          service.status === 'completed' ? 'bg-green-100 text-green-700' :
                          service.status === 'in_progress' ? 'bg-blue-100 text-blue-700' :
                          service.status === 'cancelled' ? 'bg-red-100 text-red-700' :
                          'bg-yellow-100 text-yellow-700'
                        }`}>
                          {service.status.replace('_', ' ')}
                        </span>
                      </div>
                    </CardContent>
                  </Card>
                ))}
                {(!roomServices[roomServiceRequest.booking_id] || roomServices[roomServiceRequest.booking_id].length === 0) && (
                  <p className="text-center text-gray-500 py-8">No requests yet</p>
                )}
              </div>
            </TabsContent>
          </Tabs>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default GuestPortal;
