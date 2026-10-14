from django.urls import path

from .views import PurchaseContentView, MyPurchasesView


urlpatterns = [
    path("", MyPurchasesView.as_view(), name="my-purchases"),
    path(
        "<int:content_id>/purchase/",
        PurchaseContentView.as_view(),
        name="purchase-content",
    ),
]
