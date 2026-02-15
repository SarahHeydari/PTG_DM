from rest_framework.authentication import BaseAuthentication
from rest_framework import exceptions
from django.conf import settings
import jwt

from .models import User


class JWTAuthentication(BaseAuthentication):
    """
    Bearer <token>
    Token payload must include uid (or user_id)
    """

    def authenticate(self, request):
        auth = request.headers.get("Authorization", "")

        if not auth.startswith("Bearer "):
            return None  # No header => unauthenticated (permissions decide)

        token = auth.split(" ", 1)[1].strip()
        if not token:
            raise exceptions.AuthenticationFailed("Empty token")

        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[getattr(settings, "JWT_ALGORITHM", "HS256")],
            )
        except jwt.ExpiredSignatureError:
            raise exceptions.AuthenticationFailed("Token expired")
        except jwt.InvalidTokenError:
            raise exceptions.AuthenticationFailed("Invalid token")

        uid = payload.get("uid") or payload.get("user_id")
        if not uid:
            raise exceptions.AuthenticationFailed("Invalid payload")

        user = User.objects.filter(id=uid).first()
        if not user:
            raise exceptions.AuthenticationFailed("User not found")

        return (user, None)

    def authenticate_header(self, request):
        # باعث میشه DRF برای نداشتن توکن => 401 بده، نه 403
        return "Bearer"
