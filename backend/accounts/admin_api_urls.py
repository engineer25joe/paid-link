from django.urls import path

from payments.views import (
    AdminApproveWithdrawalView,
    AdminCancelWithdrawalView,
    AdminReconcilePaymentView,
    AdminReconcileWithdrawalView,
)
from .admin_api import (
    ContentDetail, ContentList, CreatorDetail, CreatorList, DashboardStatsView,
    LearnerDetail, LearnerList, LedgerList, PurchaseDetail, PurchaseList,
    UserDetail, UserList, WithdrawalDetail, WithdrawalList,
)

urlpatterns = [
    path("dashboard/", DashboardStatsView.as_view(), name="admin-dashboard-stats"),
    path("users/", UserList.as_view(), name="admin-users"),
    path("users/<int:pk>/", UserDetail.as_view(), name="admin-user-detail"),
    path("creators/", CreatorList.as_view(), name="admin-creators"),
    path("creators/<int:pk>/", CreatorDetail.as_view(), name="admin-creator-detail"),
    path("learners/", LearnerList.as_view(), name="admin-learners"),
    path("learners/<int:pk>/", LearnerDetail.as_view(), name="admin-learner-detail"),
    path("content/", ContentList.as_view(), name="admin-content"),
    path("content/<int:pk>/", ContentDetail.as_view(), name="admin-content-detail"),
    path("purchases/", PurchaseList.as_view(), name="admin-purchases"),
    path("purchases/<int:pk>/", PurchaseDetail.as_view(), name="admin-purchase-detail"),
    path("ledger/", LedgerList.as_view(), name="admin-ledger"),
    path("withdrawals/", WithdrawalList.as_view(), name="admin-withdrawals-api"),
    path("withdrawals/<int:pk>/", WithdrawalDetail.as_view(), name="admin-withdrawal-detail"),
    path("withdrawals/<int:withdrawal_id>/approve/", AdminApproveWithdrawalView.as_view(), name="admin-withdrawal-approve"),
    path("withdrawals/<int:withdrawal_id>/cancel/", AdminCancelWithdrawalView.as_view(), name="admin-withdrawal-cancel"),
    path("withdrawals/<int:withdrawal_id>/reconcile/", AdminReconcileWithdrawalView.as_view(), name="admin-withdrawal-reconcile"),
    path("payments/<int:payment_id>/reconcile/", AdminReconcilePaymentView.as_view(), name="admin-payment-reconcile"),
]
