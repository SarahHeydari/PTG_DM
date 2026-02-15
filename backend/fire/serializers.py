from rest_framework import serializers
from .models import IndexLayer, SatelliteImage, IranProvince, IranCounty, IranForest


class IndexLayerSerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()

    class Meta:
        model = IndexLayer
        fields = ["id", "title", "minio_link", "index_name", "date", "geometry", "satellite_name"]

    def get_geometry(self, obj):
        # خروجی GeoJSON-like برای Leaflet
        if not obj.geometry:
            return None
        return obj.geometry.geojson


class SatelliteImageSerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()

    class Meta:
        model = SatelliteImage
        fields = ["id", "satellite_name", "date_time", "image_name", "minio_link", "geometry"]

    def get_geometry(self, obj):
        if not obj.geometry:
            return None
        return obj.geometry.geojson


class IranProvinceSerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()

    class Meta:
        model = IranProvince
        fields = ["id", "name", "geometry"]

    def get_geometry(self, obj):
        return obj.geometry.geojson if obj.geometry else None


class IranCountySerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()

    class Meta:
        model = IranCounty
        fields = ["id", "name", "geometry"]

    def get_geometry(self, obj):
        return obj.geometry.geojson if obj.geometry else None


class IranForestSerializer(serializers.ModelSerializer):
    geometry = serializers.SerializerMethodField()

    class Meta:
        model = IranForest
        fields = ["id", "name", "geometry"]

    def get_geometry(self, obj):
        return obj.geometry.geojson if obj.geometry else None
