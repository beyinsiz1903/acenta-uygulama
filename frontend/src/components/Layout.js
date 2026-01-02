import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Home, Hotel, FileText, TrendingUp, Award, ShoppingCart, User, LogOut, Menu, Network, Calendar, DollarSign, Smartphone, Settings as SettingsIcon, ChefHat, Wrench, Building2 } from 'lucide-react';
import LanguageSelector from '@/components/LanguageSelector';
import NotificationBell from '@/components/NotificationBell';
import PushSubscriptionManager from '@/components/PushSubscriptionManager';
import { NAV_ITEMS } from '@/config/navItems';
import { normalizeFeatures } from '@/utils/featureFlags';

const ICON_BY_KEY = {
  dashboard: Home,
  pms: Hotel,
  reservation_calendar: Calendar,
  reports: FileText,
  settings: SettingsIcon,
  rms: TrendingUp,
  ai: Award,
  marketplace: ShoppingCart,
};

const Layout = ({ children, user, tenant, onLogout, currentModule }) => {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const navScrollRef = useRef(null);

  // Normalize feature flags from tenant.features (supports both core_* and lite keys)
  const normalizedFeatures = normalizeFeatures(tenant?.features || {});

  // Filter navigation items based on feature flags and super admin rules
  const navigation = NAV_ITEMS.filter((item) => {
    // Super admin only items
    if (item.requireSuperAdmin && user?.role !== 'super_admin') {
      return false;
    }

    // Feature-based visibility
    if (item.feature && normalizedFeatures) {
      if (!normalizedFeatures[item.feature]) {
        return false;
      }
    }

    return true;
  }).map((item) => ({
    ...item,
    name: item.i18nKey ? t(item.i18nKey) : item.label,
  }));

  // Debug logging
  useEffect(() => {
    console.log('🔍 Layout Debug - User Info:', {
      email: user?.email,
      name: user?.name,
      role: user?.role,
      isSuperAdmin: user?.role === 'super_admin'
    });
  }, [user]);

  // Scroll active item into view when currentModule changes
  useEffect(() => {
    if (navScrollRef.current && currentModule) {
      const activeButton = navScrollRef.current.querySelector(`[data-testid="nav-${currentModule}"]`);
      if (activeButton) {
        activeButton.scrollIntoView({ behavior: 'smooth', block: 'nearest', inline: 'center' });
      }
    }
  }, [currentModule]);

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <img 
                src="/syroce-logo.svg"
                alt="Syroce Logo" 
                className="h-10 w-auto cursor-pointer"
                onClick={() => navigate('/')}
                data-testid="logo"
              />
              <div className="flex flex-col leading-tight min-w-0">
                <span className="text-xs uppercase tracking-[0.2em] text-gray-400 hidden md:block">
                  Syroce PMS
                </span>
                <span
                  className="text-sm font-semibold text-gray-700 truncate max-w-[160px] sm:max-w-[240px] md:max-w-xs"
                  title={tenant?.property_name || 'Hotel Management'}
                >
                  {tenant?.property_name || 'Hotel Management'}
                </span>
              </div>
            </div>

            {/* Desktop Navigation - Compact & Beautiful with Scroll Preservation */}
            <nav 
              ref={navScrollRef}
              className="hidden md:flex items-center space-x-1 max-w-3xl overflow-x-auto scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100"
              style={{ scrollBehavior: 'smooth' }}
            >
              {navigation.map((item) => {
                // Super Admin kontrolü - sadece super_admin görebilir
                if (item.requireSuperAdmin && user?.role !== 'super_admin') {
                  return null;
                }
                
                // Eğer tenant.modules varsa, backend modül yetkilerine göre menüyü filtrele
                if (tenant?.modules && item.moduleKey) {
                  if (tenant.modules[item.moduleKey] === false) {
                    return null;
                  }
                }
                const Icon = item.icon || ICON_BY_KEY[item.key] || Home;
                const isActive = currentModule === item.id;
                return (
                  <Button
                    key={item.path}
                    variant={isActive ? 'default' : 'ghost'}
                    size="sm"
                    onClick={() => navigate(item.path)}
                    className={`flex items-center space-x-1.5 px-3 py-2 text-xs whitespace-nowrap ${
                      item.highlight 
                        ? 'bg-gradient-to-r from-blue-500 to-purple-500 text-white hover:from-blue-600 hover:to-purple-600' 
                        : isActive 
                        ? 'bg-blue-600 text-white hover:bg-blue-700'
                        : 'hover:bg-gray-100'
                    }`}
                    data-testid={`nav-${item.id}`}
                  >
                    {Icon ? <Icon className="w-3.5 h-3.5" /> : null}
                    <span className="font-medium">{item.name}</span>
                  </Button>
                );
              })}
            </nav>

            {/* User Menu and Utilities */}
            <div className="flex items-center space-x-3">
              <div className="hidden md:block">
                <LanguageSelector />
              </div>
              <PushSubscriptionManager />
              <NotificationBell />
              <Button
                variant="ghost"
                className="md:hidden"
                onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
                data-testid="mobile-menu-btn"
              >
                <Menu className="w-5 h-5" />
              </Button>
              
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="outline" size="sm" data-testid="user-menu-btn">
                    <User className="w-4 h-4 mr-2" />
                    {user.name}
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  <DropdownMenuLabel>My Account</DropdownMenuLabel>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem className="text-sm">
                    {user.email}
                  </DropdownMenuItem>
                  <DropdownMenuItem className="text-sm text-gray-500">
                    Role: {user.role}
                  </DropdownMenuItem>
                  <DropdownMenuSeparator />
                  <DropdownMenuItem onClick={onLogout} data-testid="logout-btn">
                    <LogOut className="w-4 h-4 mr-2" />
                    {t('common.logout')}
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {/* Mobile Navigation */}
          {mobileMenuOpen && (
            <nav className="md:hidden mt-4 pb-2 space-y-2">
              {/* Language Selector for Mobile */}
              <div className="px-2 py-2 border-b border-gray-200">
                <LanguageSelector />
              </div>
              
              {navigation.map((item) => {
                // Super Admin kontrolü - sadece super_admin görebilir
                if (item.requireSuperAdmin && user?.role !== 'super_admin') {
                  return null;
                }
                
                // Eğer tenant.modules varsa, backend modül yetkilerine göre menüyü filtrele
                if (tenant?.modules && item.moduleKey) {
                  if (tenant.modules[item.moduleKey] === false) {
                    return null;
                  }
                }
                const Icon = item.icon || ICON_BY_KEY[item.key] || Home;
                const isActive = currentModule === item.id;
                return (
                  <Button
                    key={item.path}
                    variant={isActive ? 'default' : 'ghost'}
                    onClick={() => {
                      navigate(item.path);
                      setMobileMenuOpen(false);
                    }}
                    className="w-full justify-start flex items-center space-x-2"
                  >
                    {Icon ? <Icon className="w-4 h-4" /> : null}
                    <span>{item.name}</span>
                  </Button>
                );
              })}
            </nav>
          )}
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto">
        {children}
      </main>
    </div>
  );
};

export default Layout;
