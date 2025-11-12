import { useState } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Hotel, User } from 'lucide-react';
import LanguageSelector from '@/components/LanguageSelector';

const AuthPage = ({ onLogin }) => {
  const [activeTab, setActiveTab] = useState('hotel-login');
  const [loading, setLoading] = useState(false);
  
  const [hotelLoginData, setHotelLoginData] = useState({ email: '', password: '' });
  const [guestLoginData, setGuestLoginData] = useState({ email: '', password: '' });
  
  const [hotelRegisterData, setHotelRegisterData] = useState({
    property_name: '', email: '', password: '', name: '', phone: '', address: ''
  });
  
  const [guestRegisterData, setGuestRegisterData] = useState({
    email: '', password: '', name: '', phone: ''
  });

  const handleHotelLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post('/auth/login', hotelLoginData);
      toast.success('Login successful!');
      onLogin(response.data.access_token, response.data.user, response.data.tenant);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGuestLogin = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post('/auth/login', guestLoginData);
      toast.success('Welcome back!');
      onLogin(response.data.access_token, response.data.user, response.data.tenant);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  const handleHotelRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post('/auth/register', hotelRegisterData);
      toast.success('Registration successful!');
      onLogin(response.data.access_token, response.data.user, response.data.tenant);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  const handleGuestRegister = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const response = await axios.post('/auth/register-guest', guestRegisterData);
      toast.success('Account created! Welcome!');
      onLogin(response.data.access_token, response.data.user, response.data.tenant);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Registration failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="auth-page" style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: '20px'
    }}>
      <div style={{ width: '100%', maxWidth: '500px' }}>
        <div style={{ textAlign: 'center', marginBottom: '2rem' }}>
          <h1 style={{ 
            fontSize: '3rem', 
            fontWeight: '700', 
            color: 'white',
            marginBottom: '0.5rem',
            fontFamily: 'Space Grotesk'
          }}>RoomOps</h1>
          <p style={{ color: 'rgba(255,255,255,0.9)', fontSize: '1.1rem' }}>
            Complete Hotel Management Platform
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Welcome</CardTitle>
            <CardDescription>
              Sign in to your account or create a new one
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-2 mb-4">
                <TabsTrigger value="hotel-login" data-testid="hotel-login-tab">
                  <Hotel className="w-4 h-4 mr-2" />
                  Hotel
                </TabsTrigger>
                <TabsTrigger value="guest-login" data-testid="guest-login-tab">
                  <User className="w-4 h-4 mr-2" />
                  Guest
                </TabsTrigger>
              </TabsList>
              
              {/* Hotel Login */}
              <TabsContent value="hotel-login" className="space-y-4">
                <Tabs defaultValue="login">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="login">Login</TabsTrigger>
                    <TabsTrigger value="register">Register</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="login">
                    <form onSubmit={handleHotelLogin} className="space-y-4">
                      <div>
                        <Label>Email</Label>
                        <Input
                          type="email"
                          value={hotelLoginData.email}
                          onChange={(e) => setHotelLoginData({...hotelLoginData, email: e.target.value})}
                          required
                          data-testid="hotel-login-email"
                        />
                      </div>
                      <div>
                        <Label>Password</Label>
                        <Input
                          type="password"
                          value={hotelLoginData.password}
                          onChange={(e) => setHotelLoginData({...hotelLoginData, password: e.target.value})}
                          required
                          data-testid="hotel-login-password"
                        />
                      </div>
                      <Button type="submit" className="w-full" disabled={loading} data-testid="hotel-login-btn">
                        {loading ? 'Logging in...' : 'Login'}
                      </Button>
                    </form>
                  </TabsContent>
                  
                  <TabsContent value="register">
                    <form onSubmit={handleHotelRegister} className="space-y-4">
                      <div>
                        <Label>Property Name</Label>
                        <Input
                          value={hotelRegisterData.property_name}
                          onChange={(e) => setHotelRegisterData({...hotelRegisterData, property_name: e.target.value})}
                          required
                        />
                      </div>
                      <div>
                        <Label>Admin Name</Label>
                        <Input
                          value={hotelRegisterData.name}
                          onChange={(e) => setHotelRegisterData({...hotelRegisterData, name: e.target.value})}
                          required
                        />
                      </div>
                      <div>
                        <Label>Email</Label>
                        <Input
                          type="email"
                          value={hotelRegisterData.email}
                          onChange={(e) => setHotelRegisterData({...hotelRegisterData, email: e.target.value})}
                          required
                        />
                      </div>
                      <div>
                        <Label>Phone</Label>
                        <Input
                          value={hotelRegisterData.phone}
                          onChange={(e) => setHotelRegisterData({...hotelRegisterData, phone: e.target.value})}
                          required
                        />
                      </div>
                      <div>
                        <Label>Address</Label>
                        <Input
                          value={hotelRegisterData.address}
                          onChange={(e) => setHotelRegisterData({...hotelRegisterData, address: e.target.value})}
                          required
                        />
                      </div>
                      <div>
                        <Label>Password</Label>
                        <Input
                          type="password"
                          value={hotelRegisterData.password}
                          onChange={(e) => setHotelRegisterData({...hotelRegisterData, password: e.target.value})}
                          required
                        />
                      </div>
                      <Button type="submit" className="w-full" disabled={loading}>
                        {loading ? 'Registering...' : 'Register Property'}
                      </Button>
                    </form>
                  </TabsContent>
                </Tabs>
              </TabsContent>

              {/* Guest Login */}
              <TabsContent value="guest-login" className="space-y-4">
                <Tabs defaultValue="login">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="login">Login</TabsTrigger>
                    <TabsTrigger value="register">Register</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="login">
                    <form onSubmit={handleGuestLogin} className="space-y-4">
                      <div>
                        <Label>Email</Label>
                        <Input
                          type="email"
                          value={guestLoginData.email}
                          onChange={(e) => setGuestLoginData({...guestLoginData, email: e.target.value})}
                          required
                          data-testid="guest-login-email"
                        />
                      </div>
                      <div>
                        <Label>Password</Label>
                        <Input
                          type="password"
                          value={guestLoginData.password}
                          onChange={(e) => setGuestLoginData({...guestLoginData, password: e.target.value})}
                          required
                          data-testid="guest-login-password"
                        />
                      </div>
                      <Button type="submit" className="w-full" disabled={loading} data-testid="guest-login-btn">
                        {loading ? 'Logging in...' : 'Login as Guest'}
                      </Button>
                    </form>
                  </TabsContent>
                  
                  <TabsContent value="register">
                    <form onSubmit={handleGuestRegister} className="space-y-4">
                      <div>
                        <Label>Name</Label>
                        <Input
                          value={guestRegisterData.name}
                          onChange={(e) => setGuestRegisterData({...guestRegisterData, name: e.target.value})}
                          required
                          data-testid="guest-register-name"
                        />
                      </div>
                      <div>
                        <Label>Email</Label>
                        <Input
                          type="email"
                          value={guestRegisterData.email}
                          onChange={(e) => setGuestRegisterData({...guestRegisterData, email: e.target.value})}
                          required
                          data-testid="guest-register-email"
                        />
                      </div>
                      <div>
                        <Label>Phone</Label>
                        <Input
                          value={guestRegisterData.phone}
                          onChange={(e) => setGuestRegisterData({...guestRegisterData, phone: e.target.value})}
                          required
                          data-testid="guest-register-phone"
                        />
                      </div>
                      <div>
                        <Label>Password</Label>
                        <Input
                          type="password"
                          value={guestRegisterData.password}
                          onChange={(e) => setGuestRegisterData({...guestRegisterData, password: e.target.value})}
                          required
                          data-testid="guest-register-password"
                        />
                      </div>
                      <Button type="submit" className="w-full" disabled={loading} data-testid="guest-register-btn">
                        {loading ? 'Creating Account...' : 'Create Guest Account'}
                      </Button>
                    </form>
                  </TabsContent>
                </Tabs>
              </TabsContent>
            </Tabs>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};

export default AuthPage;
