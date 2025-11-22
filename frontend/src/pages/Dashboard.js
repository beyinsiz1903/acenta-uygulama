import { useState, useEffect } from 'react';
import axios from 'axios';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import Layout from '@/components/Layout';
import { Hotel, FileText, TrendingUp, Award, ShoppingCart, Users, BedDouble, Calendar } from 'lucide-react';

const Dashboard = ({ user, tenant, onLogout }) => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [aiBriefing, setAiBriefing] = useState(null);
  const [loadingAI, setLoadingAI] = useState(false);

  useEffect(() => {
    loadDashboardStats();
    loadAIBriefing();
  }, []);

  const loadAIBriefing = async () => {
    setLoadingAI(true);
    try {
      const response = await axios.get('/ai/dashboard/briefing');
      setAiBriefing(response.data);
    } catch (error) {
      console.error('Failed to load AI briefing:', error);
      // Fail silently - AI features are optional
    } finally {
      setLoadingAI(false);
    }
  };

  const loadDashboardStats = async () => {
    try {
      const pmsResponse = await axios.get('/pms/dashboard');
      const invoiceResponse = await axios.get('/invoices/stats');
      
      setStats({
        pms: pmsResponse.data,
        invoices: invoiceResponse.data
      });
    } catch (error) {
      console.error('Failed to load stats:', error);
    } finally {
      setLoading(false);
    }
  };

  const modules = [
    {
      title: t('nav.pms'),
      description: t('dashboard.propertyManagement'),
      icon: Hotel,
      path: '/pms',
      color: '#667eea',
      stats: stats?.pms
    },
    {
      title: t('nav.invoices'),
      description: t('dashboard.billingReporting'),
      icon: FileText,
      path: '/invoices',
      color: '#f093fb',
      stats: stats?.invoices
    },
    {
      title: t('nav.rms'),
      description: t('dashboard.revenueManagement'),
      icon: TrendingUp,
      path: '/rms',
      color: '#4facfe'
    },
    {
      title: 'Cost Management',
      description: 'Track operational costs & expenses',
      icon: TrendingUp,
      path: '/cost-management',
      color: '#f093fb',
      badge: 'NEW'
    },
    {
      title: 'Housekeeping',
      description: 'Staff, rooms & task management',
      icon: Hotel,
      path: '/housekeeping',
      color: '#3b82f6',
      badge: 'NEW'
    },
    {
      title: 'POS Restaurant',
      description: 'Tables, menu & orders',
      icon: ShoppingCart,
      path: '/pos',
      color: '#f97316',
      badge: 'NEW'
    },
    {
      title: '✨ New Features',
      description: 'All new features showcase',
      icon: Award,
      path: '/features',
      color: '#a855f7',
      badge: 'NEW'
    },
    {
      title: t('nav.loyalty'),
      description: t('dashboard.guestRewards'),
      icon: Award,
      path: '/loyalty',
      color: '#43e97b'
    },
    {
      title: t('nav.marketplace'),
      description: t('dashboard.wholesalePurchasing'),
      icon: ShoppingCart,
      path: '/marketplace',
      color: '#fa709a'
    }
  ];

  return (
    <Layout user={user} tenant={tenant} onLogout={onLogout} currentModule="dashboard">
      <div className="p-4 md:p-6 space-y-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold mb-1" style={{ fontFamily: 'Space Grotesk' }}>
            {t('dashboard.welcome')}, {user.name}
          </h1>
          <p className="text-sm md:text-base text-gray-600">{tenant?.property_name || 'Hotel Management System'}</p>
        </div>

        {loading ? (
          <div className="text-center py-12">{t('common.loading')}</div>
        ) : (
          <>
            {/* AI Daily Briefing Card */}
            {aiBriefing && (
              <Card className="bg-gradient-to-r from-blue-500 to-purple-600 text-white mb-4">
                <CardHeader className="p-4">
                  <CardTitle className="flex items-center justify-between text-base md:text-lg">
                    <span className="flex items-center">
                      <span className="text-xl mr-2">🤖</span>
                      {t('ai.dailyBriefing')}
                    </span>
                    <Button 
                      variant="ghost" 
                      size="sm" 
                      onClick={loadAIBriefing}
                      className="text-white hover:bg-white/20 text-xs"
                      disabled={loadingAI}
                    >
                      {loadingAI ? t('ai.loading') : t('ai.refreshInsights')}
                    </Button>
                  </CardTitle>
                </CardHeader>
                <CardContent className="p-4 pt-0">
                  <p className="text-sm md:text-base leading-relaxed mb-3">{aiBriefing.briefing}</p>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs bg-white/10 rounded-lg p-3">
                    <div>
                      <div className="opacity-75 text-xs">Occupancy</div>
                      <div className="text-lg font-bold">{aiBriefing.metrics?.occupancy_rate?.toFixed(1)}%</div>
                    </div>
                    <div>
                      <div className="opacity-75 text-xs">Check-ins Today</div>
                      <div className="text-lg font-bold">{aiBriefing.metrics?.today_checkins}</div>
                    </div>
                    <div>
                      <div className="opacity-75 text-xs">Check-outs Today</div>
                      <div className="text-lg font-bold">{aiBriefing.metrics?.today_checkouts}</div>
                    </div>
                    <div>
                      <div className="opacity-75 text-xs">Monthly Revenue</div>
                      <div className="text-lg font-bold">${(aiBriefing.metrics?.monthly_revenue || 0).toFixed(0)}</div>
                    </div>
                  </div>
                  <div className="text-xs opacity-75 mt-2 text-right">
                    {t('ai.poweredBy')} • Generated: {new Date(aiBriefing.generated_at).toLocaleTimeString()}
                  </div>
                </CardContent>
              </Card>
            )}

            {loadingAI && !aiBriefing && (
              <Card className="bg-gradient-to-r from-blue-500 to-purple-600 text-white mb-6">
                <CardContent className="py-8">
                  <div className="flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-white mr-3"></div>
                    <span className="text-lg">{t('ai.loading')}</span>
                  </div>
                </CardContent>
              </Card>
            )}

            {/* Quick Stats */}
            {stats?.pms && (
              <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-4 gap-3">
                <Card className="hover:shadow-md transition-shadow">
                  <CardContent className="p-4 text-center">
                    <div className="flex flex-col items-center space-y-2">
                      <div className="p-2 bg-blue-100 rounded-lg">
                        <BedDouble className="w-6 h-6 text-blue-500" />
                      </div>
                      <div className="text-2xl font-bold text-gray-900">{stats.pms.total_rooms}</div>
                      <div className="text-xs font-medium text-gray-600">{t('dashboard.totalRooms')}</div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="hover:shadow-md transition-shadow">
                  <CardContent className="p-4 text-center">
                    <div className="flex flex-col items-center space-y-2">
                      <div className="p-2 bg-green-100 rounded-lg">
                        <Hotel className="w-6 h-6 text-green-500" />
                      </div>
                      <div className="text-2xl font-bold text-gray-900">{stats.pms.occupancy_rate.toFixed(1)}%</div>
                      <div className="text-xs font-medium text-gray-600">{t('dashboard.occupancyRate')}</div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="hover:shadow-md transition-shadow">
                  <CardContent className="p-4 text-center">
                    <div className="flex flex-col items-center space-y-2">
                      <div className="p-2 bg-purple-100 rounded-lg">
                        <Calendar className="w-6 h-6 text-purple-500" />
                      </div>
                      <div className="text-2xl font-bold text-gray-900">{stats.pms.today_checkins}</div>
                      <div className="text-xs font-medium text-gray-600">{t('dashboard.todayCheckins')}</div>
                    </div>
                  </CardContent>
                </Card>

                <Card className="hover:shadow-md transition-shadow">
                  <CardContent className="p-4 text-center">
                    <div className="flex flex-col items-center space-y-2">
                      <div className="p-2 bg-orange-100 rounded-lg">
                        <Users className="w-6 h-6 text-orange-500" />
                      </div>
                      <div className="text-2xl font-bold text-gray-900">{stats.pms.total_guests}</div>
                      <div className="text-xs font-medium text-gray-600">{t('dashboard.totalGuests')}</div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Modules Grid */}
            <div>
              <h2 className="text-xl md:text-2xl font-bold mb-3" style={{ fontFamily: 'Space Grotesk' }}>{t('dashboard.yourModules')}</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {modules.map((module) => {
                  const Icon = module.icon;
                  return (
                    <Card 
                      key={module.path} 
                      className={`card-hover cursor-pointer ${module.badge === 'NEW' ? 'border-2 border-purple-400 shadow-lg' : ''}`}
                      onClick={() => navigate(module.path)}
                      data-testid={`module-${module.title.toLowerCase()}`}
                    >
                      <CardHeader className="p-4">
                        <div className="flex items-center space-x-2">
                          <div 
                            style={{ 
                              background: module.color,
                              padding: '8px',
                              borderRadius: '8px'
                            }}
                          >
                            <Icon className="w-5 h-5 text-white" />
                          </div>
                          <div className="flex-1">
                            <div className="flex items-center justify-between">
                              <CardTitle className="text-base">{module.title}</CardTitle>
                              {module.badge && (
                                <span className="px-1.5 py-0.5 text-xs font-bold bg-purple-100 text-purple-700 rounded">
                                  {module.badge}
                                </span>
                              )}
                            </div>
                            <CardDescription className="text-xs">{module.description}</CardDescription>
                          </div>
                        </div>
                      </CardHeader>
                      {module.stats && (
                        <CardContent>
                          <div className="grid grid-cols-2 gap-2 text-sm">
                            {Object.entries(module.stats).slice(0, 2).map(([key, value]) => (
                              <div key={key}>
                                <p className="text-gray-500 capitalize">{key.replace('_', ' ')}</p>
                                <p className="font-semibold">{typeof value === 'number' ? value.toFixed(0) : value}</p>
                              </div>
                            ))}
                          </div>
                        </CardContent>
                      )}
                    </Card>
                  );
                })}
              </div>
            </div>
          </>
        )}
      </div>
    </Layout>
  );
};

export default Dashboard;
