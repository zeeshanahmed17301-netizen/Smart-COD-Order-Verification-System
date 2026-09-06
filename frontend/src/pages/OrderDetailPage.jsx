import React, { useState, useEffect, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { 
  User, 
  MapPin, 
  Phone, 
  Mail, 
  Package, 
  AlertTriangle, 
  CheckCircle, 
  XCircle, 
  Clock,
  ArrowLeft,
  Shield,
  History,
  MapPinned,
  MoreHorizontal,
  Loader2,
  AlertCircle,
  Truck,
  MessageCircle,
  Send
} from 'lucide-react';
import clsx from 'clsx';
import ordersApi from '../api/orders';
import { getErrorMessage } from '../api/client';

const hasValue = (value) => value !== null && value !== undefined && value !== '' && (!Array.isArray(value) || value.length > 0);

const formatFieldValue = (value) => {
  if (!hasValue(value)) return 'Not available';
  if (typeof value === 'boolean') return value ? 'Yes' : 'No';
  if (Array.isArray(value)) return value.join(', ');
  return String(value);
};

const formatMoney = (amount, currency = 'PKR') => {
  if (!hasValue(amount)) return 'Not available';
  const numericAmount = Number(amount);
  if (Number.isNaN(numericAmount)) {
    return `${currency} ${amount}`;
  }
  return `${currency} ${numericAmount.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
};

const formatDateTime = (value) => {
  if (!hasValue(value)) return 'Not available';
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return String(value);
  return parsed.toLocaleString();
};

const getCourierCoverageStatus = (enrichment) => {
  const confidence = String(enrichment.courier_match_confidence || '').trim().toLowerCase();
  const coverageScore = Number(enrichment.courier_coverage_score || 0);
  const count = Number(enrichment.courier_reachable_count || 0);

  if (enrichment.courier_reachable === false || coverageScore <= 0 || count <= 0 || confidence === 'none') {
    return {
      tone: 'red',
      title: 'No Courier Coverage',
      description: 'No credible city-level courier coverage match was found for this delivery area.',
    };
  }

  if (confidence === 'exact' || confidence === 'fuzzy') {
    return {
      tone: 'emerald',
      title: 'Courier Services Available',
      description: `${count} courier service(s) cover this area.`,
    };
  }

  return {
    tone: 'amber',
    title: 'Possible Courier Coverage',
    description: 'Coverage was inferred from address text and should be manually verified before dispatch.',
  };
};

const DetailField = ({ label, value }) => (
  <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
    <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-slate-500">{label}</p>
    <p className="mt-2 break-words text-sm font-medium text-slate-900">{formatFieldValue(value)}</p>
  </div>
);

const AddressPanel = ({ title, address, fallback }) => {
  const lines = [
    address?.name,
    address?.address1,
    address?.address2,
    address?.city,
    address?.province,
    address?.country,
    address?.zip,
  ].filter(Boolean);

  const value = lines.length > 0 ? lines.join(', ') : fallback;

  return (
    <div className="rounded-xl border border-slate-200 p-4">
      <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">{title}</p>
      <p className="mt-2 text-sm font-medium leading-6 text-slate-900">{value || 'Not available'}</p>
      {address?.phone && <p className="mt-2 text-xs text-slate-500">{address.phone}</p>}
    </div>
  );
};

const InfoCard = ({ icon: Icon, label, value, iconColor }) => (
  <div className="flex items-start gap-4">
    <div className={clsx("p-2.5 rounded-xl", iconColor)}>
      <Icon className="w-5 h-5 text-white" />
    </div>
    <div className="flex-1 min-w-0">
      <p className="text-xs font-medium text-slate-500 uppercase tracking-wide">{label}</p>
      <p className="text-sm font-semibold text-slate-900 mt-0.5">{value}</p>
    </div>
  </div>
);

// Loading skeleton
const DetailSkeleton = () => (
  <div className="space-y-6 animate-pulse">
    <div className="flex gap-4">
      <div className="w-10 h-10 rounded-xl bg-slate-200" />
      <div className="space-y-2">
        <div className="w-48 h-6 bg-slate-200 rounded" />
        <div className="w-32 h-4 bg-slate-200 rounded" />
      </div>
    </div>
    <div className="bg-white rounded-2xl border border-slate-200 p-6 space-y-4">
      {Array.from({ length: 4 }).map((_, i) => (
        <div key={i} className="w-full h-4 bg-slate-200 rounded" />
      ))}
    </div>
  </div>
);

export default function OrderDetailPage() {
  const { id } = useParams();
  const [order, setOrder] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [actionLoading, setActionLoading] = useState('');

  const fetchOrder = useCallback(async () => {
    try {
      const { data } = await ordersApi.get(id);
      setOrder(data);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    fetchOrder();
  }, [fetchOrder]);

  const handleOrderAction = async (action, request) => {
    setActionLoading(action);
    try {
      await request();
      await fetchOrder();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setActionLoading('');
    }
  };

  const handleAccept = () => handleOrderAction('accept', () => ordersApi.accept(id));
  const handleConfirm = () => handleOrderAction('confirm', () => ordersApi.confirm(id));
  const handleCancel = () => handleOrderAction('cancel', () => ordersApi.cancel(id));

  const handleTriggerWhatsApp = async () => {
    setActionLoading('whatsapp');
    setError('');
    try {
      await ordersApi.triggerWhatsApp(id);
      await fetchOrder();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setActionLoading('');
    }
  };

  if (loading) return <DetailSkeleton />;

  if (error && !order) {
    return (
      <div className="space-y-4">
        <Link to="/orders" className="inline-flex items-center gap-2 text-sm text-teal-700 hover:text-teal-800">
          <ArrowLeft className="w-4 h-4" /> Back to Orders
        </Link>
        <div className="flex items-center gap-3 p-6 bg-red-50 border border-red-200 rounded-xl text-red-700">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      </div>
    );
  }

  if (!order) return null;

  // Extract data from the API response (handles both nested and flat shapes)
  const customer = order.customer || {};
  const address = order.address || {};
  const items = order.items || order.order?.items || [];
  const enrichment = order.enrichment || {};
  const conversationStatus = order.conversation_status;
  const chatLog = order.chat_log || [];
  const sourceSnapshot = order.source_snapshot || {};
  const canonicalFacts = order.canonical_facts || {};
  const canonicalCustomer = canonicalFacts.customer || {};
  const canonicalAddresses = canonicalFacts.addresses || {};
  const canonicalNotes = canonicalFacts.notes || {};
  const canonicalNetwork = canonicalFacts.network || {};
  const shopifyDetails = sourceSnapshot.shopify_details || {};
  const shopifyOrderIdentity = shopifyDetails.order_identity || {};
  const shopifyPayment = shopifyDetails.payment || {};
  const decisionSummary = order.decision_summary || {};
  const orderCurrency = shopifyPayment.currency || sourceSnapshot.raw_order_payload?.currency || 'PKR';
  const shippingLines = Array.isArray(shopifyPayment.shipping_lines) ? shopifyPayment.shipping_lines : [];
  const orderSummaryFields = [
    ['Order Number', order.display_order_number || shopifyOrderIdentity.name || shopifyOrderIdentity.order_number || order.order_id],
    ['Order Date / Time', formatDateTime(shopifyOrderIdentity.created_at || order.created_at)],
    ['Payment Status', shopifyPayment.financial_status || sourceSnapshot.financial_status],
    ['Fulfillment Status', shopifyPayment.fulfillment_status || sourceSnapshot.fulfillment_status],
    ['Total Amount', formatMoney(shopifyPayment.total_price || order.amount, orderCurrency)],
    ['Payment Method', order.payment_method?.toUpperCase()],
  ];
  const validationVerdict = enrichment.address_validation_verdict || enrichment.address_validation_status || '—';
  const signalFields = [
    ['Order IP', canonicalNetwork.order_ip || sourceSnapshot.order_ip],
    ['Validation Verdict', validationVerdict.replace(/_/g, ' ')],
    ['Address Status', (enrichment.address_confidence ?? address.confidence_score ?? 0) >= 30 ? 'Available' : 'Unconfirmed'],
  ];
  const courierStatus = getCourierCoverageStatus(enrichment);
  const courierTone = {
    red: {
      panel: 'bg-red-50 border-red-200',
      iconBg: 'bg-red-100',
      icon: 'text-red-700',
      title: 'text-red-800',
    },
    amber: {
      panel: 'bg-amber-50 border-amber-200',
      iconBg: 'bg-amber-100',
      icon: 'text-amber-700',
      title: 'text-amber-800',
    },
    emerald: {
      panel: 'bg-emerald-50 border-emerald-200',
      iconBg: 'bg-emerald-100',
      icon: 'text-emerald-700',
      title: 'text-emerald-800',
    },
  }[courierStatus.tone];

  const statusConfig = {
    pending: { label: 'Pending Verification', bg: 'bg-amber-50', text: 'text-amber-700', border: 'border-amber-200', icon: Clock },
    verified: { label: 'Verified', bg: 'bg-emerald-50', text: 'text-emerald-700', border: 'border-emerald-200', icon: CheckCircle },
    cancelled: { label: 'Cancelled', bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', icon: XCircle },
    rejected: { label: 'Rejected', bg: 'bg-red-50', text: 'text-red-700', border: 'border-red-200', icon: XCircle },
    delivered: { label: 'Delivered', bg: 'bg-green-50', text: 'text-green-700', border: 'border-green-200', icon: CheckCircle },
    rto: { label: 'RTO', bg: 'bg-slate-50', text: 'text-slate-700', border: 'border-slate-200', icon: AlertTriangle },
  };
  const orderStatus = statusConfig[order.status] || statusConfig.pending;
  const StatusIcon = orderStatus.icon;
  const riskTone =
    order.risk_level === 'critical' ? 'red'
      : order.risk_level === 'high' ? 'amber'
      : order.risk_level === 'medium' ? 'teal'
      : 'emerald';

  return (
    <div className="space-y-6">
      {/* Error Alert */}
      {error && (
        <div className="flex items-center gap-3 p-4 bg-red-50 border border-red-200 rounded-xl text-red-700">
          <AlertCircle className="h-5 w-5 flex-shrink-0" />
          <p className="text-sm">{error}</p>
        </div>
      )}

      {/* Page Header */}
      <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-4">
        <div className="flex items-start gap-4">
          <Link 
            to="/orders" 
            className="p-2.5 rounded-xl bg-white border border-slate-200 text-slate-600 hover:bg-slate-50 hover:text-slate-900 transition-colors"
          >
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <div className="flex items-center gap-3 flex-wrap">
              <h1 className="text-2xl font-bold text-slate-900">Order {order.display_order_number || order.order_id}</h1>
              <span className={clsx("inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-sm font-medium border", orderStatus.bg, orderStatus.text, orderStatus.border)}>
                <StatusIcon className="w-4 h-4" />
                {orderStatus.label}
              </span>
            </div>
            <p className="text-slate-500 mt-1">
              Placed on {order.created_at ? new Date(order.created_at).toLocaleDateString() : 'N/A'} | {order.payment_method?.toUpperCase()} Payment
            </p>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={fetchOrder}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
          >
            <MoreHorizontal className="w-4 h-4" />
            Refresh
          </button>
          <button 
            onClick={handleCancel}
            disabled={!!actionLoading || order.status !== 'pending'}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-red-50 border border-red-200 rounded-xl text-sm font-semibold text-red-700 hover:bg-red-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {actionLoading === 'cancel' ? <Loader2 className="w-4 h-4 animate-spin" /> : <XCircle className="w-4 h-4" />}
            Cancel Order
          </button>
          <button 
            onClick={handleConfirm}
            disabled={!!actionLoading || order.status !== 'pending'}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-white border border-teal-200 rounded-xl text-sm font-semibold text-teal-700 hover:bg-teal-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {actionLoading === 'confirm' ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            Confirm Order
          </button>
          <button 
            onClick={handleAccept}
            disabled={!!actionLoading || order.status !== 'pending'}
            className="inline-flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-emerald-600 to-green-600 text-white rounded-xl text-sm font-semibold hover:from-emerald-700 hover:to-green-700 transition-all shadow-lg shadow-green-200 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {actionLoading === 'accept' ? <Loader2 className="w-4 h-4 animate-spin" /> : <CheckCircle className="w-4 h-4" />}
            Accept Order
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
        <div className="space-y-6 xl:col-span-2">
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="text-lg font-semibold text-slate-900">Order Summary</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-4 p-6">
              {orderSummaryFields.map(([label, value]) => (
                <DetailField key={label} label={label} value={value} />
              ))}
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <User className="w-5 h-5 text-slate-400" />
                Customer
              </h3>
            </div>
            <div className="p-6 grid grid-cols-1 md:grid-cols-2 gap-5">
              <InfoCard icon={User} label="Full Name" value={canonicalCustomer.name || customer.name || 'N/A'} iconColor="bg-gradient-to-br from-teal-600 to-emerald-600" />
              <InfoCard icon={Phone} label="Phone Number" value={canonicalCustomer.phone || customer.phone || 'N/A'} iconColor="bg-gradient-to-br from-emerald-500 to-green-600" />
              <InfoCard icon={Mail} label="Email" value={canonicalCustomer.email || customer.email || 'N/A'} iconColor="bg-gradient-to-br from-sky-600 to-cyan-600" />
              <InfoCard icon={History} label="Customer Order Count" value={canonicalCustomer.order_count || customer.total_orders || 0} iconColor="bg-gradient-to-br from-slate-600 to-slate-800" />
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <MapPinned className="w-5 h-5 text-slate-400" />
                Delivery
              </h3>
            </div>
            <div className="p-6 space-y-4">
              <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
                <AddressPanel title="Shipping Address" address={canonicalAddresses.shipping_address} fallback={address.full_address || customer.address} />
                <div className="space-y-4">
                  <DetailField label="City / Province" value={[canonicalAddresses.city || customer.city || address.city, canonicalAddresses.province].filter(Boolean).join(', ')} />
                  <DetailField label="Billing Same As Shipping" value={canonicalAddresses.billing_matches_shipping ? 'Yes' : canonicalAddresses.billing_address ? 'No' : 'Not available'} />
                  <DetailField label="Normalized Address" value={enrichment.normalized_address || address.suggested_address} />
                </div>
              </div>
              {address.map_preview_url && (
                <a href={address.map_preview_url} target="_blank" rel="noreferrer" className="inline-flex items-center gap-2 text-sm font-semibold text-teal-700 hover:text-teal-800">
                  <MapPin className="w-4 h-4" />
                  Open map preview
                </a>
              )}

              {/* Courier Reachability */}
              <div className={clsx(
                'rounded-xl border p-5 mt-2',
                courierTone.panel
              )}>
                <div className="flex items-start gap-3">
                  <div className={clsx(
                    'p-2.5 rounded-xl',
                    courierTone.iconBg
                  )}>
                    <Truck className={clsx(
                      'w-5 h-5',
                      courierTone.icon
                    )} />
                  </div>
                  <div className="flex-1 min-w-0 space-y-3">
                    <div>
                      <p className={clsx(
                        'text-sm font-semibold',
                        courierTone.title
                      )}>
                        {courierStatus.title}
                      </p>
                      <p className="text-xs text-slate-600 mt-1">
                        {courierStatus.description}
                      </p>
                    </div>

                    {enrichment.courier_coverage_score !== undefined && (
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-[11px] font-semibold uppercase tracking-wide text-slate-500">Coverage Score</span>
                          <span className="text-xs font-bold text-slate-700">{Math.round(enrichment.courier_coverage_score)}%</span>
                        </div>
                        <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                          <div
                            className={clsx(
                              'h-full rounded-full transition-all',
                              enrichment.courier_coverage_score > 60 ? 'bg-emerald-500' :
                              enrichment.courier_coverage_score > 30 ? 'bg-amber-500' : 'bg-red-500'
                            )}
                            style={{ width: `${enrichment.courier_coverage_score || 0}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {enrichment.courier_match_confidence && (
                      <p className="text-[11px] text-slate-500">
                        Match confidence: <span className="font-semibold capitalize">{enrichment.courier_match_confidence.replace('_', ' ')}</span>
                      </p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <Package className="w-5 h-5 text-slate-400" />
                Order Contents
              </h3>
            </div>
            <div className="p-6">
              <div className="overflow-hidden border border-slate-200 rounded-xl">
                <table className="min-w-full">
                  <thead>
                    <tr className="bg-slate-50">
                      <th className="px-5 py-3.5 text-left text-xs font-semibold text-slate-500 uppercase tracking-wide">Product</th>
                      <th className="px-5 py-3.5 text-center text-xs font-semibold text-slate-500 uppercase tracking-wide">Qty</th>
                      <th className="px-5 py-3.5 text-right text-xs font-semibold text-slate-500 uppercase tracking-wide">Line Total</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {items.map((item, idx) => (
                      <tr key={idx} className="hover:bg-slate-50/50 transition-colors">
                        <td className="px-5 py-4 text-sm font-medium text-slate-900">{item.name}</td>
                        <td className="px-5 py-4 text-center text-sm font-semibold text-slate-700">{item.qty}</td>
                        <td className="px-5 py-4 text-right text-sm font-semibold text-slate-900">{formatMoney(Number(item.price) * item.qty, orderCurrency)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              {shippingLines.length > 0 && (
                <div className="mt-4 rounded-xl border border-slate-200 bg-slate-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Shipping Line</p>
                  <div className="mt-3 space-y-3">
                    {shippingLines.map((line, index) => (
                      <div key={`${line.title || 'shipping'}-${index}`} className="flex items-start justify-between gap-4 text-sm">
                        <p className="font-medium text-slate-900">{line.title || `Shipping line ${index + 1}`}</p>
                        <p className="font-semibold text-slate-900">{formatMoney(line.price, orderCurrency)}</p>
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <div className="mt-4 flex items-center justify-between rounded-xl border border-slate-200 bg-slate-50 px-5 py-4">
                <p className="text-sm font-semibold text-slate-700">Order Total</p>
                <p className="text-lg font-bold text-slate-900">{formatMoney(shopifyPayment.total_price || order.amount, orderCurrency)}</p>
              </div>
            </div>
          </div>
        </div>

        <div className="space-y-6">
          {/* Risk Score Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <Shield className="w-5 h-5 text-slate-400" />
                Risk
              </h3>
            </div>
            <div className="p-6">
              <div className="flex items-center justify-center py-8">
                <div className="relative w-36 h-36 drop-shadow-xl">
                  <svg className="w-full h-full transform -rotate-90">
                    <circle cx="72" cy="72" r="60" stroke="#f1f5f9" strokeWidth="12" fill="none" />
                    <circle 
                      cx="72" cy="72" r="60" 
                      stroke="url(#gradient)" 
                      strokeWidth="12" 
                      fill="none"
                      strokeLinecap="round"
                      strokeDasharray={`${(order.risk_score || 0) * 3.77} 377`}
                    />
                    <defs>
                      <linearGradient id="gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                        <stop offset="0%" stopColor={order.risk_level === 'low' ? '#059669' : order.risk_level === 'medium' ? '#0f766e' : order.risk_level === 'high' ? '#f97316' : '#ef4444'} />
                        <stop offset="100%" stopColor={order.risk_level === 'low' ? '#10b981' : order.risk_level === 'medium' ? '#14b8a6' : order.risk_level === 'high' ? '#ea580c' : '#dc2626'} />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-center">
                    <span className={clsx(
                      'text-4xl font-bold',
                      order.risk_level === 'low' ? 'text-emerald-600' :
                      order.risk_level === 'medium' ? 'text-teal-700' :
                      order.risk_level === 'high' ? 'text-orange-600' : 'text-red-600'
                    )}>
                      {order.risk_score || 0}
                    </span>
                    <span className="text-sm text-slate-500">Risk Score</span>
                  </div>
                </div>
              </div>

              <div className={clsx(
                'rounded-xl border p-5',
                riskTone === 'red' ? 'bg-red-50 border-red-200' :
                riskTone === 'amber' ? 'bg-amber-50 border-amber-200' :
                riskTone === 'teal' ? 'bg-teal-50 border-teal-200' :
                'bg-emerald-50 border-emerald-200'
              )}>
                <div className="flex items-start gap-3">
                  <div className={clsx(
                    'p-2 rounded-lg',
                    riskTone === 'red' ? 'bg-red-100' :
                    riskTone === 'amber' ? 'bg-amber-100' :
                    riskTone === 'teal' ? 'bg-teal-100' : 'bg-emerald-100'
                  )}>
                    <AlertTriangle className={clsx(
                      'w-5 h-5',
                      riskTone === 'red' ? 'text-red-700' :
                      riskTone === 'amber' ? 'text-amber-700' :
                      riskTone === 'teal' ? 'text-teal-700' : 'text-emerald-700'
                    )} />
                  </div>
                  <div className="space-y-2">
                    <div className="grid grid-cols-1 gap-2 text-sm text-slate-700">
                      <p><span className="font-semibold text-slate-900">Risk level:</span> {formatFieldValue(order.risk_level)}</p>
                      <p><span className="font-semibold text-slate-900">Recommendation:</span> {order.recommended_action_label || formatFieldValue(order.recommended_action)}</p>
                      <p><span className="font-semibold text-slate-900">Primary driver:</span> {decisionSummary.primary_driver || 'No major driver'}</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="text-lg font-semibold text-slate-900">Important Signals</h3>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 p-6">
              {signalFields.map(([label, value]) => (
                <DetailField key={label} label={label} value={value} />
              ))}
            </div>
          </div>

          {/* WhatsApp Verification Card */}
          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="text-lg font-semibold text-slate-900 flex items-center gap-2">
                <MessageCircle className="w-5 h-5 text-green-500" />
                WhatsApp Verification
                {conversationStatus && (
                  <span className={clsx(
                    'ml-auto text-xs font-medium px-2.5 py-1 rounded-full',
                    conversationStatus.status === 'completed' ? 'bg-emerald-100 text-emerald-700' :
                    conversationStatus.status === 'awaiting_reply' ? 'bg-amber-100 text-amber-700' :
                    conversationStatus.status === 'active' ? 'bg-blue-100 text-blue-700' :
                    conversationStatus.status === 'failed' ? 'bg-red-100 text-red-700' :
                    conversationStatus.status === 'cancelled' ? 'bg-slate-100 text-slate-700' :
                    'bg-slate-100 text-slate-600'
                  )}>
                    {conversationStatus.status === 'awaiting_reply' ? 'Awaiting Reply' :
                     conversationStatus.status?.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                  </span>
                )}
              </h3>
            </div>
            <div className="p-6">
              {chatLog.length > 0 ? (
                <div className="space-y-3 max-h-80 overflow-y-auto">
                  {chatLog.map((msg, idx) => (
                    <div
                      key={msg.id || idx}
                      className={clsx(
                        'flex',
                        msg.sender === 'bot' ? 'justify-start' : 'justify-end'
                      )}
                    >
                      <div className={clsx(
                        'max-w-[85%] rounded-2xl px-4 py-2.5 text-sm leading-relaxed',
                        msg.sender === 'bot'
                          ? 'bg-slate-100 text-slate-800 rounded-tl-none'
                          : msg.sender === 'system'
                          ? 'bg-amber-50 text-amber-700 border border-amber-200 text-xs italic w-full text-center rounded-2xl'
                          : 'bg-green-500 text-white rounded-tr-none'
                      )}>
                        <p>{msg.content}</p>
                        <p className={clsx(
                          'text-[10px] mt-1',
                          msg.sender === 'bot' ? 'text-slate-400' : msg.sender === 'system' ? 'text-amber-400' : 'text-green-200'
                        )}>
                          {msg.time}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-center py-6">
                  <MessageCircle className="w-10 h-10 text-slate-200 mx-auto mb-3" />
                  <p className="text-sm text-slate-500">No verification conversation yet</p>
                  <p className="text-xs text-slate-400 mt-1 mb-4">
                    {order.recommended_action === 'verify_address' || order.recommended_action === 'call_customer'
                      ? 'Auto-verification will trigger when chatbot is connected'
                      : 'Triggered when address verification is needed'}
                  </p>
                  <button
                    onClick={handleTriggerWhatsApp}
                    disabled={actionLoading === 'whatsapp'}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500 hover:bg-green-600 disabled:opacity-50 text-white text-sm font-medium transition-colors"
                  >
                    {actionLoading === 'whatsapp'
                      ? <Loader2 className="w-4 h-4 animate-spin" />
                      : <Send className="w-4 h-4" />}
                    Send WhatsApp
                  </button>
                </div>
              )}

              {/* Manual re-trigger — shown when previous conv failed/cancelled */}
              {conversationStatus && ['failed', 'cancelled'].includes(conversationStatus.status) && (
                <div className="mt-4 flex justify-end">
                  <button
                    onClick={handleTriggerWhatsApp}
                    disabled={actionLoading === 'whatsapp'}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-green-500 hover:bg-green-600 disabled:opacity-50 text-white text-sm font-medium transition-colors"
                  >
                    {actionLoading === 'whatsapp'
                      ? <Loader2 className="w-4 h-4 animate-spin" />
                      : <Send className="w-4 h-4" />}
                    Retry WhatsApp
                  </button>
                </div>
              )}

              {conversationStatus?.collected_data && Object.keys(conversationStatus.collected_data).length > 0 && (
                <div className="mt-4 rounded-xl border border-emerald-200 bg-emerald-50 p-4">
                  <p className="text-xs font-semibold uppercase tracking-wide text-emerald-600 mb-2">Collected via Chat</p>
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(conversationStatus.collected_data).map(([key, value]) => (
                      value && (
                        <div key={key}>
                          <p className="text-[10px] font-medium text-emerald-500 uppercase">{key}</p>
                          <p className="text-sm font-semibold text-emerald-800">{value}</p>
                        </div>
                      )
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="bg-white rounded-2xl border border-slate-200 shadow-sm overflow-hidden">
            <div className="px-6 py-4 border-b border-slate-100 bg-slate-50/50">
              <h3 className="text-lg font-semibold text-slate-900">Notes</h3>
            </div>
            <div className="p-6 space-y-4">
              <div className="rounded-xl border border-slate-200 bg-slate-50 p-4">
                <p className="text-xs font-semibold uppercase tracking-wide text-slate-500">Customer Note</p>
                <p className="mt-2 text-sm leading-6 text-slate-900">{canonicalNotes.customer_note || shopifyOrderIdentity.note || 'No notes from customer'}</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
