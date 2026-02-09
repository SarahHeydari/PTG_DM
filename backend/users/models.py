from django.db import models
from django.utils import timezone


class User(models.Model):
    class Role(models.TextChoices):
        MANAGER = "manager", "Manager"
        EXPERT = "expert", "Expert"

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(blank=True, null=True)
    password = models.CharField(max_length=128)  # demo
    role = models.CharField(max_length=20, choices=Role.choices)

    date_joined = models.DateTimeField(default=timezone.now)
    last_login = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = "users"
        indexes = [
            models.Index(fields=["username"]),
            models.Index(fields=["role"]),
        ]

    def __str__(self) -> str:
        return f"{self.username} ({self.role})"

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False


class AccessGroup(models.Model):
    class AccessLevel(models.TextChoices):
        READ = "read", "Read-only"
        WRITE = "write", "Read & Write"

    name = models.CharField(max_length=100, unique=True)
    access_level = models.CharField(max_length=10, choices=AccessLevel.choices)

    created_by = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        related_name="created_groups",
        limit_choices_to={"role": User.Role.MANAGER},
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "access_groups"
        indexes = [
            models.Index(fields=["name"]),
            models.Index(fields=["access_level"]),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.access_level})"


class GroupMember(models.Model):
    group = models.ForeignKey(AccessGroup, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="group_memberships")
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = "group_members"
        constraints = [
            models.UniqueConstraint(fields=["group", "user"], name="uq_group_user"),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} -> {self.group.name}"
