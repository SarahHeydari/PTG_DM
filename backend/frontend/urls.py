from django.urls import path
from .views import *

urlpatterns = [
    path("fire/", fire_dashboard, name="fire-dashboard"),
    path("", dashboard, name="dashboard"),
    path("login/", login_view, name="login"),
]
