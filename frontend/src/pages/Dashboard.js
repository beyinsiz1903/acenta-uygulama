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

  useEffect(() => {
    loadDashboardStats();
  }, []);

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
      <div className="p-6 space-y-6">
        <div>
          <h1 className="text-4xl font-bold mb-2" style={{ fontFamily: 'Space Grotesk' }}>
            {t('dashboard.welcome')}, {user.name}
          </h1>
          <p className="text-lg text-gray-600">{tenant.property_name}</p>
        </div>

        {loading ? (
          <div className="text-center py-12">{t('common.loading')}</div>
        ) : (
          <>
            {/* Quick Stats */}
            {stats?.pms && (
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-gray-600">{t('dashboard.totalRooms')}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center">
                      <BedDouble className="w-8 h-8 mr-3 text-blue-500" />
                      <div className="text-3xl font-bold">{stats.pms.total_rooms}</div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-gray-600">{t('dashboard.occupancyRate')}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center">
                      <Hotel className="w-8 h-8 mr-3 text-green-500" />
                      <div className="text-3xl font-bold">{stats.pms.occupancy_rate.toFixed(1)}%</div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-gray-600">{t('dashboard.todayCheckins')}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center">
                      <Calendar className="w-8 h-8 mr-3 text-purple-500" />
                      <div className="text-3xl font-bold">{stats.pms.today_checkins}</div>
                    </div>
                  </CardContent>
                </Card>

                <Card>
                  <CardHeader className="pb-2">
                    <CardTitle className="text-sm font-medium text-gray-600">{t('dashboard.totalGuests')}</CardTitle>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center">
                      <Users className="w-8 h-8 mr-3 text-orange-500" />
                      <div className="text-3xl font-bold">{stats.pms.total_guests}</div>
                    </div>
                  </CardContent>
                </Card>
              </div>
            )}

            {/* Modules Grid */}
            <div>
              <h2 className="text-2xl font-bold mb-4" style={{ fontFamily: 'Space Grotesk' }}>{t('dashboard.yourModules')}</h2>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                {modules.map((module) => {
                  const Icon = module.icon;
                  return (
                    <Card 
                      key={module.path} 
                      className="card-hover cursor-pointer"
                      onClick={() => navigate(module.path)}
                      data-testid={`module-${module.title.toLowerCase()}`}
                    >
                      <CardHeader>
                        <div className="flex items-center space-x-3">
                          <div 
                            style={{ 
                              background: module.color,
                              padding: '12px',
                              borderRadius: '12px'
                            }}
                          >
                            <Icon className="w-6 h-6 text-white" />
                          </div>
                          <div>
                            <CardTitle>{module.title}</CardTitle>
                            <CardDescription>{module.description}</CardDescription>
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
