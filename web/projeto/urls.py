# web/projeto/urls.py

from django.urls import path, include

urlpatterns = [
    path("", include("core.urls")),
]
