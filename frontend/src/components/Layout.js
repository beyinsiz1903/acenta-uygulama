import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Home, Hotel, FileText, TrendingUp, Award, ShoppingCart, User, LogOut, Menu } from 'lucide-react';

const Layout = ({ children, user, tenant, onLogout, currentModule }) => {
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navigation = [
    { name: 'Dashboard', path: '/', icon: Home, id: 'dashboard' },
    { name: 'PMS', path: '/pms', icon: Hotel, id: 'pms' },
    { name: 'Invoices', path: '/invoices', icon: FileText, id: 'invoices' },
    { name: 'RMS', path: '/rms', icon: TrendingUp, id: 'rms' },
    { name: 'Loyalty', path: '/loyalty', icon: Award, id: 'loyalty' },
    { name: 'Marketplace', path: '/marketplace', icon: ShoppingCart, id: 'marketplace' },
  ];

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-50 shadow-sm">
        <div className="px-4 py-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <h1 
                className="text-2xl font-bold cursor-pointer"
                style={{ fontFamily: 'Space Grotesk', color: '#667eea' }}
                onClick={() => navigate('/')}
                data-testid="logo"
              >
                RoomOps
              </h1>
              <div className="hidden md:block text-sm text-gray-500">
                {tenant.property_name}
              </div>
            </div>

            {/* Desktop Navigation */}
            <nav className="hidden md:flex items-center space-x-1">
              {navigation.map((item) => {
                const Icon = item.icon;
                const isActive = currentModule === item.id;
                return (
                  <Button
                    key={item.path}
                    variant={isActive ? 'default' : 'ghost'}
                    onClick={() => navigate(item.path)}
                    className="flex items-center space-x-2"
                    data-testid={`nav-${item.id}`}
                  >
                    <Icon className="w-4 h-4" />
                    <span>{item.name}</span>
                  </Button>
                );
              })}
            </nav>

            {/* User Menu */}
            <div className="flex items-center space-x-2">
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
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {/* Mobile Navigation */}
          {mobileMenuOpen && (
            <nav className="md:hidden mt-4 pb-2 space-y-1">
              {navigation.map((item) => {
                const Icon = item.icon;
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
                    <Icon className="w-4 h-4" />
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
