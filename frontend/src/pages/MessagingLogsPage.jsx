import React, { useState, useEffect, useMemo } from 'react';
import { Search, Calendar, Check, CheckCheck, Clock, XCircle, AlertCircle } from 'lucide-react';
import clsx from 'clsx';
import chatbotApi from '../api/chatbot';
import { getErrorMessage } from '../api/client';

const StatusIcon = ({ status }) => {
  const s = status?.toLowerCase();
  if (s === 'completed') return <CheckCheck className="w-4 h-4 text-emerald-600" />;
  if (s === 'active') return <Check className="w-4 h-4 text-teal-600" />;
  if (s === 'cancelled') return <XCircle className="w-4 h-4 text-red-500" />;
  return <Clock className="w-4 h-4 text-slate-400" />;
};

const SkeletonRow = () => (
  <tr className="animate-pulse">
    {Array.from({ length: 6 }).map((_, i) => (
      <td key={i} className="px-6 py-4"><div className="w-full h-4 bg-slate-200 rounded" /></td>
    ))}
  </tr>
);

export default function MessagingLogsPage() {
  const [filterStatus, setFilterStatus] = useState('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    const fetchLogs = async () => {
      setLoading(true);
      setError('');
      try {
        const { data } = await chatbotApi.listConversations();
        setConversations(data.results || data);
      } catch (err) {
        setError(getErrorMessage(err));
      } finally {
        setLoading(false);
      }
    };
    fetchLogs();
  }, []);

  const filteredConversations = useMemo(() => {
    const search = searchQuery.trim().toLowerCase();
    return conversations.filter((conversation) => {
      const matchesStatus = filterStatus === 'all' || conversation.status === filterStatus;
      const matchesSearch =
        !search ||
        conversation.customer_name?.toLowerCase().includes(search) ||
        conversation.order_id?.toLowerCase().includes(search);
      return matchesStatus && matchesSearch;
    });
  }, [conversations, filterStatus, searchQuery]);

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Messaging Logs</h1>
          <p className="mt-1 text-slate-500">Track verification conversations, current status, and message volume.</p>
        </div>
      </div>

      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Filters */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4">
        <div className="flex flex-col lg:flex-row gap-4 items-center justify-between">
          <div className="relative w-full lg:w-96">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search logs..."
              className="w-full pl-12 pr-4 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-600 focus:border-transparent"
            />
          </div>
          <div className="flex items-center gap-3 w-full lg:w-auto">
            <select 
              className="px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-600"
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value)}
            >
              <option value="all">All Statuses</option>
              <option value="active">Active</option>
              <option value="completed">Completed</option>
              <option value="timeout">Timeout</option>
              <option value="cancelled">Cancelled</option>
            </select>
            <button className="px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-700 hover:bg-slate-50 flex items-center gap-2">
              <Calendar className="w-4 h-4" />
              Latest first
            </button>
          </div>
        </div>
      </div>

      {/* Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <table className="min-w-full">
          <thead>
            <tr className="bg-slate-50 border-b border-slate-200">
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Customer</th>
              <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Order ID</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Conversation Status</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Messages</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Started</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                Array.from({ length: 4 }).map((_, i) => <SkeletonRow key={i} />)
              ) : filteredConversations.length === 0 ? (
                <tr>
                  <td colSpan="6" className="px-6 py-12 text-center text-slate-500">
                    No messaging logs found.
                  </td>
                </tr>
              ) : filteredConversations.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-slate-900">{log.customer_name}</td>
                  <td className="px-6 py-4 whitespace-nowrap text-sm text-teal-700">{log.order_id}</td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <span className={clsx(
                      "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium capitalize",
                      log.status === 'active' ? "bg-teal-100 text-teal-800" :
                      log.status === 'completed' ? "bg-emerald-100 text-emerald-800" :
                      log.status === 'timeout' ? "bg-amber-100 text-amber-800" :
                      "bg-slate-100 text-slate-800"
                    )}>
                    {log.status}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="flex items-center gap-2">
                    <StatusIcon status={log.status} />
                    <span className="text-sm text-slate-600 capitalize">{log.status}</span>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-600">{log.message_count ?? 0}</td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-slate-500">
                  {log.started_at ? new Date(log.started_at).toLocaleString() : 'N/A'}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
