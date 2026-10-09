from django.contrib import admin
from django.urls import include, path
from .health import HealthView


urlpatterns = [
    path("api/health/", HealthView.as_view(), name="api-health"),
    path("admin/", admin.site.urls),
    path("api/accounts/", include("accounts.urls")),
    path("api/content/", include("content.urls")),
    path("api/purchases/", include("purchases.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/admin/", include("accounts.admin_api_urls")),
]
