# fire/api_views.py
import json
from django.db import connection
from django.utils.dateparse import parse_datetime, parse_date
from django.contrib.gis.geos import GEOSGeometry

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status

from .models import AOI, SatelliteImage, IndexLayer


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
