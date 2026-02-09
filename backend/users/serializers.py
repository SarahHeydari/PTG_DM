# users/serializers.py
from rest_framework import serializers
from .models import *


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, max_length=128)

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "role", "date_joined"]
        read_only_fields = ["id", "date_joined"]

    def validate_username(self, value: str) -> str:
        value = value.strip()
        if not value:
            raise serializers.ValidationError("username is required.")
        return value

    def create(self, validated_data):
        # Demo only: storing raw password (NOT recommended for production)
        return User.objects.create(**validated_data)


class LoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs["username"].strip()    
        password = attrs["password"]

        user = User.objects.filter(username=username).first()
        if not user or user.password != password:
            raise serializers.ValidationError("Invalid username or password.")

        attrs["user"] = user
        return attrs


class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(write_only=True, min_length=4)
    new_password_confirm = serializers.CharField(write_only=True)

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError("New passwords do not match.")
        return attrs


class AccessGroupCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessGroup
        fields = ["id", "name", "access_level", "created_at"]
        read_only_fields = ["id", "created_at"]

    def create(self, validated_data):
        request = self.context["request"]
        return AccessGroup.objects.create(created_by=request.user, **validated_data)



class GroupMemberAddSerializer(serializers.Serializer):
    group_id = serializers.IntegerField()
    user_id = serializers.IntegerField()

    def validate(self, attrs):
        group = AccessGroup.objects.filter(id=attrs["group_id"]).first()
        if not group:
            raise serializers.ValidationError({"group_id": "Group not found."})

        user = User.objects.filter(id=attrs["user_id"]).first()
        if not user:
            raise serializers.ValidationError({"user_id": "User not found."})

        attrs["group"] = group
        attrs["user"] = user
        return attrs

    def create(self, validated_data):
        group = validated_data["group"]
        user = validated_data["user"]

        # prevent duplicates with clean message
        if GroupMember.objects.filter(group=group, user=user).exists():
            raise serializers.ValidationError("این کاربر قبلاً عضو این گروه شده است.")

        return GroupMember.objects.create(group=group, user=user)


class GroupMemberRemoveSerializer(serializers.Serializer):
    group_id = serializers.IntegerField()
    user_id = serializers.IntegerField()

    def validate(self, attrs):
        membership = GroupMember.objects.filter(
            group_id=attrs["group_id"],
            user_id=attrs["user_id"]
        ).first()

        if not membership:
            raise serializers.ValidationError("این کاربر عضو این گروه نیست یا قبلاً حذف شده است.")

        attrs["membership"] = membership
        return attrs


class AccessGroupListSerializer(serializers.ModelSerializer):
    created_by_username = serializers.CharField(source="created_by.username", read_only=True)
    members_count = serializers.IntegerField(read_only=True)

    class Meta:
        model = AccessGroup
        fields = ["id", "name", "access_level", "created_by_username", "created_at", "members_count"]



class GroupMemberListSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="user.username", read_only=True)
    role = serializers.CharField(source="user.role", read_only=True)

    class Meta:
        model = GroupMember
        fields = ["user_id", "username", "role", "joined_at"]




class AccessGroupUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AccessGroup
        fields = ["name", "access_level"]

    def validate_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("نام گروه نمی‌تواند خالی باشد.")
        return value
    


class UserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "role", "email", "date_joined", "last_login"]
        read_only_fields = ["id", "date_joined", "last_login"]




class UserMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "role", "date_joined", "last_login"]
        read_only_fields = ["id", "role", "date_joined", "last_login"]

    def validate_username(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError("username is required.")

        # Unique check (exclude current user)
        user = self.instance
        if User.objects.filter(username=value).exclude(id=user.id).exists():
            raise serializers.ValidationError("این نام کاربری قبلاً استفاده شده است.")
        return value
    

class AdminUserListSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "role", "email", "date_joined", "last_login"]