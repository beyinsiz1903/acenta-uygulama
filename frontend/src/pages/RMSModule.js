import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Layout from '../components/Layout';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Badge } from '../components/ui/badge';
import { 
  TrendingUp,
  TrendingDown,
  DollarSign,
  Zap,
  CheckCircle,
  Send,
  RefreshCw,
  AlertCircle,
  BarChart3,
  ArrowRight,
  Calendar,
  Target,
  Activity,
  Clock,
  PieChart
} from 'lucide-react';

const RMSModule = ({ user, tenant, onLogout }) => {
  const navigate = useNavigate();
  const [applyingPrices, setApplyingPrices] = useState(false);

  // Rate Suggestions with detailed impact
  const rateSuggestions = [
    {
      id: 1,
      roomType: 'Deluxe Double',
      dateRange: 'Dec 21-24, 2025',
      currentRate: 165,
      suggestedRate: 195,
      change: 30,
      changePercent: 18.2,
      impact: {
        revpar: 12.5,
        revenue: 1850,
        occupancy: 95
      },
      reason: 'High demand signal - Holiday period',
      confidence: 92,
      status: 'pending',
      channels: ['PMS', 'Booking.com', 'Expedia', 'Direct']
    },
    {
      id: 2,
      roomType: 'Standard Single',
      dateRange: 'Jan 15-18, 2025',
      currentRate: 135,
      suggestedRate: 125,
      change: -10,
      changePercent: -7.4,
      impact: {
        revpar: -2.1,
        revenue: -420,
        occupancy: 88
      },
      reason: 'Low booking pace - Weekday softness',
      confidence: 78,
      status: 'pending',
      channels: ['PMS', 'Booking.com', 'Expedia']
    },
    {
      id: 3,
      roomType: 'Suite',
      dateRange: 'Feb 14-16, 2025',
      currentRate: 285,
      suggestedRate: 325,
      change: 40,
      changePercent: 14.0,
      impact: {
        revpar: 15.8,
        revenue: 2200,
        occupancy: 100
      },
      reason: 'Valentine\'s Day - Peak demand',
      confidence: 95,
      status: 'pending',
      channels: ['PMS', 'Booking.com', 'Expedia', 'Direct', 'Agoda']
    }
  ];

  // AI Activity Log with detailed impacts
  const aiActivity = [
    { 
      id: 1, 
      time: '2 mins ago', 
      action: 'Rate updated', 
      detail: 'BAR for Dec 21-24 increased +15% (High demand signal)',
      impact: '+$850 potential revenue',
      type: 'rate_change',
      icon: TrendingUp,
      color: 'text-green-600'
    },
    { 
      id: 2, 
      time: '15 mins ago', 
      action: 'Competitor analysis', 
      detail: 'Comp set average ADR: $178 (+3% vs us)',
      impact: 'Opportunity to increase rates',
      type: 'analysis',
      icon: BarChart3,
      color: 'text-blue-600'
    },
    { 
      id: 3, 
      time: '1 hour ago', 
      action: 'Demand forecast', 
      detail: 'Weekend occupancy predicted at 96%',
      impact: 'High demand signal detected',
      type: 'forecast',
      icon: TrendingUp,
      color: 'text-purple-600'
    },
    { 
      id: 4, 
      time: '2 hours ago', 
      action: 'Rate suggestion', 
      detail: 'Generated 4 new rate recommendations',
      impact: '+$4,960 potential revenue',
      type: 'suggestion',
      icon: Zap,
      color: 'text-yellow-600'
    },
    { 
      id: 5, 
      time: '3 hours ago', 
      action: 'Channel sync', 
      detail: 'Rates synchronized across all OTAs',
      impact: '12 channels updated successfully',
      type: 'sync',
      icon: CheckCircle,
      color: 'text-green-600'
    }
  ];

  // Segment Revenue Data
  const segmentData = [
    { segment: 'Leisure', revenue: 48200, percentage: 38, rooms: 285, adr: 169 },
    { segment: 'Corporate', revenue: 38500, percentage: 30, rooms: 220, adr: 175 },
    { segment: 'OTA', revenue: 28400, percentage: 22, rooms: 168, adr: 169 },
    { segment: 'Group', revenue: 12900, percentage: 10, rooms: 85, adr: 152 }
  ];

  // Channel Revenue Mix
  const channelRevenueMix = [
    { channel: 'Direct Booking', revenue: 45600, percentage: 36, commission: 0 },
    { channel: 'Booking.com', revenue: 32400, percentage: 26, commission: 15 },
    { channel: 'Expedia', revenue: 25800, percentage: 20, commission: 18 },
    { channel: 'Corporate', revenue: 15200, percentage: 12, commission: 0 },
    { channel: 'Other OTAs', revenue: 8000, percentage: 6, commission: 15 }
  ];

  const todayStats = {
    aiUpdates: 12,
    potentialImpact: 1200,
    ratesApplied: 8,
    channelsSynced: 15,
    avgResponseTime: '< 1 min'
  };

  const handleApplyRate = (suggestion) => {
    setApplyingPrices(true);
    
    setTimeout(() => {
      alert(`✅ Rate Applied!\n\nRoom Type: ${suggestion.roomType}\nDate Range: ${suggestion.dateRange}\nNew Rate: $${suggestion.suggestedRate}\n\nApplied to:\n${suggestion.channels.map(c => `✓ ${c}`).join('\n')}\n\nEstimated Impact: +$${suggestion.impact.revenue} revenue`);
      setApplyingPrices(false);
    }, 1500);
  };

  const handleApplyAll = () => {
    const totalImpact = rateSuggestions.reduce((sum, s) => sum + s.impact.revenue, 0);
    
    if (window.confirm(`Apply all ${rateSuggestions.length} rate suggestions?\n\nTotal estimated impact: +$${totalImpact.toLocaleString()}\n\nThis will update rates in PMS and all connected channels.`)) {
      setApplyingPrices(true);
      
      setTimeout(() => {
        alert(`✅ All Rates Applied!\n\n${rateSuggestions.length} rate changes applied\nTotal estimated impact: +$${totalImpact.toLocaleString()}\n\nChannels updated: PMS, Booking.com, Expedia, Direct, Agoda`);
        setApplyingPrices(false);
      }, 2000);
    }
  };

  return (
    <Layout user={user || { name: 'Revenue Manager', role: 'admin' }} tenant={tenant} onLogout={onLogout}>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold" style={{ fontFamily: 'Space Grotesk' }}>
              Revenue Management System
            </h1>
            <p className="text-gray-600 mt-1">AI-powered pricing & segment analytics</p>
          </div>
          <div className="flex space-x-2">
            <Button 
              variant="outline" 
              onClick={() => alert('Generating new recommendations...')}
            >
              <RefreshCw className="w-4 h-4 mr-2" />
              Refresh
            </Button>
            <Button onClick={() => navigate('/')}>
              Back to Dashboard
            </Button>
          </div>
        </div>

        {/* Today's AI Impact Summary */}
        <Card className="border-2 border-yellow-400 bg-gradient-to-r from-yellow-50 to-orange-50">
          <CardHeader>
            <CardTitle className="flex items-center space-x-2">
              <Zap className="w-6 h-6 text-yellow-600" />
              <span>Today's AI Intelligence Summary</span>
            </CardTitle>
            <CardDescription>Real-time impact of AI recommendations</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
              <div className="text-center p-3 bg-white rounded-lg shadow-sm">
                <div className="text-2xl font-bold text-blue-600">{todayStats.aiUpdates}</div>
                <div className="text-xs text-gray-600 mt-1">AI Updates</div>
              </div>
              <div className="text-center p-3 bg-white rounded-lg shadow-sm">
                <div className="text-2xl font-bold text-green-600">+${todayStats.potentialImpact}</div>
                <div className="text-xs text-gray-600 mt-1">Potential Impact</div>
              </div>
              <div className="text-center p-3 bg-white rounded-lg shadow-sm">
                <div className="text-2xl font-bold text-purple-600">{todayStats.ratesApplied}</div>
                <div className="text-xs text-gray-600 mt-1">Rates Applied</div>
              </div>
              <div className="text-center p-3 bg-white rounded-lg shadow-sm">
                <div className="text-2xl font-bold text-indigo-600">{todayStats.channelsSynced}</div>
                <div className="text-xs text-gray-600 mt-1">Channels Synced</div>
              </div>
              <div className="text-center p-3 bg-white rounded-lg shadow-sm">
                <div className="text-2xl font-bold text-orange-600">{todayStats.avgResponseTime}</div>
                <div className="text-xs text-gray-600 mt-1">Avg Response</div>
              </div>
            </div>

            <div className="mt-4 p-4 bg-blue-100 border-l-4 border-blue-600 rounded">
              <p className="text-lg font-semibold text-blue-900">
                💡 "Today, AI made {todayStats.aiUpdates} pricing updates with potential +${todayStats.potentialImpact} revenue impact. {todayStats.ratesApplied} rates applied across {todayStats.channelsSynced} channels."
              </p>
            </div>
          </CardContent>
        </Card>

        {/* Rate Suggestions Header */}
        <div className="flex items-center justify-between">
          <h2 className="text-xl font-bold">AI Rate Suggestions ({rateSuggestions.length})</h2>
          <Button 
            onClick={handleApplyAll}
            disabled={applyingPrices}
            className="bg-green-600 hover:bg-green-700"
          >
            {applyingPrices ? (
              <>
                <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                Applying...
              </>
            ) : (
              <>
                <Send className="w-4 h-4 mr-2" />
                Apply All to PMS & Channels
              </>
            )}
          </Button>
        </div>

        {/* Rate Suggestions Cards */}
        <div className="space-y-4">
          {rateSuggestions.map((suggestion) => (
            <Card key={suggestion.id} className="hover:shadow-lg transition-shadow border-2 border-gray-200">
              <CardContent className="p-6">
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-3">
                      <h3 className="text-lg font-bold">{suggestion.roomType}</h3>
                      <Badge variant="outline" className="flex items-center space-x-1">
                        <Calendar className="w-3 h-3" />
                        <span>{suggestion.dateRange}</span>
                      </Badge>
                      <Badge className="bg-purple-600">
                        {suggestion.confidence}% confidence
                      </Badge>
                    </div>

                    <div className="grid grid-cols-3 gap-6 mb-4">
                      <div>
                        <div className="text-sm text-gray-600 mb-1">Current Rate</div>
                        <div className="text-2xl font-bold text-gray-700">
                          ${suggestion.currentRate}
                        </div>
                      </div>

                      <div className="flex items-center justify-center">
                        <ArrowRight className="w-8 h-8 text-blue-500" />
                      </div>

                      <div>
                        <div className="text-sm text-gray-600 mb-1">Suggested Rate</div>
                        <div className="flex items-center space-x-2">
                          <div className="text-2xl font-bold text-green-600">
                            ${suggestion.suggestedRate}
                          </div>
                          <Badge className={`${
                            suggestion.change > 0 ? 'bg-green-500' : 'bg-red-500'
                          }`}>
                            {suggestion.change > 0 ? '+' : ''}{suggestion.changePercent.toFixed(1)}%
                          </Badge>
                        </div>
                      </div>
                    </div>

                    <div className="grid grid-cols-3 gap-4 p-3 bg-gray-50 rounded-lg mb-3">
                      <div>
                        <div className="text-xs text-gray-600">RevPAR Impact</div>
                        <div className={`font-bold ${
                          suggestion.impact.revpar > 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {suggestion.impact.revpar > 0 ? '+' : ''}{suggestion.impact.revpar}%
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-600">Revenue Impact</div>
                        <div className={`font-bold ${
                          suggestion.impact.revenue > 0 ? 'text-green-600' : 'text-red-600'
                        }`}>
                          {suggestion.impact.revenue > 0 ? '+' : ''}${Math.abs(suggestion.impact.revenue).toLocaleString()}
                        </div>
                      </div>
                      <div>
                        <div className="text-xs text-gray-600">Expected Occupancy</div>
                        <div className="font-bold text-blue-600">
                          {suggestion.impact.occupancy}%
                        </div>
                      </div>
                    </div>

                    <div className="flex items-start space-x-2 text-sm mb-3">
                      <AlertCircle className="w-4 h-4 text-blue-600 mt-0.5" />
                      <div>
                        <span className="font-semibold text-gray-700">Reason: </span>
                        <span className="text-gray-600">{suggestion.reason}</span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-gray-600">Will apply to:</span>
                      {suggestion.channels.map((channel, idx) => (
                        <Badge key={idx} variant="outline" className="text-xs">
                          {channel}
                        </Badge>
                      ))}
                    </div>
                  </div>

                  <div className="flex flex-col space-y-2 ml-6">
                    <Button 
                      size="sm"
                      onClick={() => handleApplyRate(suggestion)}
                      disabled={applyingPrices}
                      className="bg-green-600 hover:bg-green-700 min-w-[180px]"
                    >
                      <Send className="w-4 h-4 mr-2" />
                      Apply to PMS & Channels
                    </Button>
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => alert('Showing detailed analysis...')}
                    >
                      <BarChart3 className="w-4 h-4 mr-2" />
                      View Analysis
                    </Button>
                    <Button 
                      size="sm" 
                      variant="outline"
                      onClick={() => alert('Suggestion dismissed')}
                    >
                      Dismiss
                    </Button>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {/* Segment Analytics */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Revenue by Segment */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <PieChart className="w-5 h-5 text-blue-600" />
                <span>Revenue by Segment (MTD)</span>
              </CardTitle>
              <CardDescription>Market segment performance breakdown</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {segmentData.map((segment, idx) => (
                  <div key={idx} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <span className="font-semibold">{segment.segment}</span>
                      <span className="text-sm text-gray-600">
                        ${segment.revenue.toLocaleString()} ({segment.percentage}%)
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <div className="flex-1 bg-gray-200 rounded-full h-2">
                        <div 
                          className={`h-2 rounded-full ${
                            idx === 0 ? 'bg-blue-600' :
                            idx === 1 ? 'bg-green-600' :
                            idx === 2 ? 'bg-purple-600' :
                            'bg-orange-600'
                          }`}
                          style={{ width: `${segment.percentage}%` }}
                        ></div>
                      </div>
                    </div>
                    <div className="flex justify-between text-xs text-gray-600">
                      <span>{segment.rooms} rooms</span>
                      <span>ADR: ${segment.adr}</span>
                    </div>
                  </div>
                ))}
                <div className="pt-3 border-t mt-4">
                  <div className="flex justify-between font-bold">
                    <span>Total:</span>
                    <span className="text-green-600">
                      ${segmentData.reduce((sum, s) => sum + s.revenue, 0).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Channel Revenue Mix */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <BarChart3 className="w-5 h-5 text-green-600" />
                <span>Channel Mix by Revenue (MTD)</span>
              </CardTitle>
              <CardDescription>Distribution channel performance</CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {channelRevenueMix.map((channel, idx) => (
                  <div key={idx} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="font-semibold">{channel.channel}</span>
                        {channel.commission > 0 && (
                          <Badge className="ml-2 text-xs bg-orange-500">
                            {channel.commission}% commission
                          </Badge>
                        )}
                      </div>
                      <span className="text-sm text-gray-600">
                        ${channel.revenue.toLocaleString()} ({channel.percentage}%)
                      </span>
                    </div>
                    <div className="flex-1 bg-gray-200 rounded-full h-2">
                      <div 
                        className={`h-2 rounded-full ${
                          idx === 0 ? 'bg-green-600' :
                          idx === 1 ? 'bg-blue-600' :
                          idx === 2 ? 'bg-purple-600' :
                          idx === 3 ? 'bg-indigo-600' :
                          'bg-gray-600'
                        }`}
                        style={{ width: `${channel.percentage * 2.5}%` }}
                      ></div>
                    </div>
                  </div>
                ))}
                <div className="pt-3 border-t mt-4">
                  <div className="flex justify-between">
                    <span className="font-bold">Total Revenue:</span>
                    <span className="font-bold text-green-600">
                      ${channelRevenueMix.reduce((sum, c) => sum + c.revenue, 0).toLocaleString()}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm text-gray-600 mt-2">
                    <span>Total Commission Cost:</span>
                    <span className="text-red-600">
                      -${channelRevenueMix.reduce((sum, c) => sum + (c.revenue * c.commission / 100), 0).toLocaleString()}
                    </span>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* AI Activity Log */}
        <Card>
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="flex items-center space-x-2">
                  <Activity className="w-5 h-5 text-blue-600" />
                  <span>AI Intelligence Activity</span>
                </CardTitle>
                <CardDescription>Real-time AI actions and recommendations</CardDescription>
              </div>
              <Button variant="outline" size="sm">
                View All
              </Button>
            </div>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {aiActivity.map((activity) => {
                const Icon = activity.icon;
                return (
                  <div 
                    key={activity.id} 
                    className="flex items-start space-x-4 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors"
                  >
                    <div className="mt-1">
                      <Icon className={`w-5 h-5 ${activity.color}`} />
                    </div>
                    <div className="flex-1">
                      <div className="flex items-center justify-between mb-1">
                        <span className="font-semibold text-sm">{activity.action}</span>
                        <span className="text-xs text-gray-500 flex items-center">
                          <Clock className="w-3 h-3 mr-1" />
                          {activity.time}
                        </span>
                      </div>
                      <div className="text-sm text-gray-700">{activity.detail}</div>
                      <div className="text-xs text-green-600 font-semibold mt-1">
                        💡 {activity.impact}
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      </div>
    </Layout>
  );
};

export default RMSModule;
