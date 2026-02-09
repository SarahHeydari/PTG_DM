# users/views.py
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import *
from .serializers import *
from .jwt_utils import create_access_token
from rest_framework.permissions import IsAuthenticated
from django.db.models import Count
from .permissions import IsManager



class RegisterAPIView(generics.CreateAPIView):
    queryset = User.objects.all()
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        return Response(
            {
                "access": create_access_token(user),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "email": user.email,
                },
            },
            status=status.HTTP_201_CREATED,
        )




class LoginAPIView(APIView):
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = serializer.validated_data["user"]

        user.last_login = timezone.now()
        user.save(update_fields=["last_login"])

        return Response(
            {
                "access": create_access_token(user),
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "email": user.email,
                    "last_login": user.last_login,
                },
            },
            status=status.HTTP_200_OK,
        )



class ChangePasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        user = request.user
        old_password = serializer.validated_data["old_password"]
        new_password = serializer.validated_data["new_password"]

        # Demo only: raw password comparison
        if user.password != old_password:
            return Response(
                {"detail": "Old password is incorrect."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user.password = new_password
        user.save(update_fields=["password"])

        return Response({"detail": "Password updated successfully."}, status=status.HTTP_200_OK)





class AccessGroupListCreateAPIView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = AccessGroup.objects.select_related("created_by").annotate(
            members_count=Count("memberships")
        ).order_by("-created_at")

        if self.request.user.role == "manager":
            return qs
        return qs.filter(memberships__user=self.request.user).distinct()

    def get_serializer_class(self):
        if self.request.method == "POST":
            return AccessGroupCreateSerializer
        return AccessGroupListSerializer

    def get_permissions(self):
        # GET: هر کاربر لاگین‌شده
        if self.request.method == "GET":
            return [IsAuthenticated()]
        # POST: فقط مدیر
        return [IsAuthenticated(), IsManager()]




class GroupMemberAddAPIView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def post(self, request):
        serializer = GroupMemberAddSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membership = serializer.save()

        return Response(
            {
                "detail": "عضو به گروه اضافه شد.",
                "membership": {
                    "id": membership.id,
                    "group_id": membership.group_id,
                    "user_id": membership.user_id,
                    "joined_at": membership.joined_at,
                },
            },
            status=status.HTTP_201_CREATED,
        )



class GroupMemberRemoveAPIView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def delete(self, request, group_id: int, user_id: int):
        membership = GroupMember.objects.select_related("group", "user").filter(
            group_id=group_id,
            user_id=user_id
        ).first()

        if not membership:
            return Response(
                {"detail": "این کاربر عضو این گروه نیست یا قبلاً حذف شده است."},
                status=status.HTTP_404_NOT_FOUND,
            )

        group_name = membership.group.name
        username = membership.user.username

        membership.delete()

        return Response(
            {"detail": f"کاربر {username} از گروه {group_name} حذف شد."},
            status=status.HTTP_200_OK,
        )



class GroupMembersListAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, group_id: int):
        group = AccessGroup.objects.filter(id=group_id).first()
        if not group:
            return Response({"detail": "گروه موردنظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        # Manager: ok
        if request.user.role != "manager":
            is_member = GroupMember.objects.filter(group_id=group_id, user=request.user).exists()
            if not is_member:
                return Response(
                    {"detail": "شما دسترسی مشاهده اعضای این گروه را ندارید."},
                    status=status.HTTP_403_FORBIDDEN,
                )

        memberships = GroupMember.objects.select_related("user").filter(group_id=group_id).order_by("joined_at")
        data = GroupMemberListSerializer(memberships, many=True).data

        return Response(
            {
                "group": {"id": group.id, "name": group.name, "access_level": group.access_level},
                "members": data,
            },
            status=status.HTTP_200_OK,
        )



    

class AccessGroupUpdateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def patch(self, request, group_id: int):
        group = AccessGroup.objects.filter(id=group_id).first()
        if not group:
            return Response({"detail": "گروه موردنظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AccessGroupUpdateSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "گروه با موفقیت به‌روزرسانی شد.",
                "group": {
                    "id": group.id,
                    "name": group.name,
                    "access_level": group.access_level,
                },
            },
            status=status.HTTP_200_OK,
        )



class AccessGroupDetailAPIView(APIView):
    permission_classes = [IsAuthenticated, IsManager]

    def patch(self, request, group_id: int):
        group = AccessGroup.objects.filter(id=group_id).first()
        if not group:
            return Response({"detail": "گروه موردنظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AccessGroupUpdateSerializer(group, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(
            {
                "detail": "گروه با موفقیت به‌روزرسانی شد.",
                "group": {"id": group.id, "name": group.name, "access_level": group.access_level},
            },
            status=status.HTTP_200_OK,
        )

    def delete(self, request, group_id: int):
        group = AccessGroup.objects.filter(id=group_id).first()
        if not group:
            return Response({"detail": "گروه موردنظر یافت نشد."}, status=status.HTTP_404_NOT_FOUND)

        name = group.name
        group.delete()
        return Response({"detail": f"گروه {name} با موفقیت حذف شد."}, status=status.HTTP_200_OK)
    

class UserListAPIView(generics.ListAPIView):
    serializer_class = UserListSerializer
    permission_classes = [IsAuthenticated, IsManager]

    def get_queryset(self):
        qs = User.objects.all().order_by("username")  # A-Z

        q = self.request.query_params.get("q")
        if q:
            q = q.strip()
            qs = qs.filter(username__icontains=q)

        return qs



class UserMeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = UserMeSerializer(request.user).data
        return Response(data, status=status.HTTP_200_OK)

    def patch(self, request):
        serializer = UserMeSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(
            {"detail": "پروفایل با موفقیت به‌روزرسانی شد.", "user": serializer.data},
            status=status.HTTP_200_OK,
        )
