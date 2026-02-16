# users/jwt_utils.py
from datetime import timedelta
from django.conf import settings
from django.utils import timezone
import jwt


def create_access_token(user) -> str:
    now = timezone.now()
    payload = {
        "uid": user.id,
        "role": user.role,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=settings.JWT_ACCESS_TTL_MINUTES)).timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
