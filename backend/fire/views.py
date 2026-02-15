from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from users.authentication import CustomJWTAuthentication
from .models import IndexLayer, SatelliteImage, IranProvince, IranCounty, IranForest
from .serializers import (
    IndexLayerSerializer, SatelliteImageSerializer,
    IranProvinceSerializer, IranCountySerializer, IranForestSerializer
)


class IndexLayerViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IndexLayer.objects.all().order_by("-date", "-id")
    serializer_class = IndexLayerSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["index_name", "satellite_name"]
    ordering_fields = ["date", "id"]


class SatelliteImageViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = SatelliteImage.objects.all().order_by("-date_time", "-id")
    serializer_class = SatelliteImageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["satellite_name"]
    ordering_fields = ["date_time", "id"]


class IranProvinceViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IranProvince.objects.all().order_by("name")
    serializer_class = IranProvinceSerializer


class IranCountyViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IranCounty.objects.all().order_by("name")
    serializer_class = IranCountySerializer


class IranForestViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [CustomJWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IranForest.objects.all().order_by("name")
    serializer_class = IranForestSerializer
