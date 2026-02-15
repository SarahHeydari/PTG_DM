# fire/serializers.py
from rest_framework_gis.serializers import GeoFeatureModelSerializer
from .models import (
    IndexLayer, SatelliteImage,
    IranProvince, IranCounty, IranForest,
    AOI, FireRiskArea
)


class IranProvinceSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = IranProvince
        geo_field = "geometry"
        fields = ("id", "name")


class IranCountySerializer(GeoFeatureModelSerializer):
    class Meta:
        model = IranCounty
        geo_field = "geometry"
        fields = ("id", "name")


class IranForestSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = IranForest
        geo_field = "geometry"
        fields = ("id", "name")


class FireRiskAreaSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = FireRiskArea
        geo_field = "geometry"
        fields = ("id", "name", "level")


class AOISerializer(GeoFeatureModelSerializer):
    class Meta:
        model = AOI
        geo_field = "geometry"
        fields = ("id", "name", "source", "created_at")


class IndexLayerSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = IndexLayer
        geo_field = "geometry"
        fields = ("id", "title", "minio_link", "index_name", "date", "satellite_name", "created_at")


class SatelliteImageSerializer(GeoFeatureModelSerializer):
    class Meta:
        model = SatelliteImage
        geo_field = "geometry"
        fields = ("id", "satellite_name", "date_time", "image_name", "minio_link", "created_at")
