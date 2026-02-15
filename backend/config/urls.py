# config/urls.py  
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import redirect

urlpatterns = [
    path("", lambda request: redirect("/ui/")),

    path("admin/", admin.site.urls),
    path("api/users/", include("users.urls")),
    path("ui/", include("frontend.urls")),
    path("api/fire/", include("fire.urls")),


]


if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)