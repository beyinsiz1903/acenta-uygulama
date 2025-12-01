import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Settings as SettingsIcon, Mail, MessageSquare, Phone, Key, AlertCircle, Cloud, RefreshCw, Server, Trash2 } from 'lucide-react';

const Settings = ({ user, tenant, onLogout }) => {
  const [integrations, setIntegrations] = useState({
    sendgrid: { enabled: false, api_key: '' },
    twilio: { enabled: false, account_sid: '', auth_token: '', phone_number: '' },
    whatsapp: { enabled: false, account_sid: '', auth_token: '' }
  });

  const [saving, setSaving] = useState(false);
  const [bookingCreds, setBookingCreds] = useState({
    property_id: '',
    username: '',
    password: '',
    settings: { base_url: '' }
  });
  const [bookingLoading, setBookingLoading] = useState(false);
  const [bookingLogs, setBookingLogs] = useState([]);
  const [ariRoom, setAriRoom] = useState({
    room_code: 'DLX',
    rate_plan: 'BAR',
    date: new Date().toISOString().slice(0, 10),
    price: 150,
    currency: 'EUR',
    min_stay: 1,
    closed: false
  });
  const [roomMappings, setRoomMappings] = useState([]);
  const [newMapping, setNewMapping] = useState({
    channel_room_type: '',
    pms_room_type: ''
  });

  const saveIntegration = async (type, config) => {
    setSaving(true);
    try {
      await axios.post(`/settings/integrations/${type}`, config);
      toast.success(`${type} integration saved successfully!`);
      setIntegrations({
        ...integrations,
        [type]: { ...integrations[type], ...config }
      });
    } catch (error) {
      toast.error('Failed to save integration settings');
    } finally {
      setSaving(false);
    }
  };

  const loadBookingCreds = async () => {
    try {
      setBookingLoading(true);
      const res = await axios.get('/ota/booking/credentials');
      setBookingCreds({
        property_id: res.data.property_id || '',
        username: res.data.username || '',
        password: '',
        settings: res.data.settings || { base_url: '' }
      });
    } catch (error) {
      // 404 simply means not configured yet
    } finally {
      setBookingLoading(false);
    }
  };

  const loadBookingLogs = async () => {
    try {
      const res = await axios.get('/ota/booking/logs?limit=10');
      setBookingLogs(res.data.items || []);
    } catch (error) {
      console.error('Failed to load booking logs', error);
    }
  };

  useEffect(() => {
    loadBookingCreds();
    loadBookingLogs();
    loadRoomMappings();
  }, []);

  const saveBookingCredentials = async () => {
    try {
      setBookingLoading(true);
      await axios.post('/ota/booking/credentials', {
        property_id: bookingCreds.property_id,
        username: bookingCreds.username,
        password: bookingCreds.password,
        settings: bookingCreds.settings
      });
      toast.success('Booking.com credentials saved');
      await loadBookingCreds();
    } catch (error) {
      toast.error('Failed to save Booking.com credentials');
    } finally {
      setBookingLoading(false);
    }
  };

  const triggerAriPush = async () => {
    try {
      await axios.post('/ota/booking/ari/push', { rooms: [ariRoom] });
      toast.success('ARI push queued');
      loadBookingLogs();
    } catch (error) {
      toast.error('ARI push failed');
    }
  };

  const triggerReservationPull = async () => {
    try {
      await axios.post('/ota/booking/reservations/pull');
      toast.success('Reservation pull queued');
      loadBookingLogs();
    } catch (error) {
      toast.error('Reservation pull failed');
    }
  };

  const loadRoomMappings = async () => {
    try {
      const res = await axios.get('/ota/room-mappings');
      setRoomMappings(res.data.mappings || []);
    } catch (error) {
      console.error('Failed to load room mappings', error);
    }
  };

  const addRoomMapping = async () => {
    try {
      await axios.post('/ota/room-mappings', {
        channel_name: 'booking',
        channel_room_type: newMapping.channel_room_type,
        pms_room_type: newMapping.pms_room_type
      });
      toast.success('Room mapping added');
      setNewMapping({ channel_room_type: '', pms_room_type: '' });
      await loadRoomMappings();
    } catch (error) {
      toast.error('Failed to add room mapping');
    }
  };

  const removeRoomMapping = async (mappingId) => {
    try {
      await axios.delete(`/ota/room-mappings/${mappingId}`);
      toast.success('Room mapping removed');
      await loadRoomMappings();
    } catch (error) {
      toast.error('Failed to remove room mapping');
    }
  };

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="settings">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold flex items-center gap-3">
              <SettingsIcon className="w-8 h-8 text-blue-600" />
              Settings & Integrations
            </h1>
            <p className="text-gray-600 mt-2">Configure external services and API integrations</p>
          </div>
        </div>

        <Tabs defaultValue="integrations" className="space-y-4">
          <TabsList>
            <TabsTrigger value="integrations">🔌 Integrations</TabsTrigger>
            <TabsTrigger value="general">⚙️ General</TabsTrigger>
            <TabsTrigger value="ota">🌐 OTA</TabsTrigger>
          </TabsList>

          <TabsContent value="integrations" className="space-y-4">
            {/* SendGrid Email */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Mail className="w-5 h-5" />
                  SendGrid Email Service
                </CardTitle>
                <CardDescription>
                  Configure SendGrid for sending emails to guests
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
                  <div className="text-sm font-semibold text-blue-900 mb-2">📖 How to get API Key:</div>
                  <ol className="text-sm text-gray-700 space-y-1 list-decimal list-inside">
                    <li>Go to <a href="https://sendgrid.com" target="_blank" rel="noopener" className="text-blue-600 underline">sendgrid.com</a> and sign up/login</li>
                    <li>Navigate to Settings → API Keys</li>
                    <li>Click "Create API Key"</li>
                    <li>Give it a name and select "Full Access"</li>
                    <li>Copy the API key and paste below</li>
                  </ol>
                </div>

                <div>
                  <Label>SendGrid API Key</Label>
                  <Input 
                    type="password"
                    value={integrations.sendgrid.api_key}
                    onChange={(e) => setIntegrations({
                      ...integrations,
                      sendgrid: { ...integrations.sendgrid, api_key: e.target.value }
                    })}
                    placeholder="SG.xxxxxxxxxxxxxxxxxxxxxxxxx"
                  />
                </div>

                <div className="flex items-center gap-3">
                  <Button 
                    onClick={() => saveIntegration('sendgrid', integrations.sendgrid)}
                    disabled={saving || !integrations.sendgrid.api_key}
                  >
                    <Key className="w-4 h-4 mr-2" />
                    Save SendGrid Config
                  </Button>
                  <Badge variant={integrations.sendgrid.enabled ? "success" : "secondary"}>
                    {integrations.sendgrid.enabled ? 'Active' : 'Not Configured'}
                  </Badge>
                </div>
              </CardContent>
            </Card>

            {/* Twilio SMS */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Phone className="w-5 h-5" />
                  Twilio SMS Service
                </CardTitle>
                <CardDescription>
                  Configure Twilio for sending SMS messages
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-purple-50 p-4 rounded-lg border border-purple-200">
                  <div className="text-sm font-semibold text-purple-900 mb-2">📖 How to get Twilio Credentials:</div>
                  <ol className="text-sm text-gray-700 space-y-1 list-decimal list-inside">
                    <li>Go to <a href="https://twilio.com" target="_blank" rel="noopener" className="text-purple-600 underline">twilio.com</a> and sign up/login</li>
                    <li>Go to Console Dashboard</li>
                    <li>Copy Account SID and Auth Token</li>
                    <li>Get a phone number from Phone Numbers → Buy a Number</li>
                    <li>Paste all credentials below</li>
                  </ol>
                </div>

                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label>Account SID</Label>
                    <Input 
                      value={integrations.twilio.account_sid}
                      onChange={(e) => setIntegrations({
                        ...integrations,
                        twilio: { ...integrations.twilio, account_sid: e.target.value }
                      })}
                      placeholder="ACxxxxxxxxxxxxxxxxxxxxxxxx"
                    />
                  </div>
                  <div>
                    <Label>Auth Token</Label>
                    <Input 
                      type="password"
                      value={integrations.twilio.auth_token}
                      onChange={(e) => setIntegrations({
                        ...integrations,
                        twilio: { ...integrations.twilio, auth_token: e.target.value }
                      })}
                      placeholder="xxxxxxxxxxxxxxxxxxxxxxxxxx"
                    />
                  </div>
                  <div className="col-span-2">
                    <Label>Phone Number</Label>
                    <Input 
                      value={integrations.twilio.phone_number}
                      onChange={(e) => setIntegrations({
                        ...integrations,
                        twilio: { ...integrations.twilio, phone_number: e.target.value }
                      })}
                      placeholder="+1234567890"
                    />
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Button 
                    onClick={() => saveIntegration('twilio', integrations.twilio)}
                    disabled={saving || !integrations.twilio.account_sid || !integrations.twilio.auth_token}
                  >
                    <Key className="w-4 h-4 mr-2" />
                    Save Twilio Config
                  </Button>
                  <Badge variant={integrations.twilio.enabled ? "success" : "secondary"}>
                    {integrations.twilio.enabled ? 'Active' : 'Not Configured'}
                  </Badge>
                </div>
              </CardContent>
            </Card>

            {/* WhatsApp */}
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <MessageSquare className="w-5 h-5" />
                  WhatsApp Business API
                </CardTitle>
                <CardDescription>
                  Configure WhatsApp for sending messages via Twilio
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="bg-green-50 p-4 rounded-lg border border-green-200">
                  <div className="text-sm font-semibold text-green-900 mb-2">📖 How to setup WhatsApp:</div>
                  <ol className="text-sm text-gray-700 space-y-1 list-decimal list-inside">
                    <li>WhatsApp Business API requires Twilio credentials (configure above first)</li>
                    <li>Go to Twilio Console → Messaging → WhatsApp Senders</li>
                    <li>Follow the setup wizard to connect your WhatsApp Business account</li>
                    <li>Once approved, use the same Twilio credentials</li>
                  </ol>
                </div>

                <div className="bg-amber-50 p-3 rounded-lg border border-amber-200 flex items-start gap-2">
                  <AlertCircle className="w-5 h-5 text-amber-600 flex-shrink-0 mt-0.5" />
                  <div className="text-sm text-amber-900">
                    <strong>Note:</strong> WhatsApp Business API requires approval from Meta/Facebook. This process can take several days.
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <Badge variant={integrations.whatsapp.enabled ? "success" : "secondary"}>
                    {integrations.whatsapp.enabled ? 'Active' : 'Use Twilio Credentials'}
                  </Badge>
                </div>
              </CardContent>
            </Card>

            {/* Info Card */}
            <Card className="border-blue-200 bg-blue-50">
              <CardContent className="pt-6">
                <div className="flex items-start gap-3">
                  <AlertCircle className="w-6 h-6 text-blue-600 flex-shrink-0" />
                  <div className="text-sm text-gray-700 space-y-2">
                    <p className="font-semibold text-blue-900">💡 Integration Tips:</p>
                    <ul className="list-disc list-inside space-y-1">
                      <li>All API keys are encrypted and stored securely</li>
                      <li>Test your integrations in the Messages module after configuration</li>
                      <li>You can disable integrations anytime by clearing the API keys</li>
                      <li>For production use, consider setting up separate API keys with restricted permissions</li>
                    </ul>
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="general">
            <Card>
              <CardHeader>
                <CardTitle>General Settings</CardTitle>
                <CardDescription>Coming soon...</CardDescription>
              </CardHeader>
            </Card>
          </TabsContent>

          <TabsContent value="ota" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Cloud className="w-5 h-5" />
                  Booking.com Credentials
                </CardTitle>
                <CardDescription>
                  Store property credentials to enable ARI push and reservation sync
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label>Property ID</Label>
                    <Input
                      value={bookingCreds.property_id}
                      onChange={(e) => setBookingCreds({ ...bookingCreds, property_id: e.target.value })}
                      placeholder="1234567"
                    />
                  </div>
                  <div>
                    <Label>Base URL</Label>
                    <Input
                      value={bookingCreds.settings?.base_url || ''}
                      onChange={(e) =>
                        setBookingCreds({
                          ...bookingCreds,
                          settings: { ...bookingCreds.settings, base_url: e.target.value }
                        })
                      }
                      placeholder="https://distribution.booking.com"
                    />
                  </div>
                  <div>
                    <Label>Username</Label>
                    <Input
                      value={bookingCreds.username}
                      onChange={(e) => setBookingCreds({ ...bookingCreds, username: e.target.value })}
                      placeholder="api_user"
                    />
                  </div>
                  <div>
                    <Label>Password</Label>
                    <Input
                      type="password"
                      value={bookingCreds.password}
                      onChange={(e) => setBookingCreds({ ...bookingCreds, password: e.target.value })}
                      placeholder="********"
                    />
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <Button onClick={saveBookingCredentials} disabled={bookingLoading}>
                    {bookingLoading ? <RefreshCw className="w-4 h-4 mr-2 animate-spin" /> : <Key className="w-4 h-4 mr-2" />}
                    Save Credentials
                  </Button>
                  <Button variant="outline" size="sm" onClick={loadBookingCreds}>
                    Reload
                  </Button>
                </div>
              </CardContent>
            </Card>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center gap-2">
                    <Server className="w-4 h-4" />
                    ARI Push
                  </CardTitle>
                  <CardDescription>Send availability/rate updates to Booking.com</CardDescription>
                </CardHeader>
                <CardContent className="space-y-4">
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <Label>Room Code</Label>
                      <Input
                        value={ariRoom.room_code}
                        onChange={(e) => setAriRoom({ ...ariRoom, room_code: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label>Rate Plan</Label>
                      <Input
                        value={ariRoom.rate_plan}
                        onChange={(e) => setAriRoom({ ...ariRoom, rate_plan: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label>Date</Label>
                      <Input
                        type="date"
                        value={ariRoom.date}
                        onChange={(e) => setAriRoom({ ...ariRoom, date: e.target.value })}
                      />
                    </div>
                    <div>
                      <Label>Price ({ariRoom.currency})</Label>
                      <Input
                        type="number"
                        value={ariRoom.price}
                        onChange={(e) => setAriRoom({ ...ariRoom, price: Number(e.target.value) })}
                      />
                    </div>
                  </div>
                  <div className="flex items-center gap-3">
                    <Button onClick={triggerAriPush}>
                      Push to Booking.com
                    </Button>
                    <Button variant="outline" onClick={triggerReservationPull}>
                      Pull Reservations
                    </Button>
                  </div>
                </CardContent>
              </Card>

              <Card>
                <CardHeader>
                  <CardTitle>Latest OTA Logs</CardTitle>
                  <CardDescription>Status of recent push/pull operations</CardDescription>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Button size="sm" variant="outline" onClick={loadBookingLogs}>
                    Refresh Logs
                  </Button>
                  <div className="space-y-2 max-h-64 overflow-y-auto">
                    {bookingLogs.length === 0 ? (
                      <p className="text-sm text-gray-500">No logs yet.</p>
                    ) : (
                      bookingLogs.map((log) => (
                        <div key={log.id} className="border rounded p-3 text-sm">
                          <div className="flex items-center justify-between">
                            <span className="font-semibold capitalize">{log.event_type}</span>
                            <Badge variant={log.status === 'success' ? 'success' : log.status === 'queued' ? 'secondary' : 'destructive'}>
                              {log.status}
                            </Badge>
                          </div>
                          <p className="text-xs text-gray-500 mt-1">
                            {log.created_at ? new Date(log.created_at).toLocaleString() : ''}
                          </p>
                          {log.message && <p className="text-xs mt-1">{log.message}</p>}
                        </div>
                      ))
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>

            <Card>
              <CardHeader>
                <CardTitle>Room Mappings</CardTitle>
                <CardDescription>Match Booking.com room codes to PMS room types</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                  <div>
                    <Label>Booking Room Code</Label>
                    <Input
                      value={newMapping.channel_room_type}
                      onChange={(e) => setNewMapping({ ...newMapping, channel_room_type: e.target.value })}
                      placeholder="DLX"
                    />
                  </div>
                  <div>
                    <Label>PMS Room Type</Label>
                    <Input
                      value={newMapping.pms_room_type}
                      onChange={(e) => setNewMapping({ ...newMapping, pms_room_type: e.target.value })}
                      placeholder="Deluxe"
                    />
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <Button
                    size="sm"
                    onClick={addRoomMapping}
                    disabled={!newMapping.channel_room_type || !newMapping.pms_room_type}
                  >
                    Add Mapping
                  </Button>
                  <Button size="sm" variant="outline" onClick={loadRoomMappings}>
                    Refresh
                  </Button>
                </div>
                <div className="space-y-2 max-h-64 overflow-y-auto">
                  {roomMappings.length === 0 ? (
                    <p className="text-sm text-gray-500">No mappings yet.</p>
                  ) : (
                    roomMappings.map((mapping) => (
                      <div key={mapping.id} className="border rounded p-3 text-sm flex items-center justify-between">
                        <div>
                          <p className="font-semibold">
                            {mapping.channel_room_type} → {mapping.pms_room_type}
                          </p>
                          <p className="text-xs text-gray-500">{mapping.channel_name || 'Booking.com'}</p>
                        </div>
                        <Button size="icon" variant="ghost" onClick={() => removeRoomMapping(mapping.id)}>
                          <Trash2 className="w-4 h-4" />
                        </Button>
                      </div>
                    ))
                  )}
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
};

export default Settings;
