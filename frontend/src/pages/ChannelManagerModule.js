import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { 
  Network, 
  Plus, 
  Download, 
  AlertTriangle, 
  CheckCircle, 
  Clock,
  XCircle,
  RefreshCw,
  Settings
} from 'lucide-react';

const ChannelManagerModule = ({ user, tenant, onLogout }) => {
  const { t } = useTranslation();
  const [activeTab, setActiveTab] = useState('connections');
  
  // Connections state
  const [connections, setConnections] = useState([]);
  const [showAddConnection, setShowAddConnection] = useState(false);
  const [newConnection, setNewConnection] = useState({
    channel_type: 'booking_com',
    channel_name: '',
    property_id: '',
    api_key: '',
    api_secret: '',
    status: 'active'
  });
  
  // OTA Reservations state
  const [otaReservations, setOtaReservations] = useState([]);
  const [reservationFilter, setReservationFilter] = useState('pending');
  
  // Exceptions state
  const [exceptions, setExceptions] = useState([]);
  const [exceptionFilter, setExceptionFilter] = useState('all');
  
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadConnections();
    loadOtaReservations();
    loadExceptions();
  }, []);

  const loadConnections = async () => {
    try {
      const response = await axios.get('/api/channel-manager/connections');
      setConnections(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Failed to load connections:', error);
      setConnections([]);
    }
  };

  const loadOtaReservations = async () => {
    try {
      const response = await axios.get(`/channel-manager/ota-reservations?status=${reservationFilter}`);
      setOtaReservations(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Failed to load OTA reservations:', error);
      setOtaReservations([]);
    }
  };

  const loadExceptions = async () => {
    try {
      const url = exceptionFilter === 'all' 
        ? '/channel-manager/exceptions'
        : `/channel-manager/exceptions?status=${exceptionFilter}`;
      const response = await axios.get(url);
      setExceptions(Array.isArray(response.data) ? response.data : []);
    } catch (error) {
      console.error('Failed to load exceptions:', error);
      setExceptions([]);
    }
  };

  const handleAddConnection = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      await axios.post('/api/channel-manager/connections', newConnection);
      toast.success('Channel connection added successfully!');
      setShowAddConnection(false);
      setNewConnection({
        channel_type: 'booking_com',
        channel_name: '',
        property_id: '',
        api_key: '',
        api_secret: '',
        status: 'active'
      });
      loadConnections();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add connection');
    } finally {
      setLoading(false);
    }
  };

  const handleImportReservation = async (otaId) => {
    setLoading(true);
    try {
      await axios.post(`/channel-manager/import-reservation/${otaId}`);
      toast.success('Reservation imported successfully!');
      loadOtaReservations();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to import reservation');
    } finally {
      setLoading(false);
    }
  };

  const getStatusBadge = (status) => {
    const statusConfig = {
      active: { color: 'bg-green-500', label: 'Active' },
      inactive: { color: 'bg-gray-500', label: 'Inactive' },
      error: { color: 'bg-red-500', label: 'Error' },
      pending: { color: 'bg-yellow-500', label: 'Pending' },
      imported: { color: 'bg-blue-500', label: 'Imported' },
      failed: { color: 'bg-red-500', label: 'Failed' }
    };
    
    const config = statusConfig[status] || statusConfig.pending;
    return <Badge className={config.color}>{config.label}</Badge>;
  };

  const channelLogos = {
    booking_com: '🅱️',
    expedia: '🅴',
    airbnb: '🅰️',
    agoda: '🅰️',
    tripadvisor: '🅣'
  };

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="channel-manager">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>
              Channel Manager
            </h1>
            <p className="text-gray-600">Manage OTA connections and reservations</p>
          </div>
          <Dialog open={showAddConnection} onOpenChange={setShowAddConnection}>
            <DialogTrigger asChild>
              <Button>
                <Plus className="w-4 h-4 mr-2" />
                Add Connection
              </Button>
            </DialogTrigger>
            <DialogContent className="max-w-lg">
              <DialogHeader>
                <DialogTitle>Add Channel Connection</DialogTitle>
              </DialogHeader>
              <form onSubmit={handleAddConnection} className="space-y-4">
                <div>
                  <Label>Channel Type</Label>
                  <select
                    className="w-full border rounded-md p-2"
                    value={newConnection.channel_type}
                    onChange={(e) => setNewConnection({...newConnection, channel_type: e.target.value})}
                  >
                    <option value="booking_com">Booking.com</option>
                    <option value="expedia">Expedia</option>
                    <option value="airbnb">Airbnb</option>
                    <option value="agoda">Agoda</option>
                    <option value="tripadvisor">TripAdvisor</option>
                  </select>
                </div>
                <div>
                  <Label>Channel Name</Label>
                  <Input
                    value={newConnection.channel_name}
                    onChange={(e) => setNewConnection({...newConnection, channel_name: e.target.value})}
                    placeholder="e.g., Grand Hotel Istanbul"
                    required
                  />
                </div>
                <div>
                  <Label>Property ID</Label>
                  <Input
                    value={newConnection.property_id}
                    onChange={(e) => setNewConnection({...newConnection, property_id: e.target.value})}
                    placeholder="Property/Hotel ID from OTA"
                    required
                  />
                </div>
                <div>
                  <Label>API Key</Label>
                  <Input
                    value={newConnection.api_key}
                    onChange={(e) => setNewConnection({...newConnection, api_key: e.target.value})}
                    placeholder="API Key"
                  />
                </div>
                <div>
                  <Label>API Secret</Label>
                  <Input
                    type="password"
                    value={newConnection.api_secret}
                    onChange={(e) => setNewConnection({...newConnection, api_secret: e.target.value})}
                    placeholder="API Secret"
                  />
                </div>
                <Button type="submit" className="w-full" disabled={loading}>
                  {loading ? 'Adding...' : 'Add Connection'}
                </Button>
              </form>
            </DialogContent>
          </Dialog>
        </div>

        {/* Tabs */}
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="connections">
              <Network className="w-4 h-4 mr-2" />
              Connections
            </TabsTrigger>
            <TabsTrigger value="rates">
              <Settings className="w-4 h-4 mr-2" />
              Rate & Availability
            </TabsTrigger>
            <TabsTrigger value="reservations">
              <Download className="w-4 h-4 mr-2" />
              OTA Reservations
            </TabsTrigger>
            <TabsTrigger value="exceptions">
              <AlertTriangle className="w-4 h-4 mr-2" />
              Exceptions
            </TabsTrigger>
          </TabsList>

          {/* Connections Tab */}
          <TabsContent value="connections" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Active Connections</CardTitle>
                <CardDescription>
                  Manage your OTA channel connections and credentials
                </CardDescription>
              </CardHeader>
              <CardContent>
                {connections.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Network className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No channel connections yet</p>
                    <p className="text-sm">Add your first connection to start receiving OTA reservations</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {connections.map((conn) => (
                      <div key={conn.id} className="border rounded-lg p-4 flex items-center justify-between">
                        <div className="flex items-center space-x-4">
                          <div className="text-4xl">
                            {channelLogos[conn.channel_type] || '🌐'}
                          </div>
                          <div>
                            <h3 className="font-semibold text-lg">{conn.channel_name}</h3>
                            <p className="text-sm text-gray-600">
                              Property ID: {conn.property_id}
                            </p>
                            <p className="text-sm text-gray-600">
                              Type: {conn.channel_type.replace('_', '.')}
                            </p>
                          </div>
                        </div>
                        <div className="flex items-center space-x-4">
                          {getStatusBadge(conn.status)}
                          <Button variant="outline" size="sm">
                            <Settings className="w-4 h-4" />
                          </Button>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>


          {/* Rate & Availability Tab */}
          <TabsContent value="rates" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Rate & Availability Management</CardTitle>
                <CardDescription>
                  Update room rates, availability, and restrictions across all channels
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-6">
                {/* Room Type Selector */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Room Type</Label>
                    <select className="w-full border rounded-md p-2 mt-1">
                      <option value="standard">Standard Room</option>
                      <option value="deluxe">Deluxe Room</option>
                      <option value="suite">Suite</option>
                    </select>
                  </div>
                  <div>
                    <Label>Date Range</Label>
                    <div className="flex space-x-2 mt-1">
                      <Input type="date" />
                      <Input type="date" />
                    </div>
                  </div>
                </div>

                {/* Rate Settings */}
                <Card className="border-blue-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Rate Settings</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <Label>Base Rate (₺)</Label>
                        <Input
                          type="number"
                          placeholder="0.00"
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label>Discount (%)</Label>
                        <Input
                          type="number"
                          placeholder="0"
                          min="0"
                          max="100"
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label>Final Rate (₺)</Label>
                        <Input
                          type="number"
                          placeholder="0.00"
                          className="mt-1"
                          disabled
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Availability Settings */}
                <Card className="border-green-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Availability Settings</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <Label>Available Rooms</Label>
                        <Input
                          type="number"
                          placeholder="0"
                          min="0"
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label>Stop Sell</Label>
                        <select className="w-full border rounded-md p-2 mt-1">
                          <option value="open">Open</option>
                          <option value="closed">Closed</option>
                        </select>
                      </div>
                      <div>
                        <Label>Closed to Arrival</Label>
                        <select className="w-full border rounded-md p-2 mt-1">
                          <option value="no">No</option>
                          <option value="yes">Yes</option>
                        </select>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Restrictions */}
                <Card className="border-purple-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Restrictions</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      <div>
                        <Label>Minimum Stay</Label>
                        <Input
                          type="number"
                          placeholder="1"
                          min="1"
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label>Maximum Stay</Label>
                        <Input
                          type="number"
                          placeholder="30"
                          min="1"
                          className="mt-1"
                        />
                      </div>
                      <div>
                        <Label>Closed to Departure</Label>
                        <select className="w-full border rounded-md p-2 mt-1">
                          <option value="no">No</option>
                          <option value="yes">Yes</option>
                        </select>
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* Channel Selection */}
                <Card className="border-orange-200">
                  <CardHeader className="pb-3">
                    <CardTitle className="text-lg">Apply to Channels</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="space-y-2">
                      <label className="flex items-center space-x-2">
                        <input type="checkbox" className="rounded" defaultChecked />
                        <span>All Channels</span>
                      </label>
                      <label className="flex items-center space-x-2">
                        <input type="checkbox" className="rounded" />
                        <span>Booking.com</span>
                      </label>
                      <label className="flex items-center space-x-2">
                        <input type="checkbox" className="rounded" />
                        <span>Expedia</span>
                      </label>
                      <label className="flex items-center space-x-2">
                        <input type="checkbox" className="rounded" />
                        <span>Airbnb</span>
                      </label>
                    </div>
                  </CardContent>
                </Card>

                {/* Action Buttons */}
                <div className="flex justify-end space-x-3 pt-4">
                  <Button variant="outline">
                    Preview Changes
                  </Button>
                  <Button className="bg-blue-600 hover:bg-blue-700">
                    <RefreshCw className="w-4 h-4 mr-2" />
                    Update All Channels
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* OTA Reservations Tab */}
          <TabsContent value="reservations" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>OTA Reservations</CardTitle>
                    <CardDescription>
                      Import reservations from connected channels
                    </CardDescription>
                  </div>
                  <div className="flex space-x-2">
                    <Button
                      variant={reservationFilter === 'pending' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => {
                        setReservationFilter('pending');
                        setTimeout(() => loadOtaReservations(), 100);
                      }}
                    >
                      Pending
                    </Button>
                    <Button
                      variant={reservationFilter === 'imported' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => {
                        setReservationFilter('imported');
                        setTimeout(() => loadOtaReservations(), 100);
                      }}
                    >
                      Imported
                    </Button>
                    <Button
                      variant={reservationFilter === 'failed' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => {
                        setReservationFilter('failed');
                        setTimeout(() => loadOtaReservations(), 100);
                      }}
                    >
                      Failed
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {otaReservations.length === 0 ? (
                  <div className="text-center py-8 text-gray-500">
                    <Download className="w-12 h-12 mx-auto mb-4 opacity-50" />
                    <p>No {reservationFilter} reservations</p>
                    <p className="text-sm">OTA reservations will appear here automatically</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {otaReservations.map((reservation) => (
                      <div key={reservation.id} className="border rounded-lg p-4">
                        <div className="flex justify-between items-start">
                          <div className="space-y-2">
                            <div className="flex items-center space-x-2">
                              <h3 className="font-semibold">{reservation.guest_name}</h3>
                              {getStatusBadge(reservation.status)}
                            </div>
                            <div className="text-sm text-gray-600 space-y-1">
                              <p>📧 {reservation.guest_email}</p>
                              <p>📞 {reservation.guest_phone}</p>
                              <p>🏨 Room: {reservation.room_type}</p>
                              <p>📅 {reservation.check_in} → {reservation.check_out}</p>
                              <p>💰 ${reservation.total_amount}</p>
                              <p className="text-xs text-gray-500">
                                Channel: {reservation.channel_type} | OTA ID: {reservation.ota_booking_id}
                              </p>
                            </div>
                          </div>
                          <div className="space-y-2">
                            {reservation.status === 'pending' && (
                              <Button
                                size="sm"
                                onClick={() => handleImportReservation(reservation.id)}
                                disabled={loading}
                              >
                                <Download className="w-4 h-4 mr-2" />
                                Import
                              </Button>
                            )}
                            {reservation.status === 'imported' && (
                              <div className="flex items-center text-green-600 text-sm">
                                <CheckCircle className="w-4 h-4 mr-1" />
                                Imported
                              </div>
                            )}
                            {reservation.status === 'failed' && (
                              <div className="flex items-center text-red-600 text-sm">
                                <XCircle className="w-4 h-4 mr-1" />
                                Failed
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Exceptions Tab */}
          <TabsContent value="exceptions" className="space-y-4">
            <Card>
              <CardHeader>
                <div className="flex justify-between items-center">
                  <div>
                    <CardTitle>Exception Queue</CardTitle>
                    <CardDescription>
                      Review and resolve channel integration issues
                    </CardDescription>
                  </div>
                  <div className="flex space-x-2">
                    <Button
                      variant={exceptionFilter === 'all' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => {
                        setExceptionFilter('all');
                        setTimeout(() => loadExceptions(), 100);
                      }}
                    >
                      All
                    </Button>
                    <Button
                      variant={exceptionFilter === 'pending' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => {
                        setExceptionFilter('pending');
                        setTimeout(() => loadExceptions(), 100);
                      }}
                    >
                      Pending
                    </Button>
                    <Button
                      variant={exceptionFilter === 'resolved' ? 'default' : 'outline'}
                      size="sm"
                      onClick={() => {
                        setExceptionFilter('resolved');
                        setTimeout(() => loadExceptions(), 100);
                      }}
                    >
                      Resolved
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                {exceptions.length === 0 ? (
                  <div className="text-center py-8 text-green-600">
                    <CheckCircle className="w-12 h-12 mx-auto mb-4" />
                    <p className="font-semibold">No Exceptions!</p>
                    <p className="text-sm">All channel operations are running smoothly</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                    {exceptions.map((exception) => (
                      <div key={exception.id} className="border border-red-200 rounded-lg p-4 bg-red-50">
                        <div className="flex justify-between items-start">
                          <div className="space-y-2">
                            <div className="flex items-center space-x-2">
                              <AlertTriangle className="w-5 h-5 text-red-600" />
                              <h3 className="font-semibold text-red-900">
                                {exception.exception_type.replace(/_/g, ' ').toUpperCase()}
                              </h3>
                              {getStatusBadge(exception.status)}
                            </div>
                            <p className="text-sm text-red-800">{exception.error_message}</p>
                            <div className="text-xs text-red-600 space-y-1">
                              <p>Channel: {exception.channel_type}</p>
                              <p>Time: {new Date(exception.created_at).toLocaleString()}</p>
                              {exception.ota_booking_id && (
                                <p>OTA Booking: {exception.ota_booking_id}</p>
                              )}
                            </div>
                          </div>
                          <div className="space-y-2">
                            {exception.status === 'pending' && (
                              <Button size="sm" variant="outline">
                                <RefreshCw className="w-4 h-4 mr-2" />
                                Retry
                              </Button>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
};

export default ChannelManagerModule;
