/**
 * Analytics API — dashboard stats, trends, heatmap, fraud
 */
import client from './client';

const analyticsApi = {
  getDashboardStats: (days = 7) =>
    client.get('/analytics/dashboard-stats/', { params: { days } }),

  getRtoTrend: (days = 7) =>
    client.get('/analytics/rto-trend/', { params: { days } }),

  getOverview: () =>
    client.get('/analytics/overview/'),

  getRiskHeatmap: () =>
    client.get('/analytics/risk-heatmap/'),

  getFraudTrends: (days = 30) =>
    client.get('/analytics/fraud-trends/', { params: { days } }),
};

export default analyticsApi;
