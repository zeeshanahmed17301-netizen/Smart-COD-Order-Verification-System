import React, { useState, useEffect, useCallback } from 'react';
import { 
  Filter, 
  Search, 
  ChevronDown, 
  Download,
  RefreshCw,
  ChevronLeft,
  ChevronRight,
  SlidersHorizontal,
  ArrowUpDown,
  MessageSquare,
  Check,
  X as XIcon,
  Loader2,
  AlertCircle,
  AlertTriangle,
  MessageCircle,
  Clock,
  MapPin,
  Copy,
  Phone,
  Truck,
  Eye
} from 'lucide-react';
import clsx from 'clsx';
import { Link, useSearchParams } from 'react-router-dom';
import ordersApi from '../api/orders';
import storesApi from '../api/stores';
import { getErrorMessage } from '../api/client';

const StatusBadge = ({ status }) => {
  const config = {
    verified: { bg: "bg-emerald-50", text: "text-emerald-700", dot: "bg-emerald-500", border: "border-emerald-200" },
    pending: { bg: "bg-amber-50", text: "text-amber-700", dot: "bg-amber-500", border: "border-amber-200" },
    rejected: { bg: "bg-red-50", text: "text-red-700", dot: "bg-red-500", border: "border-red-200" },
    delivered: { bg: "bg-green-50", text: "text-green-700", dot: "bg-green-500", border: "border-green-200" },
    rto: { bg: "bg-slate-50", text: "text-slate-700", dot: "bg-slate-500", border: "border-slate-200" },
  };
  const style = config[status] || { bg: "bg-slate-50", text: "text-slate-700", dot: "bg-slate-500", border: "border-slate-200" };
  
  return (
    <span className={clsx("inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium border capitalize", style.bg, style.text, style.border)}>
      <span className={clsx("w-1.5 h-1.5 rounded-full", style.dot)} />
      {status}
    </span>
  );
};

const RiskBadge = ({ level }) => {
  const config = {
    low:      { bg: "bg-emerald-50", text: "text-emerald-700", bar: "bg-emerald-500", border: "border-emerald-200", width: "25%" },
    medium:   { bg: "bg-amber-50",   text: "text-amber-700",   bar: "bg-amber-500",   border: "border-amber-200",  width: "55%" },
    high:     { bg: "bg-orange-50",  text: "text-orange-700",  bar: "bg-orange-500",  border: "border-orange-200", width: "80%" },
    critical: { bg: "bg-red-50",     text: "text-red-700",     bar: "bg-red-500",     border: "border-red-200",    width: "100%" },
  };
  const style = config[level] || config.low;

  return (
    <div className="flex items-center gap-3">
      <div className="w-20 h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={clsx("h-full rounded-full", style.bar)} style={{ width: style.width }} />
      </div>
      <span className={clsx("inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold border capitalize", style.bg, style.text, style.border)}>
        {level}
      </span>
    </div>
  );
};

const ScoreLoading = ({ label = 'Scoring' }) => (
  <span className="inline-flex items-center gap-2 text-xs font-medium text-slate-500">
    <Loader2 className="w-3.5 h-3.5 animate-spin" />
    {label}
  </span>
);

const ChatStatusBadge = ({ status }) => {
  const config = {
    confirmed: { icon: Check, bg: "bg-green-100", text: "text-green-700" },
    completed: { icon: Check, bg: "bg-emerald-100", text: "text-emerald-700" },
    awaiting_reply: { icon: Clock, bg: "bg-amber-100", text: "text-amber-700" },
    active: { icon: MessageCircle, bg: "bg-blue-100", text: "text-blue-700" },
    processing: { icon: Loader2, bg: "bg-blue-50", text: "text-blue-600" },
    failed: { icon: AlertCircle, bg: "bg-red-100", text: "text-red-700" },
    cancelled: { icon: XIcon, bg: "bg-slate-100", text: "text-slate-600" },
    unverified: { icon: MessageSquare, bg: "bg-slate-100", text: "text-slate-600" },
    denied: { icon: XIcon, bg: "bg-red-100", text: "text-red-700" },
    no_response: { icon: MessageSquare, bg: "bg-amber-100", text: "text-amber-700" },
  };
  const style = config[status] || config.unverified;
  const Icon = style.icon;
  const labelMap = {
    awaiting_reply: 'Awaiting Reply',
    completed: 'Verified',
    active: 'In Progress',
    processing: 'Processing',
    failed: 'Failed',
    cancelled: 'Cancelled',
    confirmed: 'Confirmed',
    unverified: 'Unverified',
    denied: 'Denied',
    no_response: 'No Response',
  };
  const displayName = labelMap[status] || status?.replace('_', ' ') || 'Unknown';

  return (
    <span className={clsx("inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium capitalize", style.bg, style.text)}>
      <Icon className={clsx("w-3.5 h-3.5", status === 'processing' && 'animate-spin')} />
      {displayName}
    </span>
  );
};

const FilterButton = ({ active, onClick, children }) => (
  <button
    onClick={onClick}
    className={clsx(
      "px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-all",
      active
        ? "bg-teal-700 text-white shadow-lg shadow-emerald-200/70"
        : "text-slate-600 hover:bg-slate-100"
    )}
  >
    {children}
  </button>
);

const CourierBadge = ({ reachable, coverageScore, confidence }) => {
  const normalizedCoverage = Number.isFinite(Number(coverageScore)) ? Number(coverageScore) : null;
  const confidenceLabel = (confidence || '').trim().toLowerCase();
  const hasCourierCoverage =
    reachable === true ||
    (normalizedCoverage !== null && normalizedCoverage > 0) ||
    (confidenceLabel && confidenceLabel !== 'none');

  if (hasCourierCoverage && ['exact', 'fuzzy'].includes(confidenceLabel)) {
    return (
      <span
        className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-emerald-100 text-emerald-700"
        title="Courier available"
        aria-label="Courier available"
      >
        <Check className="w-3.5 h-3.5" />
      </span>
    );
  }

  if (hasCourierCoverage) {
    return (
      <span
        className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-amber-100 text-amber-700"
        title="Courier coverage needs manual verification"
        aria-label="Courier coverage needs manual verification"
      >
        <AlertCircle className="w-3.5 h-3.5" />
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center justify-center w-7 h-7 rounded-lg bg-red-100 text-red-700"
      title="No courier coverage"
      aria-label="No courier coverage"
    >
      <XIcon className="w-3.5 h-3.5" />
    </span>
  );
};

const formatPercent = (value) => `${Number(value || 0).toFixed(1)}%`;

// Red badge surfaced when the same phone has placed multiple orders recently —
// a strong RTO/fraud signal that otherwise stays buried in enrichment.
const DuplicatePhoneBadge = ({ count }) => (
  <span
    className="inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold bg-red-50 text-red-700 border border-red-200"
    title={`This phone number is on ${count} orders in the last 30 days`}
  >
    <Copy className="w-3 h-3" />
    {count}× phone
  </span>
);

// Address deliverability flag next to the city. Garbage/unserviceable cities are
// a top RTO driver, so make them visible without opening the order.
const AddressQualityBadge = ({ quality }) => {
  const config = {
    verified:     { Icon: Check,         bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', label: 'Verified',     title: 'Address validated as deliverable' },
    unconfirmed:  { Icon: AlertCircle,   bg: 'bg-amber-50',   text: 'text-amber-700',   border: 'border-amber-200',   label: 'Unconfirmed',  title: 'Address could not be fully confirmed — verify before shipping' },
    undeliverable:{ Icon: AlertTriangle, bg: 'bg-red-50',     text: 'text-red-700',     border: 'border-red-200',     label: 'Bad address',  title: 'Address is unserviceable or undeliverable' },
  };
  const style = config[quality];
  if (!style) return null;
  const { Icon } = style;
  return (
    <span
      className={clsx('inline-flex items-center gap-1 px-1.5 py-0.5 rounded text-[10px] font-semibold border', style.bg, style.text, style.border)}
      title={style.title}
    >
      <Icon className="w-3 h-3" />
      {style.label}
    </span>
  );
};

// Color-coded, scannable version of the recommended action so operators can read
// the queue at a glance instead of parsing identical gray text.
const ActionBadge = ({ action, label }) => {
  const config = {
    ship_order:     { Icon: Truck,       bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200' },
    verify_address: { Icon: MapPin,      bg: 'bg-amber-50',   text: 'text-amber-700',   border: 'border-amber-200' },
    call_customer:  { Icon: Phone,       bg: 'bg-blue-50',    text: 'text-blue-700',    border: 'border-blue-200' },
    cancel_order:   { Icon: XIcon,       bg: 'bg-red-50',     text: 'text-red-700',     border: 'border-red-200' },
    manual_review:  { Icon: AlertCircle, bg: 'bg-slate-50',   text: 'text-slate-700',   border: 'border-slate-200' },
  };
  const style = config[action] || config.manual_review;
  const { Icon } = style;
  const text = label || action?.replace(/_/g, ' ') || 'Review';
  return (
    <span className={clsx('inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-semibold border capitalize', style.bg, style.text, style.border)}>
      <Icon className="w-3.5 h-3.5" />
      {text}
    </span>
  );
};

// Loading skeleton row
const SkeletonRow = () => (
  <tr className="animate-pulse">
    {Array.from({ length: 11 }).map((_, i) => (
      <td key={i} className="px-6 py-4"><div className="w-full h-4 bg-slate-200 rounded" /></td>
    ))}
  </tr>
);

export default function OrdersPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filterStatus, setFilterStatus] = useState(searchParams.get('status') || 'all');
  const [riskLevelFilter, setRiskLevelFilter] = useState(searchParams.get('risk_level') || 'all');
  const [quickFilter, setQuickFilter] = useState(searchParams.get('queue') || 'none');
  const [sortBy, setSortBy] = useState(searchParams.get('ordering') || '-risk_score');
  const [searchQuery, setSearchQuery] = useState(searchParams.get('search') || '');
  const [orders, setOrders] = useState([]);
  const [totalCount, setTotalCount] = useState(0);
  const [currentPage, setCurrentPage] = useState(Number(searchParams.get('page')) || 1);
  const [loading, setLoading] = useState(true);
  const [syncingOrders, setSyncingOrders] = useState(false);
  const [scoringOrderIds, setScoringOrderIds] = useState(() => new Set());
  const [recomputingOrderId, setRecomputingOrderId] = useState(null);
  const [error, setError] = useState('');
  const [syncMessage, setSyncMessage] = useState('');
  const pageSize = 10;

  const fetchOrders = useCallback(async ({ preserveFeedback = false } = {}) => {
    setLoading(true);
    if (!preserveFeedback) {
      setError('');
      setSyncMessage('');
    }
    try {
      const params = { page: currentPage, page_size: pageSize, ordering: sortBy };
      if (filterStatus !== 'all') params.status = filterStatus;
      if (riskLevelFilter !== 'all') params.risk_level = riskLevelFilter;
      if (quickFilter !== 'none') params[quickFilter] = true;
      if (searchQuery) params.search = searchQuery;

      const { data } = await ordersApi.list(params);
      const loadedOrders = data.results || data;
      setOrders(loadedOrders);
      setTotalCount(data.count || loadedOrders.length);
      return loadedOrders;
    } catch (err) {
      setError(getErrorMessage(err));
      return [];
    } finally {
      setLoading(false);
    }
  }, [filterStatus, riskLevelFilter, quickFilter, sortBy, searchQuery, currentPage]);

  useEffect(() => {
    fetchOrders();
  }, [fetchOrders]);

  // Reset to page 1 when filter/search changes
  useEffect(() => {
    setCurrentPage(1);
  }, [filterStatus, riskLevelFilter, quickFilter, sortBy, searchQuery]);

  useEffect(() => {
    const nextParams = new URLSearchParams();
    if (filterStatus !== 'all') nextParams.set('status', filterStatus);
    if (riskLevelFilter !== 'all') nextParams.set('risk_level', riskLevelFilter);
    if (quickFilter !== 'none') nextParams.set('queue', quickFilter);
    if (sortBy !== '-risk_score') nextParams.set('ordering', sortBy);
    if (searchQuery) nextParams.set('search', searchQuery);
    if (currentPage > 1) nextParams.set('page', String(currentPage));
    setSearchParams(nextParams, { replace: true });
  }, [filterStatus, riskLevelFilter, quickFilter, sortBy, searchQuery, currentPage, setSearchParams]);

  const totalPages = Math.ceil(totalCount / pageSize);
  const scoringInProgress = scoringOrderIds.size > 0;

  const handleStatusFilter = (status) => {
    setFilterStatus(status.toLowerCase());
  };

  // Debounced search
  const [searchInput, setSearchInput] = useState(searchParams.get('search') || '');
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearchQuery(searchInput);
    }, 400);
    return () => clearTimeout(timer);
  }, [searchInput]);

  const applyScoreResult = useCallback((orderId, data) => {
    setOrders((currentOrders) => currentOrders.map((order) => {
      if (order.id !== orderId) {
        return order;
      }

      return {
        ...order,
        address_score: data.address_score,
        risk_score: data.risk_score,
        fraud_score: data.fraud_score,
        fraud_probability: data.score_breakdown?.fraud?.probability ?? order.fraud_probability,
        fraud_confidence_interval: data.score_breakdown?.fraud?.confidence_interval ?? order.fraud_confidence_interval,
        rto_probability: data.rto_probability,
        rto_probability_score: data.rto_probability_score,
        rto_probability_percent: data.score_breakdown?.rto?.probability ?? order.rto_probability_percent,
        rto_confidence_interval: data.score_breakdown?.rto?.confidence_interval ?? order.rto_confidence_interval,
        risk_level: data.risk_level,
        recommended_action: data.recommended_action,
        score_breakdown: data.score_breakdown ?? order.score_breakdown,
      };
    }));
  }, []);

  const scoreOrdersIndividually = useCallback(async (orderIds) => {
    const uniqueOrderIds = [...new Set((orderIds || []).filter(Boolean))];
    if (uniqueOrderIds.length === 0) {
      return { scored: 0, failed: 0, firstError: '' };
    }

    setScoringOrderIds((currentIds) => new Set([...currentIds, ...uniqueOrderIds]));

    let cursor = 0;
    let scored = 0;
    let failed = 0;
    let firstError = '';

    const scoreNextOrder = async () => {
      while (cursor < uniqueOrderIds.length) {
        const orderId = uniqueOrderIds[cursor];
        cursor += 1;

        try {
          const { data } = await ordersApi.recomputeScores(orderId);
          applyScoreResult(orderId, data);
          scored += 1;
        } catch (err) {
          failed += 1;
          if (!firstError) {
            firstError = getErrorMessage(err);
          }
        } finally {
          setScoringOrderIds((currentIds) => {
            const nextIds = new Set(currentIds);
            nextIds.delete(orderId);
            return nextIds;
          });
        }
      }
    };

    const workerCount = Math.min(4, uniqueOrderIds.length);
    await Promise.all(Array.from({ length: workerCount }, scoreNextOrder));

    return { scored, failed, firstError };
  }, [applyScoreResult]);

  const handleRecomputeScores = async (orderId) => {
    setRecomputingOrderId(orderId);
    setError('');
    try {
      const { data } = await ordersApi.recomputeScores(orderId);
      applyScoreResult(orderId, data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setRecomputingOrderId(null);
    }
  };

  const handleSyncOrders = async () => {
    setSyncingOrders(true);
    setError('');
    setSyncMessage('');

    try {
      const connectionsRes = await storesApi.listConnections();
      const connections = Array.isArray(connectionsRes.data)
        ? connectionsRes.data
        : (connectionsRes.data.results || []);
      const shopifyConnection = connections.find(
        (connection) => connection.platform === 'shopify' && connection.is_active
      ) || connections.find((connection) => connection.platform === 'shopify');

      if (!shopifyConnection) {
        setError('Connect Shopify before syncing orders.');
        return;
      }

      const { data } = await storesApi.syncConnection(shopifyConnection.id, { limit: 250 });
      const summary = data?.summary;
      const syncedOrderIds = summary?.order_ids || [];
      await fetchOrders({ preserveFeedback: true });
      setSyncingOrders(false);

      if (!summary) {
        setSyncMessage('Shopify orders loaded.');
        return;
      }

      setSyncMessage(
        syncedOrderIds.length > 0
          ? `Orders loaded. Scoring ${syncedOrderIds.length} order(s)...`
          : `Sync complete. Fetched ${summary.fetched}; imported ${summary.imported}; updated ${summary.updated}.`
      );

      const scoringSummary = await scoreOrdersIndividually(syncedOrderIds);
      const firstFailure = summary.failed_orders?.[0];
      const errorMessages = [];

      if (summary.failed > 0) {
        errorMessages.push(
          `Sync finished with ${summary.failed} failed order(s). ${
            firstFailure?.error ? `First problem: ${firstFailure.error}` : 'Open Store Integrations for the full summary.'
          }`
        );
      }
      if (scoringSummary.failed > 0) {
        errorMessages.push(
          `Scoring failed for ${scoringSummary.failed} order(s). ${
            scoringSummary.firstError ? `First problem: ${scoringSummary.firstError}` : 'Try recomputing scores manually.'
          }`
        );
      }
      if (errorMessages.length > 0) {
        setError(errorMessages.join(' '));
      }

      setSyncMessage(
        `Sync complete. Fetched ${summary.fetched}; imported ${summary.imported}; updated ${summary.updated}; scored ${scoringSummary.scored}.`
      );
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSyncingOrders(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Orders</h1>
          <p className="mt-1 text-slate-500">Manage and verify your COD orders.</p>
        </div>
        <div className="flex items-center gap-3">
          <button 
            type="button"
            onClick={handleSyncOrders}
            disabled={syncingOrders || loading || scoringInProgress}
            className="inline-flex items-center gap-2 px-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium text-slate-700 hover:bg-slate-50 hover:border-slate-300 transition-all shadow-sm disabled:opacity-60 disabled:cursor-not-allowed"
          >
            <RefreshCw className={clsx("w-4 h-4", (syncingOrders || loading || scoringInProgress) && "animate-spin")} />
            {syncingOrders ? 'Syncing...' : scoringInProgress ? 'Scoring...' : 'Sync Orders'}
          </button>
          <button className="inline-flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-teal-700 to-emerald-600 text-white rounded-xl text-sm font-medium hover:from-teal-800 hover:to-emerald-700 transition-all shadow-lg shadow-emerald-200/70">
            <Download className="w-4 h-4" />
            Export CSV
          </button>
        </div>
      </div>

      {/* Error Alert */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {syncMessage && (
        <div className="flex items-center gap-3 p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-emerald-700">
          <Check className="h-5 w-5 flex-shrink-0" />
          <p className="text-sm">{syncMessage}</p>
        </div>
      )}

      {/* Filters Section */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm p-4">
        <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
          {/* Search */}
          <div className="relative w-full lg:w-96">
            <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              className="w-full pl-12 pr-4 py-3 bg-slate-50 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-teal-600 focus:border-transparent focus:bg-white transition-all"
              placeholder="Search by order ID, customer name, or phone..."
            />
          </div>
          
          {/* Status Filters */}
          <div className="flex items-center gap-2 w-full lg:w-auto overflow-x-auto pb-2 lg:pb-0">
            {['All', 'Pending', 'Verified', 'Rejected', 'Delivered', 'RTO'].map((status) => (
              <FilterButton
                key={status}
                active={filterStatus === status.toLowerCase()}
                onClick={() => handleStatusFilter(status)}
              >
                {status}
              </FilterButton>
            ))}
          </div>
        </div>
        <div className="mt-4 flex flex-col sm:flex-row gap-3 sm:items-center">
          <label htmlFor="risk-level-filter" className="text-xs font-semibold uppercase tracking-wide text-slate-500">
            Risk level
          </label>
          <select
            id="risk-level-filter"
            value={riskLevelFilter}
            onChange={(event) => setRiskLevelFilter(event.target.value)}
            className="w-full sm:w-56 px-3 py-2.5 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:border-transparent"
          >
            <option value="all">All levels</option>
            <option value="critical">Critical</option>
            <option value="high">High</option>
            <option value="medium">Medium</option>
            <option value="low">Low</option>
          </select>
        </div>
        <div className="mt-4 flex flex-col lg:flex-row gap-3 lg:items-center lg:justify-between">
          {/* Action-queue quick filters */}
          <div className="flex items-center gap-2 overflow-x-auto pb-1 lg:pb-0">
            <span className="text-xs font-semibold uppercase tracking-wide text-slate-500 whitespace-nowrap">Queue</span>
            {[
              { key: 'none', label: 'All orders', Icon: null },
              { key: 'action_needed', label: 'Action needed', Icon: AlertCircle },
              { key: 'high_risk', label: 'High risk', Icon: AlertTriangle },
              { key: 'awaiting_reply', label: 'Awaiting reply', Icon: Clock },
            ].map(({ key, label, Icon }) => (
              <button
                key={key}
                type="button"
                onClick={() => setQuickFilter(key)}
                className={clsx(
                  'inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold whitespace-nowrap border transition-all',
                  quickFilter === key
                    ? 'bg-teal-700 text-white border-teal-700 shadow-sm'
                    : 'bg-white text-slate-600 border-slate-200 hover:bg-slate-50'
                )}
              >
                {Icon && <Icon className="w-3.5 h-3.5" />}
                {label}
              </button>
            ))}
          </div>
          {/* Sort */}
          <div className="flex items-center gap-2">
            <label htmlFor="order-sort" className="text-xs font-semibold uppercase tracking-wide text-slate-500 whitespace-nowrap">Sort by</label>
            <select
              id="order-sort"
              value={sortBy}
              onChange={(event) => setSortBy(event.target.value)}
              className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-xl text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-600 focus:border-transparent"
            >
              <option value="-risk_score">Risk (high → low)</option>
              <option value="-fraud_score">Fraud (high → low)</option>
              <option value="-amount">Amount (high → low)</option>
              <option value="-created_at">Newest first</option>
              <option value="created_at">Oldest first</option>
            </select>
          </div>
        </div>
      </div>

      {/* Orders Table */}
      <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="bg-slate-50 border-b border-slate-200">
                <th scope="col" className="px-6 py-4 text-left">
                  <button className="flex items-center gap-2 text-xs font-semibold text-slate-500 uppercase tracking-wider hover:text-slate-700">
                    Order Number
                    <ArrowUpDown className="w-3.5 h-3.5" />
                  </button>
                </th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Customer</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Phone</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">City</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Courier</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Fraud Prob.</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">RTO Prob.</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">WhatsApp Status</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Overall Risk</th>
                <th scope="col" className="px-6 py-4 text-left text-xs font-semibold text-slate-500 uppercase tracking-wider">Action</th>
                <th scope="col" className="relative px-6 py-4">
                  <span className="sr-only">View</span>
                </th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                Array.from({ length: 5 }).map((_, i) => <SkeletonRow key={i} />)
              ) : orders.length === 0 ? (
                <tr>
                  <td colSpan="11" className="px-6 py-12 text-center text-slate-500">
                    No orders found matching your filters.
                  </td>
                </tr>
              ) : orders.map((order) => {
                const scoreLoading = scoringOrderIds.has(order.id) || recomputingOrderId === order.id;

                return (
                <tr key={order.id} className="hover:bg-slate-50/50 transition-colors group">
                  <td className="px-6 py-4 whitespace-nowrap">
                    <Link to={`/orders/${order.id}`} className="text-sm font-semibold text-teal-700 hover:text-teal-800">
                      {order.display_order_number || order.order_id}
                    </Link>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <div className="flex items-center gap-3">
                      <div className="w-8 h-8 rounded-full bg-gradient-to-br from-slate-200 to-slate-300 flex items-center justify-center text-xs font-semibold text-slate-600">
                        {(order.customer_name || '?').charAt(0)}
                      </div>
                      <p className="text-sm font-medium text-slate-900">{order.customer_name}</p>
                    </div>
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <p className="text-sm text-slate-600">{order.customer_phone}</p>
                    {order.signals?.duplicate_phone && (
                      <div className="mt-1">
                        <DuplicatePhoneBadge count={order.signals.repeat_phone_orders_30d} />
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <p className="text-sm text-slate-600">{order.customer_city}</p>
                    {order.signals?.address_quality === 'undeliverable' && (
                      <div className="mt-1">
                        <AddressQualityBadge quality={order.signals.address_quality} />
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <CourierBadge
                      reachable={order.courier_reachable}
                      coverageScore={order.courier_coverage_score}
                      confidence={order.courier_match_confidence}
                    />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {scoreLoading ? (
                      <ScoreLoading />
                    ) : (
                      <div
                        title={order.fraud_confidence_interval ? `CI ${formatPercent(order.fraud_confidence_interval.lower)}-${formatPercent(order.fraud_confidence_interval.upper)}` : ''}
                      >
                        <span className={clsx(
                          "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                          (order.fraud_probability ?? order.fraud_score) < 15 ? "bg-green-100 text-green-800" :
                          (order.fraud_probability ?? order.fraud_score) < 45 ? "bg-yellow-100 text-yellow-800" :
                          "bg-red-100 text-red-800"
                        )}>
                          {formatPercent(order.fraud_probability ?? order.fraud_score)}
                        </span>
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {scoreLoading ? (
                      <ScoreLoading />
                    ) : (
                      <div
                        className="space-y-1"
                        title={order.rto_confidence_interval ? `CI ${formatPercent(order.rto_confidence_interval.lower)}-${formatPercent(order.rto_confidence_interval.upper)}` : ''}
                      >
                        <span className={clsx(
                          "inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium",
                          (order.rto_probability_percent ?? order.rto_probability_score) < 20 ? "bg-green-100 text-green-800" :
                          (order.rto_probability_percent ?? order.rto_probability_score) < 40 ? "bg-yellow-100 text-yellow-800" :
                          (order.rto_probability_percent ?? order.rto_probability_score) < 70 ? "bg-orange-100 text-orange-800" :
                          "bg-red-100 text-red-800"
                        )}>
                          {formatPercent(order.rto_probability_percent ?? order.rto_probability_score)}
                        </span>
                        <p className="text-[11px] font-medium text-slate-500">{order.rto_probability}</p>
                      </div>
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    <ChatStatusBadge status={order.chat_status} />
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {scoreLoading ? (
                      <ScoreLoading />
                    ) : (
                      <RiskBadge level={order.risk_level} />
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap">
                    {scoreLoading ? (
                      <ScoreLoading />
                    ) : (
                      <ActionBadge action={order.recommended_action} label={order.recommended_action_label} />
                    )}
                  </td>
                  <td className="px-6 py-4 whitespace-nowrap text-right">
                    <div className="flex items-center justify-end gap-2">
                      <button
                        type="button"
                        onClick={() => handleRecomputeScores(order.id)}
                        disabled={scoreLoading}
                        title="Recompute risk scores"
                        aria-label="Recompute risk scores"
                        className="inline-flex items-center justify-center w-8 h-8 border border-slate-200 rounded-lg bg-white text-slate-700 hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-teal-600 disabled:opacity-60 disabled:cursor-not-allowed"
                      >
                        {scoreLoading ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <RefreshCw className="w-4 h-4" />
                        )}
                      </button>
                      <Link
                        to={`/orders/${order.id}`}
                        title="View order details"
                        aria-label="View order details"
                        className="inline-flex items-center justify-center w-8 h-8 rounded-lg text-teal-700 bg-teal-100 hover:bg-teal-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-teal-600"
                      >
                        <Eye className="w-4 h-4" />
                      </Link>
                    </div>
                  </td>
                </tr>
                );
              })}
            </tbody>
          </table>
        </div>
        
        {/* Pagination */}
        <div className="px-6 py-4 border-t border-slate-200 bg-slate-50/50">
          <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
            <p className="text-sm text-slate-600">
              Showing <span className="font-semibold text-slate-900">{orders.length}</span> of <span className="font-semibold text-slate-900">{totalCount}</span> results
            </p>
            {totalPages > 1 && (
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => setCurrentPage(p => Math.max(1, p - 1))}
                  disabled={currentPage === 1}
                  className="inline-flex items-center gap-1 px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Previous
                </button>
                <div className="flex items-center gap-1">
                  {Array.from({ length: Math.min(totalPages, 5) }, (_, i) => i + 1).map((page) => (
                    <button
                      key={page}
                      onClick={() => setCurrentPage(page)}
                      className={clsx(
                        "w-10 h-10 rounded-lg text-sm font-semibold transition-colors",
                        page === currentPage
                          ? "bg-teal-700 text-white"
                          : "border border-slate-200 bg-white text-slate-700 hover:bg-slate-50"
                      )}
                    >
                      {page}
                    </button>
                  ))}
                </div>
                <button 
                  onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))}
                  disabled={currentPage === totalPages}
                  className="inline-flex items-center gap-1 px-3 py-2 rounded-lg border border-slate-200 bg-white text-sm font-medium text-slate-600 hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Next
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
