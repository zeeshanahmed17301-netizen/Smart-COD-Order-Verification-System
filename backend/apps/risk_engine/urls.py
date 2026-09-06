"""URL configuration for risk engine."""

from django.urls import path

from .views import ScoreOrderView


urlpatterns = [
    path("score/", ScoreOrderView.as_view(), name="risk-score-order"),
]