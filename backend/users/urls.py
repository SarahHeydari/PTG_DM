# users/urls.py
from django.urls import path
from .views import *

urlpatterns = [
    path("register/", RegisterAPIView.as_view(), name="register"),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("password/update/", ChangePasswordAPIView.as_view(), name="password-update"),
    path("groups/", AccessGroupListCreateAPIView.as_view(), name="groups-list-create"),
    path("groups/members/add/", GroupMemberAddAPIView.as_view(), name="group-member-add"),
    path("groups/<int:group_id>/members/<int:user_id>/", GroupMemberRemoveAPIView.as_view(), name="group-member-remove"),
    path("groups/<int:group_id>/members/", GroupMembersListAPIView.as_view(), name="group-members-list"),
    path("groups/<int:group_id>/", AccessGroupDetailAPIView.as_view(), name="group-detail"),    
    path("users/", UserListAPIView.as_view(), name="users-list"),
    path("myprofile/", UserMeAPIView.as_view(), name="user-myprofile"),
    path("admin/ping/", AdminPingAPIView.as_view()),
    path("admin/users/", AdminUserListAPIView.as_view()),
    path("admin/users/create/", AdminUserCreateAPIView.as_view()),
    path("admin/users/<int:user_id>/", AdminUserDeleteAPIView.as_view()),
    path("admin/stats/", AdminStatsAPIView.as_view()),







]
