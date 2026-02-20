# fire/views.py
import json
import io
import os
import re
import uuid

from django.db import connection
from django.utils.dateparse import parse_datetime, parse_date
from django.contrib.gis.geos import GEOSGeometry

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .models import AOI, SatelliteImage, IndexLayer
from .utils.minio_manager import MinioManager


def feature_collection_from_sql(sql, params=None):
    params = params or []
    with connection.cursor() as cursor:
        cursor.execute(sql, params)
        rows = cursor.fetchall()

    features = []
    for props_json, geom_json in rows:
        props = json.loads(props_json)
        geom = json.loads(geom_json)
        features.append({
            "type": "Feature",
            "properties": props,
            "geometry": geom
        })

    return {"type": "FeatureCollection", "features": features}


def _slug(s: str) -> str:
    s = (s or "").strip().lower()
    s = re.sub(r"[^a-z0-9-]+", "-", s)
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s or "unknown"


def _safe_object_name(prefix: str, original_name: str) -> str:
    # keep extension if present
    _, ext = os.path.splitext(original_name or "")
    ext = (ext or "").lower()
    return f"{prefix}/{uuid.uuid4().hex}{ext}"


class CountiesGeoJSONAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        sql = """
        SELECT
          json_build_object('id', id, 'name', name)::text,
          ST_AsGeoJSON(geometry::geometry)::text
        FROM iran_counties;
        """
        return Response(feature_collection_from_sql(sql))


class ForestsGeoJSONAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        sql = """
        SELECT
          json_build_object('id', id, 'name', name)::text,
          ST_AsGeoJSON(geometry::geometry)::text
        FROM iran_forests;
        """
        return Response(feature_collection_from_sql(sql))


class FireRiskGeoJSONAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        sql = """
        SELECT
          json_build_object('id', id, 'name', name, 'level', level)::text,
          ST_AsGeoJSON(geometry::geometry)::text
        FROM fire_risk_areas;
        """
        return Response(feature_collection_from_sql(sql))


class AOIAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        qs = AOI.objects.all()
        results = []
        for obj in qs:
            results.append({
                "id": obj.id,
                "name": obj.name,
                "source": obj.source,
                "created_at": obj.created_at,
                "geometry": json.loads(obj.geometry.geojson)
            })
        return Response({"results": results})

    def post(self, request):
        name = request.data.get("name", "AOI")
        geometry = request.data.get("geometry")

        if not geometry:
            return Response({"detail": "geometry (GeoJSON Polygon) is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            geos = GEOSGeometry(json.dumps(geometry), srid=4326)
            if geos.geom_type != "Polygon":
                return Response({"detail": "Only Polygon geometry is allowed."},
                                status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"detail": f"Invalid geometry: {str(e)}"},
                            status=status.HTTP_400_BAD_REQUEST)

        obj = AOI.objects.create(name=name, source="draw", geometry=geos)

        return Response({
            "id": obj.id,
            "name": obj.name,
            "source": obj.source,
            "created_at": obj.created_at,
            "geometry": json.loads(obj.geometry.geojson)
        }, status=status.HTTP_201_CREATED)


class AOIDetailAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def delete(self, request, aoi_id):
        try:
            obj = AOI.objects.get(id=aoi_id)
        except AOI.DoesNotExist:
            return Response({"detail": "AOI not found."},
                            status=status.HTTP_404_NOT_FOUND)

        obj.delete()
        return Response({"detail": "deleted"})


class SatelliteImagesAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        satellite_name = request.GET.get("satellite_name")
        date_from = request.GET.get("date_from")
        date_to = request.GET.get("date_to")
        aoi_id = request.GET.get("aoi_id")

        qs = SatelliteImage.objects.all()

        if satellite_name:
            qs = qs.filter(satellite_name=satellite_name)

        if date_from:
            dt = parse_datetime(date_from) or parse_date(date_from)
            qs = qs.filter(date_time__gte=dt)

        if date_to:
            dt = parse_datetime(date_to) or parse_date(date_to)
            qs = qs.filter(date_time__lte=dt)

        if aoi_id:
            try:
                aoi = AOI.objects.get(id=aoi_id)
                qs = qs.filter(geometry__intersects=aoi.geometry)
            except AOI.DoesNotExist:
                pass

        qs = qs.order_by("-date_time")

        results = []
        for obj in qs:
            results.append({
                "id": obj.id,
                "satellite_name": obj.satellite_name,
                "date_time": obj.date_time,
                "image_name": obj.image_name,
                "minio_link": obj.minio_link,
            })

        return Response({"results": results})


class IndexLayersAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        index_name = request.GET.get("index_name")
        satellite_name = request.GET.get("satellite_name")
        date = request.GET.get("date")

        qs = IndexLayer.objects.all()

        if index_name:
            qs = qs.filter(index_name=index_name)

        if satellite_name:
            qs = qs.filter(satellite_name=satellite_name)

        if date:
            dt = parse_date(date)
            qs = qs.filter(date=dt)

        qs = qs.order_by("-date")

        results = []
        for obj in qs:
            results.append({
                "id": obj.id,
                "title": obj.title,
                "index_name": obj.index_name,
                "satellite_name": obj.satellite_name,
                "date": obj.date,
                "minio_link": obj.minio_link,
            })

        return Response({"results": results})


# ==========================================================
# NEW: Upload APIs (MinIO + DB only) — appended, no change to existing APIs
# ==========================================================

class UploadSatelliteImageAPIView(APIView):
    """
    Upload a satellite raster (GeoTIFF) to MinIO and save metadata to DB.

    multipart/form-data:
      - file: required
      - satellite_name: required
      - date_time: required (ISO datetime)
      - image_name: optional
      - geometry: optional GeoJSON Polygon (stringified JSON or dict)
    """
    parser_classes = (MultiPartParser, FormParser)
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        f = request.FILES.get("file")
        satellite_name = request.data.get("satellite_name")
        date_time = request.data.get("date_time")
        image_name = request.data.get("image_name") or (f.name if f else None)
        geometry = request.data.get("geometry")

        if not f:
            return Response({"detail": "file is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not satellite_name:
            return Response({"detail": "satellite_name is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not date_time:
            return Response({"detail": "date_time is required."}, status=status.HTTP_400_BAD_REQUEST)

        dt = parse_datetime(date_time)
        if not dt:
            return Response({"detail": "date_time is invalid. Use ISO datetime."},
                            status=status.HTTP_400_BAD_REQUEST)

        geos = None
        if geometry:
            try:
                if isinstance(geometry, str):
                    geometry_obj = json.loads(geometry)
                else:
                    geometry_obj = geometry
                geos = GEOSGeometry(json.dumps(geometry_obj), srid=4326)
                if geos.geom_type != "Polygon":
                    return Response({"detail": "Only Polygon geometry is allowed."},
                                    status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({"detail": f"Invalid geometry: {str(e)}"},
                                status=status.HTTP_400_BAD_REQUEST)

        mm = MinioManager()
        object_name = _safe_object_name("satellite", f.name)

        content = f.read()
        minio_url = mm.upload_satellite(
            satellite_name=satellite_name,
            file_name=object_name,
            content=content
        )

        bucket = f"sat-{_slug(satellite_name)}"

        obj = SatelliteImage.objects.create(
            satellite_name=satellite_name,
            date_time=dt,
            image_name=image_name,
            minio_link=minio_url,
            geometry=geos,
            minio_bucket=bucket,
            minio_object=object_name,
            status="minio_ok",
            is_published=False,
        )

        return Response({
            "id": obj.id,
            "satellite_name": obj.satellite_name,
            "date_time": obj.date_time,
            "image_name": obj.image_name,
            "minio_link": obj.minio_link,
            "minio_bucket": obj.minio_bucket,
            "minio_object": obj.minio_object,
            "status": obj.status,
            "is_published": obj.is_published,
        }, status=status.HTTP_201_CREATED)


class UploadIndexLayerAPIView(APIView):
    """
    Upload an index raster (GeoTIFF) to MinIO and save metadata to DB.

    multipart/form-data:
      - file: required
      - title: required
      - index_name: required (NDVI, NBR, ...)
      - date: required (YYYY-MM-DD)
      - satellite_name: required
      - geometry: optional GeoJSON Polygon (stringified JSON or dict)
    """
    parser_classes = (MultiPartParser, FormParser)
    authentication_classes = []
    permission_classes = [AllowAny]

    def post(self, request):
        f = request.FILES.get("file")
        title = request.data.get("title")
        index_name = request.data.get("index_name")
        date = request.data.get("date")
        satellite_name = request.data.get("satellite_name")
        geometry = request.data.get("geometry")

        if not f:
            return Response({"detail": "file is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not title:
            return Response({"detail": "title is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not index_name:
            return Response({"detail": "index_name is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not date:
            return Response({"detail": "date is required (YYYY-MM-DD)."}, status=status.HTTP_400_BAD_REQUEST)
        if not satellite_name:
            return Response({"detail": "satellite_name is required."}, status=status.HTTP_400_BAD_REQUEST)

        d = parse_date(date)
        if not d:
            return Response({"detail": "date is invalid. Use YYYY-MM-DD."},
                            status=status.HTTP_400_BAD_REQUEST)

        geos = None
        if geometry:
            try:
                if isinstance(geometry, str):
                    geometry_obj = json.loads(geometry)
                else:
                    geometry_obj = geometry
                geos = GEOSGeometry(json.dumps(geometry_obj), srid=4326)
                if geos.geom_type != "Polygon":
                    return Response({"detail": "Only Polygon geometry is allowed."},
                                    status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({"detail": f"Invalid geometry: {str(e)}"},
                                status=status.HTTP_400_BAD_REQUEST)

        mm = MinioManager()
        object_name = _safe_object_name("index", f.name)

        content = f.read()
        minio_url = mm.upload_index(
            index_name=index_name,
            file_name=object_name,
            content=content
        )

        bucket = f"idx-{_slug(index_name)}"

        obj = IndexLayer.objects.create(
            title=title,
            minio_link=minio_url,
            index_name=index_name,
            date=d,
            satellite_name=satellite_name,
            geometry=geos,
            minio_bucket=bucket,
            minio_object=object_name,
            status="minio_ok",
            is_published=False,
        )

        return Response({
            "id": obj.id,
            "title": obj.title,
            "index_name": obj.index_name,
            "satellite_name": obj.satellite_name,
            "date": obj.date,
            "minio_link": obj.minio_link,
            "minio_bucket": obj.minio_bucket,
            "minio_object": obj.minio_object,
            "status": obj.status,
            "is_published": obj.is_published,
        }, status=status.HTTP_201_CREATED)