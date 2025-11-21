import { useState, useEffect } from 'react';
import axios from 'axios';
import { toast } from 'sonner';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Hotel, User, Smartphone } from 'lucide-react';
import LanguageSelector from '@/components/LanguageSelector';

const AuthPage = ({ onLogin }) => {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [activeTab, setActiveTab] = useState('hotel-login');
  const [loading, setLoading] = useState(false);
  const [isMobile, setIsMobile] = useState(false);
  
  // Detect if device is mobile
  useEffect(() => {
    const checkMobile = () => {
      const mobile = window.innerWidth < 768 || /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
      setIsMobile(mobile);
    };
    
    checkMobile();
    window.addEventListener('resize', checkMobile);
    return () => window.removeEventListener('resize', checkMobile);
  }, []);
  
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
      console.log('🔐 Attempting login with:', hotelLoginData);
      console.log('📡 Axios baseURL:', axios.defaults.baseURL);
      const response = await axios.post('/auth/login', hotelLoginData);
      console.log('✅ Login successful:', response.data);
      toast.success('Login successful!');
      onLogin(response.data.access_token, response.data.user, response.data.tenant);
      // Force navigation after successful login
      setTimeout(() => {
        navigate('/');
      }, 100);
    } catch (error) {
      console.error('❌ Login error:', error);
      console.error('Error response:', error.response);
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
      console.log('📝 Register data being sent:', hotelRegisterData);
      const response = await axios.post('/auth/register', hotelRegisterData);
      console.log('✅ Register response:', response.data);
      toast.success('Registration successful!');
      onLogin(response.data.access_token, response.data.user, response.data.tenant);
    } catch (error) {
      console.error('❌ Registration error:', error);
      console.error('❌ Error response:', error.response?.data);
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
      background: isMobile 
        ? 'linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)' 
        : 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
      padding: isMobile ? '10px' : '20px'
    }}>
      <div style={{ width: '100%', maxWidth: isMobile ? '100%' : '500px' }}>
        <div style={{ textAlign: 'center', marginBottom: isMobile ? '1.5rem' : '2rem' }}>
          <h1 style={{ 
            fontSize: isMobile ? '2rem' : '3rem', 
            fontWeight: '700', 
            color: 'white',
            marginBottom: '0.5rem',
            fontFamily: 'Space Grotesk'
          }}>
            {isMobile && <Smartphone className="inline-block mr-2 mb-1" size={isMobile ? 32 : 48} />}
            RoomOps
          </h1>
          <p style={{ color: 'rgba(255,255,255,0.9)', fontSize: isMobile ? '0.9rem' : '1.1rem' }}>
            {isMobile ? 'Mobile Hotel Management' : 'Complete Hotel Management Platform'}
          </p>
          
          {/* Language Selector */}
          <div className="flex justify-center mt-4">
            <LanguageSelector />
          </div>
        </div>

        <Card style={{ 
          borderRadius: isMobile ? '20px 20px 0 0' : '8px',
          ...(isMobile && {
            position: 'fixed',
            bottom: 0,
            left: 0,
            right: 0,
            maxHeight: '80vh',
            overflowY: 'auto'
          })
        }}>
          <CardHeader>
            <CardTitle style={{ fontSize: isMobile ? '1.25rem' : '1.5rem' }}>
              {isMobile ? 'Mobile Login' : t('common.welcome')}
            </CardTitle>
            <CardDescription>
              {isMobile ? 'Access your hotel on the go' : t('auth.signIn')}
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab}>
              <TabsList className="grid w-full grid-cols-2 mb-4">
                <TabsTrigger value="hotel-login" data-testid="hotel-login-tab">
                  <Hotel className="w-4 h-4 mr-2" />
                  {t('auth.hotel')}
                </TabsTrigger>
                <TabsTrigger value="guest-login" data-testid="guest-login-tab">
                  <User className="w-4 h-4 mr-2" />
                  {t('auth.guest')}
                </TabsTrigger>
              </TabsList>
              
              {/* Hotel Login */}
              <TabsContent value="hotel-login" className="space-y-4">
                <Tabs defaultValue="login">
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="login">{t('common.login')}</TabsTrigger>
                    <TabsTrigger value="register">{t('common.register')}</TabsTrigger>
                  </TabsList>
                  
                  <TabsContent value="login">
                    <form onSubmit={handleHotelLogin} className="space-y-4" style={{ paddingTop: '1rem' }}>
                      {isMobile && (
                        <div className="bg-blue-50 p-3 rounded-lg mb-4">
                          <p className="text-sm text-blue-800 font-medium">
                            📱 Mobile Quick Access
                          </p>
                          <p className="text-xs text-blue-600 mt-1">
                            Manage your hotel from anywhere
                          </p>
                        </div>
                      )}
                      <div>
                        <Label>{t('common.email')}</Label>
                        <Input
                          type="email"
                          value={hotelLoginData.email}
                          onChange={(e) => setHotelLoginData({...hotelLoginData, email: e.target.value})}
                          required
                          data-testid="hotel-login-email"
                          placeholder={isMobile ? "your@email.com" : ""}
                          style={isMobile ? { fontSize: '16px' } : {}}
                        />
                      </div>
                      <div>
                        <Label>{t('common.password')}</Label>
                        <Input
                          type="password"
                          value={hotelLoginData.password}
                          onChange={(e) => setHotelLoginData({...hotelLoginData, password: e.target.value})}
                          required
                          data-testid="hotel-login-password"
                          placeholder={isMobile ? "••••••••" : ""}
                          style={isMobile ? { fontSize: '16px' } : {}}
                        />
                      </div>
                      <Button 
                        type="submit" 
                        className="w-full" 
                        disabled={loading} 
                        data-testid="hotel-login-btn"
                        style={isMobile ? { height: '48px', fontSize: '16px' } : {}}
                      >
                        {loading ? t('common.loading') : t('common.login')}
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
                    <form onSubmit={handleGuestLogin} className="space-y-4" style={{ paddingTop: '1rem' }}>
                      {isMobile && (
                        <div className="bg-purple-50 p-3 rounded-lg mb-4">
                          <p className="text-sm text-purple-800 font-medium">
                            👤 Guest Mobile Access
                          </p>
                          <p className="text-xs text-purple-600 mt-1">
                            View bookings and manage your stay
                          </p>
                        </div>
                      )}
                      <div>
                        <Label>Email</Label>
                        <Input
                          type="email"
                          value={guestLoginData.email}
                          onChange={(e) => setGuestLoginData({...guestLoginData, email: e.target.value})}
                          required
                          data-testid="guest-login-email"
                          placeholder={isMobile ? "your@email.com" : ""}
                          style={isMobile ? { fontSize: '16px' } : {}}
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
                          placeholder={isMobile ? "••••••••" : ""}
                          style={isMobile ? { fontSize: '16px' } : {}}
                        />
                      </div>
                      <Button 
                        type="submit" 
                        className="w-full" 
                        disabled={loading} 
                        data-testid="guest-login-btn"
                        style={isMobile ? { height: '48px', fontSize: '16px' } : {}}
                      >
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
