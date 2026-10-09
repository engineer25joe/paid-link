from django.urls import path

from .views import (
    ContentAccessView,
    ContentCreateView,
    ContentListView,
    MyContentListView,
    MyContentPublishView,
    MyContentUpdateView,
)


urlpatterns = [
    path("", ContentListView.as_view(),
         name="content-list"
    ),

    path("create/",
         ContentCreateView.as_view(),
         name="content-create"
    ),

    path(
    "my-content/",
    MyContentListView.as_view(),
    name="my-content",
    ),

    path(
    "<int:content_id>/publish/",
    MyContentPublishView.as_view(),
    name="content-publish",
    ),

    path(
    "<int:content_id>/update/",
    MyContentUpdateView.as_view(),
    name="content-update",
    ),

    path(
        "<int:content_id>/access/",
        ContentAccessView.as_view(),
        name="content-access",
    ),
]