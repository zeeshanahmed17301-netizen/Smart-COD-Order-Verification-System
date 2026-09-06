"""URL configuration for analytics."""
from django.urls import path
from .views import (
    DashboardStatsView,
    RTOTrendView,
    AnalyticsOverviewView,
    RiskHeatmapView,
    FraudTrendsView,
)

urlpatterns = [
    path("dashboard-stats/", DashboardStatsView.as_view(), name="dashboard-stats"),
    path("rto-trend/", RTOTrendView.as_view(), name="rto-trend"),
    path("overview/", AnalyticsOverviewView.as_view(), name="analytics-overview"),
    path("risk-heatmap/", RiskHeatmapView.as_view(), name="risk-heatmap"),
    path("fraud-trends/", FraudTrendsView.as_view(), name="fraud-trends"),
]
