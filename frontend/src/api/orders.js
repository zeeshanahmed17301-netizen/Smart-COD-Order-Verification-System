/**
 * Orders API — list, detail, create, accept, confirm, cancel
 */
import client from './client';

const ordersApi = {
  list: (params = {}) =>
    client.get('/orders/', { params }),

  get: (id) =>
    client.get(`/orders/${id}/`),

  create: (data) =>
    client.post('/orders/', data),

  update: (id, data) =>
    client.patch(`/orders/${id}/`, data),

  accept: (id) =>
    client.post(`/orders/${id}/accept/`),

  confirm: (id) =>
    client.post(`/orders/${id}/confirm/`),

  cancel: (id) =>
    client.post(`/orders/${id}/cancel/`),

  approve: (id) =>
    ordersApi.accept(id),

  reject: (id, reason = '') =>
    ordersApi.cancel(id, reason),

  recomputeScores: (id) =>
    client.post('/risk/score/', { order_id: id }),

  triggerWhatsApp: (id) =>
    client.post('/chatbot/trigger/', { order_id: id }),
};

export default ordersApi;
