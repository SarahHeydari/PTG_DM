from django.urls import path
from .views import *

urlpatterns = [
    path("fire/", fire_dashboard, name="fire-dashboard"),
    path("", dashboard, name="dashboard"),
    path("login/", login_page, name="login"),
    path("register/", register_page, name="register"),
    path("profile/", profile_router, name="profile_router"),
    path("profile/manager/", manager_profile, name="manager_profile"),
    path("profile/expert/", expert_profile, name="expert_profile"),
    path("profile/admin/", admin_profile, name="admin_profile"),
]
