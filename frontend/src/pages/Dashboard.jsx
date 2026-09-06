import React, { useState, useEffect } from 'react';
import { 
  TrendingDown, 
  AlertTriangle, 
  DollarSign, 
  ShoppingBag, 
  CheckCircle,
  ArrowUpRight,
  ArrowDownRight,
  Clock,
  Shield,
  Activity,
  Calendar,
  Loader2,
  AlertCircle
} from 'lucide-react';
import clsx from 'clsx';
import { Link } from 'react-router-dom';
import { motion as Motion } from 'framer-motion';
import { 
  LineChart,
  Line,
  XAxis, 
  YAxis, 
  CartesianGrid, 
  Tooltip, 
  ResponsiveContainer,
} from 'recharts';
import analyticsApi from '../api/analytics';
import ordersApi from '../api/orders';
import { getErrorMessage } from '../api/client';

const container = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: {
      staggerChildren: 0.1
    }
  }
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 }
};

const StatsCard = ({ title, value, icon: Icon, trend, trendLabel, gradient }) => (
  <Motion.div 
    initial={{ opacity: 0, y: 20 }}
    animate={{ opacity: 1, y: 0 }}
    transition={{ duration: 0.25, ease: 'easeOut' }}
    className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden hover:shadow-lg transition-all duration-300 group"
  >
    <div className="p-6">
      <div className="flex items-start justify-between">
        <div className={`p-3 rounded-xl ${gradient} group-hover:scale-110 transition-transform duration-300`}>
          <Icon className="h-6 w-6 text-white" />
        </div>
        {trend !== undefined && (
          <div className={clsx(
            "flex items-center gap-1 text-sm font-medium px-2 py-1 rounded-full",
            trend > 0 ? "bg-green-50 text-green-600" : "bg-red-50 text-red-600"
          )}>
            {trend > 0 ? <ArrowUpRight className="w-4 h-4" /> : <ArrowDownRight className="w-4 h-4" />}
            {Math.abs(trend)}%
          </div>
        )}
      </div>
      <div className="mt-4">
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <p className="text-3xl font-bold text-slate-900 mt-1">{value}</p>
        <p className="text-xs text-slate-400 mt-2">{trendLabel}</p>
      </div>
    </div>
  </Motion.div>
);

const RiskBadge = ({ level, score }) => {
  const config = {
    low: { bg: "bg-emerald-50", text: "text-emerald-700", bar: "bg-emerald-500", border: "border-emerald-200" },
    medium: { bg: "bg-amber-50", text: "text-amber-700", bar: "bg-amber-500", border: "border-amber-200" },
    high: { bg: "bg-orange-50", text: "text-orange-700", bar: "bg-orange-500", border: "border-orange-200" },
    critical: { bg: "bg-red-50", text: "text-red-700", bar: "bg-red-500", border: "border-red-200" },
  };
  const style = config[level] || config.low;
  const width = Math.max(0, Math.min(Number(score || 0), 100));

  return (
    <div className="flex items-center gap-3">
      <div className="w-20 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={clsx("h-full rounded-full", style.bar)} style={{ width: `${width}%` }} />
      </div>
      <span className={clsx("inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border capitalize", style.bg, style.text, style.border)}>
        {level || 'low'}
      </span>
    </div>
  );
};

const ChatStatusBadge = ({ status }) => {
  const config = {
    confirmed: { icon: CheckCircle, bg: "bg-green-100", text: "text-green-700", label: "Confirmed" },
    completed: { icon: CheckCircle, bg: "bg-emerald-100", text: "text-emerald-700", label: "Verified" },
    awaiting_reply: { icon: Clock, bg: "bg-amber-100", text: "text-amber-700", label: "Awaiting Reply" },
    active: { icon: Clock, bg: "bg-blue-100", text: "text-blue-700", label: "In Progress" },
    processing: { icon: Loader2, bg: "bg-blue-50", text: "text-blue-600", label: "Processing" },
    failed: { icon: AlertCircle, bg: "bg-red-100", text: "text-red-700", label: "Failed" },
    cancelled: { icon: AlertCircle, bg: "bg-slate-100", text: "text-slate-600", label: "Cancelled" },
    denied: { icon: AlertCircle, bg: "bg-red-100", text: "text-red-700", label: "Denied" },
    no_response: { icon: Clock, bg: "bg-amber-100", text: "text-amber-700", label: "No Response" },
    unverified: { icon: Clock, bg: "bg-slate-100", text: "text-slate-600", label: "Unverified" },
  };
  const style = config[status] || config.unverified;
  const Icon = style.icon;

  return (
    <span className={clsx("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium", style.bg, style.text)}>
      <Icon className={clsx("w-3.5 h-3.5", status === 'processing' && 'animate-spin')} />
      {style.label}
    </span>
  );
};

const QuickAction = ({ icon: Icon, label, description, color }) => (
  <Motion.button 
    variants={item}
    className="flex items-center gap-4 p-4 bg-white rounded-xl border border-slate-200 hover:border-teal-300 hover:shadow-md transition-all w-full text-left group"
  >
    <div className={`p-3 rounded-lg ${color} group-hover:scale-110 transition-transform`}>
      <Icon className="w-5 h-5 text-white" />
    </div>
    <div className="flex-1 min-w-0">
      <p className="font-semibold text-slate-900 group-hover:text-teal-700 transition-colors">{label}</p>
      <p className="text-sm text-slate-500 truncate">{description}</p>
    </div>
    <ArrowUpRight className="w-5 h-5 text-slate-400 group-hover:text-teal-700 transition-colors" />
  </Motion.button>
);

// Loading skeleton for stats cards
const StatsSkeleton = () => (
  <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-6 animate-pulse">
    <div className="flex items-start justify-between">
      <div className="w-12 h-12 rounded-xl bg-slate-200" />
      <div className="w-16 h-6 rounded-full bg-slate-200" />
    </div>
    <div className="mt-4 space-y-2">
      <div className="w-24 h-4 rounded bg-slate-200" />
      <div className="w-16 h-8 rounded bg-slate-200" />
    </div>
  </div>
);

export default function Dashboard() {
  const [stats, setStats] = useState(null);
  const [orders, setOrders] = useState([]);
  const [trendData, setTrendData] = useState([]);
  const [selectedDays, setSelectedDays] = useState(7);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchDashboard = async () => {
      setLoading(true);
      setError('');
      try {
        const [statsRes, ordersRes, trendRes] = await Promise.all([
          analyticsApi.getDashboardStats(selectedDays),
          ordersApi.list({ page_size: 5, ordering: '-created_at' }),
          analyticsApi.getRtoTrend(selectedDays),
        ]);
        setStats(statsRes.data);
        setOrders(ordersRes.data.results || ordersRes.data);
        setTrendData(trendRes.data);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };
    fetchDashboard();
  }, [selectedDays]);

  const handleDownloadReport = () => {
    const payload = {
      generated_at: new Date().toISOString(),
      period_days: selectedDays,
      stats,
      trend: trendData,
      recent_orders: orders,
    };
    const blob = new Blob([JSON.stringify(payload, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `riskguard-dashboard-${selectedDays}d.json`;
    link.click();
    URL.revokeObjectURL(url);
  };

  if (error) {
    return (
      <div className="flex items-center gap-3 p-6 bg-red-50 border border-red-200 rounded-xl text-red-700">
        <AlertCircle className="h-5 w-5 flex-shrink-0" />
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  return (
    <Motion.div 
      variants={container}
      initial="hidden"
      animate="show"
      className="space-y-8"
    >
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="mt-1 text-slate-500">Welcome back! Here's what's happening with your store.</p>
        </div>
        <div className="flex items-center gap-3">
          <div className="relative">
            <Calendar className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <select
              value={selectedDays}
              onChange={(event) => setSelectedDays(Number(event.target.value))}
              className="pl-10 pr-4 py-2 bg-white border border-slate-200 rounded-lg text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-600 appearance-none cursor-pointer"
            >
              <option value={7}>Last 7 days</option>
              <option value={30}>Last 30 days</option>
              <option value={90}>Last 90 days</option>
            </select>
          </div>
          <button
            onClick={handleDownloadReport}
            className="px-4 py-2 bg-gradient-to-r from-teal-700 to-emerald-600 text-white rounded-lg text-sm font-medium hover:from-teal-800 hover:to-emerald-700 transition-all shadow-lg shadow-emerald-200/70"
          >
            Download Report
          </button>
        </div>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {loading ? (
          <>
            <StatsSkeleton />
            <StatsSkeleton />
            <StatsSkeleton />
            <StatsSkeleton />
          </>
        ) : stats && (
          <>
            <StatsCard 
              title="Today COD Orders" 
              value={stats.codOrdersToday} 
              icon={ShoppingBag} 
              trendLabel="today"
              gradient="bg-gradient-to-br from-teal-600 to-emerald-600"
            />
            <StatsCard 
              title="Avg. Fraud Score" 
              value={stats.fraudScore} 
              icon={AlertTriangle} 
              trendLabel="risk indicator"
              gradient="bg-gradient-to-br from-orange-500 to-red-500"
            />
            <StatsCard 
              title="RTO Percentage" 
              value={`${stats.rtoPercentage}%`} 
              icon={TrendingDown} 
              trendLabel={`${stats.rtoCount || 0} RTO / ${stats.totalOrders || 0} orders`}
              gradient="bg-gradient-to-br from-teal-600 to-emerald-600"
            />
            <StatsCard 
              title="Est. Savings" 
              value={`PKR ${Number(stats.savings).toLocaleString()}`} 
              icon={DollarSign} 
              trendLabel="this month"
              gradient="bg-gradient-to-br from-emerald-500 to-green-600"
            />
          </>
        )}
      </div>

      {/* Charts & Quick Actions */}
      <div className="grid lg:grid-cols-3 gap-8">
        {/* Chart */}
        <Motion.div variants={item} className="lg:col-span-2 bg-white rounded-2xl border border-slate-200 shadow-sm p-6">
          <div className="flex items-center justify-between mb-6">
            <div>
              <h2 className="text-lg font-bold text-slate-900">{`Last ${selectedDays} Days RTO Trend`}</h2>
              <p className="text-sm text-slate-500">{`Actual Return to Origin rate for orders created in each day`}</p>
            </div>
          </div>
          <div className="h-[300px] w-full">
            {trendData.length > 0 ? (
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trendData}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                  <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} dy={10} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
                  <Tooltip 
                    contentStyle={{ backgroundColor: '#fff', borderRadius: '12px', border: '1px solid #e2e8f0', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                    itemStyle={{ fontSize: '12px', fontWeight: '500' }}
                    formatter={(value, name, payload) => [
                      `${Number(value || 0).toFixed(1)}% (${payload?.payload?.rto_count || 0}/${payload?.payload?.total_orders || 0})`,
                      'RTO rate',
                    ]}
                  />
                  <Line type="monotone" dataKey="rto" stroke="#ef4444" strokeWidth={3} dot={{ r: 4, fill: '#ef4444', strokeWidth: 2, stroke: '#fff' }} activeDot={{ r: 6 }} />
                </LineChart>
              </ResponsiveContainer>
            ) : (
              <div className="flex items-center justify-center h-full text-slate-400">
                <p>No trend data available</p>
              </div>
            )}
          </div>
        </Motion.div>

        {/* Quick Actions */}
        <div className="space-y-6">
          <Motion.div variants={item}>
            <h2 className="text-lg font-semibold text-slate-900 mb-4">Quick Actions</h2>
            <div className="space-y-4">
              <Link to="/orders?risk_level=high">
                <QuickAction 
                  icon={Shield}
                  label="Review High-Risk"
                  description={`${stats?.highRiskPending || 0} pending high-risk orders`}
                  color="bg-gradient-to-br from-red-500 to-orange-500"
                />
              </Link>
              <Link to="/analytics">
                <QuickAction 
                  icon={Activity}
                  label="View Analytics"
                  description="Track RTO and fraud trends"
                  color="bg-gradient-to-br from-teal-600 to-emerald-600"
                />
              </Link>
              <Link to="/orders?status=verified">
                <QuickAction 
                  icon={CheckCircle}
                  label="Verified Orders"
                  description="View confirmed orders"
                  color="bg-gradient-to-br from-emerald-500 to-green-500"
                />
              </Link>
            </div>
          </Motion.div>
          
          <Motion.div variants={item} className="bg-gradient-to-br from-slate-900 to-teal-800 rounded-2xl p-6 text-white shadow-lg shadow-emerald-200/70">
            <h3 className="font-bold text-lg mb-2">Pro Tip</h3>
            <p className="text-emerald-100/90 text-sm mb-4">
              Platform WhatsApp verification can automate order confirmation and reduce manual review.
            </p>
            <Link to="/chatbot-settings" className="block w-full py-2 bg-white/10 hover:bg-white/20 rounded-lg text-sm font-medium transition-colors border border-white/20 text-center">
              Manage WhatsApp
            </Link>
          </Motion.div>
        </div>
      </div>

      {/* Recent Orders Table */}
      <Motion.div variants={item} className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between">
          <div>
            <h3 className="text-lg font-semibold text-slate-900">Recent Orders</h3>
            <p className="text-sm text-slate-500 mt-0.5">Latest COD orders requiring attention</p>
          </div>
          <Link 
            to="/orders" 
              className="inline-flex items-center gap-1 text-sm font-medium text-teal-700 hover:text-teal-800 transition-colors"
          >
            View all
            <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
        
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="bg-slate-50">
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Order ID</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Customer Name</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">City</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Risk Level</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">WhatsApp Status</th>
                <th scope="col" className="relative px-6 py-4">
                  <span className="sr-only">Action</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i} className="animate-pulse">
                    <td className="px-6 py-4"><div className="w-20 h-4 bg-slate-200 rounded" /></td>
                    <td className="px-6 py-4"><div className="w-28 h-4 bg-slate-200 rounded" /></td>
                    <td className="px-6 py-4"><div className="w-20 h-4 bg-slate-200 rounded" /></td>
                    <td className="px-6 py-4"><div className="w-32 h-4 bg-slate-200 rounded" /></td>
                    <td className="px-6 py-4"><div className="w-20 h-4 bg-slate-200 rounded" /></td>
                    <td className="px-6 py-4"><div className="w-12 h-4 bg-slate-200 rounded" /></td>
                  </tr>
                ))
              ) : orders.map((order) => (
                <tr key={order.order_id || order.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Link to={`/orders/${order.id}`} className="text-sm font-semibold text-teal-700 hover:text-teal-800">
                      {order.order_id}
                    </Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <p className="text-sm font-medium text-slate-900">{order.customer_name}</p>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className="text-sm text-slate-600">{order.customer_city}</span>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <RiskBadge level={order.risk_level} score={order.risk_score} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <ChatStatusBadge status={order.chat_status} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <Link 
                      to={`/orders/${order.id}`}
                      className="text-sm font-medium text-teal-700 hover:text-teal-800"
                    >
                      View
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        
        <div className="px-6 py-4 border-t border-slate-100 bg-slate-50/50">
          <div className="flex items-center justify-between">
            <p className="text-sm text-slate-600">
              Showing <span className="font-medium">{orders.length}</span> of <span className="font-medium">{stats?.totalOrders || 0}</span> orders
            </p>
            <Link 
              to="/orders" 
              className="inline-flex items-center gap-1 px-4 py-2 text-sm font-medium text-teal-700 bg-teal-50 rounded-lg hover:bg-teal-100 transition-colors"
            >
              View all orders
              <ArrowUpRight className="w-4 h-4" />
            </Link>
          </div>
        </div>
      </Motion.div>
    </Motion.div>
  );
}
