from django.urls import path

from .views import (
    AdminApproveWithdrawalView,
    AdminWithdrawalListView,
    AdminSubmitWithdrawalView,
    AdminCancelWithdrawalView,
    AdminReconcileWithdrawalView,
    AdminReconcilePaymentView,
    CreatorWithdrawalRequestView,
    InitiateMpesaPaymentView,
    b2c_result_callback,
    b2c_timeout_callback,
    mpesa_callback,
)

urlpatterns = [
    path(
        "mpesa/initiate/",
        InitiateMpesaPaymentView.as_view(),
        name="mpesa-initiate",
    ),

    path(
        "mpesa/callback/",
        mpesa_callback,
        name="mpesa-callback",
    ),

    path(
    "withdrawals/request/",
    CreatorWithdrawalRequestView.as_view(),
    name="withdrawal-request",
    ),

    path(
    "withdrawals/",
    AdminWithdrawalListView.as_view(),
    name="admin-withdrawals",
    ),

    path(
    "mpesa/b2c/result/",
    b2c_result_callback,
    name="mpesa-b2c-result",
    ),

    path(
        "mpesa/b2c/timeout/",
        b2c_timeout_callback,
        name="mpesa-b2c-timeout",
    ),

    path(
    "withdrawals/<int:withdrawal_id>/approve/",
    AdminApproveWithdrawalView.as_view(),
    name="admin-approve-withdrawal",
    ),

    path(
    "withdrawals/<int:withdrawal_id>/submit/",
        AdminSubmitWithdrawalView.as_view(),
        name="admin-submit-withdrawal",
    ),

    path(
        "withdrawals/<int:withdrawal_id>/reconcile/",
        AdminReconcileWithdrawalView.as_view(),
        name="admin-reconcile-withdrawal",
    ),
    path(
        "mpesa/payments/<int:payment_id>/reconcile/",
        AdminReconcilePaymentView.as_view(),
        name="admin-reconcile-payment",
    ),

    path(
        "withdrawals/<int:withdrawal_id>/cancel/",
        AdminCancelWithdrawalView.as_view(),
        name="admin-cancel-withdrawal",
    ),
]
