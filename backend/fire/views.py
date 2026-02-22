# fire/views.py
import json
import os
import re
import uuid
import base64
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET

from django.db import connection
from django.utils.dateparse import parse_datetime, parse_date
from django.contrib.gis.geos import GEOSGeometry
from django.conf import settings

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from rest_framework.parsers import MultiPartParser, FormParser

from .models import AOI, SatelliteImage, IndexLayer
from .utils.minio_manager import MinioManager
from .utils.geoserver import GeoServerManager


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
    _, ext = os.path.splitext(original_name or "")
    ext = (ext or "").lower()
    return f"{prefix}/{uuid.uuid4().hex}{ext}"


def _geoserver_cfg():
    """
    Internal base is used ONLY for server-to-server (web->geoserver) calls.
    If someone mistakenly sets INTERNAL to localhost, fix it automatically.
    """
    base_url_internal = getattr(settings, "GEOSERVER_BASE_URL_INTERNAL", None)

    # اگر internal اشتباهی localhost بود، داخل کانتینر جواب نمی‌دهد
    if base_url_internal and ("localhost" in base_url_internal or "127.0.0.1" in base_url_internal):
        base_url_internal = None

    # fallback صحیح داخل شبکه docker
    base_url_internal = base_url_internal or "http://geoserver:8080/geoserver"

    user = getattr(settings, "GEOSERVER_ADMIN_USER", None) or "admin"
    pwd = getattr(settings, "GEOSERVER_ADMIN_PASSWORD", None) or "geoserver"
    ws = getattr(settings, "GEOSERVER_WORKSPACE", "fire") or "fire"
    return base_url_internal, user, pwd, ws


def _geoserver_public_base():
    """
    Public base is used for URLs that the browser must reach (host->geoserver mapped port).
    """
    return (
        getattr(settings, "GEOSERVER_BASE_URL_PUBLIC", None)
        or getattr(settings, "GEOSERVER_BASE_URL", None)
        or "http://localhost:8084/geoserver"
    )


def _minio_internal_url(bucket: str, object_name: str) -> str:
    host = getattr(settings, "MINIO_INTERNAL_HOST", "minio")
    port = getattr(settings, "MINIO_INTERNAL_PORT", "9000")
    return f"http://{host}:{port}/{bucket}/{object_name}"


# =========================
# GeoJSON APIs (unchanged)
# =========================

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
                "geoserver_layer": getattr(obj, "geoserver_layer", None),
                "wms_url": getattr(obj, "wms_url", None),
                "wmts_url": getattr(obj, "wmts_url", None),
                "is_published": obj.is_published,
                "status": obj.status,
                "error_message": getattr(obj, "error_message", None),
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
                "geoserver_layer": getattr(obj, "geoserver_layer", None),
                "wms_url": getattr(obj, "wms_url", None),
                "wmts_url": getattr(obj, "wmts_url", None),
                "is_published": obj.is_published,
                "status": obj.status,
                "error_message": getattr(obj, "error_message", None),
            })

        return Response({"results": results})


# ==========================================================
# Upload APIs (MinIO + DB + GeoServer publish)
# ==========================================================

class UploadSatelliteImageAPIView(APIView):
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
                geometry_obj = json.loads(geometry) if isinstance(geometry, str) else geometry
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
        minio_url_public = mm.upload_satellite(
            satellite_name=satellite_name,
            file_name=object_name,
            content=content
        )

        bucket = f"sat-{_slug(satellite_name)}"

        obj = SatelliteImage.objects.create(
            satellite_name=satellite_name,
            date_time=dt,
            image_name=image_name,
            minio_link=minio_url_public,
            geometry=geos,
            minio_bucket=bucket,
            minio_object=object_name,
            status="minio_ok",
            is_published=False,
        )

        try:
            base_url_internal, user, pwd, ws = _geoserver_cfg()
            if not base_url_internal or not user or not pwd:
                raise Exception("GeoServer settings missing (GEOSERVER_BASE_URL_INTERNAL / GEOSERVER_ADMIN_USER / GEOSERVER_ADMIN_PASSWORD).")

            gs = GeoServerManager(base_url=base_url_internal, username=user, password=pwd, workspace=ws)

            minio_url_internal = _minio_internal_url(bucket=bucket, object_name=object_name)

            store_name = f"sat_{_slug(satellite_name)}_{obj.id}"
            layer_name = f"sat_{_slug(satellite_name)}_{obj.id}"

            gs.publish_geotiff_from_minio(
                minio_internal_url=minio_url_internal,
                store_name=store_name,
                layer_name=layer_name,
            )

            public_base = _geoserver_public_base()

            obj.geoserver_workspace = ws
            obj.geoserver_store = store_name
            obj.geoserver_layer = f"{ws}:{layer_name}"
            obj.wms_url = f"{public_base}/wms"
            obj.wmts_url = f"{public_base}/gwc/service/wmts"
            obj.status = "published"
            obj.is_published = True
            obj.error_message = None
            obj.save(update_fields=[
                "geoserver_workspace", "geoserver_store", "geoserver_layer",
                "wms_url", "wmts_url", "status", "is_published", "error_message"
            ])

        except Exception as e:
            obj.status = "publish_failed"
            obj.error_message = str(e)
            obj.save(update_fields=["status", "error_message"])

            return Response({
                "detail": "publish_failed",
                "stage": "geoserver",
                "error": str(e),
                "id": obj.id,
                "minio_link": obj.minio_link,
                "minio_bucket": obj.minio_bucket,
                "minio_object": obj.minio_object,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            "geoserver_layer": obj.geoserver_layer,
            "wms_url": obj.wms_url,
            "wmts_url": obj.wmts_url,
        }, status=status.HTTP_201_CREATED)


class UploadIndexLayerAPIView(APIView):
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
                geometry_obj = json.loads(geometry) if isinstance(geometry, str) else geometry
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
        minio_url_public = mm.upload_index(
            index_name=index_name,
            file_name=object_name,
            content=content
        )

        bucket = f"idx-{_slug(index_name)}"

        obj = IndexLayer.objects.create(
            title=title,
            minio_link=minio_url_public,
            index_name=index_name,
            date=d,
            satellite_name=satellite_name,
            geometry=geos,
            minio_bucket=bucket,
            minio_object=object_name,
            status="minio_ok",
            is_published=False,
        )

        try:
            base_url_internal, user, pwd, ws = _geoserver_cfg()
            if not base_url_internal or not user or not pwd:
                raise Exception("GeoServer settings missing (GEOSERVER_BASE_URL_INTERNAL / GEOSERVER_ADMIN_USER / GEOSERVER_ADMIN_PASSWORD).")

            gs = GeoServerManager(base_url=base_url_internal, username=user, password=pwd, workspace=ws)

            minio_url_internal = _minio_internal_url(bucket=bucket, object_name=object_name)

            store_name = f"idx_{_slug(index_name)}_{obj.id}"
            layer_name = f"idx_{_slug(index_name)}_{obj.id}"

            gs.publish_geotiff_from_minio(
                minio_internal_url=minio_url_internal,
                store_name=store_name,
                layer_name=layer_name,
            )

            public_base = _geoserver_public_base()

            obj.geoserver_workspace = ws
            obj.geoserver_store = store_name
            obj.geoserver_layer = f"{ws}:{layer_name}"
            obj.wms_url = f"{public_base}/wms"
            obj.wmts_url = f"{public_base}/gwc/service/wmts"
            obj.status = "published"
            obj.is_published = True
            obj.error_message = None
            obj.save(update_fields=[
                "geoserver_workspace", "geoserver_store", "geoserver_layer",
                "wms_url", "wmts_url", "status", "is_published", "error_message"
            ])

        except Exception as e:
            obj.status = "publish_failed"
            obj.error_message = str(e)
            obj.save(update_fields=["status", "error_message"])

            return Response({
                "detail": "publish_failed",
                "stage": "geoserver",
                "error": str(e),
                "id": obj.id,
                "minio_link": obj.minio_link,
                "minio_bucket": obj.minio_bucket,
                "minio_object": obj.minio_object,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

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
            "geoserver_layer": obj.geoserver_layer,
            "wms_url": obj.wms_url,
            "wmts_url": obj.wmts_url,
        }, status=status.HTTP_201_CREATED)

# ==========================================================
# Style Legend API (Data-driven from GeoServer SLD)
# GET /api/fire/styles/<style_name>/legend/
# ==========================================================
def _dedupe_colormap(colormap):
    out = []
    seen = set()

    for item in colormap or []:
        key = (
            item.get("quantity"),
            (item.get("color") or "").lower(),
            item.get("opacity"),
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(item)

    return out


def _http_get(url: str, username: str, password: str, timeout: int = 10) -> bytes:
    token = base64.b64encode(f"{username}:{password}".encode("utf-8")).decode("ascii")
    req = urllib.request.Request(url, headers={"Authorization": f"Basic {token}"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()


def _parse_sld_colormap(sld_xml: bytes):
    try:
        root = ET.fromstring(sld_xml)
    except Exception:
        return None, "Invalid SLD XML"

    entries = []
    for el in root.iter():
        if el.tag.lower().endswith("colormapentry"):
            q = el.attrib.get("quantity")
            color = el.attrib.get("color")
            label = el.attrib.get("label")
            opacity = el.attrib.get("opacity")
            entries.append({
                "quantity": float(q) if q not in (None, "") else None,
                "color": color,
                "label": label,
                "opacity": float(opacity) if opacity not in (None, "") else None,
            })

    if not entries:
        return [], None

    sortable = [e for e in entries if e["quantity"] is not None]
    nonsort = [e for e in entries if e["quantity"] is None]
    sortable.sort(key=lambda x: x["quantity"])

    merged = sortable + nonsort
    merged = _dedupe_colormap(merged)

    return merged, None


class StyleLegendAPIView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request, style_name: str):
        style_name = (style_name or "").strip()
        if not style_name:
            return Response({"detail": "style_name is required."}, status=status.HTTP_400_BAD_REQUEST)

        base_url_internal, user, pwd, ws = _geoserver_cfg()

        sld_url = f"{base_url_internal}/rest/workspaces/{ws}/styles/{style_name}.sld"

        try:
            sld_xml = _http_get(sld_url, user, pwd)
        except urllib.error.HTTPError as e:
            return Response({
                "detail": "Failed to fetch SLD from GeoServer.",
                "status_code": e.code,
                "error": str(e),
                "url": sld_url,
            }, status=status.HTTP_502_BAD_GATEWAY)
        except Exception as e:
            return Response({
                "detail": "Failed to fetch SLD from GeoServer.",
                "error": str(e),
                "url": sld_url,
            }, status=status.HTTP_502_BAD_GATEWAY)

        entries, err = _parse_sld_colormap(sld_xml)
        if err:
            return Response({
                "detail": "Failed to parse SLD.",
                "error": err,
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # extra safety dedupe
        entries = _dedupe_colormap(entries)

        return Response({
            "workspace": ws,
            "style": style_name,
            "source": "geoserver_sld",
            "colormap": entries,
        })