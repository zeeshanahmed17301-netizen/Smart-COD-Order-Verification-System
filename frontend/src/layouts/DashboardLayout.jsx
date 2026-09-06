import React from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { 
  LayoutDashboard, 
  ShoppingCart, 
  Settings, 
  Store, 
  LogOut, 
  Menu, 
  X,
  Bell,
  Search,
  ChevronDown,
  MessageSquare,
  ShieldCheck,
  BarChart2,
  FileText,
  User
} from 'lucide-react';
import { useState } from 'react';
import clsx from 'clsx';

const SidebarItem = ({ to, icon: Icon, label, active, badge }) => (
  <Link
    to={to}
    className={clsx(
      "flex items-center gap-3 px-4 py-3 rounded-xl transition-all duration-200",
      active 
        ? "bg-gradient-to-r from-teal-700 to-emerald-600 text-white shadow-lg shadow-emerald-200/70" 
        : "text-slate-600 hover:bg-slate-100 hover:text-slate-900 hover:translate-x-1"
    )}
  >
    <Icon size={20} className={active ? "text-white" : ""} />
    <span className="font-medium">{label}</span>
    {badge && (
      <span className={clsx(
        "ml-auto text-xs font-semibold px-2 py-0.5 rounded-full",
        active ? "bg-white/20 text-white" : "bg-teal-100 text-teal-700"
      )}>
        {badge}
      </span>
    )}
  </Link>
);

const SidebarSection = ({ title, children }) => (
  <div className="space-y-1">
    <p className="px-4 text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">{title}</p>
    {children}
  </div>
);

export default function DashboardLayout() {
  const location = useLocation();
  const navigate = useNavigate();
  const { user, logout } = useAuth();
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [showNotifications, setShowNotifications] = useState(false);
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  const userName = user?.user?.first_name 
    ? `${user.user.first_name} ${user.user.last_name || ''}`.trim()
    : user?.store_name || 'User';
  const userEmail = user?.user?.email || '';
  const userInitial = userName.charAt(0).toUpperCase();

  const handleLogout = () => {
    logout();
    navigate('/login', { replace: true });
  };

  const handleSearchSubmit = (event) => {
    event.preventDefault();
    const value = searchQuery.trim();
    navigate(value ? `/orders?search=${encodeURIComponent(value)}` : '/orders');
    setIsSidebarOpen(false);
  };

  const mainNavItems = [
    { path: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { path: '/orders', label: 'Orders', icon: ShoppingCart },
    { path: '/analytics', label: 'Analytics', icon: BarChart2 },
    { path: '/logs', label: 'Messaging Logs', icon: FileText },
  ];

  const settingsNavItems = [
    { path: '/connect-store', label: 'Connect Store', icon: Store },
    { path: '/chatbot-settings', label: 'Chatbot Settings', icon: MessageSquare },
    { path: '/account', label: 'Account Settings', icon: User },
  ];

  return (
    <div className="flex h-screen bg-slate-50">
      {/* Sidebar */}
      <aside 
        className={clsx(
          "fixed inset-y-0 left-0 z-50 w-72 bg-white border-r border-slate-200 transform transition-transform duration-300 ease-in-out lg:relative lg:translate-x-0 flex flex-col",
          !isSidebarOpen && "-translate-x-full lg:hidden"
        )}
      >
        {/* Logo */}
        <div className="h-16 flex items-center justify-between px-6 border-b border-slate-100">
          <Link to="/" className="flex items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-slate-900 to-teal-700 flex items-center justify-center">
              <ShieldCheck className="w-6 h-6 text-white" />
            </div>
            <span className="text-xl font-bold text-slate-900">Risk<span className="text-teal-700">Guard</span></span>
          </Link>
          <button 
            onClick={() => setIsSidebarOpen(false)}
            className="lg:hidden p-1 rounded-md text-slate-400 hover:text-slate-600"
          >
            <X size={20} />
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 px-4 py-6 space-y-8 overflow-y-auto">
          <SidebarSection title="Main Menu">
            {mainNavItems.map((item) => (
              <SidebarItem
                key={item.path}
                to={item.path}
                icon={item.icon}
                label={item.label}
                badge={item.badge}
                active={location.pathname === item.path || (item.path !== '/dashboard' && location.pathname.startsWith(item.path))}
              />
            ))}
          </SidebarSection>

          <SidebarSection title="Settings">
            {settingsNavItems.map((item) => (
              <SidebarItem
                key={item.path}
                to={item.path}
                icon={item.icon}
                label={item.label}
                active={location.pathname.startsWith(item.path)}
              />
            ))}
          </SidebarSection>
        </nav>

        {/* User Card */}
        <div className="p-4 border-t border-slate-100">
          <div className="bg-gradient-to-r from-teal-50 to-emerald-50 rounded-xl p-4 border border-teal-100">
            <div className="flex items-center gap-3 mb-3">
              <div className="w-10 h-10 rounded-full bg-gradient-to-br from-teal-700 to-emerald-600 flex items-center justify-center text-white font-semibold">
                {userInitial}
              </div>
              <div className="flex-1 min-w-0">
                <p className="text-sm font-semibold text-slate-900 truncate">{userName}</p>
                <p className="text-xs text-slate-500 truncate">{userEmail}</p>
              </div>
            </div>
            <button 
              onClick={handleLogout}
              className="w-full flex items-center justify-center gap-2 px-3 py-2 text-sm font-medium text-red-600 bg-white rounded-lg hover:bg-red-50 transition-colors border border-red-100"
            >
              <LogOut size={16} />
              Sign out
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        {/* Header */}
        <header className="h-16 bg-white border-b border-slate-200 flex items-center justify-between px-4 lg:px-8 sticky top-0 z-40">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setIsSidebarOpen(!isSidebarOpen)}
              className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 lg:hidden"
            >
              <Menu size={24} />
            </button>
            
            {/* Search Bar */}
            <form onSubmit={handleSearchSubmit} className="hidden md:block relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
              <input
                type="text"
                value={searchQuery}
                onChange={(event) => setSearchQuery(event.target.value)}
                placeholder="Search orders, customers..."
                className="w-80 pl-10 pr-4 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-600 focus:border-transparent focus:bg-white transition-all"
              />
            </form>
          </div>
          
          <div className="flex items-center gap-3">
            

            {/* Notifications */}
            

            {/* User Menu */}
            <div className="relative">
              <button 
                onClick={() => setShowUserMenu(!showUserMenu)}
                className="flex items-center gap-3 p-1.5 rounded-lg hover:bg-slate-100 transition-colors"
              >
                <div className="w-8 h-8 rounded-full bg-gradient-to-br from-slate-900 to-teal-700 flex items-center justify-center text-white text-sm font-semibold">
                  {userInitial}
                </div>
                <span className="text-sm font-medium text-slate-700 hidden sm:block">{userName}</span>
                <ChevronDown size={16} className="text-slate-400 hidden sm:block" />
              </button>

              {showUserMenu && (
                <div className="absolute right-0 mt-2 w-56 bg-white rounded-xl shadow-xl border border-slate-200 py-2 z-50">
                  <div className="px-4 py-3 border-b border-slate-100">
                    <p className="text-sm font-semibold text-slate-900">{userName}</p>
                    <p className="text-xs text-slate-500">{userEmail}</p>
                  </div>
                  <div className="py-1">
                    <Link
                      to="/account"
                      onClick={() => setShowUserMenu(false)}
                      className="block px-4 py-2 text-sm text-slate-700 hover:bg-slate-50"
                    >
                      Account Settings
                    </Link>
                  </div>
                  <div className="border-t border-slate-100 py-1">
                    <button onClick={handleLogout} className="block w-full text-left px-4 py-2 text-sm text-red-600 hover:bg-red-50">Sign out</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </header>

        {/* Page Content */}
        <main className="flex-1 overflow-y-auto">
          <div className="p-6 lg:p-8 w-full">
            <Outlet />
          </div>
        </main>
      </div>
      
      {/* Mobile Overlay */}
      {isSidebarOpen && (
        <div 
          className="fixed inset-0 bg-slate-900/50 backdrop-blur-sm z-40 lg:hidden"
          onClick={() => setIsSidebarOpen(false)}
        />
      )}
    </div>
  );
}
