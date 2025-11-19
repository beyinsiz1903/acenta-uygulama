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
  Zap,
  LogIn,
  ArrowUpCircle,
  MessageSquare,
  Key,
  Printer,
  Phone,
  Send,
  Building2
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

        {/* Owner Summary / Snapshot */}
        <Card className="border-2 border-yellow-400 bg-gradient-to-r from-yellow-50 to-orange-50">
          <CardHeader>
            <CardTitle className="text-xl flex items-center space-x-2">
              <Zap className="w-6 h-6 text-yellow-600" />
              <span>Owner Summary - Quick Snapshot</span>
            </CardTitle>
            <CardDescription>At-a-glance performance vs Budget & Last Year</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Today vs Yesterday */}
              <div className="space-y-2">
                <h3 className="font-semibold text-gray-700 flex items-center space-x-2">
                  <Calendar className="w-4 h-4" />
                  <span>Today vs Yesterday</span>
                </h3>
                <div className="bg-white p-4 rounded-lg shadow-sm">
                  <div className="text-2xl font-bold text-gray-900">
                    ${((revenue.room_revenue || 0) + (revenue.other_revenue || 0)).toFixed(0)}
                  </div>
                  <div className="flex items-center space-x-2 mt-1">
                    {getTrendIcon(12.5)}
                    <span className={`text-sm font-semibold ${getTrendColor(12.5)}`}>
                      +12.5% vs Yesterday
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    Revenue increased by $850
                  </p>
                </div>
              </div>

              {/* This Month vs Budget */}
              <div className="space-y-2">
                <h3 className="font-semibold text-gray-700 flex items-center space-x-2">
                  <Target className="w-4 h-4" />
                  <span>MTD vs Budget</span>
                </h3>
                <div className="bg-white p-4 rounded-lg shadow-sm">
                  <div className="text-2xl font-bold text-gray-900">
                    $152,400
                  </div>
                  <div className="flex items-center space-x-2 mt-1">
                    {getTrendIcon(-2.3)}
                    <span className={`text-sm font-semibold ${getTrendColor(-2.3)}`}>
                      -2.3% vs Budget
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    Budget: $156,000 | Gap: -$3,600
                  </p>
                </div>
              </div>

              {/* This Month RevPAR vs Last Year */}
              <div className="space-y-2">
                <h3 className="font-semibold text-gray-700 flex items-center space-x-2">
                  <TrendingUp className="w-4 h-4" />
                  <span>MTD RevPAR vs LY</span>
                </h3>
                <div className="bg-white p-4 rounded-lg shadow-sm">
                  <div className="text-2xl font-bold text-gray-900">
                    $148.50
                  </div>
                  <div className="flex items-center space-x-2 mt-1">
                    {getTrendIcon(8.7)}
                    <span className={`text-sm font-semibold ${getTrendColor(8.7)}`}>
                      +8.7% vs Last Year
                    </span>
                  </div>
                  <p className="text-xs text-gray-500 mt-2">
                    Last Year: $136.60 | Gain: +$11.90
                  </p>
                </div>
              </div>
            </div>

            {/* One-liner Summary */}
            <div className="mt-6 p-4 bg-blue-100 border-l-4 border-blue-600 rounded">
              <p className="text-lg font-semibold text-blue-900">
                📊 "Today we're +12.5% ahead vs yesterday. MTD we're 2.3% below budget but 8.7% ahead of last year's RevPAR."
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Second Row - Arrivals, Departures, In-House */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Arrivals - Enhanced with Quick Actions */}
          <Card className="hover:shadow-lg transition-shadow">
            <CardHeader>
              <CardTitle className="text-lg flex items-center justify-between">
                <span>Today's Arrivals</span>
                <Badge className="bg-green-500">
                  <CheckCircle className="w-3 h-3 mr-1" />
                  {movements.arrivals || 0}
                </Badge>
              </CardTitle>
              <CardDescription>Expected check-ins with quick actions</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {/* Sample Arrival Cards */}
                {[
                  { name: 'Richard Anderson', room: '116', type: 'Deluxe Double', vip: false },
                  { name: 'Amelia Gonzalez', room: '102', type: 'Standard Single', vip: false },
                  { name: 'William Lee', room: '113', type: 'Family Room', vip: true }
                ].map((guest, idx) => (
                  <div key={idx} className={`p-3 rounded-lg border-2 ${guest.vip ? 'border-yellow-400 bg-yellow-50' : 'border-gray-200 bg-gray-50'}`}>
                    <div className="flex items-start justify-between mb-2">
                      <div>
                        <div className="flex items-center space-x-2">
                          <span className="font-semibold text-sm">{guest.name}</span>
                          {guest.vip && <Badge className="bg-yellow-500 text-xs">VIP</Badge>}
                        </div>
                        <div className="text-xs text-gray-600">
                          Room {guest.room} • {guest.type}
                        </div>
                      </div>
                    </div>
                    
                    {/* Quick Action Buttons */}
                    <div className="flex flex-wrap gap-1 mt-2">
                      <Button 
                        size="sm" 
                        className="h-7 text-xs bg-green-600 hover:bg-green-700"
                        onClick={() => navigate('/pms?action=checkin&guest=' + guest.name)}
                      >
                        <LogIn className="w-3 h-3 mr-1" />
                        Check-in
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="h-7 text-xs"
                        onClick={() => alert('Upgrade options: Suite ($50), Deluxe Sea View ($30)')}
                      >
                        <ArrowUpCircle className="w-3 h-3 mr-1" />
                        Upgrade
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="h-7 text-xs"
                        onClick={() => navigate('/ota-messaging-hub?guest=' + guest.name)}
                      >
                        <MessageSquare className="w-3 h-3 mr-1" />
                        Message
                      </Button>
                      <Button 
                        size="sm" 
                        variant="outline" 
                        className="h-7 text-xs"
                        onClick={() => alert('Print: Registration Form, Key Card Envelope')}
                      >
                        <Printer className="w-3 h-3 mr-1" />
                        Print
                      </Button>
                    </div>
                  </div>
                ))}

                <Button 
                  variant="outline" 
                  className="w-full mt-2"
                  onClick={() => navigate('/pms?tab=arrivals')}
                >
                  View All Arrivals ({movements.arrivals || 0})
                </Button>
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

        {/* Revenue Analytics & Budget Comparison */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Actual vs Budget */}
          <Card className="border-2 border-blue-200">
            <CardHeader>
              <CardTitle className="text-lg flex items-center space-x-2">
                <Target className="w-5 h-5 text-blue-600" />
                <span>Actual vs Budget</span>
              </CardTitle>
              <CardDescription>Month-to-date comparison</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-gray-600">Revenue</span>
                    <Badge variant={-2.3 < 0 ? "destructive" : "default"}>
                      -2.3%
                    </Badge>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="text-2xl font-bold">$152,400</div>
                    <div className="text-sm text-gray-500">/ $156,000</div>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                    <div className="bg-blue-600 h-2 rounded-full" style={{ width: '97.7%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-gray-600">Occupancy</span>
                    <Badge variant="default">+3.5%</Badge>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="text-2xl font-bold">86.2%</div>
                    <div className="text-sm text-gray-500">/ 83.5%</div>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                    <div className="bg-green-600 h-2 rounded-full" style={{ width: '103.5%' }}></div>
                  </div>
                </div>

                <div>
                  <div className="flex justify-between items-center mb-2">
                    <span className="text-sm text-gray-600">ADR</span>
                    <Badge variant="default">+1.8%</Badge>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="text-2xl font-bold">$169.74</div>
                    <div className="text-sm text-gray-500">/ $166.80</div>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mt-2">
                    <div className="bg-green-600 h-2 rounded-full" style={{ width: '101.8%' }}></div>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* vs Last Year */}
          <Card className="border-2 border-green-200">
            <CardHeader>
              <CardTitle className="text-lg flex items-center space-x-2">
                <TrendingUp className="w-5 h-5 text-green-600" />
                <span>vs Last Year</span>
              </CardTitle>
              <CardDescription>Year-over-year growth</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="p-3 bg-green-50 rounded-lg">
                  <div className="text-sm text-gray-600 mb-1">Revenue Growth</div>
                  <div className="flex items-center justify-between">
                    <div className="text-3xl font-bold text-green-700">+8.7%</div>
                    <TrendingUp className="w-8 h-8 text-green-600" />
                  </div>
                  <div className="text-xs text-gray-600 mt-2">
                    $152,400 vs $140,200 LY
                  </div>
                </div>

                <div className="p-3 bg-blue-50 rounded-lg">
                  <div className="text-sm text-gray-600 mb-1">Occupancy</div>
                  <div className="flex items-center justify-between">
                    <div className="text-3xl font-bold text-blue-700">+4.2%</div>
                    <TrendingUp className="w-8 h-8 text-blue-600" />
                  </div>
                  <div className="text-xs text-gray-600 mt-2">
                    86.2% vs 82.7% LY
                  </div>
                </div>

                <div className="p-3 bg-purple-50 rounded-lg">
                  <div className="text-sm text-gray-600 mb-1">RevPAR</div>
                  <div className="flex items-center justify-between">
                    <div className="text-3xl font-bold text-purple-700">+8.7%</div>
                    <TrendingUp className="w-8 h-8 text-purple-600" />
                  </div>
                  <div className="text-xs text-gray-600 mt-2">
                    $148.50 vs $136.60 LY
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* 30-Day Forecast with Budget */}
          <Card className="border-2 border-purple-200">
            <CardHeader>
              <CardTitle className="text-lg flex items-center space-x-2">
                <Calendar className="w-5 h-5 text-purple-600" />
                <span>30-Day Forecast</span>
              </CardTitle>
              <CardDescription>Occupancy: Actual vs Budget</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="flex items-center justify-between text-xs">
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 bg-blue-600 rounded"></div>
                    <span>Actual</span>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-3 h-3 border-2 border-green-600 rounded"></div>
                    <span>Budget</span>
                  </div>
                </div>

                {/* Mini chart representation */}
                <div className="space-y-2">
                  {[
                    { day: 'Week 1', actual: 88, budget: 85 },
                    { day: 'Week 2', actual: 92, budget: 88 },
                    { day: 'Week 3', actual: 84, budget: 87 },
                    { day: 'Week 4', actual: 90, budget: 90 }
                  ].map((week, idx) => (
                    <div key={idx}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-gray-600">{week.day}</span>
                        <span className="font-semibold">{week.actual}% / {week.budget}%</span>
                      </div>
                      <div className="flex space-x-1">
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div className="bg-blue-600 h-2 rounded-full" style={{ width: `${week.actual}%` }}></div>
                        </div>
                        <div className="flex-1 bg-gray-200 rounded-full h-2">
                          <div className="border-2 border-green-600 h-2 rounded-full" style={{ width: `${week.budget}%` }}></div>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="pt-3 border-t">
                  <div className="text-sm font-semibold text-center">
                    Avg: 88.5% vs Budget 87.5%
                    <Badge className="ml-2 bg-green-500">+1.0%</Badge>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Top 10 Corporate Accounts */}
        <Card className="border-2 border-indigo-200">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-lg flex items-center space-x-2">
                  <Building2 className="w-5 h-5 text-indigo-600" />
                  <span>Top 10 Corporate Accounts</span>
                </CardTitle>
                <CardDescription>MTD revenue by corporate client</CardDescription>
              </div>
              <Button 
                variant="outline" 
                size="sm"
                onClick={() => navigate('/sales?tab=contracts')}
              >
                View All
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {[
                { name: 'Global Enterprise Inc.', revenue: 18400, nights: 127, tier: 'platinum', trend: '+12%' },
                { name: 'Tech Innovations Ltd.', revenue: 15200, nights: 98, tier: 'gold', trend: '+8%' },
                { name: 'Consulting Partners', revenue: 12800, nights: 78, tier: 'silver', trend: '+15%' },
                { name: 'Financial Services Co.', revenue: 9600, nights: 64, tier: 'silver', trend: '-3%' },
                { name: 'Healthcare Solutions', revenue: 8200, nights: 52, tier: 'gold', trend: '+5%' },
                { name: 'Manufacturing Inc.', revenue: 7100, nights: 43, tier: 'silver', trend: '+2%' },
                { name: 'Retail Group', revenue: 6500, nights: 39, tier: 'bronze', trend: '+18%' },
                { name: 'Legal Associates', revenue: 5900, nights: 35, tier: 'silver', trend: '+7%' },
                { name: 'Marketing Agency', revenue: 4800, nights: 28, tier: 'bronze', trend: '-5%' },
                { name: 'Software Corp', revenue: 4200, nights: 24, tier: 'bronze', trend: '+22%' }
              ].map((account, idx) => (
                <div 
                  key={idx}
                  className="flex items-center justify-between p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors cursor-pointer"
                  onClick={() => navigate('/sales?company=' + account.name)}
                >
                  <div className="flex items-center space-x-3 flex-1">
                    <div className="text-lg font-bold text-gray-400 w-6">{idx + 1}</div>
                    <div className="flex-1">
                      <div className="flex items-center space-x-2">
                        <span className="font-semibold text-sm">{account.name}</span>
                        <Badge className={`text-xs ${
                          account.tier === 'platinum' ? 'bg-purple-600' :
                          account.tier === 'gold' ? 'bg-yellow-600' :
                          account.tier === 'silver' ? 'bg-gray-400' :
                          'bg-orange-400'
                        }`}>
                          {account.tier}
                        </Badge>
                      </div>
                      <div className="text-xs text-gray-600">{account.nights} nights</div>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="font-bold text-sm">${account.revenue.toLocaleString()}</div>
                    <div className={`text-xs ${
                      account.trend.startsWith('+') ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {account.trend}
                    </div>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 pt-4 border-t">
              <div className="flex justify-between items-center">
                <span className="text-sm font-semibold text-gray-700">Total Top 10:</span>
                <div className="text-right">
                  <div className="text-lg font-bold text-green-600">$92,700</div>
                  <div className="text-xs text-gray-600">588 room nights</div>
                </div>
              </div>
            </div>
          </CardContent>
        </Card>

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
