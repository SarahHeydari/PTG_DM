# users/views.py
from django.utils import timezone
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser, FormParser


from .models import *
from .serializers import *
from .jwt_utils import create_access_token
from rest_framework.permissions import IsAuthenticated, BasePermission  
from django.db.models import Count, Q
from .permissions import IsRoleAdmin, IsManagerOrAdmin



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

        # Admin has all manager capabilities too
        if self.request.user.role in ["manager", "admin"]:
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
        # POST: مدیر یا ادمین
        return [IsAuthenticated(), IsManagerOrAdmin()]


class GroupMemberAddAPIView(APIView):
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

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
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

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

        # Manager/Admin: ok
        if request.user.role not in ["manager", "admin"]:
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
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

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
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

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
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]

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


class AdminPingAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRoleAdmin]

    def get(self, request):
        return Response(
            {
                "ok": True,
                "user": {
                    "id": request.user.id,
                    "username": request.user.username,
                    "role": request.user.role,
                    "email": request.user.email,
                },
            },
            status=status.HTTP_200_OK,
        )
    

class AdminUserListAPIView(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsRoleAdmin]
    serializer_class = AdminUserListSerializer

    def get_queryset(self):
        qs = User.objects.all().order_by("-date_joined")

        role = self.request.query_params.get("role")
        if role in ["admin", "manager", "expert"]:
            qs = qs.filter(role=role)

        q = self.request.query_params.get("q")
        if q:
            qs = qs.filter(
                Q(username__icontains=q) |
                Q(email__icontains=q)
            )

        return qs
    

class AdminUserCreateAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRoleAdmin]

    def post(self, request):
        username = (request.data.get("username") or "").strip()
        password = (request.data.get("password") or "").strip()
        role = (request.data.get("role") or "").strip()
        email = (request.data.get("email") or "").strip()

        if not username:
            return Response({"detail": "username is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not password:
            return Response({"detail": "password is required."}, status=status.HTTP_400_BAD_REQUEST)
        if role not in ["admin", "manager", "expert"]:
            return Response(
                {"detail": "role must be one of: admin, manager, expert."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if User.objects.filter(username=username).exists():
            return Response({"detail": "این نام کاربری قبلاً ثبت شده است."}, status=status.HTTP_400_BAD_REQUEST)

        # Demo: raw password like your current ChangePassword/Login logic
        user = User.objects.create(
            username=username,
            password=password,
            role=role,
            email=email,
        )

        return Response(
            {
                "detail": "کاربر با موفقیت ایجاد شد.",
                "user": {
                    "id": user.id,
                    "username": user.username,
                    "role": user.role,
                    "email": user.email,
                    "date_joined": user.date_joined,
                    "last_login": user.last_login,
                },
            },
            status=status.HTTP_201_CREATED,
        )



class AdminUserDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRoleAdmin]

    def delete(self, request, user_id: int):
        # جلوگیری از حذف خود ادمین
        if request.user.id == user_id:
            return Response(
                {"detail": "ادمین نمی‌تواند خودش را حذف کند."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        target = User.objects.filter(id=user_id).first()
        if not target:
            return Response(
                {"detail": "کاربر موردنظر یافت نشد."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # جلوگیری از حذف آخرین ادمین (قفل شدن سیستم)
        if target.role == "admin" and User.objects.filter(role="admin").count() <= 1:
            return Response(
                {"detail": "امکان حذف آخرین ادمین وجود ندارد."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        username = target.username
        target.delete()

        return Response(
            {"detail": f"کاربر {username} حذف شد."},
            status=status.HTTP_200_OK,
        )


class AdminStatsAPIView(APIView):
    permission_classes = [IsAuthenticated, IsRoleAdmin]

    def get(self, request):
        users_total = User.objects.count()

        users_by_role = {
            "admin": User.objects.filter(role="admin").count(),
            "manager": User.objects.filter(role="manager").count(),
            "expert": User.objects.filter(role="expert").count(),
        }

        groups_total = AccessGroup.objects.count()
        memberships_total = GroupMember.objects.count()

        groups_by_access_level = {
            "read": AccessGroup.objects.filter(access_level="read").count(),
            "write": AccessGroup.objects.filter(access_level="write").count(),
        }

        # نمودار ساده: تعداد اعضا در هر گروه (Top 10)
        top_groups = (
            AccessGroup.objects.annotate(members_count=Count("memberships"))
            .order_by("-members_count", "-created_at")[:10]
        )
        top_groups_data = [
            {"id": g.id, "name": g.name, "members_count": g.members_count}
            for g in top_groups
        ]

        return Response(
            {
                "users_total": users_total,
                "users_by_role": users_by_role,
                "groups_total": groups_total,
                "memberships_total": memberships_total,
                "groups_by_access_level": groups_by_access_level,
                "top_groups": top_groups_data,
            },
            status=status.HTTP_200_OK,
        )


class ReportUploadAPIView(APIView):
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        user = getattr(request, "user", None)

        # جلوگیری از خطاهای is_authenticated و کنترل احراز هویت به سبک خودمون
        if not user or not getattr(user, "id", None):
            return Response({"detail": "ابتدا وارد شوید."}, status=status.HTTP_401_UNAUTHORIZED)

        role = (getattr(user, "role", "") or "").lower()
        if role != "expert":
            return Response({"detail": "شما دسترسی آپلود گزارش ندارید."}, status=status.HTTP_403_FORBIDDEN)

        ser = ReportUploadSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        report = ser.save(uploaded_by=user)

        file_url = ""
        try:
            file_url = request.build_absolute_uri(report.file.url)
        except Exception:
            file_url = ""

        return Response(
            {
                "detail": "گزارش با موفقیت آپلود شد.",
                "report": {
                    "id": report.id,
                    "title": report.title,
                    "subsystem": report.subsystem,
                    "file_url": file_url,
                    "created_at": report.created_at,
                },
            },
            status=status.HTTP_201_CREATED,
        )
    


class MyReportsAPIView(APIView):
    """
    GET /api/users/reports/my/
    فقط expert: لیست گزارش‌های خودش
    """
    def get(self, request):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "id", None):
            return Response({"detail": "ابتدا وارد شوید."}, status=status.HTTP_401_UNAUTHORIZED)

        role = (getattr(user, "role", "") or "").lower()
        if role != "expert":
            return Response({"detail": "شما دسترسی مشاهده این بخش را ندارید."}, status=status.HTTP_403_FORBIDDEN)

        q = (request.query_params.get("q") or "").strip()

        qs = Report.objects.select_related("uploaded_by").filter(uploaded_by=user)

        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(subsystem__icontains=q)
            )

        ser = ReportListSerializer(qs, many=True, context={"request": request})
        return Response(ser.data, status=status.HTTP_200_OK)


class ReportsListForManagerAPIView(APIView):
    """
    GET /api/users/reports/
    فقط manager: لیست همه گزارش‌ها + سرچ q روی عنوان/زیرسامانه/نام کاربری آپلودکننده
    """
    def get(self, request):
        user = getattr(request, "user", None)
        if not user or not getattr(user, "id", None):
            return Response({"detail": "ابتدا وارد شوید."}, status=status.HTTP_401_UNAUTHORIZED)

        role = (getattr(user, "role", "") or "").lower()
        if role != "manager":
            return Response({"detail": "شما دسترسی مشاهده گزارش‌ها را ندارید."}, status=status.HTTP_403_FORBIDDEN)

        q = (request.query_params.get("q") or "").strip()

        qs = Report.objects.select_related("uploaded_by").all()

        if q:
            qs = qs.filter(
                Q(title__icontains=q) |
                Q(subsystem__icontains=q) |
                Q(uploaded_by__username__icontains=q)
            )

        ser = ReportListSerializer(qs, many=True, context={"request": request})
        return Response(ser.data, status=status.HTTP_200_OK)
