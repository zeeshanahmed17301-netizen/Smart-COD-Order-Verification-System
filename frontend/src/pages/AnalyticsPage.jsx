import React, { useEffect, useMemo, useState } from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from 'recharts';
import { TrendingDown, TrendingUp, DollarSign, ShoppingBag, AlertTriangle, AlertCircle } from 'lucide-react';
import analyticsApi from '../api/analytics';
import { getErrorMessage } from '../api/client';

const StatCard = ({ title, value, subtext, icon: Icon, color }) => (
  <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div className="flex items-start justify-between">
      <div>
        <p className="text-sm font-medium text-slate-500">{title}</p>
        <h3 className="mt-2 text-2xl font-bold text-slate-900">{value}</h3>
        <p className="mt-1 text-xs text-slate-400">{subtext}</p>
      </div>
      <div className={`rounded-xl p-3 ${color}`}>
        <Icon className="h-5 w-5 text-white" />
      </div>
    </div>
  </div>
);

const ChartSkeleton = () => (
  <div className="animate-pulse rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
    <div className="mb-6 h-5 w-48 rounded bg-slate-200" />
    <div className="h-[300px] rounded-xl bg-slate-100" />
  </div>
);

export default function AnalyticsPage() {
  const [overview, setOverview] = useState(null);
  const [trendData, setTrendData] = useState([]);
  const [heatmapData, setHeatmapData] = useState([]);
  const [fraudData, setFraudData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchAnalytics = async () => {
      try {
        const [overviewRes, trendRes, heatmapRes, fraudRes] = await Promise.all([
          analyticsApi.getOverview(),
          analyticsApi.getRtoTrend(7),
          analyticsApi.getRiskHeatmap(),
          analyticsApi.getFraudTrends(30),
        ]);
        setOverview(overviewRes.data);
        setTrendData(trendRes.data);
        setHeatmapData((heatmapRes.data || []).slice(0, 5));
        setFraudData(fraudRes.data);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };

    fetchAnalytics();
  }, []);

  const stats = useMemo(() => {
    const statusBreakdown = overview?.status_breakdown || {};
    const averages = overview?.averages || {};
    const totalOrders = overview?.total_orders || 0;
    const rtoOrders = statusBreakdown.rto || 0;
    const verifiedOrders = statusBreakdown.verified || 0;
    const pendingOrders = statusBreakdown.pending || 0;

    return {
      totalOrders,
      rtoRate: totalOrders ? ((rtoOrders / totalOrders) * 100).toFixed(1) : '0.0',
      verificationRate: totalOrders ? ((verifiedOrders / totalOrders) * 100).toFixed(1) : '0.0',
      pendingRate: totalOrders ? ((pendingOrders / totalOrders) * 100).toFixed(1) : '0.0',
      avgFraud: Number(averages.fraud_score || 0).toFixed(1),
      avgRisk: Number(averages.risk_score || 0).toFixed(1),
    };
  }, [overview]);

  if (error) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Analytics Overview</h1>
        </div>
        <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 p-6 text-red-700">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-slate-900">Analytics Overview</h1>
        <p className="mt-1 text-slate-500">Live metrics derived from your tracked orders and risk scores.</p>
      </div>

      <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-5">
        {loading ? (
          Array.from({ length: 5 }).map((_, index) => (
            <div key={index} className="animate-pulse rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="mb-3 h-4 w-24 rounded bg-slate-200" />
              <div className="h-7 w-16 rounded bg-slate-200" />
            </div>
          ))
        ) : (
          <>
            <StatCard title="Total Orders" value={stats.totalOrders.toLocaleString()} subtext="All tracked COD orders" icon={ShoppingBag} color="bg-teal-600" />
            <StatCard title="RTO Rate" value={`${stats.rtoRate}%`} subtext="Orders marked RTO" icon={TrendingDown} color="bg-purple-500" />
            <StatCard title="Verified Rate" value={`${stats.verificationRate}%`} subtext="Orders marked verified" icon={TrendingUp} color="bg-green-500" />
            <StatCard title="Pending Rate" value={`${stats.pendingRate}%`} subtext="Orders still awaiting action" icon={AlertTriangle} color="bg-orange-500" />
            <StatCard title="Avg Fraud Score" value={stats.avgFraud} subtext={`Avg risk score ${stats.avgRisk}`} icon={DollarSign} color="bg-emerald-500" />
          </>
        )}
      </div>

      <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
        {loading ? (
          <ChartSkeleton />
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="mb-6 text-lg font-bold text-slate-900">RTO Trend (7 Days)</h3>
            <div className="h-[300px]">
              {trendData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={trendData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
                    <Tooltip />
                    <Line type="monotone" dataKey="rto" stroke="#ef4444" strokeWidth={3} dot={{ r: 4, fill: '#ef4444' }} />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-slate-400">No data available</div>
              )}
            </div>
          </div>
        )}

        {loading ? (
          <ChartSkeleton />
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="mb-6 text-lg font-bold text-slate-900">Average Fraud Score (30 Days)</h3>
            <div className="h-[300px]">
              {fraudData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={fraudData}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} dy={10} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
                    <Tooltip cursor={{ fill: '#f8fafc' }} />
                    <Bar dataKey="avg_fraud" fill="#3b82f6" radius={[4, 4, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-slate-400">No data available</div>
              )}
            </div>
          </div>
        )}

        {loading ? (
          <ChartSkeleton />
        ) : (
          <div className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h3 className="mb-6 text-lg font-bold text-slate-900">High Risk Cities</h3>
            <div className="h-[300px]">
              {heatmapData.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={heatmapData} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                    <XAxis type="number" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} />
                    <YAxis dataKey="city" type="category" axisLine={false} tickLine={false} tick={{ fill: '#64748b', fontSize: 12 }} width={100} />
                    <Tooltip cursor={{ fill: '#f8fafc' }} />
                    <Bar dataKey="avg_risk" fill="#f97316" radius={[0, 4, 4, 0]} barSize={20} />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex h-full items-center justify-center text-slate-400">No data available</div>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
