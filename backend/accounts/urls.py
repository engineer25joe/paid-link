from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from .views import RegisterView, ProfileView
from .earnings import (
    CreatorEarningsSummaryView,
    CreatorEarningsByContentView,
    CreatorTransactionHistoryView,
    CreatorWithdrawalHistoryView,
)


urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("creator/earnings/summary/", CreatorEarningsSummaryView.as_view(), name="creator-earnings-summary"),
    path("creator/earnings/content/", CreatorEarningsByContentView.as_view(), name="creator-earnings-by-content"),
    path("creator/transactions/", CreatorTransactionHistoryView.as_view(), name="creator-transaction-history"),
    path("creator/withdrawals/", CreatorWithdrawalHistoryView.as_view(), name="creator-withdrawal-history"),
]
