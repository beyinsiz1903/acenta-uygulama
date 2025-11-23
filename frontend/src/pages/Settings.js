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
import { Settings as SettingsIcon, Mail, MessageSquare, Phone, Key, AlertCircle } from 'lucide-react';

const Settings = ({ user, tenant, onLogout }) => {
  const [integrations, setIntegrations] = useState({
    sendgrid: { enabled: false, api_key: '' },
    twilio: { enabled: false, account_sid: '', auth_token: '', phone_number: '' },
    whatsapp: { enabled: false, account_sid: '', auth_token: '' }
  });

  const [saving, setSaving] = useState(false);

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
        </Tabs>
      </div>
    </Layout>
  );
};

export default Settings;
