# fire/views.py
import json

from django.utils.dateparse import parse_date
from django.contrib.gis.geos import GEOSGeometry, Polygon

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
# Helpers
# -----------------------
def _parse_bbox(bbox_str: str):
    """
    bbox=minx,miny,maxx,maxy (EPSG:4326)
    returns Polygon(srid=4326) or None
    """
    try:
        parts = [float(x) for x in bbox_str.split(",")]
        if len(parts) != 4:
            return None
        minx, miny, maxx, maxy = parts
        if minx >= maxx or miny >= maxy:
            return None
        poly = Polygon.from_bbox((minx, miny, maxx, maxy))
        poly.srid = 4326
        return poly
    except Exception:
        return None


def _get_limit(request, default=1000, max_limit=5000):
    limit_str = request.query_params.get("limit")
    try:
        limit = int(limit_str) if limit_str else default
    except Exception:
        limit = default
    return max(1, min(limit, max_limit))


def _apply_spatial_filters(qs, request, geom_field="geometry"):
    """
    Applies:
      - bbox (if provided)
      - aoi_id (if provided)
    """
    bbox = request.query_params.get("bbox")
    if bbox:
        poly = _parse_bbox(bbox)
        if poly:
            qs = qs.filter(**{f"{geom_field}__intersects": poly})

    aoi_id = request.query_params.get("aoi_id")
    if aoi_id:
        try:
            aoi = AOI.objects.get(id=int(aoi_id))
            qs = qs.filter(**{f"{geom_field}__intersects": aoi.geometry})
        except Exception:
            pass

    return qs


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
            return Response({"detail": "geometry is required (GeoJSON Polygon)."}, status=400)

        try:
            geom = GEOSGeometry(json.dumps(geom_geojson), srid=4326)
        except Exception as e:
            return Response({"detail": "Invalid geometry.", "error": str(e)}, status=400)

        if geom.geom_type != "Polygon":
            return Response({"detail": "Only Polygon is supported."}, status=400)

        obj = AOI.objects.create(name=name, source=source, geometry=geom)
        return Response(self.get_serializer(obj).data, status=status.HTTP_201_CREATED)


# -----------------------
# Base for vector layers (bbox/limit/simplify + aoi_id)
# -----------------------
class BaseVectorViewSet(viewsets.ReadOnlyModelViewSet):
    """
    Supports:
      - ?bbox=minx,miny,maxx,maxy
      - ?aoi_id=ID
      - ?limit=1000
      - ?simplify=0.001   (degrees; optional demo)
    """
    DEFAULT_LIMIT = 1000
    MAX_LIMIT = 5000

    def get_queryset(self):
        qs = super().get_queryset()
        qs = _apply_spatial_filters(qs, self.request, geom_field="geometry")
        limit = _get_limit(self.request, default=self.DEFAULT_LIMIT, max_limit=self.MAX_LIMIT)
        return qs[:limit]

    def list(self, request, *args, **kwargs):
        simplify_str = request.query_params.get("simplify")
        tolerance = None
        try:
            if simplify_str:
                tolerance = float(simplify_str)
        except Exception:
            tolerance = None

        qs = self.get_queryset()
        objs = list(qs)

        if tolerance and tolerance > 0:
            for obj in objs:
                try:
                    obj.geometry = obj.geometry.simplify(tolerance, preserve_topology=True)
                except Exception:
                    pass

        serializer = self.get_serializer(objs, many=True)
        return Response(serializer.data)


# -----------------------
# Vector Layers (GeoJSON)
# -----------------------
class IranProvinceViewSet(BaseVectorViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IranProvince.objects.all().order_by("name")
    serializer_class = IranProvinceSerializer


class IranCountyViewSet(BaseVectorViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IranCounty.objects.all().order_by("name")
    serializer_class = IranCountySerializer


class IranForestViewSet(BaseVectorViewSet):
    authentication_classes = [JWTAuthentication]
    permission_classes = [IsAuthenticated]
    queryset = IranForest.objects.all().order_by("name")
    serializer_class = IranForestSerializer


class FireRiskAreaViewSet(BaseVectorViewSet):
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

        # optional exact date
        d = self.request.query_params.get("date")
        if d:
            date_obj = parse_date(d)
            if date_obj:
                qs = qs.filter(date=date_obj)

        # spatial filters only if geometry exists
        if self.request.query_params.get("aoi_id") or self.request.query_params.get("bbox"):
            qs = qs.filter(geometry__isnull=False)
            qs = _apply_spatial_filters(qs, self.request, geom_field="geometry")

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

        # spatial filters only if geometry exists
        if self.request.query_params.get("aoi_id") or self.request.query_params.get("bbox"):
            qs = qs.filter(geometry__isnull=False)
            qs = _apply_spatial_filters(qs, self.request, geom_field="geometry")

        return qs
