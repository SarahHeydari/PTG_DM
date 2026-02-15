# fire/views.py
import json
from django.utils.dateparse import parse_date
from django.contrib.gis.geos import GEOSGeometry
from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated

from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import OrderingFilter

from users.authentication import JWTAuthentication

from .models import (
    IndexLayer, SatelliteImage,
    IranProvince, IranCounty, IranForest,
    AOI, FireRiskArea
)
from .serializers import (
    IndexLayerSerializer, SatelliteImageSerializer,
    IranProvinceSerializer, IranCountySerializer, IranForestSerializer,
    AOISerializer, FireRiskAreaSerializer
)


class FireCatalogAPIView(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]

    def get(self, request):
        data = {
            "vectors": [
                {"key": "provinces", "title": "مرز استان‌ها"},
                {"key": "counties", "title": "مرز شهرستان‌ها"},
                {"key": "forests", "title": "جنگل‌ها"},
                {"key": "fire_risk", "title": "مناطق مستعد آتش‌سوزی"},
            ],
            "indexes": [
                {"key": "ndvi", "title": "NDVI"},
                {"key": "nbr", "title": "NBR"},
                {"key": "ndmi", "title": "NDMI"},
            ],
            "satellites": [
                {"key": "sentinel2", "title": "Sentinel-2"},
                {"key": "landsat8", "title": "Landsat-8"},
            ],
        }
        return Response(data)


class AOIViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = AOI.objects.all().order_by("-id")
    serializer_class = AOISerializer

    def create(self, request, *args, **kwargs):
        name = request.data.get("name") or "AOI"
        source = request.data.get("source") or "draw"
        geom_geojson = request.data.get("geometry")

        if not geom_geojson:
            return Response({"detail": "geometry is required (GeoJSON Polygon)."}, status=400)

        try:
            geom = GEOSGeometry(json.dumps(geom_geojson), srid=4326)
        except Exception as e:
            return Response({"detail": "Invalid geometry.", "error": str(e)}, status=400)

        if geom.geom_type != "Polygon":
            return Response({"detail": "Only Polygon is supported."}, status=400)

        obj = AOI.objects.create(name=name, source=source, geometry=geom)
        serializer = self.get_serializer(obj)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


def _apply_aoi_filter(qs, request):
    aoi_id = request.query_params.get("aoi_id")
    if not aoi_id:
        return qs
    try:
        aoi = AOI.objects.get(id=int(aoi_id))
        return qs.filter(geometry__intersects=aoi.geometry)
    except Exception:
        return qs


class IranProvinceViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IranProvince.objects.all().order_by("name")
    serializer_class = IranProvinceSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_aoi_filter(qs, self.request)


class IranCountyViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IranCounty.objects.all().order_by("name")
    serializer_class = IranCountySerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_aoi_filter(qs, self.request)


class IranForestViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IranForest.objects.all().order_by("name")
    serializer_class = IranForestSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_aoi_filter(qs, self.request)


class FireRiskAreaViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = FireRiskArea.objects.all().order_by("name")
    serializer_class = FireRiskAreaSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        return _apply_aoi_filter(qs, self.request)


class IndexLayerViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IndexLayer.objects.all().order_by("-date", "-id")
    serializer_class = IndexLayerSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["index_name", "satellite_name"]
    ordering_fields = ["date", "id"]

    def get_queryset(self):
        qs = super().get_queryset()

        # optional date filter
        d = self.request.query_params.get("date")
        if d:
            date_obj = parse_date(d)
            if date_obj:
                qs = qs.filter(date=date_obj)

        # important: only items with geometry can be spatially filtered
        if self.request.query_params.get("aoi_id"):
            qs = qs.filter(geometry__isnull=False)
            qs = _apply_aoi_filter(qs, self.request)

        return qs


class SatelliteImageViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = SatelliteImage.objects.all().order_by("-date_time", "-id")
    serializer_class = SatelliteImageSerializer
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["satellite_name"]
    ordering_fields = ["date_time", "id"]

    def get_queryset(self):
        qs = super().get_queryset()

        date_from = self.request.query_params.get("date_from")
        date_to = self.request.query_params.get("date_to")

        if date_from:
            df = parse_date(date_from)
            if df:
                qs = qs.filter(date_time__date__gte=df)

        if date_to:
            dt = parse_date(date_to)
            if dt:
                qs = qs.filter(date_time__date__lte=dt)

        if self.request.query_params.get("aoi_id"):
            qs = qs.filter(geometry__isnull=False)
            qs = _apply_aoi_filter(qs, self.request)

        return qs
