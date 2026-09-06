/**
 * Stores API — connections, API keys, webhooks
 */
import client from './client';

const SYNC_TIMEOUT_MS = 120000;

const storesApi = {
  // ── Store Connections ───────────────────────────────────────
  listConnections: () =>
    client.get('/stores/connections/'),

  createConnection: (data) =>
    client.post('/stores/connections/', data),

  updateConnection: (id, data) =>
    client.patch(`/stores/connections/${id}/`, data),

  deleteConnection: (id) =>
    client.delete(`/stores/connections/${id}/`),

  syncConnection: (id, data = {}) =>
    client.post(`/stores/connections/${id}/sync/`, data, { timeout: SYNC_TIMEOUT_MS }),

  // ── API Keys ────────────────────────────────────────────────
  listApiKeys: () =>
    client.get('/stores/api-keys/'),

  createApiKey: (label = 'Default') =>
    client.post('/stores/api-keys/', { label }),

  deleteApiKey: (id) =>
    client.delete(`/stores/api-keys/${id}/`),

  regenerateApiKey: (id) =>
    client.post(`/stores/api-keys/${id}/regenerate/`),

  // ── Webhooks ────────────────────────────────────────────────
  listWebhooks: () =>
    client.get('/stores/webhooks/'),

  createWebhook: (data) =>
    client.post('/stores/webhooks/', data),

  updateWebhook: (id, data) =>
    client.patch(`/stores/webhooks/${id}/`, data),

  deleteWebhook: (id) =>
    client.delete(`/stores/webhooks/${id}/`),
};

export default storesApi;
