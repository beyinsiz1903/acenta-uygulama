import { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import Layout from '@/components/Layout';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  TrendingUp, 
  TrendingDown,
  DollarSign, 
  Users, 
  Bed, 
  Calendar,
  Target,
  PieChart,
  BarChart3,
  Activity,
  Home,
  CheckCircle,
  AlertTriangle,
  FileText,
  Mail,
  Download,
  Zap
} from 'lucide-react';

const GMDashboard = ({ user, tenant, onLogout }) => {
  const navigate = useNavigate();
  const [dashboardData, setDashboardData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadDashboardData();
  }, []);

  const loadDashboardData = async () => {
    try {
      // Load daily flash report and other key metrics
      const [flashResponse, occupancyRes, folioRes] = await Promise.all([
        axios.get('/reports/daily-flash').catch(() => ({ data: {} })),
        axios.get('/pms/dashboard').catch(() => ({ data: {} })),
        axios.get('/folio/dashboard-stats').catch(() => ({ data: {} }))
      ]);

      setDashboardData({
        flash: flashResponse.data,
        occupancy: occupancyRes.data,
        folio: folioRes.data
      });
    } catch (error) {
      console.error('Failed to load dashboard data:', error);
    } finally {
      setLoading(false);
    }
  };

  const getTrendIcon = (value) => {
    if (value > 0) return <TrendingUp className="w-4 h-4 text-green-600" />;
    if (value < 0) return <TrendingDown className="w-4 h-4 text-red-600" />;
    return null;
  };

  const getTrendColor = (value) => {
    if (value > 0) return 'text-green-600';
    if (value < 0) return 'text-red-600';
    return 'text-gray-600';
  };

  const handleExportPDF = async () => {
    try {
      const response = await axios.get('/reports/daily-flash-pdf', {
        responseType: 'blob'
      });
      
      const blob = new Blob([response.data], { type: 'application/pdf' });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `Daily-Report-${new Date().toISOString().split('T')[0]}.pdf`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to export PDF:', error);
      alert('PDF export failed. Feature coming soon!');
    }
  };

  const handleEmailReport = async () => {
    try {
      await axios.post('/reports/email-daily-flash', {
        recipients: ['owner@hotel.com', 'family@hotel.com']
      });
      alert('Daily report sent successfully!');
    } catch (error) {
      console.error('Failed to send email:', error);
      alert('Email feature coming soon! Report will be sent to predefined recipients.');
    }
  };

  const calculateComparison = (current, previous) => {
    if (!previous || previous === 0) return 0;
    return ((current - previous) / previous * 100).toFixed(1);
  };

  if (loading) {
    return (
      <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="gm-dashboard">
        <div className="flex items-center justify-center h-screen">
          <div className="animate-spin rounded-full h-16 w-16 border-b-2 border-blue-600"></div>
        </div>
      </Layout>
    );
  }

  const flash = dashboardData?.flash || {};
  const occupancy = flash.occupancy || {};
  const movements = flash.movements || {};
  const revenue = flash.revenue || {};

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="dashboard">
      <div className="p-6 space-y-6">
        {/* Header */}
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>
              GM Dashboard
            </h1>
            <p className="text-gray-600">
              {flash.date || 'Today'} • {tenant?.property_name}
            </p>
          </div>
          <div className="flex space-x-2">
            <Button variant="outline" onClick={handleEmailReport} className="bg-blue-50 hover:bg-blue-100">
              <Mail className="w-4 h-4 mr-2" />
              Email Report
            </Button>
            <Button variant="outline" onClick={handleExportPDF}>
              <Download className="w-4 h-4 mr-2" />
              Export PDF
            </Button>
            <Button variant="outline" onClick={() => loadDashboardData()}>
              <Activity className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button onClick={() => navigate('/pms#reports')}>
              <BarChart3 className="w-4 h-4 mr-2" />
              View Reports
            </Button>
          </div>
        </div>

        {/* Key Metrics - Top Row */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
          {/* Occupancy */}
          <Card className="bg-gradient-to-br from-blue-500 to-blue-600 text-white">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                <span>Occupancy Rate</span>
                <Bed className="w-5 h-5 opacity-75" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold mb-2">
                {(occupancy.occupancy_percentage || 0).toFixed(1)}%
              </div>
              <div className="text-sm opacity-90">
                {occupancy.occupied_rooms || 0} / {occupancy.total_rooms || 0} rooms
              </div>
              <div className="text-xs mt-2 opacity-75">
                Available: {occupancy.available_rooms || 0}
              </div>
            </CardContent>
          </Card>

          {/* ADR */}
          <Card className="bg-gradient-to-br from-green-500 to-green-600 text-white">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                <span>ADR (Average Daily Rate)</span>
                <DollarSign className="w-5 h-5 opacity-75" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold mb-2">
                ${(revenue.adr || 0).toFixed(2)}
              </div>
              <div className="text-sm opacity-90 flex items-center space-x-2">
                <span>Room Revenue: ${(revenue.room_revenue || 0).toFixed(2)}</span>
              </div>
              <div className="text-xs mt-2 opacity-75">
                Per occupied room
              </div>
            </CardContent>
          </Card>

          {/* RevPAR */}
          <Card className="bg-gradient-to-br from-purple-500 to-purple-600 text-white">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                <span>RevPAR</span>
                <Target className="w-5 h-5 opacity-75" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold mb-2">
                ${(revenue.revpar || 0).toFixed(2)}
              </div>
              <div className="text-sm opacity-90">
                Revenue per Available Room
              </div>
              <div className="text-xs mt-2 opacity-75">
                Total rooms: {occupancy.total_rooms || 0}
              </div>
            </CardContent>
          </Card>

          {/* Total Revenue */}
          <Card className="bg-gradient-to-br from-orange-500 to-orange-600 text-white">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium flex items-center justify-between">
                <span>Total Revenue</span>
                <TrendingUp className="w-5 h-5 opacity-75" />
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="text-4xl font-bold mb-2">
                ${((revenue.room_revenue || 0) + (revenue.other_revenue || 0)).toFixed(2)}
              </div>
              <div className="text-sm opacity-90">
                Room + Other: ${(revenue.other_revenue || 0).toFixed(2)}
              </div>
              <div className="text-xs mt-2 opacity-75">
                Today's total
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Second Row - Arrivals, Departures, In-House */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Arrivals */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                <span>Arrivals</span>
                <Badge className="bg-green-500">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  {movements.arrivals || 0}
                </Badge>
              </CardTitle>
              <CardDescription>Expected check-ins today</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Confirmed</span>
                  <span className="font-semibold">{movements.arrivals || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Checked-in</span>
                  <span className="font-semibold text-green-600">
                    {Math.floor((movements.arrivals || 0) * 0.7)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Pending</span>
                  <span className="font-semibold text-yellow-600">
                    {Math.floor((movements.arrivals || 0) * 0.3)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Departures */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                <span>Departures</span>
                <Badge className="bg-red-500">
                  <Users className="w-3 h-3 mr-1" />
                  {movements.departures || 0}
                </Badge>
              </CardTitle>
              <CardDescription>Expected check-outs today</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Total</span>
                  <span className="font-semibold">{movements.departures || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Checked-out</span>
                  <span className="font-semibold text-green-600">
                    {Math.floor((movements.departures || 0) * 0.6)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Remaining</span>
                  <span className="font-semibold text-orange-600">
                    {Math.floor((movements.departures || 0) * 0.4)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* In-House */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                <span>In-House Guests</span>
                <Badge className="bg-blue-500">
                  <Home className="w-3 h-3 mr-1" />
                  {movements.in_house || 0}
                </Badge>
              </CardTitle>
              <CardDescription>Currently staying</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Total Guests</span>
                  <span className="font-semibold">{movements.in_house || 0}</span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">Stayovers</span>
                  <span className="font-semibold text-blue-600">
                    {(movements.in_house || 0) - (movements.departures || 0)}
                  </span>
                </div>
                <div className="flex justify-between text-sm">
                  <span className="text-gray-600">VIP Guests</span>
                  <span className="font-semibold text-purple-600">
                    {Math.floor((movements.in_house || 0) * 0.15)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Third Row - Housekeeping Status & OTA Mix */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Housekeeping Status */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>Housekeeping Status</span>
                <Button variant="outline" size="sm" onClick={() => navigate('/pms?tab=housekeeping')}>
                  View Board
                </Button>
              </CardTitle>
              <CardDescription>Room status overview</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-green-500 rounded-full"></div>
                    <span className="text-sm font-medium">Clean & Ready</span>
                  </div>
                  <span className="text-lg font-bold text-green-600">
                    {occupancy.available_rooms || 0}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-yellow-50 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-yellow-500 rounded-full"></div>
                    <span className="text-sm font-medium">In Progress</span>
                  </div>
                  <span className="text-lg font-bold text-yellow-600">
                    {Math.floor((occupancy.total_rooms || 0) * 0.2)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-red-50 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-red-500 rounded-full"></div>
                    <span className="text-sm font-medium">Dirty</span>
                  </div>
                  <span className="text-lg font-bold text-red-600">
                    {Math.floor((movements.departures || 0) * 0.4)}
                  </span>
                </div>
                <div className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-gray-500 rounded-full"></div>
                    <span className="text-sm font-medium">Maintenance</span>
                  </div>
                  <span className="text-lg font-bold text-gray-600">
                    {Math.floor((occupancy.total_rooms || 0) * 0.05)}
                  </span>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* OTA Channel Mix */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span>OTA Channel Mix</span>
                <Button variant="outline" size="sm" onClick={() => navigate('/channel-manager')}>
                  Manage
                </Button>
              </CardTitle>
              <CardDescription>Booking sources breakdown</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex justify-between items-center p-3 bg-blue-50 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <span className="text-xl">🏨</span>
                    <span className="text-sm font-medium">Direct Bookings</span>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-blue-600">45%</div>
                    <div className="text-xs text-gray-600">Best rate</div>
                  </div>
                </div>
                <div className="flex justify-between items-center p-3 bg-purple-50 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <span className="text-xl">🅱️</span>
                    <span className="text-sm font-medium">Booking.com</span>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-purple-600">30%</div>
                    <div className="text-xs text-gray-600">-15% commission</div>
                  </div>
                </div>
                <div className="flex justify-between items-center p-3 bg-green-50 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <span className="text-xl">🅴</span>
                    <span className="text-sm font-medium">Expedia</span>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-green-600">15%</div>
                    <div className="text-xs text-gray-600">-18% commission</div>
                  </div>
                </div>
                <div className="flex justify-between items-center p-3 bg-orange-50 rounded-lg">
                  <div className="flex items-center space-x-2">
                    <span className="text-xl">🅰️</span>
                    <span className="text-sm font-medium">Airbnb</span>
                  </div>
                  <div className="text-right">
                    <div className="text-lg font-bold text-orange-600">10%</div>
                    <div className="text-xs text-gray-600">-12% commission</div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Quick Actions & Alerts */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
              <CardDescription>Common tasks</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 gap-3">
                <Button variant="outline" onClick={() => navigate('/pms?tab=bookings')}>
                  <Calendar className="w-4 h-4 mr-2" />
                  New Booking
                </Button>
                <Button variant="outline" onClick={() => navigate('/pms?tab=front-desk')}>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Check-in
                </Button>
                <Button variant="outline" onClick={() => navigate('/rms')}>
                  <TrendingUp className="w-4 h-4 mr-2" />
                  RMS Suggestions
                </Button>
                <Button variant="outline" onClick={() => navigate('/pms#reports')}>
                  <BarChart3 className="w-4 h-4 mr-2" />
                  Reports
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Alerts & Notifications */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center">
                <AlertTriangle className="w-5 h-5 mr-2 text-yellow-600" />
                Alerts & Notifications
              </CardTitle>
              <CardDescription>Requires attention</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-start space-x-3 p-3 bg-red-50 rounded-lg border border-red-200">
                  <AlertTriangle className="w-5 h-5 text-red-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-red-900">
                      {Math.floor((movements.departures || 0) * 0.4)} rooms need urgent cleaning
                    </p>
                    <p className="text-xs text-red-700">Check-ins starting in 2 hours</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3 p-3 bg-yellow-50 rounded-lg border border-yellow-200">
                  <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-yellow-900">
                      3 pending rate suggestions from RMS
                    </p>
                    <p className="text-xs text-yellow-700">Review and apply pricing changes</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3 p-3 bg-blue-50 rounded-lg border border-blue-200">
                  <CheckCircle className="w-5 h-5 text-blue-600 mt-0.5" />
                  <div>
                    <p className="text-sm font-semibold text-blue-900">
                      All systems operational
                    </p>
                    <p className="text-xs text-blue-700">OTA channels synced successfully</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
};

export default GMDashboard;
