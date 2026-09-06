import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Store,
} from 'lucide-react';
import clsx from 'clsx';
import storesApi from '../api/stores';
import ordersApi from '../api/orders';
import { getErrorMessage } from '../api/client';

export default function ConnectStorePage() {
  const [connections, setConnections] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const [savingShopify, setSavingShopify] = useState(false);
  const [syncingShopify, setSyncingShopify] = useState(false);
  const [scoringShopify, setScoringShopify] = useState(false);
  const [syncLimit, setSyncLimit] = useState(50);
  const [shopifyForm, setShopifyForm] = useState({ store_url: '', client_id: '', client_secret: '' });

  const loadData = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const connectionsRes = await storesApi.listConnections();
      setConnections(Array.isArray(connectionsRes.data) ? connectionsRes.data : (connectionsRes.data.results || []));
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  const shopifyConnection = useMemo(
    () => connections.find((connection) => connection.platform === 'shopify'),
    [connections]
  );

  useEffect(() => {
    if (shopifyConnection?.store_url) {
      setShopifyForm((prev) => ({ ...prev, store_url: shopifyConnection.store_url }));
    }
  }, [shopifyConnection]);

  const setFeedback = (nextError = '', nextSuccess = '') => {
    setError(nextError);
    setSuccess(nextSuccess);
  };

  const handleSaveShopify = async () => {
    setSavingShopify(true);
    setFeedback();
    try {
      const payload = {
        platform: 'shopify',
        store_url: shopifyForm.store_url,
        is_active: true,
      };
      if (shopifyForm.client_id) {
        payload.client_id = shopifyForm.client_id;
      }
      if (shopifyForm.client_secret) {
        payload.client_secret = shopifyForm.client_secret;
      }

      if (shopifyConnection) {
        await storesApi.updateConnection(shopifyConnection.id, payload);
      } else {
        await storesApi.createConnection({ ...payload, client_id: shopifyForm.client_id, client_secret: shopifyForm.client_secret });
      }

      setShopifyForm((prev) => ({ ...prev, client_id: '', client_secret: '' }));
      setFeedback('', 'Shopify connection saved.');
      await loadData();
    } catch (err) {
      setFeedback(getErrorMessage(err));
    } finally {
      setSavingShopify(false);
    }
  };

  const handleSyncShopify = async () => {
    if (!shopifyConnection) {
      setFeedback('Save the Shopify connection before syncing.');
      return;
    }

    setSyncingShopify(true);
    setFeedback();
    try {
      const { data } = await storesApi.syncConnection(shopifyConnection.id, { limit: syncLimit });
      const summary = data?.summary;
      const firstFailure = summary?.failed_orders?.[0];
      const syncedOrderIds = [...new Set((summary?.order_ids || []).filter(Boolean))];
      await loadData();
      setSyncingShopify(false);

      let scored = 0;
      let scoringFailed = 0;
      let firstScoringError = '';
      if (syncedOrderIds.length > 0) {
        setScoringShopify(true);
        setFeedback('', `Orders loaded. Scoring ${syncedOrderIds.length} order(s)...`);
        for (const orderId of syncedOrderIds) {
          try {
            await ordersApi.recomputeScores(orderId);
            scored += 1;
          } catch (err) {
            scoringFailed += 1;
            if (!firstScoringError) {
              firstScoringError = getErrorMessage(err);
            }
          }
        }
      }

      const scoringMessage = syncedOrderIds.length
        ? ` Scored ${scored}.${scoringFailed ? ` Scoring failed for ${scoringFailed} order(s): ${firstScoringError}` : ''}`
        : '';
      setFeedback(
        scoringFailed ? `Scoring failed for ${scoringFailed} order(s). ${firstScoringError}` : '',
        summary
          ? `Sync complete. Fetched ${summary.fetched}. Imported ${summary.imported}, updated ${summary.updated}, failed ${summary.failed}.${firstFailure ? ` First failed order: ${firstFailure.shopify_order_id}.` : ''}${scoringMessage}`
          : 'Shopify sync completed.'
      );
    } catch (err) {
      setFeedback(getErrorMessage(err));
    } finally {
      setSyncingShopify(false);
      setScoringShopify(false);
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex flex-col gap-3 lg:flex-row lg:items-end lg:justify-between">
        <div>
          <h1 className="text-3xl font-bold text-slate-900">Store Integrations</h1>
          <p className="mt-2 text-slate-500">
            Manage your Shopify connection and run manual order syncs from one place.
          </p>
        </div>
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700">
          {connections.filter((connection) => connection.is_active).length} active connection(s)
        </div>
      </div>

      {(error || success) && (
        <div className="space-y-3">
          {error && (
            <div className="flex items-center gap-3 rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
              <AlertCircle className="h-4 w-4" />
              <span>{error}</span>
            </div>
          )}
          {success && (
            <div className="flex items-center gap-3 rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm text-emerald-700">
              <CheckCircle className="h-4 w-4" />
              <span>{success}</span>
            </div>
          )}
        </div>
      )}

      <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <div className="flex items-start justify-between gap-4">
              <div>
                <h2 className="flex items-center gap-2 text-lg font-semibold text-slate-900">
                  <Store className="h-5 w-5 text-slate-400" />
                  Shopify
                </h2>
                <p className="mt-1 text-sm text-slate-500">
                  Save your store domain and admin token, then run manual syncs when needed.
                </p>
              </div>
              {shopifyConnection?.is_active && (
                <span className="rounded-full border border-emerald-200 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
                  Connected
                </span>
              )}
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2">
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">Store URL</label>
                <input
                  value={shopifyForm.store_url}
                  onChange={(event) => setShopifyForm((prev) => ({ ...prev, store_url: event.target.value }))}
                  placeholder="your-store.myshopify.com"
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-600"
                />
              </div>
              <div>
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Client ID {shopifyConnection ? '(leave blank to keep current)' : ''}
                </label>
                <input
                  value={shopifyForm.client_id}
                  onChange={(event) => setShopifyForm((prev) => ({ ...prev, client_id: event.target.value }))}
                  placeholder="From Dev Dashboard → Settings"
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-600"
                />
              </div>
              <div className="md:col-span-2">
                <label className="mb-2 block text-sm font-medium text-slate-700">
                  Client Secret {shopifyConnection ? '(leave blank to keep current)' : ''}
                </label>
                <input
                  type="password"
                  value={shopifyForm.client_secret}
                  onChange={(event) => setShopifyForm((prev) => ({ ...prev, client_secret: event.target.value }))}
                  placeholder="shpss_..."
                  className="w-full rounded-xl border border-slate-200 px-4 py-3 text-sm focus:outline-none focus:ring-2 focus:ring-teal-600"
                />
              </div>
            </div>

            <div className="mt-6 flex flex-wrap gap-3">
              <select
                value={syncLimit}
                onChange={(event) => setSyncLimit(Number(event.target.value))}
                className="rounded-xl border border-slate-200 bg-white px-3 py-2.5 text-sm text-slate-700 focus:outline-none focus:ring-2 focus:ring-teal-600"
              >
                <option value={25}>Sync 25</option>
                <option value={50}>Sync 50</option>
                <option value={100}>Sync 100</option>
                <option value={250}>Sync 250</option>
              </select>
              <button
                type="button"
                onClick={handleSaveShopify}
                disabled={savingShopify || loading}
                className="rounded-xl bg-gradient-to-r from-teal-700 to-emerald-600 px-4 py-2.5 text-sm font-semibold text-white disabled:opacity-60"
              >
                {savingShopify ? 'Saving...' : shopifyConnection ? 'Update Shopify' : 'Connect Shopify'}
              </button>
              <button
                type="button"
                onClick={handleSyncShopify}
                disabled={!shopifyConnection || syncingShopify || scoringShopify || loading}
                className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-2.5 text-sm font-semibold text-slate-700 disabled:opacity-60"
              >
                <RefreshCw className={clsx('h-4 w-4', (syncingShopify || scoringShopify) && 'animate-spin')} />
                {syncingShopify ? 'Syncing...' : scoringShopify ? 'Scoring...' : 'Sync Orders'}
              </button>
            </div>
          </section>

          <section className="rounded-2xl border border-slate-200 bg-white p-6 shadow-sm">
            <h2 className="text-lg font-semibold text-slate-900">Connection Status</h2>
            {loading ? (
              <p className="mt-4 text-sm text-slate-500">Loading integrations...</p>
            ) : shopifyConnection ? (
              <div className="mt-4 space-y-3 text-sm text-slate-600">
                <div className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3">
                  <span>Domain</span>
                  <span className="font-medium text-slate-900">{shopifyConnection.store_url}</span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3">
                  <span>Status</span>
                  <span className={clsx('font-medium', shopifyConnection.is_active ? 'text-emerald-700' : 'text-slate-700')}>
                    {shopifyConnection.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <div className="flex items-center justify-between rounded-xl bg-slate-50 px-4 py-3">
                  <span>Last sync</span>
                  <span className="font-medium text-slate-900">
                    {shopifyConnection.last_sync_at ? new Date(shopifyConnection.last_sync_at).toLocaleString() : 'Never'}
                  </span>
                </div>
              </div>
            ) : (
              <p className="mt-4 text-sm text-slate-500">No Shopify connection saved yet.</p>
            )}
          </section>
      </div>

    </div>
  );
}
