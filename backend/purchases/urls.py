from django.urls import path

from .views import PurchaseContentView


urlpatterns = [
    path(
        "<int:content_id>/purchase/",
        PurchaseContentView.as_view(),
        name="purchase-content",
    ),
]
