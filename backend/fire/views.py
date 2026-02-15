# fire/views.py
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


# -----------------------
# Catalog (for frontend menu)
# -----------------------
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


# -----------------------
# AOI (KML/DRAW -> GeoJSON polygon)
# -----------------------
class AOIViewSet(viewsets.ModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = AOI.objects.all().order_by("-id")
    serializer_class = AOISerializer

    def create(self, request, *args, **kwargs):
        """
        Expected:
        {
          "name": "optional",
          "source": "draw" | "kml",
          "geometry": { GeoJSON Polygon }
        }
        """
        name = request.data.get("name") or "AOI"
        source = request.data.get("source") or "draw"
        geom_geojson = request.data.get("geometry")

        if not geom_geojson:
            return Response({"error": "geometry is required (GeoJSON Polygon)."}, status=400)

        try:
            import json
            geom = GEOSGeometry(json.dumps(geom_geojson), srid=4326)
        except Exception as e:
            return Response({"error": "Invalid geometry.", "details": str(e)}, status=400)

        if geom.geom_type != "Polygon":
            return Response({"error": "Only Polygon is supported."}, status=400)

        obj = AOI.objects.create(name=name, source=source, geometry=geom)
        return Response(self.get_serializer(obj).data, status=status.HTTP_201_CREATED)


# -----------------------
# Vector Layers (GeoJSON)
# -----------------------
class IranProvinceViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IranProvince.objects.all().order_by("name")
    serializer_class = IranProvinceSerializer


class IranCountyViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IranCounty.objects.all().order_by("name")
    serializer_class = IranCountySerializer


class IranForestViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IranForest.objects.all().order_by("name")
    serializer_class = IranForestSerializer


class FireRiskAreaViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = FireRiskArea.objects.all().order_by("name")
    serializer_class = FireRiskAreaSerializer


# -----------------------
# Index layers (metadata list with filters)
# -----------------------
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

        d = self.request.query_params.get("date")
        if d:
            date_obj = parse_date(d)
            if date_obj:
                qs = qs.filter(date=date_obj)

        aoi_id = self.request.query_params.get("aoi_id")
        if aoi_id:
            try:
                aoi = AOI.objects.get(id=int(aoi_id))
                qs = qs.filter(geometry__intersects=aoi.geometry)
            except Exception:
                pass

        return qs


# -----------------------
# Satellite images (metadata list with filters)
# -----------------------
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

        aoi_id = self.request.query_params.get("aoi_id")
        if aoi_id:
            try:
                aoi = AOI.objects.get(id=int(aoi_id))
                qs = qs.filter(geometry__intersects=aoi.geometry)
            except Exception:
                pass

        return qs
